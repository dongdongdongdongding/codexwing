"""⑤ KOSPI 선별 레인(§7-E) 강건성: 3시드 × 비용 0.3/0.5/0.8 스윕 (rank-1, t5/5d, 8 OOS월)."""
import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
import lightgbm as lgb, xgboost as xgb
from sklearn.ensemble import ExtraTreesClassifier
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, assemble
from exit_policy_research import attach_paths
from model_zoo_intraday import policy_ret_frame
BASE = ITF + [c+"_d" for c in DLF]
P = assemble(); gd = GUARDS["KOSPI"]
dm = P[P["mkt"]=="KOSPI"].dropna(subset=ITF+["y3"]).sort_values("date").copy()
dm = attach_paths(dm); dm["pret_gross"] = policy_ret_frame(dm, 5.0)
rows=[]
for seed in (0,1,2):
    pools=[]
    for tm in TEST_MONTHS:
        t0=pd.Timestamp(tm+"-01"); t1=t0+pd.offsets.MonthEnd(1)
        tr=dm[dm["date"]<t0]; te=dm[(dm["date"]>=t0)&(dm["date"]<=t1)].copy()
        if len(tr)<3000 or te.empty: continue
        Xtr=tr[BASE].replace([np.inf,-np.inf],np.nan).clip(-1e4,1e4).fillna(0)
        Xte=te[BASE].replace([np.inf,-np.inf],np.nan).clip(-1e4,1e4).fillna(0)
        ps=[]
        for m in (lgb.LGBMClassifier(n_estimators=400,learning_rate=0.04,num_leaves=31,min_child_samples=60,subsample=0.8,colsample_bytree=0.7,reg_lambda=3,random_state=seed,verbose=-1),
                  xgb.XGBClassifier(n_estimators=400,max_depth=5,learning_rate=0.04,subsample=0.8,colsample_bytree=0.7,reg_lambda=3,verbosity=0,n_jobs=-1,random_state=seed),
                  ExtraTreesClassifier(n_estimators=250,min_samples_leaf=40,random_state=seed,n_jobs=-1)):
            m.fit(Xtr,tr["y3"]); ps.append(m.predict_proba(Xte)[:,1])
        te["p"]=np.mean(ps,axis=0)
        q=te[(te["liq"]>=gd["min_liq"])&(te["close_vwap"]>=gd["vwap"])&(te["idx_vol20_d"]>=gd["idx_vol_min"])]
        pk=q.sort_values("p",ascending=False).groupby("date",group_keys=False).head(1)
        pools.append(pk)
    A=pd.concat(pools).dropna(subset=["pret_gross"])
    for cost in (0.3,0.5,0.8):
        net=A["pret_gross"]-cost
        mo=A.assign(m=A["date"].dt.to_period("M")).groupby("m").apply(lambda g:(g["pret_gross"]-cost).mean())
        rows.append((seed,cost,len(A),round((net>0).mean()*100,1),round(net.mean(),2),int((mo<0).sum()),len(mo)))
        print(f"seed={seed} cost={cost} n={len(A)} win={(net>0).mean()*100:.1f}% EV={net.mean():.2f} negMo={int((mo<0).sum())}/{len(mo)}", flush=True)
import json; json.dump(rows, open("kospi_robustness.json","w"))
