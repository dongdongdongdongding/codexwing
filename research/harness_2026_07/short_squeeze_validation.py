#!/usr/bin/env python3
"""공매도 8y 검증 (사전등록 — 백필 완료 시 즉시 실행, swing-main 재개봉 큐 short_squeeze).

난제 정식화: 공매도 신호가 엣지이려면
  (a) 반대편: 숏커버 강제청산/과도숏의 되돌림 — 행동·구조적 원천 존재
  (b) 비용벽: 표준계약 net EV CI>0
  (c) 검출: short.parquet 8y × px_long 라벨
  (d) 증분: 랭커 위에서 노이즈 플라시보 초과 (§19 하한 ±0.1~0.2 → 시드3 필수)

가설 (모두 사전등록, 결과 후 수정 금지):
  H-A 스퀴즈 연료: 공매도 비중 급증(20d Δ 상위) × 항복픽(ret_5d<=-13) → 반등 증폭?
  H-B 피크아웃: 비중 20d 고점 대비 급감 전환 → 커버링 랠리?
  H-C 과열숏: 비중 절대 상위 10% 자체의 forward
  규율: 시장초과(pol_ex) + 일내셔플 플라시보(서브셋 편향 — 공매도 데이터 커버 종목군 자체가
  대형주 편향임을 T3 대차에서 확인) + 연도 일관성. 통과 시에만 랭커 증분 단계 진행.
"""
import os, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = "/Users/dongdong/research_cache"
COST = 0.3
rng = np.random.default_rng(0)


def stat(d, name):
    v = d["pol_ex"].dropna()
    if len(v) < 150:
        print(f"  {name:44s} n={len(v)} 부족")
        return
    bs = [rng.choice(v.values, len(v), True).mean() for _ in range(300)]
    net = d["policy_ret"].dropna() - COST
    yr = v.groupby(d["date"].dt.year).mean()
    print(f"  {name:44s} n={len(v):6d} 초과={v.mean():+.3f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] "
          f"netEV={net.mean():+.2f} yr+={int((yr>0).sum())}/{len(yr)}")


def main():
    sh = pd.read_parquet(f"{CACHE}/short.parquet")
    sh["date"] = pd.to_datetime(sh["date"], format="%Y%m%d", errors="coerce")
    sh["code"] = sh["code"].astype(str).str.zfill(6)
    for c in ("short_vol_pct", "short_cum_pct"):
        sh[c] = pd.to_numeric(sh[c], errors="coerce")
    sh = sh.sort_values(["code", "date"])
    g = sh.groupby("code", group_keys=False)
    sh["sv_ma5"] = g["short_vol_pct"].apply(lambda s: s.rolling(5, min_periods=3).mean())
    sh["sv_d20"] = g["sv_ma5"].apply(lambda s: s - s.shift(20))
    sh["sv_pk"] = g["sv_ma5"].apply(lambda s: s / (s.rolling(20, min_periods=10).max() + 1e-9))
    # 신호는 전일값 (당일 공매도량은 장중 미확정 — PIT)
    for c in ("sv_ma5", "sv_d20", "sv_pk"):
        sh[c] = g[c].shift(1)
    print(f"short 패널: {len(sh)} rows, {sh['code'].nunique()}종목, {sh['date'].min().date()}..{sh['date'].max().date()}", flush=True)

    cols = ["code", "date", "market", "liq", "ft_5_5", "exec_5d", "ret_5d"]
    px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    px["code"] = px["code"].astype(str)
    px["exec_5d"] = px["exec_5d"].replace([np.inf, -np.inf], np.nan)
    liq_ok = ((px["market"] == "KOSPI") & (px["liq"] >= 100e8)) | ((px["market"] == "KOSDAQ") & (px["liq"] >= 30e8))
    px = px[liq_ok].copy()
    px["policy_ret"] = np.where(px["ft_5_5"] == 1, 5.0, px["exec_5d"])
    # 시장초과: 공매도 커버 서브셋 평균 대비 (T3 교훈 — 전체 풀 대비면 서브셋 편향)
    m = px.merge(sh[["code", "date", "sv_ma5", "sv_d20", "sv_pk"]], on=["code", "date"], how="inner")
    sub_mean = m.groupby("date")["policy_ret"].transform("mean")
    m["pol_ex"] = m["policy_ret"] - sub_mean
    print(f"병합: {len(m)} rows", flush=True)

    q_d20 = m.groupby("date")["sv_d20"].rank(pct=True)
    q_lvl = m.groupby("date")["sv_ma5"].rank(pct=True)
    cap = m["ret_5d"] <= -13

    print("\n== H-C 비중 절대 상위/하위 (레벨)", flush=True)
    stat(m[q_lvl >= 0.9], "공매도비중 상위10%")
    stat(m[q_lvl <= 0.1], "공매도비중 하위10%")
    print("\n== H-A 급증 × 항복 (스퀴즈 연료)", flush=True)
    stat(m[q_d20 >= 0.9], "비중 급증 상위10%")
    stat(m[(q_d20 >= 0.9) & cap], "급증 × 항복픽")
    stat(m[(q_d20 <= 0.1) & cap], "급감 × 항복픽 (대조)")
    stat(m[cap], "항복픽 전체 (기저)")
    print("\n== H-B 피크아웃 (고점대비 냉각)", flush=True)
    stat(m[(m["sv_pk"] <= 0.5) & (q_lvl >= 0.7)], "고비중이었다가 반토막 냉각")
    print("\n== 플라시보 (일내 셔플)", flush=True)
    P = m.copy()
    P["sv_d20"] = P.groupby("date")["sv_d20"].transform(lambda s: rng.permutation(s.values))
    qp = P.groupby("date")["sv_d20"].rank(pct=True)
    stat(P[qp >= 0.9], "플라시보 급증 상위10%")
    stat(P[(qp >= 0.9) & (P["ret_5d"] <= -13)], "플라시보 급증 × 항복")
    json.dump({"done": True}, open(os.path.join(HERE, "short_squeeze_validation.done"), "w"))
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
