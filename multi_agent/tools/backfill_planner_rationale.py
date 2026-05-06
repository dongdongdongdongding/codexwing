#!/usr/bin/env python3
"""Backfill planner gate-rationale columns onto market_scan_results rows.

Why this exists
---------------
swing-main-h4x: market_scan_results historically lacked physical columns for
market_gate, scanner_timeframe_profile, kr_universe_role, selection_lane,
rationale, theme_risk. SCAN_RESULT_COLUMNS mapped three of them but
_filter_payload_to_existing_columns silently dropped the values because the
columns did not exist. rationale and theme_risk were never even mapped.

After the migration in add_columns.sql adds the columns, all rows persisted
before this point have NULL gate-rationale. Local planner_handoff.json
artifacts in runtime_state/shared_working/RUN-* still hold the truth for
recent runs — this script lifts those values into the DB so DB-only
priority_watchlist_gap reports can name the gate cause.

What this does
--------------
1. Iterate RUN-* directories in runtime_state/shared_working/
2. For each planner_handoff.json, read decisions[] entries with rationale,
   theme_risk, selection_lane (and pull market_gate / scanner_timeframe_profile
   / kr_universe_role from realized_outcomes.json next to it when present).
3. Build an index keyed by (ticker, recommended_at YYYY-MM-DD) → fields.
4. For each key, look up matching market_scan_results rows where the target
   column is NULL, and UPDATE only the missing fields. Never overwrite
   non-NULL values.
5. Print a summary: artifacts_seen, rows_updated_per_column, dry_run flag.

Safety
------
- No leakage: gate-rationale fields are inference-time metadata, not future
  outcomes. They were already attached to the same recommended_at when the
  planner ran.
- Idempotent: only writes a column when its current value is NULL.
- Dry-run by default with --apply to actually write.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TARGET_COLUMNS = (
    "rationale",
    "theme_risk",
    "selection_lane",
    "market_gate",
    "scanner_timeframe_profile",
    "kr_universe_role",
)


def _load_local_env() -> None:
    for candidate in (Path(".env.local"), Path(".env")):
        if not candidate.exists():
            continue
        try:
            for raw_line in candidate.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = value
        except Exception:
            continue


def _norm_date(value: Any) -> Optional[str]:
    if not value:
        return None
    try:
        s = str(value)
        # ISO timestamps with timezone — take the date portion
        if "T" in s:
            return s.split("T", 1)[0]
        if " " in s:
            return s.split(" ", 1)[0]
        return s[:10]
    except Exception:
        return None


def _norm_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else None
    if isinstance(value, (list, tuple)):
        cleaned = [str(v).strip() for v in value if v is not None and str(v).strip()]
        return cleaned or None
    return None


def _norm_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _load_decision_index(handoff_path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Read planner_handoff.json + sibling realized_outcomes.json and
    yield {(ticker, date): {column: value, ...}}.
    """
    try:
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    produced_at = _norm_date(handoff.get("produced_at"))
    decisions = handoff.get("decisions") or []

    realized_path = handoff_path.parent / "realized_outcomes.json"
    realized_by_ticker: Dict[str, Dict[str, Any]] = {}
    realized_date: Optional[str] = None
    if realized_path.exists():
        try:
            realized = json.loads(realized_path.read_text(encoding="utf-8"))
            rows = realized.get("rows") if isinstance(realized, dict) else realized
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    t = str(row.get("ticker") or "").strip()
                    if not t:
                        continue
                    realized_by_ticker[t] = row
                    if realized_date is None:
                        realized_date = _norm_date(row.get("recommended_at"))
        except Exception:
            pass

    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for dec in decisions:
        if not isinstance(dec, dict):
            continue
        ticker = str(dec.get("ticker") or "").strip()
        if not ticker:
            continue
        # Prefer realized_outcomes recommended_at (this is what landed in DB),
        # fall back to handoff.produced_at.
        rrow = realized_by_ticker.get(ticker, {})
        date = _norm_date(rrow.get("recommended_at")) or realized_date or produced_at
        if not date:
            continue

        fields: Dict[str, Any] = {}
        rationale = _norm_list(dec.get("rationale"))
        theme_risk = _norm_list(dec.get("theme_risk"))
        if rationale:
            fields["rationale"] = rationale
        if theme_risk:
            fields["theme_risk"] = theme_risk

        # selection_lane / market_gate / scanner_timeframe_profile / kr_universe_role
        # are not all on the planner decision object — pull from realized row when
        # present (legacy_orchestration._build_realized_outcomes_placeholder copies
        # them from PlannerDecision attrs that the JSON dump may not surface).
        for col in ("selection_lane", "market_gate", "scanner_timeframe_profile", "kr_universe_role"):
            v = _norm_str(dec.get(col))
            if v is None:
                v = _norm_str(rrow.get(col))
            if v:
                fields[col] = v

        if not fields:
            continue
        out[(ticker, date)] = fields
    return out


def _column_filter(client, run_limit: Optional[int] = None) -> set:
    """Probe market_scan_results to confirm target columns exist."""
    available = set()
    for col in TARGET_COLUMNS:
        try:
            client.table("market_scan_results").select(col).limit(1).execute()
            available.add(col)
        except Exception:
            pass
    return available


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-working", type=str, default="runtime_state/shared_working")
    parser.add_argument("--apply", action="store_true", help="Actually write updates (default: dry-run)")
    parser.add_argument("--limit-runs", type=int, default=None, help="Process at most N RUN dirs (newest first)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    _load_local_env()

    import warnings
    warnings.filterwarnings("ignore")
    from modules.db_manager import DBManager

    dm = DBManager()
    if not dm.client:
        print("Supabase client unavailable; aborting.", file=sys.stderr)
        return 2

    available = _column_filter(dm.client)
    missing = set(TARGET_COLUMNS) - available
    if missing:
        print(f"⚠️ target columns missing in DB (run add_columns.sql first): {sorted(missing)}", file=sys.stderr)
        if not available:
            return 2

    base = PROJECT_ROOT.parent / args.shared_working if not Path(args.shared_working).is_absolute() else Path(args.shared_working)
    if not base.exists():
        # Fallback: caller invoked from repo root
        base = Path(args.shared_working)
    if not base.exists():
        print(f"shared_working dir not found: {base}", file=sys.stderr)
        return 2

    run_dirs = sorted(
        [p for p in base.iterdir() if p.is_dir() and p.name.startswith("RUN-")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if args.limit_runs:
        run_dirs = run_dirs[: args.limit_runs]

    aggregate: Dict[Tuple[str, str], Dict[str, Any]] = {}
    artifacts_seen = 0
    for d in run_dirs:
        handoff = d / "planner_handoff.json"
        if not handoff.exists():
            continue
        artifacts_seen += 1
        idx = _load_decision_index(handoff)
        # Older runs win only if newer one didn't supply the column.
        for key, fields in idx.items():
            if key not in aggregate:
                aggregate[key] = dict(fields)
            else:
                for col, v in fields.items():
                    aggregate[key].setdefault(col, v)

    print(f"artifacts_seen={artifacts_seen} keys_indexed={len(aggregate)}")

    updates_per_col: Dict[str, int] = defaultdict(int)
    rows_updated = 0
    rows_examined = 0
    rows_no_target = 0
    rows_already_filled = 0

    for (ticker, date), fields in aggregate.items():
        active_fields = {k: v for k, v in fields.items() if k in available}
        if not active_fields:
            continue
        select_cols = "id," + ",".join(active_fields.keys())
        try:
            day_start = f"{date}T00:00:00"
            day_end = f"{date}T23:59:59.999"
            res = (
                dm.client.table("market_scan_results")
                .select(select_cols)
                .eq("ticker", ticker)
                .gte("recommended_at", day_start)
                .lte("recommended_at", day_end)
                .execute()
            )
        except Exception as e:
            if args.verbose:
                print(f"  query_err {ticker} {date}: {str(e)[:120]}")
            continue
        rows = res.data or []
        if not rows:
            rows_no_target += 1
            continue
        for row in rows:
            rows_examined += 1
            patch: Dict[str, Any] = {}
            for col, value in active_fields.items():
                if row.get(col) in (None, "", []):
                    patch[col] = value
            if not patch:
                rows_already_filled += 1
                continue
            for col in patch:
                updates_per_col[col] += 1
            if args.apply:
                try:
                    dm.client.table("market_scan_results").update(patch).eq("id", row["id"]).execute()
                    rows_updated += 1
                except Exception as e:
                    if args.verbose:
                        print(f"  update_err {ticker} {date} id={row.get('id')}: {str(e)[:120]}")
            else:
                rows_updated += 1
                if args.verbose:
                    print(f"  DRY {ticker} {date} id={row.get('id')} patch_cols={list(patch.keys())}")

    summary = {
        "mode": "apply" if args.apply else "dry-run",
        "artifacts_seen": artifacts_seen,
        "keys_indexed": len(aggregate),
        "rows_examined": rows_examined,
        "rows_updated": rows_updated,
        "rows_no_match": rows_no_target,
        "rows_already_filled": rows_already_filled,
        "updates_per_col": dict(updates_per_col),
        "available_columns": sorted(available),
        "missing_columns": sorted(missing),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
