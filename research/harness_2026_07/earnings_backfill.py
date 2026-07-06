"""US earnings dates + surprise backfill (P3 PEAD, swing-main-x1vj).
858 NASDAQ panel symbols x yfinance get_earnings_dates -> ~/research_cache/us_daily/earnings_dates.parquet"""
import os, time, warnings; warnings.filterwarnings("ignore")
import pandas as pd, yfinance as yf, pyarrow.parquet as pq

PANEL = os.path.expanduser("~/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet")
OUT = os.path.expanduser("~/research_cache/us_daily/earnings_dates.parquet")
syms = sorted(pd.read_parquet(PANEL, columns=["symbol"])["symbol"].unique())
print(f"symbols: {len(syms)}", flush=True)
rows = []
t0 = time.time()
for i, s in enumerate(syms):
    try:
        ed = yf.Ticker(s).get_earnings_dates(limit=80)
        if ed is not None and len(ed):
            for ts, r in ed.iterrows():
                rows.append({"symbol": s, "ann_ts": str(ts), "eps_est": r.get("EPS Estimate"),
                             "eps_act": r.get("Reported EPS"), "surprise_pct": r.get("Surprise(%)")})
    except Exception:
        pass
    time.sleep(0.25)
    if (i + 1) % 100 == 0:
        pd.DataFrame(rows).to_parquet(OUT, index=False)
        print(f"  {i+1}/{len(syms)} events={len(rows)} ({time.time()-t0:.0f}s)", flush=True)
pd.DataFrame(rows).to_parquet(OUT, index=False)
print(f"DONE events={len(rows)} -> {OUT} ({time.time()-t0:.0f}s)", flush=True)
