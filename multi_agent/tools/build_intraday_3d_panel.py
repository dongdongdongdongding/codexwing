"""Rebuild ~/research_cache/intraday_3d_panel.parquet from the preserved minute cache.

Restores the panel that report_kospi_intraday_swing._train() reads. The original
research builder (intraday_3d_panel.py) was deleted during cleanup; this reconstructs
it from ~/research_cache/intraday/ (per-stock 1-min OHLCV) using the SAME
intraday_features() definition, plus the 3-day +5% MFE touch label (y3).

Panel columns: code, date, mkt, <13 ITF features>, y3.
  (daily-context DLF features are merged from px_long at train time, not stored here.)

Usage: python3 multi_agent/tools/build_intraday_3d_panel.py
Output: ~/research_cache/intraday_3d_panel.parquet
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import numpy as np
import pandas as pd

CACHE = Path(os.path.expanduser("~/research_cache"))
INTRADAY_DIR = CACHE / "intraday"
OUT = CACHE / "intraday_3d_panel.parquet"

ITF = ["day_ret", "or30_ret", "morning_ret", "afternoon_ret", "late30_ret", "day_range", "close_loc",
       "close_vwap", "up_min_frac", "intraday_vol", "accel", "gap", "vol_z"]
TARGET_UP = 0.05   # +5%
HORIZON = 3        # 3 forward trading days (MFE touch)


def _itf_for_day(g: pd.DataFrame, prev_close: float, vol_hist: pd.Series | None):
    """One day's 1-min OHLCV → 13 intraday features. MUST match
    report_kospi_intraday_swing.intraday_features()."""
    g = g.sort_index()
    if len(g) < 60:
        return None
    t = pd.to_datetime(g.index).time
    o = g["Open"].iloc[0]; c = g["Close"].iloc[-1]; hi = g["High"].max(); lo = g["Low"].min()
    if o <= 0 or c <= 0:
        return None
    vwap = (g["Close"] * g["Volume"]).sum() / (g["Volume"].sum() + 1)
    import datetime as _dt
    T0930 = _dt.time(9, 30); NOON = _dt.time(12, 0); T1500 = _dt.time(15, 0)
    p0930 = g[t <= T0930]["Close"].iloc[-1] if (t <= T0930).any() else o
    pnoon = g[t <= NOON]["Close"].iloc[-1] if (t <= NOON).any() else c
    p1500 = g[t <= T1500]["Close"].iloc[-1] if (t <= T1500).any() else c
    r = g["Close"].pct_change()
    vol = g["Volume"].sum()
    vol_z = float((vol - vol_hist.mean()) / (vol_hist.std() + 1e-9)) if vol_hist is not None and len(vol_hist) >= 5 else 0.0
    return {"day_ret": (c / o - 1) * 100, "or30_ret": (p0930 / o - 1) * 100, "morning_ret": (pnoon / o - 1) * 100,
            "afternoon_ret": (c / pnoon - 1) * 100, "late30_ret": (c / p1500 - 1) * 100, "day_range": (hi / lo - 1) * 100,
            "close_loc": float((c - lo) / (hi - lo + 1e-9)), "close_vwap": (c / vwap - 1) * 100,
            "up_min_frac": float((r > 0).mean()), "intraday_vol": float(r.std() * 100),
            "accel": ((c / pnoon - 1) - (pnoon / o - 1)) * 100, "gap": (o / prev_close - 1) * 100 if prev_close else np.nan,
            "vol_z": vol_z}


def main():
    if not INTRADAY_DIR.exists():
        sys.exit(f"minute cache missing: {INTRADAY_DIR}")
    # market map (code -> KOSPI/KOSDAQ)
    mkt_map = {}
    try:
        m = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "market"]).dropna()
        m["code"] = m["code"].astype(str).str.zfill(6)
        mkt_map = m.drop_duplicates("code").set_index("code")["market"].to_dict()
    except Exception as e:
        print(f"[warn] market map unavailable: {e}")
    # daily OHLC for y3 forward-high label
    daily = pd.read_parquet(CACHE / "ohlc_daily.parquet", columns=["date", "high", "close", "code"])
    daily["code"] = daily["code"].astype(str).str.zfill(6)
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values(["code", "date"])
    dgrp = {c: g.reset_index(drop=True) for c, g in daily.groupby("code")}

    files = sorted(INTRADAY_DIR.glob("*.parquet"))
    print(f"[build] {len(files)} stocks, horizon={HORIZON}d +{TARGET_UP:.0%} MFE")
    out_rows = []
    for i, fp in enumerate(files):
        code = fp.stem.zfill(6)
        try:
            m = pd.read_parquet(fp)
        except Exception:
            continue
        if m.empty or "Close" not in m.columns:
            continue
        m.index = pd.to_datetime(m.index)
        tt = m.index.time
        m = m[(tt >= pd.Timestamp("09:00").time()) & (tt <= pd.Timestamp("15:30").time())]
        if m.empty:
            continue
        m["_d"] = m.index.normalize()
        days = sorted(m["_d"].unique())
        # daily volume series (per day total) for vol_z trailing window
        dayvol = m.groupby("_d")["Volume"].sum()
        # daily close/high for y3 (prefer ohlc_daily; fallback to minute)
        dd = dgrp.get(code)
        if dd is not None:
            dd_idx = dd.set_index("date")
        prev_close = None
        for di, day in enumerate(days):
            g = m[m["_d"] == day]
            vol_hist = dayvol.loc[:day].iloc[-21:-1]  # trailing up to 20 prior days
            feat = _itf_for_day(g, prev_close if prev_close else 0.0, vol_hist)
            prev_close = float(g["Close"].iloc[-1])
            if feat is None:
                continue
            # y3: max daily high over next HORIZON days >= ref_close * (1+TARGET_UP)
            y3 = np.nan
            ref = None
            if dd is not None and day in dd_idx.index:
                ref = float(dd_idx.loc[day, "close"]) if np.isscalar(dd_idx.loc[day, "close"]) else None
                fut = dd[dd["date"] > day].head(HORIZON)
                if ref and len(fut) >= 1:
                    y3 = 1.0 if float(fut["high"].max()) >= ref * (1 + TARGET_UP) else 0.0
            if ref is None:  # fallback: minute-derived ref + forward minute highs unavailable → skip label
                continue
            row = {"code": code, "date": pd.Timestamp(day), "mkt": mkt_map.get(code, ""), "y3": y3}
            row.update(feat)
            out_rows.append(row)
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(files)} processed, rows={len(out_rows)}")
    panel = pd.DataFrame(out_rows)
    panel = panel.dropna(subset=ITF + ["y3"])
    panel.to_parquet(OUT, index=False)
    print(f"[done] {OUT} rows={len(panel)} "
          f"KOSPI={int((panel['mkt']=='KOSPI').sum())} KOSDAQ={int((panel['mkt']=='KOSDAQ').sum())} "
          f"y3_pos={panel['y3'].mean():.3f}")


if __name__ == "__main__":
    main()
