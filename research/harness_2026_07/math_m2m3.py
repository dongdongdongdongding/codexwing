#!/usr/bin/env python3
"""M2(잔차모멘텀)+M3(시계열구조) 결합 증분 — 시드 강건성 판정."""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE); sys.path.insert(0, HERE)
import numpy as np, pandas as pd, lightgbm as lgb
from math_features import build, FEATS, COST

PANEL = os.path.join(HERE, "math_panel.parquet")
M23 = ["beta60", "resid_mom20", "ivol20", "ar1_60", "vratio5", "ewvol_ratio"]
if os.path.exists(PANEL):
    px = pd.read_parquet(PANEL)
    px["date"] = pd.to_datetime(px["date"])
    print("패널 캐시 재사용", flush=True)
else:
    px, _ = build()
    px.to_parquet(PANEL)
assert all(c in px.columns for c in M23), "패널에 M2M3 피처 없음"
rng = np.random.default_rng(7)
for i in range(6):
    px[f"nz6_{i}"] = rng.standard_normal(len(px))
NZ6 = [f"nz6_{i}" for i in range(6)]


def wf(feats, tag, seed):
    pools = []
    for yr in (2024, 2025, 2026):
        t0 = pd.Timestamp(f"{yr}-01-01")
        tr = px[(px["date"] < t0) & (px["date"] >= t0 - pd.DateOffset(years=2))]
        te = px[(px["date"] >= t0) & (px["date"] < t0 + pd.DateOffset(years=1))].copy()
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=seed, verbose=-1)
        m.fit(tr[feats].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4), tr["ft_5_5"])
        te["p"] = m.predict_proba(te[feats].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4))[:, 1]
        pools.append(te.sort_values("p", ascending=False).groupby("date", group_keys=False).head(3))
    A = pd.concat(pools).dropna(subset=["policy_ret"])
    net = A["policy_ret"] - COST
    yrs = {int(k): round(v, 3) for k, v in net.groupby(A["date"].dt.year).mean().items()}
    print(f"  seed{seed} {tag:12s} EV={net.mean():+.3f} 연도별 {yrs}", flush=True)
    return float(net.mean())


res = {}
for tag, feats in (("베이스", FEATS), ("+M2M3", FEATS + M23), ("+노이즈6", FEATS + NZ6)):
    vals = [wf(feats, tag, s) for s in (0, 1, 2)]
    res[tag] = {"mean": float(np.mean(vals)), "std": float(np.std(vals)), "vals": vals}
    print(f"  == {tag}: 평균 {np.mean(vals):+.3f} ± {np.std(vals):.3f}", flush=True)
json.dump(res, open(os.path.join(HERE, "math_m2m3.done"), "w"))
print("DONE", flush=True)
