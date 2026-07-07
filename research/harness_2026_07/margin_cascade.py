#!/usr/bin/env python3
"""난제 접근 2호: 신용융자 반대매매 과잉투매 가설 (사전등록).

정식화: 반대편(a) = 강제청산 레버리지 개인(반대매매는 선택권 없음, 익일 동시호가 투매).
H-M1: 항복(ret_5d<=-13) × 고신용잔고율 → 반등(표준계약) 더 강함?
H-M2: 항복 × 신용 급감중(이미 청산 진행 = 투매 소진) → 최강?
H-M3(대조): 항복 × 저신용 = 순수 정보 하락 → 반등 약함?
규율: 신용신호 T-3 지연(공표 T+2 보수), 커버 서브셋 평균 대비 초과, 일내셔플 플라시보,
연도 일관성. 스프레드 > 0.3 & CI 분리 & 7/9년 시 §17류 발행 태그 후보.
"""
import os, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
CACHE = "/Users/dongdong/research_cache"; COST = 0.3
rng = np.random.default_rng(0)

cr = pd.read_parquet(f"{CACHE}/credit.parquet", columns=["code","date","loan_rate"])
cr["date"] = pd.to_datetime(cr["date"]); cr["code"] = cr["code"].astype(str).str.zfill(6)
cr = cr.sort_values(["code","date"])
g = cr.groupby("code", group_keys=False)
cr["loan_d10"] = g["loan_rate"].apply(lambda s: s - s.shift(10))
for c in ("loan_rate","loan_d10"):
    cr[c] = g[c].shift(3)   # T-3 PIT

px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=["code","date","market","liq","ft_5_5","exec_5d","ret_5d"])
px["date"] = pd.to_datetime(px["date"]); px["code"] = px["code"].astype(str)
px["exec_5d"] = px["exec_5d"].replace([np.inf,-np.inf], np.nan)
liq_ok = ((px["market"]=="KOSPI")&(px["liq"]>=100e8))|((px["market"]=="KOSDAQ")&(px["liq"]>=30e8))
px = px[liq_ok].copy()
px["policy_ret"] = np.where(px["ft_5_5"]==1, 5.0, px["exec_5d"])
m = px.merge(cr, on=["code","date"], how="inner").dropna(subset=["loan_rate","policy_ret"])
m["pol_ex"] = m["policy_ret"] - m.groupby("date")["policy_ret"].transform("mean")
print(f"병합 {len(m)} rows, {m['code'].nunique()}종목, {m['date'].min().date()}..{m['date'].max().date()}", flush=True)

def stat(d, name):
    v = d["pol_ex"].dropna()
    if len(v) < 120: print(f"  {name:40s} n={len(v)} 부족"); return
    bs=[rng.choice(v.values,len(v),True).mean() for _ in range(300)]
    net=(d["policy_ret"]-COST).dropna(); yr=v.groupby(d["date"].dt.year).mean()
    print(f"  {name:40s} n={len(v):6d} 초과={v.mean():+.3f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] "
          f"netEV={net.mean():+.2f} 터치={(d['ft_5_5']==1).mean()*100:.0f}% yr+={int((yr>0).sum())}/{len(yr)}")

cap = m[m["ret_5d"] <= -13].copy()
q_lvl = cap.groupby("date")["loan_rate"].rank(pct=True)
q_chg = cap.groupby("date")["loan_d10"].rank(pct=True)
print(f"\n항복 표본: {len(cap)}")
stat(cap, "항복 전체 (기저)")
print("== H-M1 신용잔고율 레벨")
stat(cap[q_lvl >= 0.7], "항복 × 고신용(상위30%)")
stat(cap[q_lvl <= 0.3], "항복 × 저신용(하위30%) [H-M3 대조]")
print("== H-M2 신용 변화 (청산 진행도)")
stat(cap[q_chg <= 0.3], "항복 × 신용 급감중(청산 진행)")
stat(cap[q_chg >= 0.7], "항복 × 신용 유지/증가(청산 전)")
stat(cap[(q_lvl >= 0.7) & (q_chg <= 0.3)], "고신용 × 급감중 (소진 국면)")
print("== 플라시보 (일내 셔플)")
P = cap.copy(); P["loan_rate"] = P.groupby("date")["loan_rate"].transform(lambda s: rng.permutation(s.values))
qp = P.groupby("date")["loan_rate"].rank(pct=True)
stat(P[qp >= 0.7], "플라시보 항복 × 고신용")
stat(P[qp <= 0.3], "플라시보 항복 × 저신용")
print("\n== 비항복 대조 (신호가 항복 전용인지)")
non = m[m["ret_5d"] > -3]
qn = non.groupby("date")["loan_rate"].rank(pct=True)
stat(non[qn >= 0.7], "비항복 × 고신용")
print("DONE", flush=True)
