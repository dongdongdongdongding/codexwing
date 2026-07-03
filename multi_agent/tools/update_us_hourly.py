#!/usr/bin/env python3
"""Incremental refresh of ~/research_cache/us_daily/hourly/{SYM}.parquet (swing-main-f9yw).

Feeds the NASDAQ session-tape shadow lane. Per symbol: download the recent window
(period=1mo, 1h) and merge-dedup into the cached file. ~350 symbols, ~4-6 min.

  python3 multi_agent/tools/update_us_hourly.py
"""
from __future__ import annotations

import glob
import os
import time
import warnings

warnings.filterwarnings("ignore")
import pandas as pd

HOURD = os.path.expanduser("~/research_cache/us_daily/hourly")


def main() -> None:
    import yfinance as yf
    files = sorted(glob.glob(os.path.join(HOURD, "*.parquet")))
    print(f"[us_hourly] {len(files)} symbols", flush=True)
    t0 = time.time()
    ok = 0
    for i, fp in enumerate(files):
        sym = os.path.basename(fp).replace(".parquet", "")
        try:
            new = yf.download(sym, period="1mo", interval="1h", progress=False, auto_adjust=False)
            if new is None or new.empty:
                continue
            new.columns = [c[0] if isinstance(c, tuple) else c for c in new.columns]
            old = pd.read_parquet(fp)
            merged = pd.concat([old, new])
            merged = merged[~merged.index.duplicated(keep="last")].sort_index()
            merged.to_parquet(fp)
            ok += 1
        except Exception:
            continue
        time.sleep(0.2)
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(files)} ok={ok} ({time.time()-t0:.0f}s)", flush=True)
    print(f"[us_hourly] DONE ok={ok}/{len(files)} ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
