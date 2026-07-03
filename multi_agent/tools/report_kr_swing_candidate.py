#!/usr/bin/env python3
"""KR swing CANDIDATE-pick producer (swing-main-zls0, RESEARCH_LOG §7-A). Observation-only.

Basis: 8y quarterly walk-forward, ft_5_5 LGBM ranker (rolling 2y train), placebo-dead:
  KOSDAQ EV +0.67/trade net CI(0.41,0.97), 62% of picks touch +5%; KOSPI +0.63 CI(0.35,0.90).
  Median pick liquidity 76~260억 (tradeable). Honest tier: CANDIDATE — real durable edge,
  below the +5%/trade PRIMARY bar. Fills "no-pick days" alongside the intraday PRIMARY lane.

Contract: signal at close t -> BUY NEXT OPEN (t+1); exit +5% touch within 5 sessions
(entry day counts) else 5d close. No stop. Never routed to production buy lists.

  python3 multi_agent/tools/report_kr_swing_candidate.py [--top-k 3]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
CACHE = Path(os.path.expanduser("~/research_cache"))
EXP = PROJECT_ROOT / "runtime_state" / "reports" / "experimental"
LEDGER = EXP / "kr_swing_candidate_ledger.jsonl"
REPORT_JSON = EXP / "kr_swing_candidate_latest.json"
REPORT_MD = EXP / "kr_swing_candidate_latest.md"

FEATS = ["ret_1d","ret_3d","ret_5d","ret_10d","ret_20d","ret_60d","ma5_dist","ma20_dist","ma60_dist",
         "ma120_dist","ma20_slope","ma60_slope","rsi14","rsi_slope","accel","consec_up","dist_hi20",
         "dist_hi60","dist_hi120","dist_lo20","dist_lo60","pos20","bb_pctb","bb_bw","atr_pct","vol20",
         "close_loc","gap","vol_ratio","vol_trend","turn_z","obv_slope","cmf20","idx_mom20","idx_vol20"]
LIQ = {"KOSPI": 100e8, "KOSDAQ": 30e8}
TRAIN_YEARS = 2
COST = 0.3


def score_today(top_k: int) -> Dict[str, Any]:
    import lightgbm as lgb
    cols = list(dict.fromkeys(["code", "date", "market", "liq", "ft_5_5", "close"] + FEATS))
    px = pd.read_parquet(CACHE / "px_long.parquet", columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    latest = px["date"].max()
    out: Dict[str, Any] = {"as_of": str(latest.date()), "picks": []}
    for mkt in ("KOSPI", "KOSDAQ"):
        d = px[(px["market"] == mkt) & (px["liq"] >= LIQ[mkt])]
        tr = d[(d["date"] < latest) & (d["date"] >= latest - pd.DateOffset(years=TRAIN_YEARS))].dropna(subset=["ft_5_5"])
        te = d[d["date"] == latest].dropna(subset=FEATS[:6]).copy()
        if len(tr) < 20000 or te.empty:
            continue
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0, verbose=-1)
        m.fit(tr[FEATS].clip(-1e4, 1e4), tr["ft_5_5"])
        te["p"] = m.predict_proba(te[FEATS].clip(-1e4, 1e4))[:, 1]
        # RISK_OFF flag: swing ranker EV roughly doubles in drawdown states (8y: 0.85 vs
        # 0.49 KOSDAQ, 0.76 vs 0.50 KOSPI touch-exit) — complementary to the intraday lanes.
        try:
            from multi_agent.tools.report_kospi_intraday_swing import market_drawdown_state
            state = market_drawdown_state(mkt)
        except Exception:
            state = {"mkt_state": "UNKNOWN"}
        for _, r in te.nlargest(top_k, "p").iterrows():
            out["picks"].append({"date": str(latest.date()), "market": mkt, **state,
                                 "ticker": str(r["code"]) + (".KS" if mkt == "KOSPI" else ".KQ"),
                                 "p": round(float(r["p"]), 4), "close": float(r["close"]),
                                 "liq_eok": round(float(r["liq"]) / 1e8, 1),
                                 "tier": "CANDIDATE",
                                 "contract": "buy next open; +5% touch exit within 5 sessions else 5d close"})
    return out


def resolve_pending(today: pd.Timestamp) -> Dict[str, Any]:
    import FinanceDataReader as fdr
    if not LEDGER.exists():
        return {"resolved": 0}
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    changed = False
    for row in rows:
        if row.get("policy_ret") is not None:
            continue
        d = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.isna(d) or (today - d).days < 10:
            continue
        try:
            bare = str(row["ticker"]).split(".")[0]
            h = fdr.DataReader(bare, str(d.date()))
            h = h[h.index > d]  # sessions after signal day
            if len(h) < 6:
                continue
            entry = float(h["Open"].iloc[0])
            if not np.isfinite(entry) or entry <= 0:
                continue
            tgt = entry * 1.05
            win5 = h.iloc[:5]
            ret = float((win5["Close"].iloc[-1] / entry - 1) * 100)
            touched = 0
            for k in range(5):
                hi = float(win5["High"].iloc[k])
                if np.isfinite(hi) and hi >= tgt:
                    o = float(win5["Open"].iloc[k])
                    fill = max(tgt, o) if (k > 0 and np.isfinite(o) and o > 0) else tgt
                    ret = (fill / entry - 1) * 100
                    touched = 1
                    break
            row["entry_open"] = round(entry, 2)
            row["ft_touch5"] = touched
            row["policy_ret"] = round(ret, 2)
            changed = True
        except Exception:
            continue
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    res = [r for r in rows if r.get("policy_ret") is not None]
    if not res:
        return {"resolved": 0}
    rets = [float(r["policy_ret"]) - COST for r in res]
    return {"resolved": len(res),
            "touch5_pct": round(float(np.mean([r["ft_touch5"] for r in res])) * 100, 1),
            "ev_net_avg": round(float(np.mean(rets)), 2),
            "worst": round(float(np.min(rets)), 2)}


def main() -> None:
    ap = argparse.ArgumentParser(description="KR swing CANDIDATE producer (observation-only).")
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    scored = score_today(args.top_k)
    # append only new (date, ticker) rows
    existing = set()
    if LEDGER.exists():
        for l in LEDGER.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                existing.add((r.get("date"), r.get("ticker")))
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        for p in scored["picks"]:
            if (p["date"], p["ticker"]) not in existing:
                fh.write(json.dumps({**p, "ft_touch5": None, "policy_ret": None,
                                     "logged_at": now.isoformat()}, ensure_ascii=False) + "\n")
    summary = resolve_pending(pd.Timestamp(now.date()))
    report = {"generated_at": now.isoformat(), "as_of": scored["as_of"], "tier": "CANDIDATE",
              "expectation": "8y walk-forward: ~60-62% touch +5%, EV ~+0.65/trade net — honest modest edge",
              "picks": scored["picks"], "forward_summary": summary}
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# KR swing CANDIDATE picks — {scored['as_of']}", "",
             f"- tier: CANDIDATE (후보픽) | forward: {summary}", "",
             "| Market | Ticker | p | liq(억) | close |", "|---|---|---:|---:|---:|"]
    for p in scored["picks"]:
        lines.append(f"| {p['market']} | {p['ticker']} | {p['p']} | {p['liq_eok']} | {p['close']} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"as_of": scored["as_of"], "picks": len(scored["picks"]), "forward": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
