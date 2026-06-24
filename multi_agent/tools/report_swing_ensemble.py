#!/usr/bin/env python3
"""Live SWING producer — daily price-ML ENSEMBLE (structure 1 of the 2-structure SWING scan).

Structure 1 (this tool): a calibrated 3-model ensemble (LGBM/XGB/ExtraTrees) over price-only
features predicts first-touch ft_5_5 (price touches +5% before -5% within 5 sessions), restricted
to >=100억 daily trading value, emitting only the top ~1% highest-confidence names per market.
Validated 2026-06-24 (Claude+Codex, 8y walk-forward, same-day size-matched): the top-1% confidence
slice hits ft_5_5 ~66-67% (KOSPI/KOSDAQ), durable across regimes, with a +5/-5 structure that gives
8:2-style downside control. It does NOT reach the 75% accuracy goal (efficient-market ceiling ~70%),
so it is shipped to validate live. Structure 2 = Exception Leader (unchanged, from the planner).

LIVE per operator decision (2026-06-24): routes to the live surface AND records a ledger that
auto-resolves the realised 5D ft_5_5 outcome + first-touch return, so the edge is measured while
live. Both markets (KOSPI + KOSDAQ), scan_mode=SWING.

  python3 multi_agent/tools/report_swing_ensemble.py [--top-pct 1.0] [--min-liq 100]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
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

CACHE = Path(os.path.expanduser("~/research_cache"))
LEDGER = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "swing_ensemble_ledger.jsonl"
REPORT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "swing_ensemble_latest.json"
REPORT_MD = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "swing_ensemble_latest.md"

FEAT = ["ret_1d", "ret_3d", "ret_5d", "ret_10d", "ret_20d", "ret_60d", "ma5_dist", "ma20_dist", "ma60_dist",
        "ma120_dist", "ma20_slope", "ma60_slope", "rsi14", "rsi_slope", "accel", "consec_up", "dist_hi20",
        "dist_hi60", "dist_hi120", "dist_lo20", "dist_lo60", "pos20", "bb_pctb", "bb_bw", "atr_pct", "vol20",
        "close_loc", "gap", "vol_ratio", "vol_trend", "turn_z", "obv_slope", "cmf20"]


def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff(); up = d.clip(lower=0).rolling(n).mean(); dn = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / (dn + 1e-9))


def compute_features(h: pd.DataFrame) -> pd.DataFrame:
    """Identical to ~/research_cache/build_px_long.py so live features match the training panel."""
    c, o, hi, lo, v = h["Close"], h["Open"], h["High"], h["Low"], h["Volume"]
    f = pd.DataFrame(index=h.index)
    for n in (1, 3, 5, 10, 20, 60):
        f[f"ret_{n}d"] = c.pct_change(n) * 100
    for n in (5, 20, 60, 120):
        f[f"ma{n}_dist"] = (c / c.rolling(n).mean() - 1) * 100
    f["ma20_slope"] = (c.rolling(20).mean() / c.rolling(20).mean().shift(5) - 1) * 100
    f["ma60_slope"] = (c.rolling(60).mean() / c.rolling(60).mean().shift(10) - 1) * 100
    f["rsi14"] = _rsi(c); f["rsi_slope"] = f["rsi14"] - f["rsi14"].shift(5)
    f["accel"] = c.pct_change(5) * 100 - c.pct_change(5).shift(5) * 100
    up = (c > c.shift(1)).astype(int); f["consec_up"] = up.groupby((up != up.shift()).cumsum()).cumsum() * up
    f["dist_hi20"] = (c / hi.rolling(20).max() - 1) * 100; f["dist_hi60"] = (c / hi.rolling(60).max() - 1) * 100
    f["dist_hi120"] = (c / hi.rolling(120).max() - 1) * 100
    f["dist_lo20"] = (c / lo.rolling(20).min() - 1) * 100; f["dist_lo60"] = (c / lo.rolling(60).min() - 1) * 100
    f["pos20"] = (c - lo.rolling(20).min()) / (hi.rolling(20).max() - lo.rolling(20).min() + 1e-9)
    m20 = c.rolling(20).mean(); sd20 = c.rolling(20).std()
    f["bb_pctb"] = (c - (m20 - 2 * sd20)) / (4 * sd20 + 1e-9); f["bb_bw"] = (4 * sd20) / (m20 + 1e-9) * 100
    tr = pd.concat([hi - lo, (hi - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
    f["atr_pct"] = tr.rolling(14).mean() / c * 100; f["vol20"] = c.pct_change().rolling(20).std() * 100
    f["close_loc"] = (c - lo) / (hi - lo + 1e-9); f["gap"] = (o / c.shift(1) - 1) * 100
    f["vol_ratio"] = v / v.rolling(20).mean(); f["vol_trend"] = v.rolling(5).mean() / v.rolling(20).mean()
    f["turn_z"] = (v - v.rolling(60).mean()) / (v.rolling(60).std() + 1e-9)
    obv = (np.sign(c.diff()) * v).fillna(0).cumsum(); f["obv_slope"] = (obv - obv.shift(10)) / (v.rolling(20).mean() * 10 + 1e-9)
    mfm = ((c - lo) - (hi - c)) / (hi - lo + 1e-9); f["cmf20"] = (mfm * v).rolling(20).sum() / (v.rolling(20).sum() + 1e-9)
    return f


def _train_ensemble(market: str, trailing_days: int = 600):
    import lightgbm as lgb, xgboost as xgb
    from sklearn.ensemble import ExtraTreesClassifier
    px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "market", "ft_5_5"] + FEAT)
    px = px[px["market"] == market]; px["date"] = pd.to_datetime(px["date"])
    px = px[px["date"] >= px["date"].max() - pd.Timedelta(days=trailing_days)].dropna(subset=FEAT + ["ft_5_5"])
    X = px[FEAT].replace([np.inf, -np.inf], np.nan).clip(-1e6, 1e6).fillna(0); y = px["ft_5_5"]
    mk = [lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31, min_child_samples=80,
                             subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1),
          xgb.XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8,
                            colsample_bytree=0.7, reg_lambda=3, verbosity=0, n_jobs=-1),
          ExtraTreesClassifier(n_estimators=200, min_samples_leaf=50, random_state=0, n_jobs=-1)]
    for m in mk:
        m.fit(X, y)
    return mk


def _liquid_universe(market: str, min_liq_eok: float) -> List[str]:
    """Codes whose recent median daily trading value >= min_liq_eok (억), from the research panel."""
    px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "liq", "market"])
    px = px[px["market"] == market]; px["date"] = pd.to_datetime(px["date"])
    recent = px[px["date"] >= px["date"].max() - pd.Timedelta(days=90)]
    med = recent.groupby("code")["liq"].median()
    return med[med >= min_liq_eok * 1e8].index.astype(str).tolist()


def score_market(market: str, top_pct: float, min_liq: float) -> List[Dict[str, Any]]:
    import FinanceDataReader as fdr
    mk = _train_ensemble(market)
    codes = _liquid_universe(market, min_liq)
    start = f"{datetime.now().year - 2}-01-01"; rows = []
    for code in codes:
        try:
            h = fdr.DataReader(code, start)
        except Exception:
            continue
        if h is None or len(h) < 130 or "Close" not in h.columns:
            continue
        feat = compute_features(h).iloc[-1]
        x = feat.reindex(FEAT).replace([np.inf, -np.inf], np.nan).clip(-1e6, 1e6).fillna(0)
        p = float(np.mean([m.predict_proba(x.values.reshape(1, -1))[:, 1][0] for m in mk]))
        liq = float((h["Close"] * h["Volume"]).tail(20).mean())
        rows.append({"code": code, "p": p, "liq": liq, "close": float(h["Close"].iloc[-1])})
    if not rows:
        return []
    X = pd.DataFrame(rows)
    X = X[X["liq"] >= min_liq * 1e8]          # enforce tradeable liquidity at emission (fresh 20D value)
    if X.empty:
        return []
    thr = X["p"].quantile(1 - top_pct / 100.0)
    sfx = ".KS" if market == "KOSPI" else ".KQ"
    picks = []
    for _, r in X[X["p"] >= thr].sort_values("p", ascending=False).iterrows():
        picks.append({"ticker": str(r["code"]) + sfx, "market": market, "p": round(float(r["p"]), 4),
                      "liq억": round(float(r["liq"]) / 1e8, 1), "entry_reference_price": round(float(r["close"]), 1)})
    return picks


def resolve_pending(today: str) -> Dict[str, Any]:
    import FinanceDataReader as fdr
    if not LEDGER.exists():
        return {"resolved": 0, "ft55_hit_pct": None, "first_touch_ret_avg": None}
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = False
    for row in rows:
        if row.get("ft55") is not None:
            continue
        d = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.isna(d) or (pd.Timestamp(today) - d).days < 9:
            continue
        try:
            bare = str(row["ticker"]).replace(".KS", "").replace(".KQ", "")
            h = fdr.DataReader(bare, str(d.date()))
            o = pd.to_numeric(h["Open"], errors="coerce"); hi = pd.to_numeric(h["High"], errors="coerce"); lo = pd.to_numeric(h["Low"], errors="coerce")
            if len(o) >= 6:
                entry = float(o.iloc[1]); ub = entry * 1.05; lb = entry * 0.95; hit = None; ret = None
                for k in range(1, 6):
                    if hi.iloc[k] >= ub:
                        hit = 1; ret = 5.0; break
                    if lo.iloc[k] <= lb:
                        hit = 0; ret = -5.0; break
                if hit is None:
                    hit = 0; ret = float((pd.to_numeric(h["Close"], errors="coerce").iloc[5] / entry - 1) * 100)
                row["ft55"] = hit; row["first_touch_ret"] = round(ret, 2); changed = True
        except Exception:
            pass
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    res = [r for r in rows if r.get("ft55") is not None]
    if not res:
        return {"resolved": 0, "ft55_hit_pct": None, "first_touch_ret_avg": None}
    return {"resolved": len(res), "ft55_hit_pct": round(float(np.mean([r["ft55"] for r in res]) * 100), 1),
            "first_touch_ret_avg": round(float(np.mean([r["first_touch_ret"] for r in res])), 2)}


def _route_live(picks: List[Dict[str, Any]], run_id: str, recommended_at: str) -> int:
    from modules.db_schema import build_scan_result_payload
    from modules.db_manager import DBManager
    from modules.top_deep_report import generate_and_store_top_deep_reports
    db = DBManager(); n = 0
    by_market: Dict[str, List[Dict[str, Any]]] = {}
    for i, p in enumerate(sorted(picks, key=lambda x: -x["p"]), start=1):
        src = {"ticker": p["ticker"], "market_type": p["market"], "scan_mode": "SWING", "decision_score": p["p"],
               "ml_prob": round(p["p"] * 100, 2), "run_id": run_id, "priority_rank": i, "decision": "SWING_ENSEMBLE_BUY",
               "decision_bucket": "swing_ensemble", "recommended_at": recommended_at, "selection_lane": "SWING_ENSEMBLE",
               "entry_reference_price": p.get("entry_reference_price")}
        payload = build_scan_result_payload(src, overrides={"market": p["market"], "recommended_at": recommended_at})
        payload["allow_incomplete_scan_result"] = True
        db.upsert_scan_result(payload); n += 1
        by_market.setdefault(p["market"], []).append({**src, "allow_incomplete_scan_result": True})
    for mkt, mrows in by_market.items():
        try:
            generate_and_store_top_deep_reports(scan_rows=mrows, planner_payload={}, run_id=run_id, market=mkt,
                                                scan_mode="SWING", top_n=len(mrows), write_db=True)
        except Exception as exc:
            print(json.dumps({"deep_report_error": repr(exc)[:160]}, ensure_ascii=False))
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="Live SWING price-ML ensemble producer (both markets).")
    ap.add_argument("--top-pct", type=float, default=1.0)
    ap.add_argument("--min-liq", type=float, default=100.0)
    args = ap.parse_args()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    picks: List[Dict[str, Any]] = []
    per_market: Dict[str, int] = {}
    for market in ("KOSPI", "KOSDAQ"):
        try:
            mp = score_market(market, args.top_pct, args.min_liq)
        except Exception as exc:
            print(json.dumps({"error": f"{market}:{repr(exc)[:160]}"}, ensure_ascii=False)); mp = []
        per_market[market] = len(mp); picks += mp

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        for p in picks:
            fh.write(json.dumps({"date": today, "ft55": None, "first_touch_ret": None, **p}, ensure_ascii=False) + "\n")
    summary = resolve_pending(today)

    production = os.getenv("AG_SWING_ENSEMBLE_PRODUCTION", "1").strip() not in ("0", "", "false", "False")
    routed = 0
    if production and picks:
        try:
            routed = _route_live(picks, "SWING-ENS-" + today.replace("-", ""), datetime.now(timezone.utc).isoformat())
        except Exception as exc:
            routed = -1; print(json.dumps({"route_error": repr(exc)[:200]}, ensure_ascii=False))

    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "today": today, "structure": "swing_ensemble (1 of 2)",
              "top_pct": args.top_pct, "min_liq": args.min_liq, "per_market": per_market, "picks": picks,
              "forward_summary": summary, "production_enabled": production, "routed": routed,
              "note": "Live SWING structure-1 = price-ML ensemble -> ft_5_5 top~1%, KOSPI+KOSDAQ, >=100억. "
                      "Validated 8y size-matched (hit ~66-67%, not 75%). Structure-2 = Exception Leader (planner)."}
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# SWING ensemble (structure 1/2) — {today}", "",
             f"- per-market picks: {per_market} | routed live: {routed} | production: {production}",
             f"- forward (resolved): n={summary['resolved']} ft_5_5 hit={summary['ft55_hit_pct']}% "
             f"first-touch ret avg={summary['first_touch_ret_avg']}%", "",
             "| Market | Ticker | p | liq(억) |", "|---|---|---:|---:|"]
    for p in sorted(picks, key=lambda x: -x["p"]):
        lines.append(f"| {p['market']} | {p['ticker']} | {p['p']:.3f} | {p['liq억']} |")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"per_market": per_market, "picks": len(picks), "routed": routed, "forward": summary,
                      "production": production}, ensure_ascii=False))


if __name__ == "__main__":
    main()
