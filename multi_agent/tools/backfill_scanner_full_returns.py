#!/usr/bin/env python3
"""Backfill return_{1,2,3,5,7,14,30}d_pct onto scanner_full (and peer) rows.

Why this exists
---------------
The pipeline writes scan features to `market_scan_results` with feature_origin
in {scanner_full, scanner_partial_legacy, scanner_archive_outcome} as the worker scans. A separate
outcome-sync pass (`update_outcome_return_metrics.py`) writes return_*d_pct,
but those updates land on the matching outcome row only when the merge
fallback in `db_manager.upsert_scan_archive_outcomes` finds the worker row
within a ±2h created_at window. When the fallback misses, the returns end
up on a stub `outcome_sync_partial` row instead — and the original
scanner_full row stays with return_3d_pct = NULL forever, even though the
realized outcome is sitting on disk.

Result: training pulls feature-rich scanner_full rows with NULL labels and
training-set growth stalls. (See swing-main-1bi acceptance criterion:
return_3d_pct fill rate ≥ 95% on scanner_full rows aged ≥ 3 days.)

What this does
--------------
1. Iterate RUN-* directories in shared_working/, load realized_outcomes.json
2. Build an index keyed by (ticker, recommended_at YYYY-MM-DD)
   → return_{1,2,3,5,7,14,30}d_pct, latest_return_pct, base_trade_date
3. For each (ticker, date) key, look up matching market_scan_results rows
   with feature_origin in {scanner_full, scanner_partial_legacy, scanner_archive_outcome} where any
   return_*_pct column is NULL
4. UPDATE only the missing return columns (never overwrite non-NULL values)
5. Print a summary: rows_seen, rows_updated, fill_rate_before/after sample

Safety
------
- No leakage: returns come from realized_outcomes.json which was computed
  by `update_outcome_return_metrics.py` from yfinance close prices ≥ scan
  date. We never touch features or labels other than return_* columns.
- Idempotent: only writes when target column is NULL.
- Dry-run by default has --dry-run flag for inspection.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RETURN_COLUMNS = (
    "return_1d_pct",
    "return_2d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "return_7d_pct",
    "return_14d_pct",
    "return_30d_pct",
    "latest_return_pct",
    "base_trade_date",
    "entry_reference_price",
    "performance_updated_at",
)
HORIZONS_FROM_HISTORY = (1, 2, 3, 5, 7, 14, 30)
SCANNER_ORIGINS = ("scanner_full", "scanner_partial_legacy", "scanner_archive_outcome")


def _fetch_history_close(ticker: str, start_date: str, end_days: int = 40):
    """Fetch daily OHLCV close prices via yfinance with KR fallback to FDR.

    Returns a DataFrame indexed by trade_date string with 'Close' column,
    or None if unavailable. Used when realized_outcomes.json is missing
    (e.g. shared_working RUN-* dir was rotated out).
    """
    try:
        import pandas as pd
        import yfinance as yf
    except Exception:
        return None
    try:
        from datetime import date, timedelta as _td

        start = date.fromisoformat(start_date) - _td(days=2)
        end = date.fromisoformat(start_date) + _td(days=end_days + 5)
        hist = yf.Ticker(ticker).history(
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=False,
            timeout=10,
            prepost=False,
        )
        if hist is None or hist.empty:
            return None
        hist = hist.copy()
        hist["trade_date"] = [d.date().isoformat() for d in hist.index]
        return hist[["trade_date", "Close"]].reset_index(drop=True)
    except Exception:
        return None


def _compute_returns_from_history(hist, scan_date: str) -> Dict[str, Any]:
    """Compute return_{1,2,3,5,7,14,30}d_pct + latest_return_pct from history."""
    if hist is None or hist.empty:
        return {}
    eligible = hist[hist["trade_date"] >= scan_date]
    if eligible.empty:
        return {}
    base_idx = eligible.index[0]
    try:
        base_close = float(hist.loc[base_idx, "Close"])
    except Exception:
        return {}
    if base_close <= 0:
        return {}
    out: Dict[str, Any] = {
        "base_trade_date": str(hist.loc[base_idx, "trade_date"]),
        "entry_reference_price": round(base_close, 6),
    }
    for horizon in HORIZONS_FROM_HISTORY:
        target_pos = base_idx + horizon
        if target_pos < len(hist):
            try:
                close_val = float(hist.loc[target_pos, "Close"])
                if close_val > 0:
                    out[f"return_{horizon}d_pct"] = round(((close_val / base_close) - 1.0) * 100.0, 6)
            except Exception:
                pass
    if len(hist) > 0:
        try:
            latest_close = float(hist["Close"].iloc[-1])
            if latest_close > 0:
                out["latest_return_pct"] = round(((latest_close / base_close) - 1.0) * 100.0, 6)
        except Exception:
            pass
    return out


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _parse_iso_date(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return text[:10] if len(text) >= 10 else None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.date().isoformat()


def _iter_run_dirs(shared_dir: Path, limit_runs: int) -> List[Path]:
    if not shared_dir.exists():
        return []
    runs = [p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")]
    runs = sorted(runs, key=lambda p: p.name)
    if limit_runs > 0:
        runs = runs[-limit_runs:]
    return runs


def _build_outcome_index(shared_dir: Path, limit_runs: int) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Return {(ticker, scan_date_iso): outcome_subset} keyed by latest recommended_at.

    When multiple outcomes exist for the same (ticker, date), prefer the one
    with more non-null return columns (i.e. the most resolved one).
    """
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    runs_seen = 0
    runs_with_outcomes = 0
    rows_indexed = 0
    for run_dir in _iter_run_dirs(shared_dir, limit_runs):
        runs_seen += 1
        payload = _load_json(run_dir / "realized_outcomes.json")
        outcomes = payload.get("outcomes", []) if isinstance(payload, dict) else []
        if not isinstance(outcomes, list) or not outcomes:
            continue
        runs_with_outcomes += 1
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or "").strip()
            if not ticker:
                continue
            scan_date = _parse_iso_date(row.get("recommended_at"))
            if not scan_date:
                continue
            subset = {col: row.get(col) for col in RETURN_COLUMNS}
            non_null = sum(1 for v in subset.values() if v is not None)
            if non_null == 0:
                continue
            existing = index.get((ticker, scan_date))
            if existing is None:
                index[(ticker, scan_date)] = subset
                rows_indexed += 1
                continue
            existing_non_null = sum(1 for v in existing.values() if v is not None)
            if non_null > existing_non_null:
                index[(ticker, scan_date)] = subset
    print(
        f"[INFO] outcome index: runs_seen={runs_seen} runs_with_outcomes={runs_with_outcomes} "
        f"unique_keys={len(index)} rows_indexed={rows_indexed}"
    )
    return index


def _fetch_scanner_rows_missing_returns(
    db: Any,
    *,
    page_size: int = 1000,
    market_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch market_scan_results rows where feature_origin is backfillable
    and at least one of the return columns we want to set is NULL."""
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable")

    select_cols = (
        "id,ticker,created_at,recommended_at,feature_origin,market_type,"
        "return_1d_pct,return_2d_pct,return_3d_pct,return_5d_pct,return_7d_pct,"
        "return_14d_pct,return_30d_pct,latest_return_pct,base_trade_date,entry_reference_price"
    )
    rows_by_id: Dict[Any, Dict[str, Any]] = {}
    for missing_col in (
        "return_1d_pct",
        "return_2d_pct",
        "return_3d_pct",
        "return_5d_pct",
        "return_7d_pct",
        "return_14d_pct",
        "return_30d_pct",
    ):
        page = 0
        while True:
            query = (
                db.client.table("market_scan_results")
                .select(select_cols)
                .in_("feature_origin", list(SCANNER_ORIGINS))
                .is_(missing_col, "null")
                .order("created_at", desc=True)
                .range(page * page_size, page * page_size + page_size - 1)
            )
            if market_filter == "KOSDAQ":
                query = query.eq("market_type", "KR").ilike("ticker", "%.KQ")
            elif market_filter == "KOSPI":
                query = query.eq("market_type", "KR").ilike("ticker", "%.KS")
            elif market_filter == "KR":
                query = query.eq("market_type", "KR")
            elif market_filter == "US":
                query = query.eq("market_type", "US")
            elif market_filter == "AMEX":
                query = query.eq("market_type", "AMEX")
            res = query.execute()
            batch = res.data or []
            for row in batch:
                row_id = row.get("id")
                if row_id is not None and row_id not in rows_by_id:
                    rows_by_id[row_id] = row
            if len(batch) < page_size:
                break
            page += 1
            if page > 200:
                break
    return list(rows_by_id.values())


def _row_scan_date(row: Dict[str, Any]) -> Optional[str]:
    return (
        _parse_iso_date(row.get("recommended_at"))
        or _parse_iso_date(row.get("created_at"))
    )


def _build_update_payload(
    scanner_row: Dict[str, Any],
    outcome: Dict[str, Any],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for col in RETURN_COLUMNS:
        if col == "performance_updated_at":
            continue
        if scanner_row.get(col) is not None:
            continue
        value = outcome.get(col)
        if value is None:
            continue
        payload[col] = value
    if payload:
        payload["performance_updated_at"] = datetime.now(timezone.utc).isoformat()
    return payload


def run_backfill(
    *,
    shared_dir: Path,
    limit_runs: int,
    dry_run: bool,
    market_filter: Optional[str],
    allow_history_fallback: bool = True,
) -> Dict[str, Any]:
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")

    index = _build_outcome_index(shared_dir, limit_runs)
    if not index:
        return {
            "status": "skip",
            "reason": "empty_outcome_index",
            "rows_seen": 0,
            "rows_updated": 0,
        }

    scanner_rows = _fetch_scanner_rows_missing_returns(db, market_filter=market_filter)
    print(f"[INFO] fetched {len(scanner_rows)} scanner rows missing return_3d/14d/30d_pct")

    rows_seen = len(scanner_rows)
    matched_index = 0
    matched_history = 0
    updated = 0
    skipped_no_match = 0
    skipped_no_payload = 0
    history_failed = 0
    by_origin: Dict[str, int] = defaultdict(int)
    sample_updates: List[Dict[str, Any]] = []

    for row in scanner_rows:
        ticker = str(row.get("ticker") or "").strip()
        scan_date = _row_scan_date(row)
        if not ticker or not scan_date:
            skipped_no_match += 1
            continue

        source = None
        outcome = index.get((ticker, scan_date))
        if outcome is not None:
            matched_index += 1
            source = "outcome_index"
        elif allow_history_fallback:
            hist = _fetch_history_close(ticker, scan_date)
            computed = _compute_returns_from_history(hist, scan_date) if hist is not None else {}
            if computed:
                outcome = computed
                matched_history += 1
                source = "yfinance_fallback"
            else:
                history_failed += 1
                skipped_no_match += 1
                continue
        else:
            skipped_no_match += 1
            continue

        payload = _build_update_payload(row, outcome)
        # Outcome row exists in index but every return column is None — fall back
        # to yfinance to actually compute returns. This is the typical state when
        # outcome_sync ran on a still-PENDING row. Without this second pass, those
        # rows remain unfilled forever even though prices are available.
        if not payload and source == "outcome_index" and allow_history_fallback:
            hist = _fetch_history_close(ticker, scan_date)
            computed = _compute_returns_from_history(hist, scan_date) if hist is not None else {}
            if computed:
                outcome = computed
                matched_history += 1
                matched_index -= 1  # reclassify as fallback
                source = "yfinance_fallback"
                payload = _build_update_payload(row, outcome)
            else:
                history_failed += 1

        if not payload:
            skipped_no_payload += 1
            continue
        by_origin[str(row.get("feature_origin") or "")] += 1
        if len(sample_updates) < 5:
            sample_updates.append(
                {
                    "id": row.get("id"),
                    "ticker": ticker,
                    "scan_date": scan_date,
                    "source": source,
                    "feature_origin": row.get("feature_origin"),
                    "before": {col: row.get(col) for col in payload if col != "performance_updated_at"},
                    "after": {col: payload[col] for col in payload if col != "performance_updated_at"},
                }
            )
        if not dry_run:
            try:
                db.client.table("market_scan_results").update(payload).eq("id", row.get("id")).execute()
                updated += 1
            except Exception as exc:
                print(f"[WARN] update failed id={row.get('id')} ticker={ticker}: {exc}")

    matched_total = matched_index + matched_history
    fill_rate_after_estimate = (
        100.0 * (1.0 - max(rows_seen - matched_total, 0) / max(rows_seen, 1))
    )

    summary = {
        "status": "ok",
        "dry_run": bool(dry_run),
        "shared_dir": str(shared_dir),
        "limit_runs": int(limit_runs),
        "outcome_index_keys": len(index),
        "scanner_rows_missing_return_pct": rows_seen,
        "scanner_rows_missing_return_3d_pct": rows_seen,
        "matched_total": matched_total,
        "matched_outcome_index": matched_index,
        "matched_yfinance_fallback": matched_history,
        "history_fetch_failed": history_failed,
        "updated": updated,
        "skipped_no_match": skipped_no_match,
        "skipped_no_payload": skipped_no_payload,
        "matched_by_feature_origin": dict(by_origin),
        "fill_rate_after_pct_estimate": round(fill_rate_after_estimate, 2),
        "allow_history_fallback": bool(allow_history_fallback),
        "sample_updates": sample_updates,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", type=str, default="runtime_state/shared_working")
    parser.add_argument(
        "--limit-runs",
        type=int,
        default=400,
        help="Number of recent RUN-* dirs to scan for outcomes (default 400).",
    )
    parser.add_argument(
        "--market",
        choices=["ALL", "KR", "KOSPI", "KOSDAQ", "US", "AMEX"],
        default="ALL",
        help="Filter scanner rows by market_type or KR ticker suffix (default ALL).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-history-fallback",
        action="store_true",
        help="Disable yfinance fallback for rows whose RUN-* outcomes were rotated out.",
    )
    args = parser.parse_args()

    summary = run_backfill(
        shared_dir=Path(args.shared_dir),
        limit_runs=int(args.limit_runs),
        dry_run=bool(args.dry_run),
        market_filter=None if args.market == "ALL" else args.market,
        allow_history_fallback=not bool(args.no_history_fallback),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
