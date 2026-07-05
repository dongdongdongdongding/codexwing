#!/usr/bin/env python3
"""Build 5-min sequence dataset aligned to intraday_3d_panel rows (swing-main-jszr Exp2).

Per panel row (code,date): day's 1-min bars -> 5-min bars (09:00-15:30, 78 slots),
features per bar: [logret_close, range_pct, vol_share, cum_vwap_dist, minute_pos].
Output: seq_dataset.npz  (X [n,78,5] float32, keys code/date aligned arrays).
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from pathlib import Path

CACHE = Path(os.path.expanduser("~/research_cache"))
OUTP = Path(os.path.dirname(os.path.abspath(__file__))) / "seq_dataset.npz"
SLOTS = 78  # 6.5h * 12

P = pd.read_parquet(CACHE / "intraday_3d_panel.parquet", columns=["code", "date", "mkt"])
P["code"] = P["code"].astype(str).str.zfill(6)
P["date"] = pd.to_datetime(P["date"])
need = P.groupby("code")["date"].apply(lambda s: set(s.dt.normalize())).to_dict()
print(f"panel rows={len(P)} codes={len(need)}", flush=True)

Xs, codes_out, dates_out = [], [], []
t0 = pd.Timestamp("09:00").time(); t1 = pd.Timestamp("15:30").time()
import time as _t
start = _t.time()
for i, (code, dates) in enumerate(sorted(need.items())):
    fp = CACHE / "intraday" / f"{code}.parquet"
    if not fp.exists():
        alt = CACHE / "intraday" / f"{code.lstrip('0') or code}.parquet"
        if alt.exists():
            fp = alt
        else:
            continue
    try:
        m = pd.read_parquet(fp, columns=["Open", "High", "Low", "Close", "Volume"])
    except Exception:
        continue
    m.index = pd.to_datetime(m.index)
    tt = m.index.time
    m = m[(tt >= t0) & (tt <= t1)]
    if m.empty:
        continue
    m["_d"] = m.index.normalize()
    for day, g in m.groupby("_d"):
        if day not in dates or len(g) < 60:
            continue
        r5 = g.resample("5min").agg({"Open": "first", "High": "max", "Low": "min",
                                     "Close": "last", "Volume": "sum"}).dropna(subset=["Close"])
        if len(r5) < 30:
            continue
        c = r5["Close"].values; h = r5["High"].values; lo = r5["Low"].values; v = r5["Volume"].values
        logret = np.diff(np.log(np.maximum(c, 1e-9)), prepend=np.log(max(c[0], 1e-9)))
        logret[0] = 0.0
        rng = (h - lo) / np.maximum(c, 1e-9)
        vsh = v / max(v.sum(), 1.0)
        cumv = np.cumsum(v); cumpv = np.cumsum(c * v)
        vwap = cumpv / np.maximum(cumv, 1e-9)
        vdist = c / np.maximum(vwap, 1e-9) - 1.0
        pos = np.linspace(0, 1, len(c))
        feat = np.stack([logret * 100, rng * 100, vsh * 100, vdist * 100, pos], axis=1).astype(np.float32)
        arr = np.zeros((SLOTS, 5), dtype=np.float32)
        arr[:min(SLOTS, len(feat))] = feat[:SLOTS]
        Xs.append(arr); codes_out.append(code); dates_out.append(str(day.date()))
    if (i + 1) % 300 == 0:
        print(f"  {i+1}/{len(need)} rows={len(Xs)} ({_t.time()-start:.0f}s)", flush=True)

X = np.stack(Xs) if Xs else np.zeros((0, SLOTS, 5), dtype=np.float32)
np.savez_compressed(OUTP, X=X, code=np.array(codes_out), date=np.array(dates_out))
print(f"DONE rows={len(X)} -> {OUTP} ({_t.time()-start:.0f}s)", flush=True)
