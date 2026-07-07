#!/usr/bin/env python3
"""완벽한 엣지 난제 — 재정식화: 검증축 3개(선별×레짐×프로필)의 교집합 최대 셀 (사전등록).

축(각각 독립 증명 완료): A 선별 = rank-1 (§7-D/E)  B 레짐 = RISK_OFF(dd20<-5|ret5<-3, §6)
C 프로필 = 베타항복 (ret_5d<=-13 & mkt5<=-3, §24: +1.24 9/9년)
사전등록 예측: 3중 셀은 단일축 최대치(+1.5)를 넘고 터치승률 70%+ — 아니면 축들이 중복 정보.
낚시 통제: 셀 정의는 위 3축 고정(그리드 탐색 금지), 8y 스윙 픽 + 연도 일관성으로만 판정.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
HERE = "/private/tmp/claude-501/-Users-dongdong-Projects-codex-swing-swing-main/4f929c12-f183-4aa8-ab51-372498389c15/scratchpad"
rng = np.random.default_rng(0)
P = pd.read_parquet(f"{HERE}/picks_8y.parquet")
P["date"] = pd.to_datetime(P["date"])
px = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet", columns=["code","date","market","ret_1d","liq"])
px["date"] = pd.to_datetime(px["date"])
for mkt in ("KOSPI","KOSDAQ"):
    liq = 100e8 if mkt=="KOSPI" else 30e8
    m = px[(px["market"]==mkt)&(px["liq"]>=liq)].groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1+m/100).cumprod()
    P.loc[P["market"]==mkt,"mkt5"] = P.loc[P["market"]==mkt,"date"].map(((lvl/lvl.shift(5)-1)*100))
    P.loc[P["market"]==mkt,"dd20"] = P.loc[P["market"]==mkt,"date"].map(((lvl/lvl.rolling(20).max()-1)*100))
P["risk_off"] = (P["dd20"]<-5)|(P["mkt5"]<-3)
P["beta_cap"] = (P["ret_5d"]<=-13)&(P["mkt5"]<=-3)

def stat(d, name):
    v = (d["policy_ret"]-0.3).dropna()
    if len(v)<25: print(f"  {name:44s} n={len(v)} 부족"); return None
    bs=[rng.choice(v.values,len(v),True).mean() for _ in range(400)]
    yr=v.groupby(d["date"].dt.year).mean()
    touch=(d["ft_5_5"]==1).mean()*100
    wk = len(v)/ (8*52)
    print(f"  {name:44s} n={len(v):5d} EV={v.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] "
          f"터치={touch:.0f}% yr+={int((yr>0).sum())}/{len(yr)} 주당{wk:.1f}픽")
    return v.mean()

r1 = P[P["rank"]==1]
print("== 단일축 (기준)")
stat(P, "전체 픽 (rank1-3)")
stat(r1, "A: rank-1")
stat(P[P["risk_off"]], "B: RISK_OFF")
stat(P[P["beta_cap"]], "C: 베타항복")
print("== 2중 교집합")
stat(r1[r1["risk_off"]], "A×B rank1 × RISK_OFF")
stat(r1[r1["beta_cap"]], "A×C rank1 × 베타항복")
stat(P[P["risk_off"]&P["beta_cap"]], "B×C RISK_OFF × 베타항복 (rank1-3)")
print("== 3중 교집합 (사전등록 본명제)")
stat(r1[r1["risk_off"]&r1["beta_cap"]], "A×B×C rank1 × RISK_OFF × 베타항복")
stat(P[(P["rank"]<=3)&P["risk_off"]&P["beta_cap"]], "완화: rank1-3 × RISK_OFF × 베타항복")
print("== 시장별 (3중, rank1-3)")
for mkt in ("KOSPI","KOSDAQ"):
    stat(P[(P["market"]==mkt)&P["risk_off"]&P["beta_cap"]], f"  {mkt} 3중")
print("DONE", flush=True)
