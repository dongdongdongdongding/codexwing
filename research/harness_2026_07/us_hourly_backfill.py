"""P2: NASDAQ hourly bars backfill (yfinance 1h, ~730d limit) for session-feature research.
Universe: panel symbols with liq20>=$100M recent (tradeable tier only, ~300-400 syms).
Output: ~/research_cache/us_daily/hourly/{SYM}.parquet"""
import os, time, warnings; warnings.filterwarnings("ignore")
import pandas as pd, yfinance as yf

PANEL = os.path.expanduser("~/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet")
OUTD = os.path.expanduser("~/research_cache/us_daily/hourly")
os.makedirs(OUTD, exist_ok=True)
d = pd.read_parquet(PANEL, columns=["symbol","date","liq20"])
d["date"]=pd.to_datetime(d["date"])
recent = d[d["date"] >= d["date"].max() - pd.Timedelta(days=90)]
syms = sorted(recent.groupby("symbol")["liq20"].median().loc[lambda s: s>=1e8].index)
print(f"universe: {len(syms)} symbols (liq20>=$100M)", flush=True)
t0=time.time(); ok=0
for i,s in enumerate(syms):
    fp = os.path.join(OUTD, f"{s}.parquet")
    if os.path.exists(fp): ok+=1; continue
    try:
        h = yf.download(s, period="730d", interval="1h", progress=False, auto_adjust=False)
        if h is not None and len(h) > 500:
            h.columns = [c[0] if isinstance(c, tuple) else c for c in h.columns]
            h.to_parquet(fp); ok+=1
    except Exception:
        pass
    time.sleep(0.3)
    if (i+1)%50==0: print(f"  {i+1}/{len(syms)} ok={ok} ({time.time()-t0:.0f}s)", flush=True)
print(f"DONE ok={ok}/{len(syms)} ({time.time()-t0:.0f}s)", flush=True)
