#!/usr/bin/env python3
"""Shadow forward-tracker for the calibrated first-touch DOWN-market emission model.

Validated edge (research, ~/research_cache): in a DOWN index regime (index 20D momentum < -2),
a calibrated model over stock-own time-series-normalised features predicts P(price touches +5%
before -5% within 5 sessions). Emitting only candidates with p >= tau gives ~60% first-touch
(8yr OOS: DOWN 중형 56% 6/6yr, 대형 61% 5/6yr). Outside DOWN, the model abstains (no edge).

This is observation-only: writes a JSONL ledger + report, resolves the realised first-touch of
past picks, and only routes picks to the live web/Discord surface when AG_FIRSTTOUCH_DOWN_PRODUCTION=1
(default OFF). The model is built by ~/research_cache/train_firsttouch.py → models/firsttouch_down_v1.pkl.

  python3 multi_agent/tools/report_firsttouch_down_shadow.py [--top-universe 300]
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

MODEL_PATH = PROJECT_ROOT / "models" / "firsttouch_down_v1.pkl"
LEDGER = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "firsttouch_down_shadow_ledger.jsonl"
REPORT_JSON = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "firsttouch_down_shadow_latest.json"
REPORT_MD = PROJECT_ROOT / "runtime_state" / "reports" / "experimental" / "firsttouch_down_shadow_latest.md"


# ---------------------------------------------------------------------------
# Feature computation (MUST match ~/research_cache/build_px.py exactly)
# ---------------------------------------------------------------------------

def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff(); up = d.clip(lower=0).rolling(n).mean(); dn = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / (dn + 1e-9))


def compute_features(h: pd.DataFrame) -> pd.DataFrame:
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


def latest_znorm(feat: pd.DataFrame, features: List[str], roll: int, min_p: int) -> Optional[Dict[str, float]]:
    """z-normalise each feature by its own trailing window; return the latest row's z-values."""
    if len(feat) < min_p:
        return None
    out: Dict[str, float] = {}
    for f in features:
        s = feat[f]
        m = s.rolling(roll, min_periods=min_p).mean(); sd = s.rolling(roll, min_periods=min_p).std()
        z = (s - m) / (sd + 1e-9)
        val = z.iloc[-1]
        out[f + "_z"] = float(np.clip(val, -6, 6)) if pd.notna(val) else np.nan
    return out


# ---------------------------------------------------------------------------
# DB adapters (mirror report_regime_signal_shadow; distinct FIRSTTOUCH_DOWN lane)
# ---------------------------------------------------------------------------

def firsttouch_scan_rows(picks, run_id, recommended_at):
    """market_scan_results payloads. The model emits a calibrated first-touch probability, NOT the
    legacy scanner's alpha/tech/whale features -- so rows carry the real fields we DO have
    (ml_prob=p + volume_ratio/position/trend/tier/entry_reference_price) and set
    allow_incomplete_scan_result (db_manager.py:628) rather than fabricating legacy scores
    (the no-dummy quality gate is intentional)."""
    from modules.db_schema import build_scan_result_payload
    rows = []
    for i, p in enumerate(sorted(picks, key=lambda x: -x["p"]), start=1):
        src = {"ticker": p["ticker"], "market_type": p["market"], "scan_mode": "SWING",
               "decision_score": p["p"], "ml_prob": round(p["p"] * 100, 2), "run_id": run_id, "priority_rank": i,
               "decision": "FIRSTTOUCH_DOWN_BUY", "decision_bucket": "firsttouch_down",
               "recommended_at": recommended_at, "selection_lane": "FIRSTTOUCH_DOWN",
               "volume_ratio": p.get("volume_ratio"), "position": p.get("position"),
               "trend": p.get("trend"), "tier": p.get("tier"),
               "entry_reference_price": p.get("entry_reference_price")}
        payload = build_scan_result_payload(src, overrides={"market": p["market"], "recommended_at": recommended_at})
        payload["allow_incomplete_scan_result"] = True
        rows.append(payload)
    return rows


def firsttouch_deep_rows(picks, run_id, recommended_at):
    from modules.candidate_interpretation import build_candidate_interpretation
    rows = []
    for i, p in enumerate(sorted(picks, key=lambda x: -x["p"]), start=1):
        row = {"ticker": p["ticker"], "stock_name": p.get("stock_name") or p["ticker"], "market": p["market"],
               "run_id": run_id, "rank": i, "decision": "FIRSTTOUCH_DOWN_BUY", "decision_bucket": "firsttouch_down",
               "signal_label": "FIRSTTOUCH_DOWN_BUY", "analysis_section": "Top5", "analysis_section_rank": i,
               "buy_score": p["p"], "generated_at": recommended_at,
               "selection_alignment": {"analysis_section": "Top5", "analysis_section_rank": i}}
        row["candidate_interpretation"] = build_candidate_interpretation(row)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------

def _universe(market: str, top_n: int) -> List[str]:
    import FinanceDataReader as fdr
    lst = fdr.StockListing(market)
    if "Marcap" in lst.columns:
        lst = lst.sort_values("Marcap", ascending=False)
    return [str(c) for c in lst["Code"].astype(str).head(int(top_n)).tolist()]


def _index_regime(market: str) -> Optional[str]:
    import FinanceDataReader as fdr
    idx = "KS11" if market == "KOSPI" else "KQ11"
    h = fdr.DataReader(idx, (datetime.now().year - 1).__str__() + "-01-01")
    c = pd.to_numeric(h["Close"], errors="coerce").dropna()
    if len(c) < 25:
        return None
    mom = (c.iloc[-1] / c.iloc[-21] - 1) * 100
    return "DOWN" if mom < -2.0 else ("UP" if mom > 2.0 else "NORMAL")


def score_today(model: Dict[str, Any], top_universe: int, top_picks: int = 5) -> List[Dict[str, Any]]:
    import FinanceDataReader as fdr
    feats = model["features"]; zf = model["zfeatures"]; roll = model["roll"]; min_p = model["min_periods"]
    clf = model["model"]; tau = model["tau"]
    start = f"{datetime.now().year - 2}-01-01"
    picks: List[Dict[str, Any]] = []
    for market in ("KOSPI", "KOSDAQ"):
        if _index_regime(market) != "DOWN":   # abstain outside DOWN
            continue
        rows = []
        for code in _universe(market, top_universe):
            try:
                h = fdr.DataReader(code, start)
            except Exception:
                continue
            if h is None or len(h) < min_p + 5 or "Close" not in h.columns:
                continue
            feat = compute_features(h)
            zr = latest_znorm(feat, feats, roll, min_p)
            if zr is None:
                continue
            last = feat.iloc[-1]
            dist_hi20 = float(last.get("dist_hi20")) if pd.notna(last.get("dist_hi20")) else None
            zr.update({"ticker": code, "market": market,
                       "liq": float((h["Close"] * h["Volume"]).tail(20).mean()),
                       "entry_ref": float(h["Close"].iloc[-1]),
                       "volume_ratio": float(last.get("vol_ratio")) if pd.notna(last.get("vol_ratio")) else None,
                       "position": float(last.get("pos20")) if pd.notna(last.get("pos20")) else None,
                       "ma60_dist": float(last.get("ma60_dist")) if pd.notna(last.get("ma60_dist")) else None,
                       "dist_hi20": dist_hi20})
            rows.append(zr)
        if not rows:
            continue
        X = pd.DataFrame(rows)
        X[zf] = X[zf].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        X["p"] = clf.predict_proba(X[zf])[:, 1]
        qual = X[X["p"] >= tau].nlargest(int(top_picks), "p")   # top-K among p>=tau, or fewer/0
        sfx = ".KS" if market == "KOSPI" else ".KQ"
        for _, r in qual.iterrows():
            d = r.get("dist_hi20")
            tier = "A" if (d is not None and d >= -4) else ("B" if (d is not None and d >= -8) else "C")
            trend = "UP" if (r.get("ma60_dist") or 0) > 0 else "DOWN"
            picks.append({"ticker": str(r["ticker"]) + sfx, "market": market, "p": round(float(r["p"]), 4),
                          "liq": round(float(r["liq"]) / 1e8, 1),
                          "entry_reference_price": r.get("entry_ref"),
                          "volume_ratio": r.get("volume_ratio"), "position": r.get("position"),
                          "trend": trend, "tier": tier})
    return picks


def _resolve_pending(today: str) -> Dict[str, Any]:
    import FinanceDataReader as fdr
    if not LEDGER.exists():
        return {"resolved": 0, "first_touch_pct": None}
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = False
    for row in rows:
        if row.get("first_touch") is not None:
            continue
        d = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.isna(d) or (pd.Timestamp(today) - d).days < 9:
            continue
        try:
            bare = str(row["ticker"]).replace(".KS", "").replace(".KQ", "")
            h = fdr.DataReader(bare, str(d.date()))
            o = pd.to_numeric(h["Open"], errors="coerce"); hi = pd.to_numeric(h["High"], errors="coerce"); lo = pd.to_numeric(h["Low"], errors="coerce")
            if len(o) >= 6:
                entry = float(o.iloc[1]); ub = entry * 1.05; lb = entry * 0.95; res = None
                for k in range(1, 6):
                    if hi.iloc[k] >= ub and lo.iloc[k] <= lb:
                        res = 1 if float(pd.to_numeric(h["Open"], errors="coerce").iloc[k]) >= lb else 0; break
                    if hi.iloc[k] >= ub:
                        res = 1; break
                    if lo.iloc[k] <= lb:
                        res = 0; break
                if res is not None:
                    row["first_touch"] = res; changed = True
        except Exception:
            pass
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    res = [r["first_touch"] for r in rows if r.get("first_touch") is not None]
    if not res:
        return {"resolved": 0, "first_touch_pct": None}
    return {"resolved": len(res), "first_touch_pct": round(float(np.mean(res) * 100), 1)}


def main() -> None:
    ap = argparse.ArgumentParser(description="First-touch DOWN-market shadow forward-tracker.")
    ap.add_argument("--top-universe", type=int, default=300)
    ap.add_argument("--top-picks", type=int, default=5)
    args = ap.parse_args()
    import joblib

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not MODEL_PATH.exists():
        print(json.dumps({"error": "model_missing", "path": str(MODEL_PATH)})); return
    model = joblib.load(MODEL_PATH)
    picks = score_today(model, args.top_universe, args.top_picks)

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        for p in picks:
            fh.write(json.dumps({"date": today, "first_touch": None, **p}, ensure_ascii=False) + "\n")
    summary = _resolve_pending(today)

    persisted = deep_persisted = 0
    production = os.getenv("AG_FIRSTTOUCH_DOWN_PRODUCTION", "0").strip() not in ("0", "", "false", "False")
    if production and picks:
        run_id = "FIRSTTOUCH-DOWN-" + today.replace("-", "")
        recommended_at = datetime.now(timezone.utc).isoformat()
        try:
            from modules.db_manager import DBManager
            db = DBManager()
            # archive + learning: market_scan_results (allow_incomplete bypass; verified)
            for payload in firsttouch_scan_rows(picks, run_id, recommended_at):
                db.upsert_scan_result(payload); persisted += 1
            # web + Discord surface: enrich picks into scan_deep_reports via the production pipeline
            # (it fetches price/flow/readiness/gates -- verified to surface in both consumers)
            from modules.top_deep_report import generate_and_store_top_deep_reports
            scan_dicts = [{"ticker": p["ticker"], "market": p["market"], "market_type": p["market"],
                           "scan_mode": "SWING", "decision": "FIRSTTOUCH_DOWN_BUY", "decision_bucket": "firsttouch_down",
                           "decision_score": p["p"], "ml_prob": round(p["p"] * 100, 2), "priority_rank": i + 1,
                           "run_id": run_id, "recommended_at": recommended_at, "selection_lane": "FIRSTTOUCH_DOWN",
                           "volume_ratio": p.get("volume_ratio"), "position": p.get("position"), "trend": p.get("trend"),
                           "tier": p.get("tier"), "entry_reference_price": p.get("entry_reference_price"),
                           "allow_incomplete_scan_result": True} for i, p in enumerate(sorted(picks, key=lambda x: -x["p"]))]
            by_market: Dict[str, List[Dict[str, Any]]] = {}
            for r in scan_dicts:
                by_market.setdefault(r["market"], []).append(r)
            for mkt, rows in by_market.items():
                generate_and_store_top_deep_reports(scan_rows=rows, planner_payload={}, run_id=run_id,
                                                    market=mkt, scan_mode="SWING", top_n=len(rows), write_db=True)
                deep_persisted += len(rows)
        except Exception as exc:
            persisted = -1
            print(json.dumps({"firsttouch_persist_error": repr(exc)[:200]}, ensure_ascii=False))

    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "version": model.get("version"),
              "today": today, "model_tau": model["tau"], "model_base_rate": model.get("base_rate"),
              "picks_today": picks, "forward_summary": summary, "scan_persisted": persisted,
              "deep_persisted": deep_persisted, "production_enabled": production,
              "note": "DOWN-regime only; emits 0 outside DOWN. Observation-only until AG_FIRSTTOUCH_DOWN_PRODUCTION=1."}
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# First-touch DOWN Shadow ({today})", "",
             f"- tau={model['tau']:.4f} base={model.get('base_rate')} | picks: {len(picks)}",
             f"- forward (resolved): n={summary['resolved']} first_touch={summary['first_touch_pct']}%", "",
             "| Market | Ticker | p | liq(억) |", "|---|---|---:|---:|"]
    for p in sorted(picks, key=lambda x: -x["p"]):
        lines.append(f"| {p['market']} | {p['ticker']} | {p['p']:.3f} | {p['liq']} |")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"picks": len(picks), "forward_summary": summary, "production": production}, ensure_ascii=False))


if __name__ == "__main__":
    main()
