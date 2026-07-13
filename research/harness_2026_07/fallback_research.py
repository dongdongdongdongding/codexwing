#!/usr/bin/env python3
"""기권일 FALLBACK 후보 실증 (swing-main-xfnc, 사전등록).
질문: 티어 미달일의 최선 후보(argmax 확률)는 얼마나 맞나 — win>=55% & EV>0이면 배포.
K1 코스닥: 월재학습 walk-forward(2025-11..2026-06), max pcal<0.70일 → argmax pcal 1픽 코호트.
K2 코스피: 8OOS월 rank-1 + 운영 티어규칙(trailing 40일 q0.2) 순차 적용 → CANDIDATE일 코호트.
둘 다 pcal/p 밴드별 층화(정직 확률 표시용)."""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main/research/harness_2026_07")

print("===== K1 코스닥 장중 (t10/5d, 비용 0.33) =====", flush=True)
import lightgbm as lgb, joblib
from sklearn.isotonic import IsotonicRegression
P = pd.read_parquet(os.path.join(HERE, "kosdaq_1500_panel.parquet"))
P["date"] = pd.to_datetime(P["date"]); P["code"] = P["code"].astype(str).str.zfill(6)
b = joblib.load("/Users/dongdong/Projects/codex_swing/swing-main/models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl")
FEATS = [f for f in b["features"] if f in P.columns]
print(f"패널 {len(P)} | 피처 {len(FEATS)}/{len(b['features'])}", flush=True)
LGBP = {k: v for k, v in (b.get("lgbm_params") or {}).items() if k not in ("random_state", "verbose")}
d = P.dropna(subset=["touch3d_t5"]).sort_values("date").copy()
months = pd.period_range("2025-11", "2026-06", freq="M")
pools = []
for tm in months:
    t0, t1 = tm.start_time, tm.end_time
    tr = d[d["date"] < t0]; te = d[(d["date"] >= t0) & (d["date"] <= t1)].copy()
    if te.empty or len(tr) < 3000: continue
    Xtr = tr[FEATS].fillna(0).values; ytr = tr["touch3d_t5"].values
    ncut = int(len(tr) * 0.85)
    m = lgb.LGBMClassifier(**LGBP, random_state=0, verbose=-1); m.fit(Xtr[:ncut], ytr[:ncut])
    iso = IsotonicRegression(out_of_bounds="clip").fit(m.predict_proba(Xtr[ncut:])[:, 1], ytr[ncut:])
    mf = lgb.LGBMClassifier(**LGBP, random_state=0, verbose=-1); mf.fit(Xtr, ytr)
    te["pcal"] = iso.predict(mf.predict_proba(te[FEATS].fillna(0).values)[:, 1])
    pools.append(te)
    print(f"  {tm} done", flush=True)
A = pd.concat(pools)
A = A[A["pre_vwap_dist_pct"] >= 0].dropna(subset=["policy_t10_h5"])
rng = np.random.default_rng(0)
def seg(s, name):
    if len(s) < 15: print(f"  {name:36s} n={len(s)} 부족"); return
    net = s["policy_t10_h5"] - 0.33
    bs = [rng.choice(net.values, len(net), True).mean() for _ in range(300)]
    print(f"  {name:36s} n={len(s):4d} win={(net>0).mean()*100:.0f}% EV={net.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}]")
day_max = A.groupby("date")["pcal"].transform("max")
prim_day = day_max >= 0.70
r1 = A.sort_values("pcal", ascending=False).groupby("date", group_keys=False).head(1)
seg(r1[r1["pcal"] >= 0.70], "PRIMARY일 rank-1 (현행 발행)")
fb = r1[r1["pcal"] < 0.70]
seg(fb, "기권일 FALLBACK (argmax pcal)")
for lo, hi in ((0.60, 0.70), (0.50, 0.60), (0.0, 0.50)):
    seg(fb[(fb["pcal"] >= lo) & (fb["pcal"] < hi)], f"  FALLBACK pcal {lo:.2f}-{hi:.2f}")
tw = A["date"].dt.to_period("W").nunique()
print(f"  발행일: PRIMARY {prim_day.groupby(A['date']).first().sum()} / 전체 {A['date'].nunique()}일 ({tw}주)")

print("\n===== K2 코스피 장중 (t5/5d, 비용 0.3, 운영 티어규칙 재현) =====", flush=True)
import xgboost as xgb
from sklearn.ensemble import ExtraTreesClassifier
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, assemble
from exit_policy_research import attach_paths
from model_zoo_intraday import policy_ret_frame
BASE = ITF + [c + "_d" for c in DLF]
gd = GUARDS["KOSPI"]
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
# 운영 티어규칙 순차 재현: p >= trailing 40일 rank-1 p의 q0.2 (min 15, fallback 0.65)
thr = []
for i in range(len(R)):
    w = R["p"].iloc[max(0, i-40):i]
    thr.append(float(np.quantile(w, 0.2)) if len(w) >= 15 else 0.65)
R["thr"] = thr
R["tier"] = np.where(R["p"] >= R["thr"], "PRIMARY", "CANDIDATE")
def seg2(s, name):
    if len(s) < 10: print(f"  {name:36s} n={len(s)} 부족"); return
    net = s["pret"] - 0.3
    bs = [rng.choice(net.values, len(net), True).mean() for _ in range(300)]
    print(f"  {name:36s} n={len(s):4d} win={(net>0.0).mean()*100:.0f}% EV={net.mean():+.2f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}]")
seg2(R[R["tier"]=="PRIMARY"], "PRIMARY일 (현행 발행)")
seg2(R[R["tier"]=="CANDIDATE"], "기권일 CANDIDATE (=FALLBACK 후보)")
qb = R[R["tier"]=="CANDIDATE"]
med = qb["p"].median()
seg2(qb[qb["p"] >= med], "  CANDIDATE 상위半 (p 중앙 이상)")
seg2(qb[qb["p"] < med], "  CANDIDATE 하위半")
json.dump({"done": True}, open(os.path.join(HERE, "fallback_research.done"), "w"))
print("\nDONE", flush=True)
