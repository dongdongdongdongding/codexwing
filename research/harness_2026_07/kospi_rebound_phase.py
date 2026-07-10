#!/usr/bin/env python3
"""코스피 장중 레인: 반등국면 조건화 검증 (사전등록, §24 보조정리 유도).
가설: 레인 픽의 항복류 매수는 동반붕괴(mkt5<=-3)에서만 유효 — 반등국면(dd20 깊지만
mkt5>-3)에선 EV 열화 (라이브 7/1-3 손실 클러스터 재현 구조).
셀 정의는 §24에서 고정 (그리드 탐색 금지): mkt5<=-3 / -3<mkt5<1 / mkt5>=1."""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
os.chdir("/Users/dongdong/Projects/codex_swing/swing-main/research/harness_2026_07")
sys.path.insert(0, "."); sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
import lightgbm as lgb, xgboost as xgb
from sklearn.ensemble import ExtraTreesClassifier
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, assemble
from exit_policy_research import attach_paths
from model_zoo_intraday import policy_ret_frame
BASE = ITF + [c+"_d" for c in DLF]; COST = 0.3
rng = np.random.default_rng(0)
px = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet", columns=["date","market","ret_1d","liq"])
px["date"] = pd.to_datetime(px["date"])
m = px[(px["market"]=="KOSPI")&(px["liq"]>=100e8)].groupby("date")["ret_1d"].mean().sort_index()
lvl = (1+m/100).cumprod()
ST = pd.DataFrame({"mkt5": (lvl/lvl.shift(5)-1)*100, "dd20": (lvl/lvl.rolling(20).max()-1)*100})
P = assemble(); gd = GUARDS["KOSPI"]
dm = P[P["mkt"]=="KOSPI"].dropna(subset=ITF+["y3"]).sort_values("date").copy()
dm = attach_paths(dm); dm["pret"] = policy_ret_frame(dm, 5.0)
pools = []
for seed in (0,1,2):
    for tm in TEST_MONTHS:
        t0 = pd.Timestamp(tm+"-01"); t1 = t0+pd.offsets.MonthEnd(1)
        tr = dm[dm["date"]<t0]; te = dm[(dm["date"]>=t0)&(dm["date"]<=t1)].copy()
        if len(tr)<3000 or te.empty: continue
        Xtr = tr[BASE].replace([np.inf,-np.inf],np.nan).clip(-1e4,1e4).fillna(0)
        Xte = te[BASE].replace([np.inf,-np.inf],np.nan).clip(-1e4,1e4).fillna(0)
        ps=[]
        for mm in (lgb.LGBMClassifier(n_estimators=400,learning_rate=0.04,num_leaves=31,min_child_samples=60,subsample=0.8,colsample_bytree=0.7,reg_lambda=3,random_state=seed,verbose=-1),
                   xgb.XGBClassifier(n_estimators=400,max_depth=5,learning_rate=0.04,subsample=0.8,colsample_bytree=0.7,reg_lambda=3,verbosity=0,n_jobs=-1,random_state=seed),
                   ExtraTreesClassifier(n_estimators=250,min_samples_leaf=40,random_state=seed,n_jobs=-1)):
            mm.fit(Xtr,tr["y3"]); ps.append(mm.predict_proba(Xte)[:,1])
        te["p"]=np.mean(ps,axis=0)
        q=te[(te["liq"]>=gd["min_liq"])&(te["close_vwap"]>=gd["vwap"])&(te["idx_vol20_d"]>=gd["idx_vol_min"])]
        pools.append(q.sort_values("p",ascending=False).groupby("date",group_keys=False).head(1))
A = pd.concat(pools).dropna(subset=["pret"]).join(ST, on="date")
A["capit"] = A["ret_5d_d"] <= -13

def seg(d, name):
    v = (d["pret"]-COST).dropna()
    if len(v)<15: print(f"  {name:40s} n={len(v)} 부족"); return
    bs=[rng.choice(v.values,len(v),True).mean() for _ in range(400)]
    print(f"  {name:40s} n={len(v):4d} EV={v.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] 승={(v>0.3).mean()*100:.0f}%")

print(f"rank-1 픽 {len(A)} (3시드)")
seg(A, "전체")
print("== §24 셀 (시장 5d 국면)")
seg(A[A["mkt5"]<=-3], "동반붕괴 국면 (mkt5<=-3)")
seg(A[(A["mkt5"]>-3)&(A["mkt5"]<1)], "중립/반등 국면 (-3<mkt5<1)")
seg(A[A["mkt5"]>=1], "상승 국면 (mkt5>=1)")
print("== 항복픽 한정")
seg(A[A["capit"]&(A["mkt5"]<=-3)], "항복픽 × 동반붕괴")
seg(A[A["capit"]&(A["mkt5"]>-3)], "항복픽 × 중립/반등 ← 라이브 손실 재현?")
print("== 드로다운 깊지만 반등 중 (라이브 7/1-3 정확 재현)")
seg(A[(A["dd20"]<-8)&(A["mkt5"]>-3)], "dd20<-8 & mkt5>-3")
json.dump({"done":True}, open("/private/tmp/claude-501/-Users-dongdong-Projects-codex-swing-swing-main/4f929c12-f183-4aa8-ab51-372498389c15/scratchpad/kospi_rebound_phase.done","w"))
print("DONE", flush=True)
