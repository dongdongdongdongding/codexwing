#!/usr/bin/env python3
"""난제 2호-b: 항복 해부 (사전등록). 베타 항복(시장 동반 붕괴=공황) vs 고유 항복(시장 멀쩡,
단독 붕괴=정보성 하락 개연). 예측: 고유 항복은 반등 약함(§23 informed shorts 보조정리 정합),
베타 항복이 코어. 검증 통과 시 → 장중/스윙 항복픽 신뢰 태그(§17류 발행 조건화 후보)."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
CACHE="/Users/dongdong/research_cache"; COST=0.3
rng=np.random.default_rng(0)
px=pd.read_parquet(f"{CACHE}/px_long.parquet",columns=["code","date","market","liq","ft_5_5","exec_5d","ret_5d","ret_1d"])
px["date"]=pd.to_datetime(px["date"])
liq_ok=((px["market"]=="KOSPI")&(px["liq"]>=100e8))|((px["market"]=="KOSDAQ")&(px["liq"]>=30e8))
px=px[liq_ok].copy()
px["exec_5d"]=px["exec_5d"].replace([np.inf,-np.inf],np.nan)
px["policy_ret"]=np.where(px["ft_5_5"]==1,5.0,px["exec_5d"])
# 시장 5d (시장별 등가중)
mret=px.groupby(["market","date"])["ret_1d"].mean().rename("m1")
lvl=(1+mret/100).groupby("market").cumprod()
m5=(lvl/lvl.groupby("market").shift(5)-1)*100
px=px.join(m5.rename("mkt5"),on=["market","date"])
px["pol_ex"]=px["policy_ret"]-px.groupby("date")["policy_ret"].transform("mean")
cap=px[px["ret_5d"]<=-13].dropna(subset=["policy_ret","mkt5"]).copy()
cap["idio5"]=cap["ret_5d"]-cap["mkt5"]

def stat(d,name):
    v=d["pol_ex"].dropna()
    if len(v)<200: print(f"  {name:42s} n={len(v)} 부족"); return
    bs=[rng.choice(v.values,len(v),True).mean() for _ in range(300)]
    net=(d["policy_ret"]-COST).dropna(); yr=v.groupby(d["date"].dt.year).mean()
    print(f"  {name:42s} n={len(v):6d} 초과={v.mean():+.3f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] "
          f"netEV={net.mean():+.2f} 터치={(d['ft_5_5']==1).mean()*100:.0f}% yr+={int((yr>0).sum())}/{len(yr)}")

print(f"항복 표본 {len(cap)} (8y 전체 유동풀)")
stat(cap,"항복 전체")
print("== 시장 상태로 분해")
stat(cap[cap["mkt5"]<=-3],"베타 항복 (시장 5d<=-3 동반붕괴)")
stat(cap[(cap["mkt5"]>-3)&(cap["mkt5"]<1)],"중립시장 항복")
stat(cap[cap["mkt5"]>=1],"고유 항복 (시장 상승 중 단독붕괴)")
print("== 고유성 강도로 분해 (idio5 = ret5d - mkt5)")
q=cap.groupby("date")["idio5"].rank(pct=True)
stat(cap[q<=0.3],"최고 고유붕괴 (하위30%)")
stat(cap[q>=0.7],"최소 고유붕괴 (베타성)")
print("== netEV 관점 (절대, 시장 리스크 포함 — 운영 계약 기준)")
for nm,d in (("베타항복",cap[cap["mkt5"]<=-3]),("고유항복",cap[cap["mkt5"]>=1])):
    net=(d["policy_ret"]-COST).dropna()
    if len(net)>200:
        bs=[rng.choice(net.values,len(net),True).mean() for _ in range(300)]
        print(f"  {nm}: netEV {net.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] n={len(net)}")
print("DONE",flush=True)
