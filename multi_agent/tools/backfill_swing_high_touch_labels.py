#!/usr/bin/env python3
"""Backfill forward-high 5d swing target labels on market_scan_results."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager
from multi_agent.tools.update_outcome_return_metrics import _compute_row_returns, _parse_iso


SELECT_COLS = (
    "id,run_id,ticker,market,market_type,scan_mode,recommended_at,base_trade_date,"
    "entry_reference_price,return_5d_pct,max_high_return_5d_pct,hit_5pct_within_5d,"
    "hit_5pct_within_5d_at,swing_target_label_version"
)


def _target_query(db: DBManager, *, market: str):
    q = (
        db.client.table("market_scan_results")
        .select(SELECT_COLS)
        .eq("scan_mode", "SWING")
        .not_.is_("return_5d_pct", "null")
        .is_("max_high_return_5d_pct", "null")
        .not_.is_("base_trade_date", "null")
        .order("recommended_at", desc=True)
    )
    if market in {"KOSPI", "KOSDAQ"}:
        q = q.eq("market", market)
    elif market == "KR":
        q = q.eq("market_type", "KR")
    return q


def _fetch_targets(db: DBManager, *, market: str, limit: int, batch_size: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    page_size = max(1, min(int(batch_size), 1000))
    offset = 0
    while True:
        remaining = None if limit <= 0 else max(0, int(limit) - len(rows))
        if remaining == 0:
            break
        request_size = page_size if remaining is None else min(page_size, remaining)
        page = (
            _target_query(db, market=market)
            .range(offset, offset + request_size - 1)
            .execute()
            .data
            or []
        )
        rows.extend(list(page))
        if len(page) < request_size:
            break
        offset += request_size
    return rows


def _history_window(row: Dict[str, Any]) -> tuple[str, str]:
    rec = _parse_iso(row.get("recommended_at"))
    if rec is None:
        base_text = str(row.get("base_trade_date") or "").strip()
        if base_text:
            try:
                base = datetime.fromisoformat(base_text[:10]).replace(tzinfo=timezone.utc)
            except Exception:
                base = datetime.now(timezone.utc) - timedelta(days=20)
        else:
            base = datetime.now(timezone.utc) - timedelta(days=20)
    else:
        base = rec.astimezone(timezone.utc)
    return (base.date() - timedelta(days=7)).isoformat(), (base.date() + timedelta(days=20)).isoformat()


def _combined_history_window(rows: List[Dict[str, Any]]) -> tuple[str, str]:
    starts: List[str] = []
    ends: List[str] = []
    for row in rows:
        start, end = _history_window(row)
        starts.append(start)
        ends.append(end)
    return min(starts), max(ends)


def _fetch_history_with_timeout(ticker: str, start: str, end: str):
    try:
        hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False, timeout=10)
        if hist is None or hist.empty:
            return None
        hist = hist.copy()
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC")
        hist["trade_date"] = hist.index.date
        return hist
    except Exception:
        return None


def _process_ticker_group(ticker: str, rows: List[Dict[str, Any]], market: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "ticker": ticker,
        "rows_seen": len(rows),
        "patches": [],
        "history_missing": 0,
        "rows_unlabeled": 0,
        "examples": [],
        "error": None,
    }
    try:
        start, end = _combined_history_window(rows)
        hist = _fetch_history_with_timeout(ticker, start, end)
        if hist is None or hist.empty:
            result["history_missing"] = len(rows)
            return result
        for row in rows:
            working = dict(row)
            row_market = str(row.get("market") or market)
            if not _compute_row_returns(working, hist, row_market):
                result["rows_unlabeled"] += 1
                continue
            patch = {
                key: working.get(key)
                for key in (
                    "max_high_return_5d_pct",
                    "hit_5pct_within_5d",
                    "hit_5pct_within_5d_at",
                    "swing_target_label_version",
                )
            }
            if patch["max_high_return_5d_pct"] is None:
                result["rows_unlabeled"] += 1
                continue
            patch["performance_updated_at"] = datetime.now(timezone.utc).isoformat()
            result["patches"].append({"id": row["id"], "patch": patch})
            if len(result["examples"]) < 5:
                result["examples"].append(
                    {
                        "ticker": ticker,
                        "run_id": row.get("run_id"),
                        "max_high_return_5d_pct": patch.get("max_high_return_5d_pct"),
                        "hit_5pct_within_5d": patch.get("hit_5pct_within_5d"),
                    }
                )
    except Exception as exc:
        result["error"] = str(exc)
    return result


def run(*, market: str, limit: int, dry_run: bool, batch_size: int, max_workers: int, progress_every: int) -> Dict[str, Any]:
    db = DBManager()
    if not db.client:
        raise RuntimeError("Supabase client unavailable.")
    rows = _fetch_targets(db, market=market, limit=limit, batch_size=batch_size)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    skipped_no_ticker = 0
    for row in rows:
        ticker = str(row.get("ticker") or "").strip()
        if not ticker:
            skipped_no_ticker += 1
            continue
        grouped[ticker].append(row)

    stats: Dict[str, Any] = {
        "market": market,
        "rows_seen": len(rows),
        "ticker_groups": len(grouped),
        "skipped_no_ticker": skipped_no_ticker,
        "rows_updated": 0,
        "history_missing": 0,
        "rows_unlabeled": 0,
        "errors": [],
        "dry_run": bool(dry_run),
        "examples": [],
    }
    workers = max(1, int(max_workers))
    completed_groups = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_process_ticker_group, ticker, ticker_rows, market)
            for ticker, ticker_rows in grouped.items()
        ]
        for future in as_completed(futures):
            completed_groups += 1
            result = future.result()
            stats["history_missing"] += int(result.get("history_missing") or 0)
            stats["rows_unlabeled"] += int(result.get("rows_unlabeled") or 0)
            if result.get("error"):
                stats["errors"].append({"ticker": result.get("ticker"), "error": result.get("error")})
                continue
            for item in result.get("patches", []):
                if not dry_run:
                    db.client.table("market_scan_results").update(item["patch"]).eq("id", item["id"]).execute()
                stats["rows_updated"] += 1
            for example in result.get("examples", []):
                if len(stats["examples"]) < 10:
                    stats["examples"].append(example)
            if progress_every > 0 and completed_groups % progress_every == 0:
                print(
                    json.dumps(
                        {
                            "progress": {
                                "ticker_groups_done": completed_groups,
                                "ticker_groups_total": len(grouped),
                                "rows_updated": stats["rows_updated"],
                                "history_missing": stats["history_missing"],
                                "rows_unlabeled": stats["rows_unlabeled"],
                                "errors": len(stats["errors"]),
                            }
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=["KR", "KOSPI", "KOSDAQ"], default="KR")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum rows to process. Use 0 for all pending rows.")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--progress-every", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run(
        market=str(args.market).upper(),
        limit=int(args.limit),
        dry_run=bool(args.dry_run),
        batch_size=int(args.batch_size),
        max_workers=int(args.max_workers),
        progress_every=int(args.progress_every),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
