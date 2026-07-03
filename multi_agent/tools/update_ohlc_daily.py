#!/usr/bin/env python3
"""Incremental updater for ~/research_cache/ohlc_daily.parquet (swing-main-jszr).

ohlc_daily feeds the intraday panel's forward labels (y3) and the KOSPI lane's
policy-return training target. It went stale (last build 2026-06-26), which §6 showed
truncates panel-tail labels. This tool upserts recent daily OHLC via FDR for the
panel's ~300 codes. Runs before build_intraday_3d_panel in daily ops.

  python3 multi_agent/tools/update_ohlc_daily.py [--lookback-days 14]
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(os.path.expanduser("~/research_cache"))
OUT = CACHE / "ohlc_daily.parquet"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback-days", type=int, default=14)
    args = ap.parse_args()
    import FinanceDataReader as fdr

    old = pd.read_parquet(OUT)
    old["code"] = old["code"].astype(str).str.zfill(6)
    old["date"] = pd.to_datetime(old["date"])
    codes = sorted(old["code"].unique())
    start = (old["date"].max() - pd.Timedelta(days=args.lookback_days)).date()
    print(f"[ohlc_daily] {len(codes)} codes, upsert from {start} (last={old['date'].max().date()})", flush=True)
    rows = []
    t0 = time.time()
    for i, code in enumerate(codes):
        try:
            h = fdr.DataReader(code, str(start))
        except Exception:
            continue
        if h is None or h.empty:
            continue
        h = h.reset_index().rename(columns={"Date": "date", "Open": "open", "High": "high",
                                            "Low": "low", "Close": "close"})
        h["code"] = code
        rows.append(h[["date", "open", "high", "low", "close", "code"]])
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(codes)} ({time.time()-t0:.0f}s)", flush=True)
        time.sleep(0.02)
    if not rows:
        print("[ohlc_daily] no new data"); return
    add = pd.concat(rows, ignore_index=True)
    add["date"] = pd.to_datetime(add["date"])
    for c in ("open", "high", "low", "close"):
        add[c] = pd.to_numeric(add[c], errors="coerce")
    merged = pd.concat([old, add], ignore_index=True).drop_duplicates(["code", "date"], keep="last")
    merged = merged.sort_values(["code", "date"]).reset_index(drop=True)
    merged.to_parquet(OUT, index=False)
    print(f"[ohlc_daily] {len(old)} -> {len(merged)} rows, max date {merged['date'].max().date()} ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
