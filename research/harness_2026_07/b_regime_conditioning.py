#!/usr/bin/env python3
"""B 레짐 조건화 24폴드 검증 (swing-main-l2n8, 사전등록).

라이브 붕괴 원인 가설: 반등국면(드로다운 저점 이후)에서 B의 수급-모멘텀 틸트가
베타항복 반등에 역풍. 처방 후보 3개를 월별 walk-forward(24폴드, 운영 학습기 그대로)로 판정:
  C1 레짐 발행보류: RISK_OFF(dd20<-5|ret5<-3)에서 픽 발행 안 함 — 남는 픽의 α?
  C2 프로필 베토(§17식): 최근 급등(ret_5d>+10) 픽 제외
  C3 레짐 반전틸트: RISK_OFF에서는 pred 순위 대신 항복프로필(ret_5d<=-13) 상위 선택
평가: α/트레이드(a5), 승률, RISK_OFF/NORMAL 분해, 연도, top3/top10.
판정: 라이브 재현 구간(2026-06~07 유사 = RISK_OFF 월)의 개선 + 전체 EV 비열화.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
from b_engine import model_engine as E

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    px = E.load_panel()
    px = px.dropna(subset=["a5"]).copy()
    px["date"] = pd.to_datetime(px["date"])
    # 시장상태 (등가중, causal)
    mret = px.groupby("date")["f5"].mean() if "f5" in px else None
    d1 = px.groupby("date")["a5"].count()  # placeholder
    # ret_1d 기반 상태: 패널에 ret_1d 있으면 사용, 없으면 f5 롤링 근사 대신 px_long에서
    pxl = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet", columns=["date", "market", "ret_1d", "liq"])
    pxl["date"] = pd.to_datetime(pxl["date"])
    pool = pxl[((pxl["market"] == "KOSPI") & (pxl["liq"] >= 100e8)) | ((pxl["market"] == "KOSDAQ") & (pxl["liq"] >= 30e8))]
    m = pool.groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1 + m / 100).cumprod()
    st = pd.DataFrame({"dd20": (lvl / lvl.rolling(20).max() - 1) * 100,
                       "ret5": (lvl / lvl.shift(5) - 1) * 100})
    st["risk_off"] = (st["dd20"] < -5) | (st["ret5"] < -3)
    px = px.join(st["risk_off"], on="date")
    has_r5 = "ret_5d" in px.columns
    print(f"패널 {len(px)} rows | ret_5d 보유: {has_r5} | RISK_OFF 일 비중 {px.groupby('date')['risk_off'].first().mean()*100:.0f}%", flush=True)

    months = pd.period_range("2024-07", "2026-06", freq="M")
    pools = []
    for tm in months:
        t0, t1 = tm.start_time, tm.end_time
        tr = px[(px["date"] < t0) & (px["date"] >= t0 - pd.DateOffset(months=E.TRAIN_MONTHS))]
        te = px[(px["date"] >= t0) & (px["date"] <= t1)].copy()
        if len(tr) < 20000 or te.empty:
            continue
        models = E._fit_ensemble(tr)
        te["pred"] = E._predict(models, te)
        pools.append(te)
        print(f"  {tm} done", flush=True)
    A = pd.concat(pools)

    def pick_eval(frame, k, name, veto=None, invert_ro=False):
        f = frame.copy()
        if veto is not None:
            f = f[~veto.reindex(f.index).fillna(False)]
        rows = []
        for dt, g in f.groupby("date"):
            ro = bool(g["risk_off"].iloc[0]) if g["risk_off"].notna().any() else False
            if invert_ro and ro and has_r5:
                gg = g[g["ret_5d"] <= -13]
                sel = gg.nsmallest(k, "ret_5d") if len(gg) >= k else g.nlargest(k, "pred")
            else:
                sel = g.nlargest(k, "pred")
            rows.append(sel)
        P = pd.concat(rows)
        a = P["a5"].dropna()
        ro_mask = P["risk_off"].fillna(False).astype(bool)
        parts = {"all": a, "risk_off": P.loc[ro_mask, "a5"].dropna(), "normal": P.loc[~ro_mask, "a5"].dropna()}
        out = f"  {name:34s}"
        for tag, v in parts.items():
            out += f" | {tag} n={len(v):5d} α={v.mean():+.2f} 승={(v>0).mean()*100:.0f}%"
        print(out, flush=True)
        return a.mean()

    for k in (10, 3):
        print(f"\n===== top{k} =====", flush=True)
        pick_eval(A, k, "C0 베이스 (현행)")
        # C1: RISK_OFF 발행보류 = risk_off 날 픽 제외 후 all 지표
        NA = A[~A["risk_off"].fillna(False)]
        pick_eval(NA, k, "C1 RISK_OFF 발행보류")
        if has_r5:
            pick_eval(A, k, "C2 급등베토 (ret_5d>+10 제외)", veto=(A["ret_5d"] > 10))
            pick_eval(A, k, "C3 RISK_OFF 반전틸트(항복선택)", invert_ro=True)
    json.dump({"done": True}, open(os.path.join(HERE, "b_regime_conditioning.done"), "w"))
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
