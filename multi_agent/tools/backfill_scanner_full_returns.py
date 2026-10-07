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
2. Build an index keyed by (run_id, ticker)
   → return_{1,2,3,5,7,14,30}d_pct, latest_return_pct, base_trade_date
3. For each (run_id, ticker) key, look up matching market_scan_results rows
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
- Use --dry-run for inspection; the daily job applies coherent missing values.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
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


def _parse_iso_date(value: Any, timezone_name: str = "UTC") -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        # Date-only values already name a market day; do not timezone-shift them.
        if len(text) == 10:
            return datetime.fromisoformat(text).date().isoformat()
        # Python 3.9 accepts only 3/6 fractional digits, while PostgREST emits
        # variable precision (e.g. .17633). Normalize without losing the day.
        text = re.sub(r"(\d{2}:\d{2}:\d{2})\.(\d+)",
                      lambda m: m[1] + "." + m[2][:6].ljust(6, "0"), text)
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo(timezone_name)).date().isoformat()
    except (ValueError, TypeError):
        return None


def _iter_run_dirs(shared_dir: Path, limit_runs: int) -> List[Path]:
    if not shared_dir.exists():
        return []
    runs = [p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")]
    runs = sorted(runs, key=lambda p: (p.stat().st_mtime_ns, p.name))
    if limit_runs > 0:
        runs = runs[-limit_runs:]
    return runs


def _build_outcome_index(shared_dir: Path, limit_runs: int) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Return {(run_id, ticker): outcome_subset}; never borrow another run.

    Conflicting duplicate outcomes inside one run are ambiguous and omitted.
    """
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    ambiguous_keys = set()
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
            scan_date = _row_scan_date(row)
            if not scan_date:
                continue
            key = (run_dir.name, ticker)
            if key in ambiguous_keys:
                continue
            subset = {col: row.get(col) for col in RETURN_COLUMNS}
            subset["_source_run_id"] = run_dir.name
            snapshot = row.get("feature_snapshot") or {}
            if isinstance(snapshot, dict) and snapshot.get("daily_outcome_basis"):
                subset["feature_snapshot"] = {"daily_outcome_basis":snapshot["daily_outcome_basis"]}
            non_null = sum(subset.get(col) is not None for col in RETURN_COLUMNS)
            if non_null == 0:
                continue
            existing = index.get(key)
            if existing is not None and _conflicting_daily_field(existing, subset):
                del index[key]
                ambiguous_keys.add(key)
                continue
            if existing is None or non_null > sum(existing.get(col) is not None for col in RETURN_COLUMNS):
                index[key] = subset
    rows_indexed = len(index)
    print(
        f"[INFO] outcome index: runs_seen={runs_seen} runs_with_outcomes={runs_with_outcomes} "
        f"unique_keys={len(index)} rows_indexed={rows_indexed} ambiguous_run_tickers={len(ambiguous_keys)}"
    )
    return index


def _fetch_scanner_rows_missing_returns(
    db: Any,
    *,
    page_size: int = 1000,
    market_filter: Optional[str] = None,
    progress_callback=None,
) -> List[Dict[str, Any]]:
    """Fetch market_scan_results rows where feature_origin is backfillable
    and at least one of the return columns we want to set is NULL."""
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable")

    select_cols = (
        "id,ticker,run_id,created_at,recommended_at,feature_origin,market_type,feature_snapshot,"
        "return_1d_pct,return_2d_pct,return_3d_pct,return_5d_pct,return_7d_pct,"
        "return_14d_pct,return_30d_pct,latest_return_pct,base_trade_date,entry_reference_price,"
        "performance_updated_at,validation_excluded_reason"
    )
    missing_cols = [f"return_{h}d_pct" for h in HORIZONS_FROM_HISTORY]
    rows_by_id: Dict[Any, Dict[str, Any]] = {}
    # Seven independent NULL-filtered OFFSET scans timed out on the live DB.
    # Traverse the primary key once and filter missing horizons locally. Freeze
    # the upper ID so concurrent inserts cannot make the scan unbounded.
    def scoped(columns):
        query = db.client.table("market_scan_results").select(columns).in_("feature_origin", list(SCANNER_ORIGINS))
        if market_filter in {"KOSDAQ", "KOSPI"}:
            query = query.eq("market_type", "KR").ilike("ticker", "%.KQ" if market_filter == "KOSDAQ" else "%.KS")
        elif market_filter in {"KR", "US", "AMEX"}:
            query = query.eq("market_type", market_filter)
        return query
    newest = scoped("id").order("id", desc=True).limit(1).execute().data or []
    if not newest:
        return []
    upper = newest[0]["id"]
    last_id = None
    scanned = 0
    page_size = max(1, min(page_size, 500))
    while True:
        query = scoped(select_cols).lte("id", upper).order("id").limit(page_size)
        if last_id is not None:
            query = query.gt("id", last_id)
        batch = query.execute().data or []
        if not batch:
            break
        ids = [row["id"] for row in batch]
        if ids != sorted(set(ids)) or last_id is not None and ids[0] <= last_id:
            raise ValueError("archive keyset scan did not advance")
        for row in batch:
            if any(row.get(col) is None for col in missing_cols):
                rows_by_id[row["id"]] = row
        last_id = ids[-1]
        scanned += len(batch)
        if progress_callback:
            progress_callback(fetch_rows_scanned=scanned, fetch_rows_eligible=len(rows_by_id),
                              fetch_last_id=last_id, fetch_upper_id=upper)
        if len(batch) < page_size or last_id >= upper:
            break
    return list(rows_by_id.values())


def _row_scan_date(row: Dict[str, Any]) -> Optional[str]:
    ticker = str(row.get("ticker") or "")
    market = str(row.get("market_type") or row.get("market") or "").upper()
    tz = "Asia/Seoul" if ticker.endswith((".KS", ".KQ")) or market in {"KR", "KOSPI", "KOSDAQ"} else "America/New_York"
    return (_parse_iso_date(row.get("recommended_at"), tz)
            or _parse_iso_date(row.get("created_at"), tz)
            or _parse_iso_date(row.get("base_trade_date"), tz))


def _conflicting_daily_field(scanner_row, outcome):
    source_run = outcome.get("_source_run_id")
    if source_run and source_run != (scanner_row.get("run_id") or scanner_row.get("_source_run_id")):
        return "_source_run_id"
    # A null-only merge can combine KRX and integrated-market prices: the
    # existing denominator/short horizon remains while a different provider's
    # longer horizon is appended. Refuse evidence of a different daily basis.
    for key in RETURN_COLUMNS:
        if key in {"performance_updated_at", "latest_return_pct"}:
            continue  # latest return legitimately changes as the source advances
        existing, incoming = scanner_row.get(key), outcome.get(key)
        if existing is None or incoming is None:
            continue
        if key == "base_trade_date":
            if str(existing)[:10] != str(incoming)[:10]:
                return key
        else:
            try:
                left, right = float(existing), float(incoming)
            except (TypeError, ValueError):
                return key
            if not (math.isfinite(left) and math.isfinite(right) and
                    math.isclose(left, right, rel_tol=1e-8, abs_tol=1e-6)):
                return key
    return None


def _build_update_payload(
    scanner_row: Dict[str, Any],
    outcome: Dict[str, Any],
) -> Dict[str, Any]:
    if str(scanner_row.get("run_id") or "").startswith("SWING-CAND-"):
        # Dedicated adjusted-price refresh owns these daily outcomes.
        return {}
    basis = (scanner_row.get("feature_snapshot") or {}).get("daily_outcome_basis")
    if basis and basis != (outcome.get("feature_snapshot") or {}).get("daily_outcome_basis"):
        # An unadjusted or differently dated fallback cannot fill the immature
        # cells of an explicitly normalized adjusted-price outcome.
        return {}
    if _conflicting_daily_field(scanner_row, outcome):
        return {}
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
    max_rows: int = 0,
    max_history_requests: int = 0,
    max_planning_seconds: float = 0,
    resume_path: Optional[Path] = None,
    progress_path: Optional[Path] = None,
) -> Dict[str, Any]:
    from multi_agent.tools.repair_flow_snapshot_metadata import write_json
    from modules.db_manager import DBManager

    if min(max_rows, max_history_requests, max_planning_seconds) < 0:
        raise ValueError("backfill bounds must be nonnegative")
    scope = {"version": 1, "market": market_filter, "shared_dir": str(shared_dir.resolve())}
    cursor = 0
    if resume_path and resume_path.exists():
        state = json.loads(resume_path.read_text())
        if state.get("scope") != scope or type(state.get("last_id")) is not int or state["last_id"] < 0:
            raise ValueError("incompatible or invalid backfill cursor")
        cursor = state["last_id"]
    started = time.monotonic()
    processed = 0
    history_requests = 0
    history_cache_hits = 0
    history_cache = {}
    last_id = cursor
    last_progress = -float("inf")

    def progress(phase, force=False, **extra):
        nonlocal last_progress
        now = time.monotonic()
        if progress_path and (force or now - last_progress >= 5):
            write_json(progress_path, {"scope": scope, "pid": os.getpid(), "phase": phase,
                "dry_run": dry_run, "processed": processed, "last_id": last_id,
                "history_requests": history_requests, "history_cache_hits": history_cache_hits,
                "elapsed_seconds": round(now-started, 3),
                "checked_at": datetime.now(timezone.utc).isoformat(), **extra})
            last_progress = now

    class BudgetExhausted(Exception):
        pass

    def history(ticker, scan_date):
        nonlocal history_requests, history_cache_hits
        key = (ticker, scan_date)
        if key in history_cache:
            history_cache_hits += 1
            return history_cache[key]
        if max_history_requests and history_requests >= max_history_requests:
            raise BudgetExhausted("history_request_limit")
        history_requests += 1
        progress("fetching_history", force=True, ticker=ticker, signal_date=scan_date)
        captured = _fetch_history_close(ticker, scan_date)
        # Reuse even an unavailable response only within this invocation.
        # Later invocations request fresh data as prices/labels mature.
        history_cache[key] = captured
        return captured

    progress("fetching_rows", force=True)
    db = DBManager()
    if not getattr(db, "client", None):
        raise RuntimeError("Supabase client unavailable.")

    index = _build_outcome_index(shared_dir, limit_runs)
    if not index and not allow_history_fallback:
        result = {
            "status": "skip",
            "reason": "empty_outcome_index",
            "rows_seen": 0,
            "rows_updated": 0,
        }
        progress("finished", force=True, summary=result)
        return result

    scanner_rows = sorted(_fetch_scanner_rows_missing_returns(db, market_filter=market_filter,
        progress_callback=lambda **data: progress("fetching_rows", force=True, **data)), key=lambda r: r["id"])
    scanner_rows = [r for r in scanner_rows if r["id"] > cursor] + [r for r in scanner_rows if r["id"] <= cursor]
    planning_started = time.monotonic()
    print(f"[INFO] fetched {len(scanner_rows)} scanner rows missing return_3d/14d/30d_pct")

    rows_seen = len(scanner_rows)
    matched_index = 0
    matched_history = 0
    updated = 0
    skipped_no_match = 0
    skipped_no_payload = 0
    conflicting_fields = defaultdict(int)
    eligible_updates = 0
    history_failed = 0
    by_origin: Dict[str, int] = defaultdict(int)
    sample_updates: List[Dict[str, Any]] = []
    plan = []
    skipped_dedicated = 0
    budget_reason = None

    for row in scanner_rows:
        if max_rows and processed >= max_rows:
            budget_reason = "row_limit"
            break
        if max_planning_seconds and time.monotonic() - planning_started >= max_planning_seconds:
            budget_reason = "planning_time_limit"
            break
        # This dedicated lane is never patched here; skip before external IO.
        if str(row.get("run_id") or "").startswith("SWING-CAND-"):
            skipped_dedicated += 1
            processed += 1
            last_id = row["id"]
            progress("planning")
            continue
        ticker = str(row.get("ticker") or "").strip()
        scan_date = _row_scan_date(row)
        if not ticker or not scan_date:
            skipped_no_match += 1
            processed += 1
            last_id = row["id"]
            continue

        source = None
        outcome = index.get((str(row.get("run_id") or ""), ticker))
        if outcome is not None:
            matched_index += 1
            source = "outcome_index"
        elif allow_history_fallback:
            try:
                hist = history(ticker, scan_date)
            except BudgetExhausted as exc:
                budget_reason = str(exc)
                break
            computed = _compute_returns_from_history(hist, scan_date) if hist is not None else {}
            if computed:
                outcome = computed
                matched_history += 1
                source = "yfinance_fallback"
            else:
                history_failed += 1
                skipped_no_match += 1
                processed += 1
                last_id = row["id"]
                continue
        else:
            skipped_no_match += 1
            processed += 1
            last_id = row["id"]
            continue

        payload = _build_update_payload(row, outcome)
        # Outcome row exists in index but every return column is None — fall back
        # to yfinance to actually compute returns. This is the typical state when
        # outcome_sync ran on a still-PENDING row. Without this second pass, those
        # rows remain unfilled forever even though prices are available.
        if not payload and source == "outcome_index" and allow_history_fallback:
            try:
                hist = history(ticker, scan_date)
            except BudgetExhausted as exc:
                matched_index -= 1
                budget_reason = str(exc)
                break
            computed = _compute_returns_from_history(hist, scan_date) if hist is not None else {}
            if computed:
                outcome = computed
                matched_history += 1
                matched_index -= 1  # reclassify as fallback
                source = "yfinance_fallback"
                payload = _build_update_payload(row, outcome)
            else:
                history_failed += 1

        processed += 1
        last_id = row["id"]
        progress("planning", eligible_updates=eligible_updates)
        if not payload:
            conflict = _conflicting_daily_field(row, outcome)
            if conflict:
                conflicting_fields[conflict] += 1
            skipped_no_payload += 1
            continue
        eligible_updates += 1
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
        plan.append({"before":row,
                     "patch":{k:v for k,v in payload.items() if k != "performance_updated_at"},
                     "source":source,"source_values":outcome})

    audit_result = None
    progress("applying" if not dry_run else "auditing", force=True, eligible_updates=eligible_updates)
    if plan:
        from multi_agent.tools.repair_issued_outcomes import audit_and_apply
        audit_result = audit_and_apply(plan,PROJECT_ROOT/"runtime_state/audit/scanner_full_return_backfill",
                                      {"tool":"backfill_scanner_full_returns","market_filter":market_filter,
                                       "shared_dir":str(shared_dir),"limit_runs":limit_runs},
                                      db.client,apply=not dry_run)
        if not dry_run:
            updated = audit_result["changes"]

    # Only advance after the complete selected plan has passed CAS/readback.
    # A crash or conflict leaves the prior cursor; replay re-reads current rows.
    if resume_path and not dry_run and processed:
        write_json(resume_path, {"scope": scope, "last_id": last_id,
            "checked_at": datetime.now(timezone.utc).isoformat()})

    matched_total = matched_index + matched_history
    fill_rate_after_estimate = (
        100.0 * eligible_updates / max(rows_seen, 1)
    )

    summary = {
        "status": "partial" if budget_reason else "degraded" if history_failed or conflicting_fields else "ok",
        "degraded_reasons": (["history_unavailable"] if history_failed else []) +
                            (["incompatible_daily_basis"] if conflicting_fields else []),
        "coverage_complete": processed == rows_seen,
        "coverage_scope": "current eligible rows attempted, not every horizon filled",
        "budget_reason": budget_reason,
        "rows_processed": processed,
        "rows_unvisited": rows_seen - processed,
        "skipped_dedicated_refresh": skipped_dedicated,
        "history_requests": history_requests,
        "history_cache_hits": history_cache_hits,
        "resume_last_id": last_id,
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
        "incompatible_daily_basis_by_field": dict(conflicting_fields),
        "eligible_updates": eligible_updates,
        "fill_estimate_scope": "rows with at least one coherent patch; not all horizons filled",
        "matched_by_feature_origin": dict(by_origin),
        "fill_rate_after_pct_estimate": round(fill_rate_after_estimate, 2),
        "allow_history_fallback": bool(allow_history_fallback),
        "sample_updates": sample_updates,
        "audit": audit_result,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    progress("finished", force=True, summary=summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", type=str, default="runtime_state/shared_working")
    parser.add_argument(
        "--limit-runs",
        type=int,
        default=400,
        help="Number of most recently modified RUN-* dirs to scan for outcomes (default 400).",
    )
    parser.add_argument(
        "--market",
        choices=["ALL", "KR", "KOSPI", "KOSDAQ", "US", "AMEX"],
        default="ALL",
        help="Filter scanner rows by market_type or KR ticker suffix (default ALL).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-rows", type=int, default=0, help="Rows attempted per invocation; 0 is unlimited.")
    parser.add_argument("--max-history-requests", type=int, default=0, help="Unique external price requests; 0 is unlimited.")
    parser.add_argument("--max-planning-seconds", type=float, default=0,
                        help="Planning budget after DB fetch; final audited writes may take longer. 0 is unlimited.")
    parser.add_argument("--resume-path", type=Path, help="Cursor path; bounded runs default to a market-specific cursor.")
    parser.add_argument("--progress-path", type=Path, help="Atomic progress receipt (default: unique ops receipt).")
    parser.add_argument(
        "--no-history-fallback",
        action="store_true",
        help="Disable yfinance fallback for rows whose RUN-* outcomes were rotated out.",
    )
    args = parser.parse_args()

    from multi_agent.tools.repair_flow_snapshot_metadata import write_json
    ops = PROJECT_ROOT / "runtime_state/long_term/ops"
    progress_path = args.progress_path or ops / "scanner_returns" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + f"_{os.getpid()}.json")
    resume_path = args.resume_path
    if not resume_path and any((args.max_rows, args.max_history_requests, args.max_planning_seconds)):
        resume_path = ops / f"scanner_return_backfill_cursor_{args.market}.json"
    lock_path = ops / "scanner_return_backfill.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            write_json(progress_path, {"phase": "busy", "pid": os.getpid()})
            return 2
        try:
            summary = run_backfill(
                shared_dir=Path(args.shared_dir),
                limit_runs=int(args.limit_runs),
                dry_run=bool(args.dry_run),
                market_filter=None if args.market == "ALL" else args.market,
                allow_history_fallback=not bool(args.no_history_fallback),
                max_rows=args.max_rows, max_history_requests=args.max_history_requests,
                max_planning_seconds=args.max_planning_seconds,
                resume_path=resume_path, progress_path=progress_path,
            )
        except Exception as exc:
            receipt = json.loads(progress_path.read_text()) if progress_path.exists() else {}
            write_json(progress_path, {**receipt, "phase": "failed", "error_type": type(exc).__name__})
            raise
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if summary["status"] in {"partial", "degraded"} else 0


if __name__ == "__main__":
    sys.exit(main())
