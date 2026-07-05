#!/usr/bin/env python3
"""A2 (swing-main-q0ia): skill vs base-rate decomposition of the intraday lanes.

Question: was the 2026-06 collapse (hit 52.8% both markets) a MODEL-SKILL failure or a
MARKET-BASE-RATE failure? Same-day universe control (down_edge_was_beta_correction lesson):
  skill_margin(month) = picks_hit(month) − guard-pool_hit(month)
If June skill margin held while pool base rate collapsed → market-timing problem (B1 fix).
If skill margin went negative → model decay (refresh cadence fix).
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, assemble

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill_baserate_results.json")


def main():
    import lightgbm as lgb, xgboost as xgb
    from sklearn.ensemble import ExtraTreesClassifier
    P = assemble()
    BASE = ITF + [c + "_d" for c in DLF]
    results = {}
    for mkt in ("KOSPI", "KOSDAQ"):
        gd = GUARDS[mkt]
        dm = P[P["mkt"] == mkt].dropna(subset=ITF + ["y3"]).copy()
        dm["month"] = dm["date"].dt.strftime("%Y-%m")
        # market-wide base rate for every panel month (no model needed)
        allmo = dm.groupby("month").agg(mkt_y3=("y3", "mean"), mkt_ret3d=("ret3d", "mean"), n=("y3", "size"))
        # guard-pool base rate
        pool = dm[(dm["liq"] >= gd["min_liq"]) & (dm["close_vwap"] >= gd["vwap"])]
        if gd["idx_vol_min"] is not None:
            pool = pool[pool["idx_vol20_d"] >= gd["idx_vol_min"]]
        poolmo = pool.groupby("month").agg(pool_y3=("y3", "mean"), pool_ret3d=("ret3d", "mean"), pool_n=("y3", "size"))
        # walk-forward picks (identical to lane config)
        rows = []
        for tm in TEST_MONTHS:
            t0 = pd.Timestamp(tm + "-01"); t1 = t0 + pd.offsets.MonthEnd(1)
            tr = dm[dm["date"] < t0]
            te = dm[(dm["date"] >= t0) & (dm["date"] <= t1)].copy()
            if len(tr) < 3000 or te.empty:
                continue
            Xtr = tr[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
            Xte = te[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
            ps = []
            for m in (lgb.LGBMClassifier(n_estimators=400, learning_rate=0.04, num_leaves=31, min_child_samples=60,
                                         subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1),
                      xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.04, subsample=0.8,
                                        colsample_bytree=0.7, reg_lambda=3, verbosity=0, n_jobs=-1),
                      ExtraTreesClassifier(n_estimators=250, min_samples_leaf=40, random_state=0, n_jobs=-1)):
                m.fit(Xtr, tr["y3"]); ps.append(m.predict_proba(Xte)[:, 1])
            te["p"] = np.mean(ps, axis=0)
            q = te[(te["liq"] >= gd["min_liq"]) & (te["close_vwap"] >= gd["vwap"])]
            if gd["idx_vol_min"] is not None:
                q = q[q["idx_vol20_d"] >= gd["idx_vol_min"]]
            pk = q.sort_values("p", ascending=False).groupby("date", group_keys=False).head(gd["topn"])
            if pk.empty:
                continue
            rows.append({"month": tm, "picks_n": int(len(pk)),
                         "picks_y3": round(float(pk["y3"].mean()) * 100, 1),
                         "picks_ret3d": round(float(pk["ret3d"].mean()), 2) if pk["ret3d"].notna().any() else None})
        picks = pd.DataFrame(rows).set_index("month") if rows else pd.DataFrame()
        tbl = allmo.join(poolmo).join(picks)
        tbl["mkt_y3"] = (tbl["mkt_y3"] * 100).round(1)
        tbl["pool_y3"] = (tbl["pool_y3"] * 100).round(1)
        tbl["skill_pp"] = (tbl["picks_y3"] - tbl["pool_y3"]).round(1)
        tbl["ev_skill"] = (tbl["picks_ret3d"] - tbl["pool_ret3d"]).round(2)
        tbl["mkt_ret3d"] = tbl["mkt_ret3d"].round(2); tbl["pool_ret3d"] = tbl["pool_ret3d"].round(2)
        print(f"\n=== {mkt} — monthly base rate vs skill (y3 %, ret3d %) ===")
        print(tbl[["mkt_y3", "pool_y3", "picks_y3", "skill_pp", "pool_ret3d", "picks_ret3d", "ev_skill", "pool_n", "picks_n"]].to_string())
        results[mkt] = json.loads(tbl.reset_index().to_json(orient="records"))
    with open(OUT, "w") as fh:
        json.dump(results, fh, indent=1)
    print(f"\n[done] {OUT}")


if __name__ == "__main__":
    main()
