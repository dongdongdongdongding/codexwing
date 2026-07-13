#!/usr/bin/env python3
"""발행 임계 프론티어 (swing-main 신규, 사전등록): 승률·EV vs 빈도 곡선 — 배포 없음, 제안만.
F1 코스닥: pcal 임계 0.70~0.85 (월재학습 walk-forward 8개월)
F2 코스피: 티어분위 q0.2~q0.5 + 절대 p 플로어 (8OOS월, 운영규칙 순차 재현)
F3 스윙: top3 기본 vs rank1 vs 저ATR(§22) vs 베타항복(§24) — 빈도·승률·EV 표
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main/research/harness_2026_07")
rng = np.random.default_rng(0)

print("===== F1 코스닥 pcal 프론티어 =====", flush=True)
import lightgbm as lgb, joblib
from sklearn.isotonic import IsotonicRegression
P = pd.read_parquet("/Users/dongdong/Projects/codex_swing/swing-main/research/harness_2026_07/kosdaq_1500_panel.parquet")
P["date"] = pd.to_datetime(P["date"])
b = joblib.load("/Users/dongdong/Projects/codex_swing/swing-main/models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl")
FEATS = [f for f in b["features"] if f in P.columns]
LGBP = {k: v for k, v in (b.get("lgbm_params") or {}).items() if k not in ("random_state", "verbose")}
d = P.dropna(subset=["touch3d_t5"]).sort_values("date")
pools = []
for tm in pd.period_range("2025-11", "2026-06", freq="M"):
    t0, t1 = tm.start_time, tm.end_time
    tr = d[d["date"] < t0]; te = d[(d["date"] >= t0) & (d["date"] <= t1)].copy()
    if te.empty or len(tr) < 3000: continue
    Xtr = tr[FEATS].fillna(0).values; ytr = tr["touch3d_t5"].values
    n85 = int(len(tr) * 0.85)
    m = lgb.LGBMClassifier(**LGBP, random_state=0, verbose=-1); m.fit(Xtr[:n85], ytr[:n85])
    iso = IsotonicRegression(out_of_bounds="clip").fit(m.predict_proba(Xtr[n85:])[:, 1], ytr[n85:])
    mf = lgb.LGBMClassifier(**LGBP, random_state=0, verbose=-1); mf.fit(Xtr, ytr)
    te["pcal"] = iso.predict(mf.predict_proba(te[FEATS].fillna(0).values)[:, 1])
    pools.append(te)
A = pd.concat(pools)
A = A[A["pre_vwap_dist_pct"] >= 0].dropna(subset=["policy_t10_h5"])
tw = A["date"].dt.to_period("W").nunique()
for th in (0.70, 0.75, 0.80, 0.85):
    s = A[A["pcal"] >= th].sort_values("pcal", ascending=False).groupby("date", group_keys=False).head(1)
    if len(s) < 12: print(f"  pcal>={th}: n={len(s)} 부족"); continue
    net = s["policy_t10_h5"] - 0.33
    bs = [rng.choice(net.values, len(net), True).mean() for _ in range(300)]
    print(f"  pcal>={th}: 주당 {len(s)/tw:.1f}픽 win={(net>0).mean()*100:.0f}% EV={net.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}]", flush=True)

print("\n===== F2 코스피 티어 프론티어 =====", flush=True)
import xgboost as xgb
from sklearn.ensemble import ExtraTreesClassifier
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, assemble
from exit_policy_research import attach_paths
from model_zoo_intraday import policy_ret_frame
BASE = ITF + [c + "_d" for c in DLF]; gd = GUARDS["KOSPI"]
PP = assemble()
dm = PP[PP["mkt"] == "KOSPI"].dropna(subset=ITF + ["y3"]).sort_values("date").copy()
dm = attach_paths(dm); dm["pret"] = policy_ret_frame(dm, 5.0)
pools = []
for tm in TEST_MONTHS:
    t0 = pd.Timestamp(tm + "-01"); t1 = t0 + pd.offsets.MonthEnd(1)
    tr = dm[dm["date"] < t0]; te = dm[(dm["date"] >= t0) & (dm["date"] <= t1)].copy()
    if len(tr) < 3000 or te.empty: continue
    Xtr = tr[BASE].replace([np.inf,-np.inf],np.nan).clip(-1e4,1e4).fillna(0)
    Xte = te[BASE].replace([np.inf,-np.inf],np.nan).clip(-1e4,1e4).fillna(0)
    ps = []
    for mm in (lgb.LGBMClassifier(n_estimators=400,learning_rate=0.04,num_leaves=31,min_child_samples=60,subsample=0.8,colsample_bytree=0.7,reg_lambda=3,random_state=0,verbose=-1),
               xgb.XGBClassifier(n_estimators=400,max_depth=5,learning_rate=0.04,subsample=0.8,colsample_bytree=0.7,reg_lambda=3,verbosity=0,n_jobs=-1,random_state=0),
               ExtraTreesClassifier(n_estimators=250,min_samples_leaf=40,random_state=0,n_jobs=-1)):
        mm.fit(Xtr, tr["y3"]); ps.append(mm.predict_proba(Xte)[:, 1])
    te["p"] = np.mean(ps, axis=0)
    q = te[(te["liq"]>=gd["min_liq"])&(te["close_vwap"]>=gd["vwap"])&(te["idx_vol20_d"]>=gd["idx_vol_min"])]
    pools.append(q.sort_values("p",ascending=False).groupby("date",group_keys=False).head(1))
R = pd.concat(pools).dropna(subset=["pret"]).sort_values("date").reset_index(drop=True)
tw2 = R["date"].dt.to_period("W").nunique()
for qq in (0.2, 0.35, 0.5):
    thr = [float(np.quantile(R["p"].iloc[max(0,i-40):i], qq)) if i >= 15 else 0.65 for i in range(len(R))]
    s = R[R["p"] >= pd.Series(thr, index=R.index)]
    net = s["pret"] - 0.3
    bs = [rng.choice(net.values, len(net), True).mean() for _ in range(300)]
    print(f"  분위 q{qq}: 주당 {len(s)/tw2:.1f}픽 win={(net>0).mean()*100:.0f}% EV={net.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}]", flush=True)

print("\n===== F3 스윙 티어 표 (8y) =====", flush=True)
S = pd.read_parquet(os.path.join(HERE, "picks_8y.parquet"))
S["date"] = pd.to_datetime(S["date"])
qa = S.groupby("date")["atr_pct"].rank(pct=True)
px = pd.read_parquet("/Users/dongdong/research_cache/px_long.parquet", columns=["date","market","ret_1d","liq"])
px["date"] = pd.to_datetime(px["date"])
for mkt in ("KOSPI","KOSDAQ"):
    liq = 100e8 if mkt=="KOSPI" else 30e8
    m = px[(px["market"]==mkt)&(px["liq"]>=liq)].groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1+m/100).cumprod()
    S.loc[S["market"]==mkt,"mkt5"] = S.loc[S["market"]==mkt,"date"].map((lvl/lvl.shift(5)-1)*100)
def seg(dd, name):
    v = (dd["policy_ret"]-0.3).dropna()
    if len(v)<80: print(f"  {name:34s} n={len(v)} 부족"); return
    bs=[rng.choice(v.values,len(v),True).mean() for _ in range(300)]
    yr=v.groupby(dd["date"].dt.year).mean()
    print(f"  {name:34s} 주당{len(v)/(8*52):.1f}픽 터치={(dd['ft_5_5']==1).mean()*100:.0f}% EV={v.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}] yr+={int((yr>0).sum())}/{len(yr)}")
seg(S, "기본 top3 (현행)")
seg(S[S["rank"]==1], "rank-1만")
seg(S[qa<=0.33], "저ATR 1/3 (§22)")
seg(S[(S["ret_5d"]<=-13)&(S["mkt5"]<=-3)], "베타항복 (§24)")
seg(S[(qa<=0.33)&(S["rank"]==1)], "rank-1 × 저ATR")
json.dump({"done": True}, open(os.path.join(HERE, "threshold_frontier.done"), "w"))
print("\nDONE", flush=True)
