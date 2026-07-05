"""P1 (swing-main-67zc): KOSDAQ 15:00 lane pick-frequency recovery.
H1: p_cal threshold frontier 0.65-0.80 (pass: 3+ picks/wk & EV CI>0 & win>=70%).
H2: STATIC (train once, never retrain — current production style) vs MONTHLY retrain.
Same panel/folds as wvdd revalidation; contract t10/5d, cost 0.33 (production RT)."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
import lightgbm as lgb, joblib
from sklearn.isotonic import IsotonicRegression

HERE="/private/tmp/claude-501/-Users-dongdong-Projects-codex-swing-swing-main/4f929c12-f183-4aa8-ab51-372498389c15/scratchpad"
P = pd.read_parquet(f"{HERE}/kosdaq_1500_panel.parquet")
P["date"]=pd.to_datetime(P["date"]); P["code"]=P["code"].astype(str).str.zfill(6)
px = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet", columns=["code","date","vol_ratio","vol_trend"])
px["code"]=px["code"].astype(str).str.zfill(6); px["date"]=pd.to_datetime(px["date"])
px=px.sort_values(["code","date"]); g=px.groupby("code")
px["vol_ratio_prev"]=g["vol_ratio"].shift(1); px["vol_trend_prev"]=g["vol_trend"].shift(1)
P = P.merge(px[["code","date","vol_ratio_prev","vol_trend_prev"]], on=["code","date"], how="left")
b = joblib.load("/Users/dongdong/Projects/codex_swing/swing-main/models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl")
FEATS=b["features"]; LGBP={k:v for k,v in (b.get("lgbm_params") or {}).items() if k not in ("random_state","verbose")}
d = P.dropna(subset=["touch3d_t5"]).sort_values("date").copy()
months = pd.period_range("2025-11","2026-06",freq="M")

def fit_cal(tr):
    Xtr=tr[FEATS].fillna(0).values; ytr=tr["touch3d_t5"].values
    ncut=int(len(tr)*0.85)
    m=lgb.LGBMClassifier(**LGBP, random_state=0, verbose=-1); m.fit(Xtr[:ncut],ytr[:ncut])
    iso=IsotonicRegression(out_of_bounds="clip").fit(m.predict_proba(Xtr[ncut:])[:,1], ytr[ncut:])
    mf=lgb.LGBMClassifier(**LGBP, random_state=0, verbose=-1); mf.fit(Xtr,ytr)
    return mf, iso

# STATIC: train once before first test month
tr0 = d[d["date"] < months[0].start_time]
ms, isos = fit_cal(tr0)
pools=[]
for tm in months:
    t0,t1=tm.start_time,tm.end_time
    tr=d[d["date"]<t0]; te=d[(d["date"]>=t0)&(d["date"]<=t1)].copy()
    if te.empty: continue
    Xte=te[FEATS].fillna(0).values
    te["pcal_static"]=isos.predict(ms.predict_proba(Xte)[:,1])
    if len(tr)>=3000:
        mm,ii=fit_cal(tr)
        te["pcal_monthly"]=ii.predict(mm.predict_proba(Xte)[:,1])
    pools.append(te.assign(month=str(tm)))
A=pd.concat(pools)
A=A[A["pre_vwap_dist_pct"]>=0]
tw=A["date"].dt.to_period("W").nunique()
print(f"pool after vwap guard: {len(A)} rows, {A['month'].nunique()} months, {tw} weeks\n")
print(f"{'variant':>8} {'pcal>=':>6} {'n':>4} {'pk/wk':>5} {'win%':>5} {'EV':>6} {'CI':>15} {'negMo':>5}")
for var in ("pcal_static","pcal_monthly"):
    Av=A.dropna(subset=[var])
    for th in (0.65,0.70,0.75,0.80):
        q=Av[Av[var]>=th]
        s=q.sort_values(var,ascending=False).groupby("date",group_keys=False).head(1).dropna(subset=["policy_t10_h5"])
        if len(s)<20: 
            print(f"{var[5:]:>8} {th:>6} n<20"); continue
        net=s["policy_t10_h5"]-0.33
        mo=s.groupby("month")["policy_t10_h5"].mean()-0.33
        bs=[np.random.default_rng(x).choice(net.values,len(net),True).mean() for x in range(300)]
        print(f"{var[5:]:>8} {th:>6} {len(s):>4} {len(s)/tw:>5.1f} {(net>0).mean()*100:>5.1f} {net.mean():>6.2f} ({np.percentile(bs,2.5):>5.2f},{np.percentile(bs,97.5):>5.2f}) {int((mo<0).sum())}/{len(mo)}")
