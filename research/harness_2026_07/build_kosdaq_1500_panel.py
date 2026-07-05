#!/usr/bin/env python3
"""Rebuild the KOSDAQ 15:00 training panel with the PRODUCTION feature functions
(modules.kosdaq_intraday_vwap_guard.compute_pre_entry_features / compute_daily_prev_context)
for the wvdd LambdaRank revalidation. Labels: touch3d_t5 (bundle target) +
policy_t10_h5 (promoted contract realized return, entry = 15:00 price).
Output: kosdaq_1500_panel.parquet
"""
import os, sys, time, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
from modules.kosdaq_intraday_vwap_guard import compute_pre_entry_features, compute_daily_prev_context

CACHE = Path(os.path.expanduser("~/research_cache"))
OUT = Path(os.path.dirname(os.path.abspath(__file__))) / "kosdaq_1500_panel.parquet"
MIN_LIQ_EOK = 30.0

px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "market", "liq", "idx_mom20", "idx_vol20"])
px["code"] = px["code"].astype(str).str.zfill(6)
px["date"] = pd.to_datetime(px["date"])
kq = px[px["market"] == "KOSDAQ"]
liq_map = kq.set_index(["code", "date"])["liq"]
idx_map = kq.drop_duplicates("date").set_index("date")[["idx_mom20", "idx_vol20"]]

ohlc = pd.read_parquet(CACHE / "ohlc_daily.parquet")
ohlc["code"] = ohlc["code"].astype(str).str.zfill(6)
ohlc["date"] = pd.to_datetime(ohlc["date"])
ohlc = ohlc.sort_values(["code", "date"])
og = {c: g.reset_index(drop=True) for c, g in ohlc.groupby("code")}

codes = sorted(set(kq["code"].unique()) & set(og.keys()))
rows = []
t0 = time.time()
done = 0
for code in codes:
    fp = CACHE / "intraday" / f"{code}.parquet"
    if not fp.exists():
        continue
    try:
        m = pd.read_parquet(fp)
    except Exception:
        continue
    m.index = pd.to_datetime(m.index)
    tt = m.index.time
    m = m[(tt >= pd.Timestamp("09:00").time()) & (tt <= pd.Timestamp("15:30").time())]
    if m.empty:
        continue
    m["_d"] = m.index.normalize()
    dd = og[code]
    # daily bars frame in the module's expected shape (date-indexed OHLCV-ish)
    dframe = dd.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}).copy()
    dframe["Volume"] = 0.0
    dframe = dframe.set_index("date")
    didx = {d: i for i, d in enumerate(dd["date"])}
    for day, g in m.groupby("_d"):
        i = didx.get(day)
        if i is None or i == 0 or len(g) < 60:
            continue
        prev_close = float(dd["close"].iloc[i - 1])
        # liq of PREV day (production uses liq_prev)
        liq_prev = liq_map.get((code, dd["date"].iloc[i - 1]), np.nan)
        if not np.isfinite(liq_prev) or liq_prev < MIN_LIQ_EOK * 1e8:
            continue
        tstr = day.strftime("%Y%m%d")
        try:
            idxrow = idx_map.loc[day] if day in idx_map.index else None
            ctx = compute_daily_prev_context(dframe.loc[:day], trade_date=tstr,
                                             index_context={"idx_mom20_prev": (float(idxrow["idx_mom20"]) if idxrow is not None else None),
                                                            "idx_vol20_prev": (float(idxrow["idx_vol20"]) if idxrow is not None else None)})
            feat = compute_pre_entry_features(g, prev_close=prev_close, liq_prev_eok=liq_prev / 1e8, trade_date=tstr)
        except Exception:
            continue
        if not isinstance(feat, dict) or feat.get("entry_reference_price") is None:
            continue
        entry = float(feat["entry_reference_price"])
        if entry <= 0:
            continue
        # labels from ohlc paths after day
        fut = dd.iloc[i + 1:i + 6]
        if len(fut) < 1:
            continue
        touch3 = 1.0 if len(fut) >= 3 and float(fut["high"].iloc[:3].max()) >= entry * 1.05 else (0.0 if len(fut) >= 3 else np.nan)
        pol = np.nan
        if len(fut) >= 5:
            tgt = entry * 1.10
            pol = (float(fut["close"].iloc[4]) / entry - 1) * 100
            for k in range(5):
                if float(fut["high"].iloc[k]) >= tgt:
                    o = float(fut["open"].iloc[k])
                    fill = max(tgt, o) if (k > 0 and np.isfinite(o) and o > 0) else tgt
                    pol = (fill / entry - 1) * 100
                    break
        rec = {"code": code, "date": day, "entry": entry, "liq_prev_eok": liq_prev / 1e8,
               "touch3d_t5": touch3, "policy_t10_h5": pol}
        rec.update({k: v for k, v in ctx.items() if isinstance(v, (int, float))})
        rec.update({k: v for k, v in feat.items() if isinstance(v, (int, float))})
        rows.append(rec)
    done += 1
    if done % 100 == 0:
        print(f"  {done} codes, rows={len(rows)} ({time.time()-t0:.0f}s)", flush=True)

P = pd.DataFrame(rows)
P.to_parquet(OUT, index=False)
print(f"DONE rows={len(P)} codes={P['code'].nunique()} span={P['date'].min()}..{P['date'].max()} -> {OUT} ({time.time()-t0:.0f}s)", flush=True)
