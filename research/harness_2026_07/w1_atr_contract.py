#!/usr/bin/env python3
"""W1 근사: 변동성(ATR) 조건부 계약 배정 — 라벨수학 (swing-main-h3cu).
같은 랭커 픽(picks_8y rank1-3)에 ATR 터실별로 +5%/5d vs +7%/10d 계약 성과 비교.
가설: 고정 +5%가 저변동주엔 먼 목표/고변동주엔 노이즈 — 계약을 변동성에 맞추면 EV↑."""
import os, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = "/Users/dongdong/research_cache"
COST = 0.3
rng = np.random.default_rng(0)
P = pd.read_parquet(os.path.join(HERE, "picks_8y.parquet"))
P["date"] = pd.to_datetime(P["date"])
lab = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=["code","date","ft10_7_4","exec_10d","ft_5_3","atr_pct"])
lab["date"] = pd.to_datetime(lab["date"])
P = P.drop(columns=["atr_pct"], errors="ignore").merge(lab, on=["code","date"], how="left")
for c in ("exec_10d",):
    P[c] = P[c].replace([np.inf,-np.inf], np.nan)
P["pol_55"] = np.where(P["ft_5_5"]==1, 5.0, P["exec_5d"])          # +5/5d (현행)
P["pol_74"] = np.where(P["ft10_7_4"]==1, 7.0, P["exec_10d"])       # +7/10d
P["pol_53"] = np.where(P["ft_5_3"]==1, 5.0, P["exec_5d"])          # +5/-3 스톱형 참고

def seg(d, col, name, days):
    v = (d[col] - COST).dropna()
    if len(v) < 150: print(f"  {name:34s} n={len(v)} 부족"); return
    bs=[rng.choice(v.values,len(v),True).mean() for _ in range(300)]
    yr=v.groupby(d["date"].dt.year).mean()
    print(f"  {name:34s} n={len(v):5d} EV={v.mean():+.3f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] "
          f"일평균={v.mean()/days:+.3f} 승률={(v>0).mean()*100:.0f}% yr+={int((yr>0).sum())}/{len(yr)}")

q = P.groupby("date")["atr_pct"].rank(pct=True)
for tname, m in (("저변동(하위1/3)", q<=0.33), ("중변동", (q>0.33)&(q<=0.67)), ("고변동(상위1/3)", q>0.67)):
    d = P[m]
    print(f"-- ATR {tname}")
    seg(d, "pol_55", "  +5%/5d (현행)", 5)
    seg(d, "pol_74", "  +7%/10d", 10)
print("-- 전체")
seg(P, "pol_55", "  고정 +5%/5d", 5)
mix = P.copy()
mix["pol_mix"] = np.where(q>0.67, mix["pol_74"], mix["pol_55"])
seg(mix, "pol_mix", "  혼합(고변동만 +7/10d)", 6.7)
print("DONE", flush=True)
