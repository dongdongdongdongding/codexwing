#!/usr/bin/env python3
"""Live KOSPI INTRADAY SWING producer (Claude lane of the Claude+Codex synthesis).

Model (KR_INTRADAY_3D_T5_CONTEXT_VWAP_GUARD, KOSPI lane): a 3-model ensemble (LGBM/XGB/ET) over
intraday-path features + daily-context features predicts the 3-day +5% MFE touch (y3 = price reaches
+5% within 3 sessions). Close-buy entry (scan-day close), >=100억, with two quality guards found in
the joint study: close_vwap >= 0 (price closed above the day's VWAP = strong tape) AND idx_vol20 >= 8
(market-volatility floor -- the only sub-70% backtest month, 2025-11, was a low-vol regime where +5%
is structurally rare). Top-2 confidence per day. Exit contract = 3-day close hold (no tight stop;
stops reduced expectancy in both Claude and Codex studies).

Backtest (8 OOS months, walk-forward, ~/research_cache/intraday_kospi_regime.py): top2 + close_vwap>=0
+ idx_vol20>=8 -> 85% hit, monthly floor 71% (5/5 >=70), +6.2% 3D close return. KOSPI was held back
in the synthesis for a broken monthly floor; the idx_vol20 guard repairs it, but rests on n=1 weak
month -> shipped LIVE to validate forward (operator decision). Codex runs the KOSDAQ lane separately.

  python3 multi_agent/tools/report_kospi_intraday_swing.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env.local")
except Exception:
    pass
os.environ.setdefault("KIS_ENABLE_LIVE_CALLS", "1")

CACHE = Path(os.path.expanduser("~/research_cache"))
LEDGER = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "kospi_intraday_swing_ledger.jsonl"
REPORT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "kospi_intraday_swing_latest.json"
REPORT_MD = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "kospi_intraday_swing_latest.md"

ITF = ["day_ret", "or30_ret", "morning_ret", "afternoon_ret", "late30_ret", "day_range", "close_loc",
       "close_vwap", "up_min_frac", "intraday_vol", "accel", "gap", "vol_z"]
DLF = ["ret_1d", "ret_3d", "ret_5d", "ret_10d", "ret_20d", "ret_60d", "ma5_dist", "ma20_dist", "ma60_dist",
       "ma120_dist", "ma20_slope", "ma60_slope", "rsi14", "rsi_slope", "dist_hi20", "dist_hi60", "dist_lo20",
       "pos20", "bb_pctb", "atr_pct", "vol_ratio", "turn_z", "obv_slope", "cmf20", "idx_mom20", "idx_vol20"]


def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff(); up = d.clip(lower=0).rolling(n).mean(); dn = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / (dn + 1e-9))


def daily_features(h: pd.DataFrame) -> Dict[str, float]:
    """build_px_long-matching daily features from a stock's daily OHLCV (latest row)."""
    c, o, hi, lo, v = h["Close"], h["Open"], h["High"], h["Low"], h["Volume"]
    f: Dict[str, float] = {}
    for n in (1, 3, 5, 10, 20, 60):
        f[f"ret_{n}d"] = (c.iloc[-1] / c.iloc[-1 - n] - 1) * 100 if len(c) > n else np.nan
    for n in (5, 20, 60, 120):
        f[f"ma{n}_dist"] = (c.iloc[-1] / c.rolling(n).mean().iloc[-1] - 1) * 100 if len(c) >= n else np.nan
    f["ma20_slope"] = (c.rolling(20).mean().iloc[-1] / c.rolling(20).mean().iloc[-6] - 1) * 100 if len(c) >= 26 else np.nan
    f["ma60_slope"] = (c.rolling(60).mean().iloc[-1] / c.rolling(60).mean().iloc[-11] - 1) * 100 if len(c) >= 71 else np.nan
    f["rsi14"] = float(_rsi(c).iloc[-1]); f["rsi_slope"] = float(_rsi(c).iloc[-1] - _rsi(c).iloc[-6]) if len(c) > 20 else np.nan
    f["dist_hi20"] = (c.iloc[-1] / hi.rolling(20).max().iloc[-1] - 1) * 100 if len(c) >= 20 else np.nan
    f["dist_hi60"] = (c.iloc[-1] / hi.rolling(60).max().iloc[-1] - 1) * 100 if len(c) >= 60 else np.nan
    f["dist_lo20"] = (c.iloc[-1] / lo.rolling(20).min().iloc[-1] - 1) * 100 if len(c) >= 20 else np.nan
    f["pos20"] = float((c.iloc[-1] - lo.rolling(20).min().iloc[-1]) / (hi.rolling(20).max().iloc[-1] - lo.rolling(20).min().iloc[-1] + 1e-9)) if len(c) >= 20 else np.nan
    m20 = c.rolling(20).mean().iloc[-1] if len(c) >= 20 else np.nan; sd20 = c.rolling(20).std().iloc[-1] if len(c) >= 20 else np.nan
    f["bb_pctb"] = float((c.iloc[-1] - (m20 - 2 * sd20)) / (4 * sd20 + 1e-9)) if len(c) >= 20 else np.nan
    tr = pd.concat([hi - lo, (hi - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    f["atr_pct"] = float(tr.rolling(14).mean().iloc[-1] / c.iloc[-1] * 100) if len(c) >= 14 else np.nan
    f["vol_ratio"] = float(v.iloc[-1] / v.rolling(20).mean().iloc[-1]) if len(c) >= 20 else np.nan
    f["turn_z"] = float((v.iloc[-1] - v.rolling(60).mean().iloc[-1]) / (v.rolling(60).std().iloc[-1] + 1e-9)) if len(c) >= 60 else np.nan
    obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
    f["obv_slope"] = float((obv.iloc[-1] - obv.iloc[-11]) / (v.rolling(20).mean().iloc[-1] * 10 + 1e-9)) if len(c) >= 20 else np.nan
    mfm = ((c - lo) - (hi - c)) / (hi - lo + 1e-9); f["cmf20"] = float((mfm * v).rolling(20).sum().iloc[-1] / (v.rolling(20).sum().iloc[-1] + 1e-9)) if len(c) >= 20 else np.nan
    return f


def intraday_features(g: pd.DataFrame, prev_close: float, vol_hist: Optional[pd.Series]) -> Optional[Dict[str, float]]:
    """Intraday-path features from one day's 1-min OHLCV (matches ~/research_cache/intraday_3d_panel.py)."""
    g = g.sort_index()
    if len(g) < 60:
        return None
    t = pd.to_datetime(g.index).time
    o = g["Open"].iloc[0]; c = g["Close"].iloc[-1]; hi = g["High"].max(); lo = g["Low"].min()
    if o <= 0 or c <= 0:
        return None
    vwap = (g["Close"] * g["Volume"]).sum() / (g["Volume"].sum() + 1)
    T0930 = pd.Timestamp("09:30").time(); NOON = pd.Timestamp("12:00").time(); T1500 = pd.Timestamp("15:00").time()
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
            "vol_z": vol_z, "_close": c, "_liq": float(c * vol)}


def _train():
    import lightgbm as lgb, xgboost as xgb
    from sklearn.ensemble import ExtraTreesClassifier
    P = pd.read_parquet(CACHE / "intraday_3d_panel.parquet"); P["date"] = pd.to_datetime(P["date"])
    px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date"] + DLF)
    px["code"] = px["code"].astype(str); px["date"] = pd.to_datetime(px["date"]); px = px.rename(columns={c: c + "_d" for c in DLF})
    P = P[P["mkt"] == "KOSPI"].merge(px, on=["code", "date"], how="left")
    FEAT = ITF + [c + "_d" for c in DLF]
    d = P.dropna(subset=ITF + ["y3"]).copy()
    X = d[FEAT].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0); y = d["y3"]
    mk = [lgb.LGBMClassifier(n_estimators=400, learning_rate=0.04, num_leaves=31, min_child_samples=60, subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1),
          xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.04, subsample=0.8, colsample_bytree=0.7, reg_lambda=3, verbosity=0, n_jobs=-1),
          ExtraTreesClassifier(n_estimators=250, min_samples_leaf=40, random_state=0, n_jobs=-1)]
    for m in mk:
        m.fit(X, y)
    return mk, FEAT


def score_today(min_liq: float) -> List[Dict[str, Any]]:
    import FinanceDataReader as fdr
    from modules.kis_openapi import KISOpenAPIClient, KISConfig
    from modules.kis_operational_adapter import normalize_kis_minute_bars
    mk, FEAT = _train()
    # universe + KS11 vol context
    pxl = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "liq", "market"])
    pxl = pxl[pxl["market"] == "KOSPI"]; pxl["date"] = pd.to_datetime(pxl["date"])
    recent = pxl[pxl["date"] >= pxl["date"].max() - pd.Timedelta(days=90)]
    codes = recent.groupby("code")["liq"].median().loc[lambda s: s >= min_liq * 1e8].index.astype(str).tolist()
    ks = pd.to_numeric(fdr.DataReader("KS11", (datetime.now().year - 1).__str__() + "-01-01")["Close"], errors="coerce").dropna()
    idx_mom20 = float((ks.iloc[-1] / ks.iloc[-21] - 1) * 100); idx_vol20 = float(ks.pct_change().iloc[-20:].std() * 100 * np.sqrt(20))
    cli = KISOpenAPIClient(KISConfig.from_env()); cli.get_access_token()
    HOURS = ["153000", "133000", "113000", "100000"]
    trade_date = datetime.now().strftime("%Y%m%d")   # KST trade date; daily_minute_bars gives full session post-close
    rows = []
    for code in codes:
        try:
            h = fdr.DataReader(code, (datetime.now().year - 2).__str__() + "-01-01")
        except Exception:
            continue
        if h is None or len(h) < 130:
            continue
        dfe = daily_features(h)
        # today's minute bars (full session)
        parts = []
        for hh in HOURS:
            try:
                pl = cli.daily_minute_bars(code, trade_date=trade_date, input_hour=hh, include_past=True)
                fr = normalize_kis_minute_bars(code, pl, trade_date=trade_date)
                if len(fr):
                    parts.append(fr)
            except Exception:
                pass
            time.sleep(0.02)
        if not parts:
            continue
        m = pd.concat(parts); m = m[~m.index.duplicated(keep="first")].sort_index()
        mi = pd.to_datetime(m.index)
        m = m[(mi.strftime("%Y%m%d") == trade_date) & (mi.time >= pd.Timestamp("09:00").time()) & (mi.time <= pd.Timestamp("15:30").time())]
        if len(m) < 60:
            continue
        itf = intraday_features(m, float(h["Close"].iloc[-2]), h["Volume"].tail(20))
        if itf is None:
            continue
        feat = {**itf, **{k + "_d": v for k, v in dfe.items()}, "idx_mom20_d": idx_mom20, "idx_vol20_d": idx_vol20}
        x = pd.Series(feat).reindex(FEAT).replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
        p = float(np.mean([mm.predict_proba(x.values.reshape(1, -1))[:, 1][0] for mm in mk]))
        rows.append({"code": code, "p": p, "close_vwap": itf["close_vwap"], "liq": itf["_liq"], "close": itf["_close"]})
    if not rows:
        return []
    X = pd.DataFrame(rows)
    # guards: tradeable liq, VWAP-positive tape, market-vol floor; then top-2 by prob
    X = X[(X["liq"] >= min_liq * 1e8) & (X["close_vwap"] >= 0)]
    if idx_vol20 < 8 or X.empty:
        return []
    top = X.nlargest(2, "p")
    return [{"ticker": str(r["code"]) + ".KS", "market": "KOSPI", "p": round(float(r["p"]), 4),
             "liq억": round(float(r["liq"]) / 1e8, 1), "close_vwap": round(float(r["close_vwap"]), 2),
             "entry_reference_price": round(float(r["close"]), 1)} for _, r in top.iterrows()]


def resolve_pending(today: str) -> Dict[str, Any]:
    import FinanceDataReader as fdr
    if not LEDGER.exists():
        return {"resolved": 0, "touch5_pct": None, "ret3d_avg": None}
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = False
    for row in rows:
        if row.get("touch5") is not None:
            continue
        d = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.isna(d) or (pd.Timestamp(today) - d).days < 6:
            continue
        try:
            bare = str(row["ticker"]).replace(".KS", "")
            h = fdr.DataReader(bare, str(d.date()))
            c0 = float(pd.to_numeric(h["Close"], errors="coerce").iloc[0])
            fhi = pd.to_numeric(h["High"], errors="coerce").iloc[1:4]; fc = pd.to_numeric(h["Close"], errors="coerce").iloc[1:4]
            if len(fhi) >= 1:
                row["touch5"] = int((fhi.max() / c0 - 1) * 100 >= 5)
                row["ret3d"] = round(float((fc.iloc[-1] / c0 - 1) * 100), 2); changed = True
        except Exception:
            pass
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    res = [r for r in rows if r.get("touch5") is not None]
    if not res:
        return {"resolved": 0, "touch5_pct": None, "ret3d_avg": None}
    return {"resolved": len(res), "touch5_pct": round(float(np.mean([r["touch5"] for r in res]) * 100), 1),
            "ret3d_avg": round(float(np.mean([r["ret3d"] for r in res])), 2)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Live KOSPI intraday SWING producer (3D +5%, VWAP+vol guard).")
    ap.add_argument("--min-liq", type=float, default=100.0)
    args = ap.parse_args()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        picks = score_today(args.min_liq)
    except Exception as exc:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps({"error": repr(exc)[:300], "today": today}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"error": repr(exc)[:200]}, ensure_ascii=False)); return
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        for p in picks:
            fh.write(json.dumps({"date": today, "touch5": None, "ret3d": None, **p}, ensure_ascii=False) + "\n")
    summary = resolve_pending(today)
    production = os.getenv("AG_KOSPI_INTRADAY_PRODUCTION", "1").strip() not in ("0", "", "false", "False")
    routed = 0
    if production and picks:
        try:
            from report_swing_ensemble import _route_live  # reuse proven dual-write parity
        except Exception:
            sys.path.insert(0, str(Path(__file__).resolve().parent)); from report_swing_ensemble import _route_live
        try:
            routed = _route_live(picks, "KOSPI-ITD-" + today.replace("-", ""), datetime.now(timezone.utc).isoformat(),
                                 bucket="kospi_intraday", decision="KOSPI_INTRADAY_BUY", lane="KOSPI_INTRADAY")
        except Exception as exc:
            routed = -1; print(json.dumps({"route_error": repr(exc)[:200]}, ensure_ascii=False))
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "today": today, "lane": "kospi_intraday (Claude)",
              "picks": picks, "forward_summary": summary, "production_enabled": production, "routed": routed,
              "note": "KOSPI intraday 3D+5% ensemble (intraday+daily ctx), close_vwap>=0 + idx_vol20>=8 guards, top2, "
                      "3D close hold. Backtest hit 85%/floor 71%/+6.2%. Live to validate (n=1 weak-month guard)."}
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# KOSPI intraday SWING (3D +5%) — {today}", "",
             f"- picks: {len(picks)} | routed: {routed} | production: {production}",
             f"- forward: n={summary['resolved']} touch5%={summary['touch5_pct']}% ret3d_avg={summary['ret3d_avg']}%", "",
             "| Ticker | p | liq(억) | close_vwap |", "|---|---:|---:|---:|"]
    for p in picks:
        lines.append(f"| {p['ticker']} | {p['p']:.3f} | {p['liq억']} | {p['close_vwap']} |")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"picks": len(picks), "routed": routed, "forward": summary, "production": production}, ensure_ascii=False))


if __name__ == "__main__":
    main()
