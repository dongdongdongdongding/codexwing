#!/usr/bin/env python3
"""NASDAQ session-tape shadow lane (swing-main-f9yw, RESEARCH_LOG §12-D). OBSERVATION-ONLY.

Research basis (29mo walk-forward, 351 liquid syms): session-tape rank-1 win 79.3% vs
label-shuffle placebo 69.9% (+9.4pp ~ 5 sigma), EV 1.68 net vs placebo 1.12 — honest true
edge ~+0.5-1.0/trade (half the raw EV is vol-tilt/survivorship/bull-window artifact).
Contract: close(t) entry -> +5% touch within 5 sessions (fill max(open,target)) else 5d close.

Self-consistent single data source: ~/research_cache/us_daily/hourly/{SYM}.parquet — session
features AND daily context are both derived from the hourly cache (no panel-parity risk).
Trains in-process on the full cache (like the KOSPI lane), scores the latest US session,
appends rank-1 to a ledger, auto-resolves with yfinance daily bars. Never routed to buy lists.

  python3 multi_agent/tools/update_us_hourly.py   # refresh cache first (daily ops)
  python3 multi_agent/tools/report_nasdaq_session_tape.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

HOURD = os.path.expanduser("~/research_cache/us_daily/hourly")
USR = PROJECT_ROOT / "runtime_state" / "reports" / "us_research"
LEDGER = USR / "nasdaq_session_tape_ledger.jsonl"
REPORT_JSON = USR / "nasdaq_session_tape_latest.json"
REPORT_MD = USR / "nasdaq_session_tape_latest.md"
COST = 0.25
STF = ["s_day_ret", "s_h1_ret", "s_last_ret", "s_close_loc", "s_range", "s_vwap_dist", "s_up_frac", "s_accel", "s_vol_z"]
DLF = ["ret_1d", "ret_3d", "ret_5d", "ret_10d", "ret_20d", "ret_60d", "ma20_dist", "ma60_dist", "ma120_dist",
       "ma20_slope", "rsi14", "dist_hi20", "dist_hi60", "dist_lo20", "pos20", "bb_pctb", "atr_pct",
       "vol_ratio", "turn_z", "liq20"]
FEAT = STF + DLF


def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / (dn + 1e-9))


def build_symbol(fp: str) -> Optional[pd.DataFrame]:
    """Hourly file -> per-day rows: 9 session features + 20 daily-context features + y label."""
    sym = os.path.basename(fp).replace(".parquet", "")
    try:
        h = pd.read_parquet(fp)
    except Exception:
        return None
    if h.empty or "Close" not in h.columns:
        return None
    h.index = pd.to_datetime(h.index)
    try:
        h.index = h.index.tz_convert("America/New_York")
    except Exception:
        return None
    tt = h.index.time
    h = h[(tt >= pd.Timestamp("09:30").time()) & (tt <= pd.Timestamp("16:00").time())]
    if len(h) < 500:
        return None
    h["_d"] = h.index.normalize().tz_localize(None)
    # daily bars from hourly
    dly = h.groupby("_d").agg(o=("Open", "first"), hi=("High", "max"), lo=("Low", "min"),
                              c=("Close", "last"), v=("Volume", "sum"))
    c, hi, lo, v = dly["c"], dly["hi"], dly["lo"], dly["v"]
    f = pd.DataFrame(index=dly.index)
    for n in (1, 3, 5, 10, 20, 60):
        f[f"ret_{n}d"] = c.pct_change(n) * 100
    for n in (20, 60, 120):
        f[f"ma{n}_dist"] = (c / c.rolling(n).mean() - 1) * 100
    f["ma20_slope"] = (c.rolling(20).mean() / c.rolling(20).mean().shift(5) - 1) * 100
    f["rsi14"] = _rsi(c)
    f["dist_hi20"] = (c / hi.rolling(20).max() - 1) * 100
    f["dist_hi60"] = (c / hi.rolling(60).max() - 1) * 100
    f["dist_lo20"] = (c / lo.rolling(20).min() - 1) * 100
    f["pos20"] = (c - lo.rolling(20).min()) / (hi.rolling(20).max() - lo.rolling(20).min() + 1e-9)
    m20, s20 = c.rolling(20).mean(), c.rolling(20).std()
    f["bb_pctb"] = (c - (m20 - 2 * s20)) / (4 * s20 + 1e-9)
    tr = pd.concat([hi - lo, (hi - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    f["atr_pct"] = tr.rolling(14).mean() / c * 100
    f["vol_ratio"] = v / v.rolling(20).mean()
    f["turn_z"] = (v - v.rolling(60).mean()) / (v.rolling(60).std() + 1e-9)
    f["liq20"] = (c * v).rolling(20).mean()
    # session features per day
    srows = {}
    volhist = dly["v"]
    for day, g in h.groupby("_d"):
        if len(g) < 5:
            continue
        o = float(g["Open"].iloc[0]); cc = float(g["Close"].iloc[-1])
        dhi = float(g["High"].max()); dlo = float(g["Low"].min())
        if o <= 0 or cc <= 0:
            continue
        vv = g["Volume"].values.astype(float)
        vwap = float((g["Close"].values * vv).sum() / (vv.sum() + 1))
        r = g["Close"].pct_change().dropna()
        vh = volhist.loc[:day].iloc[-21:-1]
        vz = float((vv.sum() - vh.mean()) / (vh.std() + 1e-9)) if len(vh) >= 5 else 0.0
        pm = float(g["Close"].iloc[len(g) // 2])
        srows[day] = {"s_day_ret": (cc / o - 1) * 100, "s_h1_ret": (float(g["Close"].iloc[0]) / o - 1) * 100,
                      "s_last_ret": (cc / float(g["Close"].iloc[-2]) - 1) * 100 if len(g) >= 2 else 0.0,
                      "s_close_loc": (cc - dlo) / (dhi - dlo + 1e-9), "s_range": (dhi / dlo - 1) * 100,
                      "s_vwap_dist": (cc / vwap - 1) * 100, "s_up_frac": float((r > 0).mean()),
                      "s_accel": ((cc / pm - 1) - (pm / o - 1)) * 100, "s_vol_z": vz}
    if not srows:
        return None
    S = pd.DataFrame.from_dict(srows, orient="index")
    out = S.join(f, how="inner")
    # label: +5% touch within next 5 sessions from close (for training)
    tgt = c * 1.05
    touched = pd.Series(0.0, index=dly.index)
    fwd_ok = pd.Series(False, index=dly.index)
    for k in range(1, 6):
        hk = hi.shift(-k)
        touched = np.maximum(touched, (hk >= tgt).astype(float).fillna(0))
        if k == 5:
            fwd_ok = hk.notna()
    out["y"] = touched.where(fwd_ok, np.nan)
    out["close"] = c
    out["symbol"] = sym
    return out.reset_index().rename(columns={"index": "date", "_d": "date"})


def _read_ledger() -> List[Dict[str, Any]]:
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]


def resolve_pending(today: pd.Timestamp) -> Dict[str, Any]:
    import yfinance as yf
    rows = _read_ledger()
    changed = False
    for row in rows:
        if row.get("policy_ret") is not None:
            continue
        d = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.isna(d) or (today - d).days < 10:
            continue
        try:
            h = yf.download(row["symbol"], start=str(d.date()), progress=False, auto_adjust=False)
            if h is None or h.empty:
                continue
            h.columns = [c[0] if isinstance(c, tuple) else c for c in h.columns]
            h = h[h.index > d]
            if len(h) < 5:
                continue
            entry = float(row["entry"])
            tgt = entry * 1.05
            win5 = h.iloc[:5]
            ret = (float(win5["Close"].iloc[-1]) / entry - 1) * 100
            touched = 0
            for k in range(5):
                if float(win5["High"].iloc[k]) >= tgt:
                    o = float(win5["Open"].iloc[k])
                    fill = max(tgt, o) if (k > 0 and np.isfinite(o) and o > 0) else tgt
                    ret = (fill / entry - 1) * 100
                    touched = 1
                    break
            row["touch5"] = touched
            row["policy_ret"] = round(ret, 2)
            changed = True
        except Exception:
            continue
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    res = [r for r in rows if r.get("policy_ret") is not None]
    if not res:
        return {"resolved": 0}
    rets = [float(r["policy_ret"]) - COST for r in res]
    return {"resolved": len(res), "touch5_pct": round(float(np.mean([r["touch5"] for r in res])) * 100, 1),
            "ev_net_avg": round(float(np.mean(rets)), 2), "worst": round(float(np.min(rets)), 2)}


def main() -> None:
    import lightgbm as lgb
    files = sorted(glob.glob(os.path.join(HOURD, "*.parquet")))
    parts = [b for b in (build_symbol(fp) for fp in files) if b is not None]
    P = pd.concat(parts, ignore_index=True)
    P["date"] = pd.to_datetime(P["date"])
    latest = P["date"].max()
    tr = P.dropna(subset=["y"] + STF)
    te = P[(P["date"] == latest) & (P["liq20"] >= 1e8)].dropna(subset=STF).copy()
    m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=60,
                           subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1)
    m.fit(tr[FEAT].clip(-1e6, 1e6), tr["y"])
    te["p"] = m.predict_proba(te[FEAT].clip(-1e6, 1e6))[:, 1]
    top = te.nlargest(1, "p")
    now = datetime.now(timezone.utc)
    picks = [{"date": str(latest.date()), "symbol": str(r["symbol"]), "p": round(float(r["p"]), 4),
              "entry": round(float(r["close"]), 2), "tier": "SHADOW",
              "contract": "+5% touch within 5 sessions else 5d close (close entry)"}
             for _, r in top.iterrows()]
    existing = {(r.get("date"), r.get("symbol")) for r in _read_ledger()}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        for p in picks:
            if (p["date"], p["symbol"]) not in existing:
                fh.write(json.dumps({**p, "touch5": None, "policy_ret": None,
                                     "logged_at": now.isoformat()}) + "\n")
    summary = resolve_pending(pd.Timestamp(now.date()))
    report = {"generated_at": now.isoformat(), "as_of": str(latest.date()),
              "capital_status": "observation_only_shadow",
              "expectation": "backtest: rank-1 win 79.3%, EV 1.68 net (placebo-separated +9.4pp/5sig); "
                             "honest true edge ~+0.5-1.0/trade — no capital before forward n>=30",
              "train_rows": int(len(tr)), "universe": int(te["symbol"].nunique()),
              "picks": picks, "forward_summary": summary}
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [f"# NASDAQ session-tape shadow — {report['as_of']}", "",
             f"- observation-only | forward: {summary}", "",
             "| Symbol | p | entry |", "|---|---:|---:|"]
    for p in picks:
        lines.append(f"| {p['symbol']} | {p['p']} | {p['entry']} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"as_of": report["as_of"], "picks": picks, "forward": summary}))


if __name__ == "__main__":
    main()
