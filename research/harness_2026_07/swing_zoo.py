import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
import lightgbm as lgb
from swing_firsttouch_ranker_8y import FEATS, COST, load

for mkt in ("KOSDAQ","KOSPI"):
    px = load(mkt)
    d = px.dropna(subset=["ft_5_5"]+FEATS[:6]).sort_values("date").copy()
    quarters = pd.period_range("2019Q1","2026Q2",freq="Q")
    pools=[]
    for q in quarters:
        t0,t1=q.start_time,q.end_time
        tr=d[(d["date"]<t0)&(d["date"]>=t0-pd.DateOffset(years=2))].sort_values("date")
        te=d[(d["date"]>=t0)&(d["date"]<=t1)].copy()
        if len(tr)<20000 or te.empty: continue
        Xtr=tr[FEATS].clip(-1e4,1e4).values; Xte=te[FEATS].clip(-1e4,1e4).values
        mc=lgb.LGBMClassifier(n_estimators=400,learning_rate=0.05,num_leaves=63,min_child_samples=100,
                              subsample=0.8,colsample_bytree=0.7,reg_lambda=5,random_state=0,verbose=-1)
        mc.fit(Xtr,tr["ft_5_5"]); te["p_cls"]=mc.predict_proba(Xte)[:,1]
        ok=tr["policy_ret"].notna().values
        mr=lgb.LGBMRegressor(n_estimators=400,learning_rate=0.05,num_leaves=63,min_child_samples=100,
                             subsample=0.8,colsample_bytree=0.7,reg_lambda=5,random_state=0,verbose=-1)
        mr.fit(Xtr[ok],tr.loc[ok,"policy_ret"].values); te["p_ev"]=mr.predict(Xte)
        grade=tr.groupby("date")["policy_ret"].rank(pct=True).fillna(0.5)
        ylab=np.clip((grade*4).astype(int),0,3).values
        grp=tr.groupby("date",sort=False).size().values
        rk=lgb.LGBMRanker(objective="lambdarank",n_estimators=300,learning_rate=0.05,num_leaves=63,
                          min_child_samples=100,subsample=0.8,colsample_bytree=0.7,reg_lambda=5,
                          random_state=0,verbose=-1,label_gain=list(range(32)))
        rk.fit(Xtr,ylab,group=grp); te["p_rk"]=rk.predict(Xte)
        pools.append(te[["date","code","ft_5_5","policy_ret","p_cls","p_ev","p_rk"]])
        print(f"[{mkt} {q}] done", flush=True)
    A=pd.concat(pools); A["year"]=A["date"].dt.year
    print(f"\n== {mkt} swing zoo (rank-1/day, +5 touch-exit policy, net)", flush=True)
    base_yr=None
    for nm in ("p_cls","p_ev","p_rk"):
        s=A.sort_values(nm,ascending=False).groupby("date",group_keys=False).head(1).dropna(subset=["policy_ret"])
        net=s["policy_ret"]-COST
        yr=s.groupby("year").apply(lambda g:(g["policy_ret"]-COST).mean())
        bs=[np.random.default_rng(x).choice(net.values,len(net),True).mean() for x in range(300)]
        extra=""
        if nm=="p_cls": base_yr=yr
        else:
            dd=(yr-base_yr).dropna(); extra=f" Δyr={dd.mean():+.2f} better={int((dd>0).sum())}/{len(dd)}"
        print(f"  {nm[2:]:4s} n={len(s)} win_ft={s['ft_5_5'].mean()*100:.1f}% EV={net.mean():.2f} CI=({np.percentile(bs,2.5):.2f},{np.percentile(bs,97.5):.2f}) yr+={int((yr>0).sum())}/{len(yr)}{extra}", flush=True)
