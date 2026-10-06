"""Recover the existing extended-session research cohort from observed dates.

KRX+NXT UN bars stay separate from regular-session J bars. This preserves the
existing research cohort, not a point-in-time or full-market universe claim.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.backfill_kr_intraday import KST, collect, legacy_writers, targets

HOURS = ("200000", "180000", "160000", "140000", "120000", "100000")


def extended_schedule(panel, out, now, retention):
    codes = sorted(p.stem for p in out.glob("*.parquet"))
    if not codes or any(len(code) != 6 or not code.isdigit() for code in codes):
        raise ValueError("missing_or_invalid_existing_extended_cohort")
    frame = panel.copy()
    frame["code"] = frame.code.astype(str).str.zfill(6)
    schedule = targets(frame[frame.code.isin(codes)], now, retention, close_time=(20, 0))
    return codes, schedule


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, default=Path.home()/"research_cache")
    ap.add_argument("--budget", type=float, default=float(os.getenv("EXT_TIME_BUDGET", "600")))
    ap.add_argument("--retention-days", type=int, default=355)
    ap.add_argument("--sleep", type=float, default=float(os.getenv("EXT_SLEEP", ".04")))
    ap.add_argument("--min-free-gb", type=float, default=float(os.getenv("ITD_MIN_FREE_GB", "10")))
    ap.add_argument("--plan", action="store_true")
    args = ap.parse_args()
    if (not math.isfinite(args.budget) or args.budget <= 0 or args.retention_days <= 0
            or not math.isfinite(args.sleep) or args.sleep < 0
            or not math.isfinite(args.min_free_gb) or args.min_free_gb < 0):
        ap.error("invalid budget, retention, sleep or storage reserve")
    out = args.cache/"intraday_ext"
    now = datetime.now(KST)
    codes, schedule = extended_schedule(pd.read_parquet(args.cache/"px_long.parquet",
                                        columns=["code", "date"]), out, now, args.retention_days)
    if "EXT_UNIVERSE_N" in os.environ and int(os.environ["EXT_UNIVERSE_N"]) < len(codes):
        ap.error("EXT_UNIVERSE_N cannot truncate the existing cohort")
    summary = {"cohort": "existing_extended_cache_codes", "codes": len(codes),
               "latest_observed_session": max(schedule), "sessions": len(schedule),
               "target_pairs": sum(map(len, schedule.values())), "market_div": "UN",
               "session": "08:00-20:00", "point_in_time_universe_verified": False}
    print(json.dumps(summary), flush=True)
    if args.plan:
        return 0
    state = out/".backfill"
    state.mkdir(parents=True, exist_ok=True)
    with (state/"writer.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "BUSY", "reason": "writer_lock"}))
            return 2
        pids = legacy_writers(args.cache, entrypoints=("intraday_ext_update.py", "build_intraday_ext.py"))
        if pids:
            print(json.dumps({"status": "BUSY", "reason": "legacy_extended_writer", "pids": pids}))
            return 2
        from dotenv import load_dotenv
        from modules.kis_openapi import KISOpenAPIClient
        load_dotenv(ROOT/".env.local")
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
        os.environ["KIS_LIVE_RETRY_COUNT"] = "0"
        report = collect(schedule, out, KISOpenAPIClient(timeout=10), args.budget, args.sleep,
                         now=now, min_free_bytes=int(args.min_free_gb*1024**3), hours=HOURS,
                         market_div="UN", session_start="08:00", session_end="20:00",
                         universe="existing_extended_cache_codes_with_observed_daily_dates")
        print(json.dumps(report), flush=True)
        return 1 if report["storage_errors"] or report["request_errors"] or report["status"] == "STORAGE_BUDGET_EXHAUSTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
