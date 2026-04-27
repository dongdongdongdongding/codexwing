#!/usr/bin/env python3
"""Backfill volume_ratio + volume_confirmed for KOSDAQ SWING training rows.

Why this exists
---------------
KOSDAQ phase25_kosdaq_swing model has feature_importance_top15 showing
vol_confirmed/vol_gt25x/vol_18_25x/vol_lt05x all = 0.0, because volume_ratio
fill rate in RESOLVED rows is 0% (verified 2026-04-27 across 479 rows). The
model collapses onto alpha_score alone (importance 746 vs others ≤82),
producing raw_auc 0.46 → signal_direction='uncertain' → production gate blocks.

This script fetches historical OHLCV via yfinance and computes the same
5d/20d volume ratio that quant_analysis.get_trade_setup uses, then UPDATEs
market_scan_results rows in place. Strict no-leakage: only uses bars on or
before the row's base_trade_date / created_at date.

Usage
-----
  python3 multi_agent/tools/backfill_kosdaq_volume_ratio.py --dry-run --limit 30
  python3 multi_agent/tools/backfill_kosdaq_volume_ratio.py --market KOSDAQ --scan-mode SWING
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager

try:
    import yfinance as yf
except ImportError:
    print("yfinance is required. pip install yfinance", file=sys.stderr)
    sys.exit(1)


def _parse_scan_date(row: Dict[str, Any]) -> Optional[datetime]:
    btd = row.get("base_trade_date")
    if btd:
        try:
            return datetime.fromisoformat(str(btd)[:10])
        except Exception:
            pass
    ca = row.get("created_at")
    if ca:
        try:
            return datetime.fromisoformat(str(ca).replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
    return None


def _compute_volume_ratio(ticker: str, scan_dt: datetime) -> Optional[float]:
    """Fetch ~30 trading days ending at scan_dt and compute 5d_mean / 20d_mean.

    Pure pre-scan: never includes bars after scan_dt to avoid leakage.
    """
    end = scan_dt + timedelta(days=1)
    start = scan_dt - timedelta(days=45)
    try:
        hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    except Exception:
        return None
    if hist is None or hist.empty or "Volume" not in hist.columns:
        return None
    if len(hist) < 20:
        return None
    vols = hist["Volume"].dropna()
    if len(vols) < 20:
        return None
    vol_recent = float(vols.tail(5).mean())
    vol_baseline = float(vols.tail(20).mean())
    if vol_baseline <= 0:
        return None
    return round(vol_recent / vol_baseline, 2)


def _select_targets(
    db: DBManager,
    market: str,
    scan_mode: str,
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    suffix = ".KQ" if market == "KOSDAQ" else ".KS"
    page_size = 1000
    rows: List[Dict[str, Any]] = []
    page = 0
    select_cols = "id,ticker,scan_mode,base_trade_date,created_at,volume_ratio,volume_confirmed,outcome_status,return_5d_pct,feature_origin"
    while True:
        q = (
            db.client.table("market_scan_results")
            .select(select_cols)
            .eq("scan_mode", scan_mode)
            .like("ticker", f"%{suffix}")
            .is_("volume_ratio", "null")
            .not_.is_("return_5d_pct", "null")
            .eq("outcome_status", "RESOLVED")
            .order("created_at", desc=True)
            .range(page * page_size, page * page_size + page_size - 1)
        )
        res = q.execute()
        batch = res.data or []
        rows.extend(batch)
        if limit is not None and len(rows) >= limit:
            return rows[:limit]
        if len(batch) < page_size:
            break
        page += 1
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=["KOSDAQ", "KOSPI"], default="KOSDAQ")
    parser.add_argument("--scan-mode", default="SWING")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.05, help="seconds between yfinance calls")
    args = parser.parse_args()

    db = DBManager()
    if not db.client:
        print("Supabase client unavailable.", file=sys.stderr)
        return 2

    targets = _select_targets(db, args.market, args.scan_mode, args.limit)
    print(f"📊 Found {len(targets)} {args.market} {args.scan_mode} rows missing volume_ratio")
    if not targets:
        return 0

    updated = 0
    skipped_no_date = 0
    skipped_fetch_fail = 0
    skipped_too_few_bars = 0
    other_exc = 0

    for i, row in enumerate(targets, 1):
        ticker = row.get("ticker") or ""
        scan_dt = _parse_scan_date(row)
        if not scan_dt:
            skipped_no_date += 1
            continue
        try:
            vr = _compute_volume_ratio(ticker, scan_dt)
        except Exception:
            other_exc += 1
            continue
        if vr is None:
            skipped_fetch_fail += 1
            time.sleep(args.sleep)
            continue
        vc = bool(vr >= 1.5)  # threshold matches quant_analysis live logic spirit
        payload = {"volume_ratio": vr, "volume_confirmed": vc}
        if args.dry_run:
            print(f"  [DRY] {ticker} @ {scan_dt.date()} → vr={vr} vc={vc}")
        else:
            try:
                db.client.table("market_scan_results").update(payload).eq("id", row["id"]).execute()
                updated += 1
            except Exception as exc:
                other_exc += 1
                print(f"  ⚠️ update failed {ticker} id={row.get('id')}: {exc}")
        if i % 50 == 0:
            print(f"  progress: {i}/{len(targets)} updated={updated}")
        time.sleep(args.sleep)

    print()
    print("=== Backfill summary ===")
    print(f"  total candidates    : {len(targets)}")
    print(f"  updated             : {updated}")
    print(f"  skipped_no_date     : {skipped_no_date}")
    print(f"  skipped_fetch_fail  : {skipped_fetch_fail}")
    print(f"  skipped_too_few_bars: {skipped_too_few_bars}")
    print(f"  other_exc           : {other_exc}")
    if args.dry_run:
        print("(dry-run: no rows actually updated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
