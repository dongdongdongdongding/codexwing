"""wvdd: KOSDAQ 15:00 pipeline — production-style classifier vs LambdaRank ordering.
Identical monthly folds; gates faithful to production (pre_vwap_dist>=0, p_cal>=0.80 where applicable).
Contract: rank-1, +10% touch/5d policy (promoted)."""
import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings("ignore")
import lightgbm as lgb, joblib
from sklearn.isotonic import IsotonicRegression

HERE="/private/tmp/claude-501/-Users-dongdong-Projects-codex-swing-swing-main/4f929c12-f183-4aa8-ab51-372498389c15/scratchpad"
P = pd.read_parquet(f"{HERE}/kosdaq_1500_panel.parquet")
P["date"]=pd.to_datetime(P["date"]); P["code"]=P["code"].astype(str).str.zfill(6)
# fill 2 missing bundle features from px_long prev-day
px = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet", columns=["code","date","vol_ratio","vol_trend"])
px["code"]=px["code"].astype(str).str.zfill(6); px["date"]=pd.to_datetime(px["date"])
px=px.sort_values(["code","date"])
g=px.groupby("code")
px["vol_ratio_prev"]=g["vol_ratio"].shift(1); px["vol_trend_prev"]=g["vol_trend"].shift(1)
P = P.merge(px[["code","date","vol_ratio_prev","vol_trend_prev"]], on=["code","date"], how="left")

b = joblib.load("/Users/dongdong/Projects/codex_swing/swing-main/models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl")
FEATS = b["features"]; LGBP = {k:v for k,v in (b.get("lgbm_params") or {}).items() if k not in ("random_state","verbose")}
print("features:", len(FEATS), "| lgbm_params:", LGBP or "default")
d = P.dropna(subset=["touch3d_t5"]).sort_values("date").copy()
months = pd.period_range("2025-11","2026-06",freq="M")
pools=[]
for tm in months:
    t0,t1=tm.start_time,tm.end_time
    tr=d[d["date"]<t0]; te=d[(d["date"]>=t0)&(d["date"]<=t1)].copy()
    if len(tr)<3000 or te.empty: continue
    Xtr=tr[FEATS].fillna(0).values; Xte=te[FEATS].fillna(0).values
    ytr=tr["touch3d_t5"].values
    params = LGBP or dict(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=60,
                          subsample=0.8, colsample_bytree=0.7, reg_lambda=3)
    m=lgb.LGBMClassifier(**params, random_state=0, verbose=-1)
    ncut=int(len(tr)*0.85)
    m.fit(Xtr[:ncut],ytr[:ncut])
    pv=m.predict_proba(Xtr[ncut:])[:,1]
    iso=IsotonicRegression(out_of_bounds="clip").fit(pv, ytr[ncut:])
    mfull=lgb.LGBMClassifier(**params, random_state=0, verbose=-1); mfull.fit(Xtr,ytr)
    te["p_raw"]=mfull.predict_proba(Xte)[:,1]
    te["p_cal"]=iso.predict(te["p_raw"].values)
    # ranker on policy-return grade
    grade=tr.groupby("date")["policy_t10_h5"].rank(pct=True).fillna(0.5)
    ylab=np.clip((grade*4).astype(int),0,3).values
    grp=tr.groupby("date",sort=False).size().values
    rk=lgb.LGBMRanker(objective="lambdarank",n_estimators=400,learning_rate=0.05,num_leaves=31,
                      min_child_samples=60,subsample=0.8,colsample_bytree=0.7,reg_lambda=3,
                      random_state=0,verbose=-1,label_gain=list(range(32)))
    rk.fit(Xtr,ylab,group=grp)
    te["p_rank"]=rk.predict(Xte)
    pools.append(te.assign(month=str(tm)))
    print(f"[{tm}] pool={len(te)}", flush=True)
A=pd.concat(pools)
A=A[A["pre_vwap_dist_pct"]>=0]  # production entry guard (all variants)
print(f"\nafter vwap guard: {len(A)} rows, months={A['month'].nunique()}")
def ev(sel,label):
    s=sel.dropna(subset=["policy_t10_h5"])
    if len(s)<10: print(f" {label:34s} n<10"); return
    net=s["policy_t10_h5"]-0.33
    mo=s.groupby("month")["policy_t10_h5"].mean()
    bs=[np.random.default_rng(x).choice(net.values,len(net),True).mean() for x in range(300)]
    dwk=s.groupby(s["date"].dt.to_period("W"))["date"].nunique().mean()
    print(f" {label:34s} n={len(s):3d} win={(net>0).mean()*100:5.1f}% EV={net.mean():5.2f} CI=({np.percentile(bs,2.5):.2f},{np.percentile(bs,97.5):.2f}) d/wk={dwk:.1f} negMo={int((mo<0.33).sum())}/{len(mo)}")
# A) production mimic: p_cal>=0.80, rank by p_cal, top-1
qa=A[A["p_cal"]>=0.80]
ev(qa.sort_values("p_cal",ascending=False).groupby("date",group_keys=False).head(1), "A prod-mimic: pcal>=0.8, top1 by pcal")
# B) gate kept, ordered by ranker
ev(qa.sort_values("p_rank",ascending=False).groupby("date",group_keys=False).head(1), "B gate pcal>=0.8, top1 by RANKER")
# C) no p gate, top1 by ranker
ev(A.sort_values("p_rank",ascending=False).groupby("date",group_keys=False).head(1), "C no-gate, top1 by RANKER")
# D) no p gate, top1 by p_cal (gate ablation)
ev(A.sort_values("p_cal",ascending=False).groupby("date",group_keys=False).head(1), "D no-gate, top1 by pcal")
