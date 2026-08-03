#!/usr/bin/env python3
"""KR swing CANDIDATE-pick producer (swing-main-zls0, RESEARCH_LOG §7-A). Observation-only.

Basis: 8y quarterly walk-forward, ft_5_5 LGBM ranker (rolling 2y train), placebo-dead:
  KOSDAQ EV +0.67/trade net CI(0.41,0.97), 62% of picks touch +5%; KOSPI +0.63 CI(0.35,0.90).
  Median pick liquidity 76~260억 (tradeable). Honest tier: CANDIDATE — real durable edge,
  below the +5%/trade PRIMARY bar. Fills "no-pick days" alongside the intraday PRIMARY lane.

Contract: signal at close t -> BUY NEXT OPEN (t+1); exit +5% touch within 5 sessions
(entry day counts) else 5d close. No stop. Never routed to production buy lists.

2026-08-03 PKG-C ③ (§40, 사전등록): 랭킹 shadow 보드 — 유동 풀(≥30억/100억) 전수 스코어의
top-50/시장을 kr_ranking_shadow_ledger.jsonl에 관측 전용 축적, px_long 종가 기반 fwd5 자동 정산.
목적: "상승확률 최고 종목" 기능의 전제인 랭킹 심도(top1 vs top10 vs top50) 실측 차등 검증.
사전등록 킬 기준: forward n>=30/구간에서 심도 단조성(top1>top10>top50 EV) 부재 시 보드 폐기
(§25/§38/§11-B가 '셀 내 서열 무정보'로 부정적 사전확률 — 이 검증이 통과해야만 웹 노출 후보).
원시 p 표시 금지·발행/라우팅 금지. 비활성: AG_SWING_RANKING_SHADOW=0.

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
RANK_LEDGER = EXP / "kr_ranking_shadow_ledger.jsonl"
RANK_TOP = 50
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
        # PKG-C ③: 전수 스코어 top-50 랭킹 shadow (관측 전용 — 발행/라우팅 아님)
        for rank, (_, r) in enumerate(te.nlargest(RANK_TOP, "p").iterrows(), 1):
            out.setdefault("ranking", []).append(
                {"date": str(latest.date()), "market": mkt, "rank": rank,
                 "ticker": str(r["code"]) + (".KS" if mkt == "KOSPI" else ".KQ"),
                 "p": round(float(r["p"]), 4), "close": float(r["close"]),
                 "liq_eok": round(float(r["liq"]) / 1e8, 1)})
        for _, r in te.nlargest(top_k, "p").iterrows():
            out["picks"].append({"date": str(latest.date()), "market": mkt, **state,
                                 "ticker": str(r["code"]) + (".KS" if mkt == "KOSPI" else ".KQ"),
                                 "p": round(float(r["p"]), 4), "close": float(r["close"]),
                                 "ret_5d": round(float(r["ret_5d"]), 2) if pd.notna(r.get("ret_5d")) else None,
                                 "atr_pct": round(float(r["atr_pct"]), 2) if pd.notna(r.get("atr_pct")) else None,
                                 "liq_eok": round(float(r["liq"]) / 1e8, 1),
                                 "contract": "buy next open; +5% touch exit within 5 sessions else 5d close"})
    # §29 출구혼합 shadow: 당일 픽 내 ATR 3분위 밴드 → 출구 플랜 스탬프 (계약 불변, 병행채점용)
    atrs = [p["atr_pct"] for p in out["picks"] if p.get("atr_pct") is not None]
    if len(atrs) >= 3:
        lo_t, hi_t = float(np.quantile(atrs, 0.33)), float(np.quantile(atrs, 0.67))
        for p in out["picks"]:
            a = p.get("atr_pct")
            if a is None:
                continue
            if a > hi_t:
                p["exit_band"], p["exit_mix_plan"] = "HIGH", f"고ATR → +{1.5*a:.1f}%(1.5×ATR) 배리어 shadow"
            elif a <= lo_t:
                p["exit_band"], p["exit_mix_plan"] = "LOW", f"저ATR → 트레일링(고점-{1.5*a:.1f}%) shadow"
            else:
                p["exit_band"], p["exit_mix_plan"] = "MID", "중ATR → 현행 +5% 터치 (shadow 동일)"
    return out


def ranking_shadow(ranking: List[Dict[str, Any]], now_iso: str) -> Dict[str, Any]:
    """PKG-C ③: 랭킹 shadow 원장 append + px_long 종가 기반 fwd5 정산 (관측 전용).

    정산 근사: 익일 종가 진입 → +5세션 종가 (close-to-close; 터치 미반영 — 심도 비교는
    랭크 간 동일 기준이면 공정하므로 근사로 충분, 명시). 심도 요약: top1/2-10/11-50."""
    rows: List[Dict[str, Any]] = []
    if RANK_LEDGER.exists():
        rows = [json.loads(l) for l in RANK_LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    existing = {(r.get("date"), r.get("ticker")) for r in rows}
    for r in ranking:
        if (r["date"], r["ticker"]) not in existing:
            rows.append({**r, "fwd5_cc": None, "logged_at": now_iso})
    # 정산: 8일+ 경과 & 미정산 → px_long 종가 조인
    need = [r for r in rows if r.get("fwd5_cc") is None
            and (pd.Timestamp.utcnow().tz_localize(None) - pd.Timestamp(r["date"])).days >= 8]
    if need:
        try:
            px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "close"])
            px["date"] = pd.to_datetime(px["date"])
            by_code = {c: g.sort_values("date").reset_index(drop=True) for c, g in
                       px[px["code"].isin({str(r["ticker"]).split(".")[0] for r in need})].groupby("code")}
            for r in need:
                g = by_code.get(str(r["ticker"]).split(".")[0])
                if g is None:
                    continue
                after = g[g["date"] > pd.Timestamp(r["date"])]
                if len(after) < 6:
                    continue
                entry, exitc = float(after["close"].iloc[0]), float(after["close"].iloc[5])
                if entry > 0:
                    r["fwd5_cc"] = round((exitc / entry - 1) * 100, 2)
        except Exception:
            pass
    RANK_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    RANK_LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    # 심도 요약 (net, COST 차감)
    done = [r for r in rows if isinstance(r.get("fwd5_cc"), (int, float))]
    def _band(lo, hi):
        v = [r["fwd5_cc"] - COST for r in done if lo <= r["rank"] <= hi]
        return {"n": len(v), "ev": round(float(np.mean(v)), 2)} if v else {"n": 0}
    return {"ledger_rows": len(rows), "settled": len(done),
            "depth": {"top1": _band(1, 1), "r2_10": _band(2, 10), "r11_50": _band(11, 50)},
            "kill_rule": "n>=30/구간에서 top1>r2_10>r11_50 단조성 부재 시 보드 폐기 (사전등록)"}


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
            # §29 출구혼합 shadow 병행채점 (계약 불변): 밴드별 대체 출구의 실현수익
            a = row.get("atr_pct"); band = row.get("exit_band")
            if a is not None and band in ("HIGH", "LOW", "MID"):
                op5 = win5["Open"].astype(float); hi5v = win5["High"].astype(float)
                cl5 = win5["Close"].astype(float)
                if band == "HIGH":
                    mtg = entry * (1 + 0.015 * float(a))
                    mret = float((cl5.iloc[-1] / entry - 1) * 100)
                    for k in range(len(win5)):
                        if np.isfinite(hi5v.iloc[k]) and hi5v.iloc[k] >= mtg:
                            o = op5.iloc[k]
                            fill = max(mtg, float(o)) if (k > 0 and np.isfinite(o) and o > 0) else mtg
                            mret = (fill / entry - 1) * 100
                            break
                elif band == "LOW":
                    hh = entry
                    mret = float((cl5.iloc[-1] / entry - 1) * 100)
                    for k in range(len(win5)):
                        hh = max(hh, float(hi5v.iloc[k]) if np.isfinite(hi5v.iloc[k]) else hh)
                        if float(cl5.iloc[k]) <= hh * (1 - 0.015 * float(a)):
                            mret = (float(cl5.iloc[k]) / entry - 1) * 100
                            break
                else:
                    mret = ret
                row["exit_mix"] = round(float(mret), 2)
            changed = True
        except Exception:
            continue
    if changed:
        LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    res = [r for r in rows if r.get("policy_ret") is not None]
    if not res:
        return {"resolved": 0}
    rets = [float(r["policy_ret"]) - COST for r in res]
    mix = [float(r["exit_mix"]) - COST for r in res if isinstance(r.get("exit_mix"), (int, float))]
    return {"resolved": len(res),
            **({"exit_mix_n": len(mix), "exit_mix_ev": round(float(np.mean(mix)), 2)} if mix else {}),
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
    # P3 교체 스위치 (기본 OFF): AG_SWING_CANDIDATE_ROUTE=1이면 후보픽을 라이브 라우팅 —
    # 스윙 앙상블(fwd 45%/-0.5, DEGRADE 궤도) 교체 결정 시 env 플립 하나로 전환.
    # 근거: 8y walk-forward +0.65 CI>0 (§7-A) vs 앙상블 실측 미달 (§13/재귀게이트).
    routed = 0
    # 2026-07-06 운영자 결정(P3): 기본 ON — 스윙 앙상블(DEGRADE) 교체. 근거: 8y +0.65 CI>0 (§7-A).
    if os.getenv("AG_SWING_CANDIDATE_ROUTE", "1").strip() in ("1", "true", "True") and scored["picks"]:
        try:
            from report_swing_ensemble import _route_live
            rp = [{"ticker": p["ticker"], "market": p["market"], "p": p["p"] if p["p"] <= 1.5 else p["p"] / 100.0,
                   "entry_reference_price": p["close"]} for p in scored["picks"]]
            routed = _route_live(rp, "SWING-CAND-" + scored["as_of"].replace("-", ""), now.isoformat(),
                                 bucket="swing_candidate", decision="SWING_CANDIDATE_BUY", lane="SWING_CANDIDATE")
        except Exception as exc:
            routed = -1
            print(json.dumps({"route_error": repr(exc)[:200]}))
    summary = resolve_pending(pd.Timestamp(now.date()))
    rank_summary = None
    if os.getenv("AG_SWING_RANKING_SHADOW", "1").strip() in ("1", "true", "True") and scored.get("ranking"):
        try:
            rank_summary = ranking_shadow(scored["ranking"], now.isoformat())
        except Exception as exc:
            rank_summary = {"error": repr(exc)[:200]}
    report = {"generated_at": now.isoformat(), "as_of": scored["as_of"], "tier": "CANDIDATE",
              "expectation": "8y walk-forward: ~60-62% touch +5%, EV ~+0.65/trade net — honest modest edge",
              "picks": scored["picks"], "forward_summary": summary, "routed": routed,
              "ranking_shadow": rank_summary}
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
