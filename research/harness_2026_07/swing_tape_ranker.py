#!/usr/bin/env python3
"""Swing model search (swing-main-hv1q): does intraday tape (ITF + multi-day aggregates)
add increment on a SWING contract (next-open entry, +7% touch within 10d else 10d close)?

Variants on identical folds: DLF_ONLY (daily features — 8y-ranker equivalent) vs
+ITF (signal-day tape) vs +TAPE3 (3-day tape persistence aggregates, invisible to daily bars).
Label/policy from px_long: ft10_7_4 (entry=next open, +7 before -4, 10 sessions),
policy_ret = ft10==1 ? +7 : exec_10d, net 0.3 cost.
June caveat: ft10 needs 10 fwd sessions -> test months effectively 2025-11..2026-06(partial).
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flow_increment_research import ITF, DLF, TEST_MONTHS, COST

CACHE = os.path.expanduser("~/research_cache")
LIQ = {"KOSPI": 100e8, "KOSDAQ": 30e8}
TAPE3 = ["cv_pos3", "cv_mean3", "umf_mean3", "umf_trend", "vz_sum3", "acc_mean3", "dr_sum3", "gap_sum3"]


def assemble_swing() -> pd.DataFrame:
    P = pd.read_parquet(os.path.join(CACHE, "intraday_3d_panel.parquet"))
    P["code"] = P["code"].astype(str).str.zfill(6)
    P["date"] = pd.to_datetime(P["date"])
    cols = ["code", "date", "liq", "ft10_7_4", "exec_10d"] + DLF
    px = pd.read_parquet(os.path.join(CACHE, "px_long.parquet"), columns=cols)
    px["code"] = px["code"].astype(str).str.zfill(6)
    px["date"] = pd.to_datetime(px["date"])
    px["exec_10d"] = px["exec_10d"].replace([np.inf, -np.inf], np.nan)
    px = px.rename(columns={c: c + "_d" for c in DLF})
    P = P.merge(px, on=["code", "date"], how="left")
    P["policy_ret"] = np.where(P["ft10_7_4"] == 1, 7.0, P["exec_10d"])
    # multi-day tape aggregates (per code, trailing 3 sessions incl. today — all known at close t)
    P = P.sort_values(["code", "date"]).reset_index(drop=True)
    g = P.groupby("code", group_keys=False)
    P["cv_pos3"] = g["close_vwap"].apply(lambda s: (s > 0).rolling(3, min_periods=2).sum())
    P["cv_mean3"] = g["close_vwap"].apply(lambda s: s.rolling(3, min_periods=2).mean())
    P["umf_mean3"] = g["up_min_frac"].apply(lambda s: s.rolling(3, min_periods=2).mean())
    P["umf_trend"] = g["up_min_frac"].apply(lambda s: s - s.rolling(3, min_periods=2).mean())
    P["vz_sum3"] = g["vol_z"].apply(lambda s: s.rolling(3, min_periods=2).sum())
    P["acc_mean3"] = g["accel"].apply(lambda s: s.rolling(3, min_periods=2).mean())
    P["dr_sum3"] = g["day_ret"].apply(lambda s: s.rolling(3, min_periods=2).sum())
    P["gap_sum3"] = g["gap"].apply(lambda s: s.rolling(3, min_periods=2).sum())
    return P


def run(P: pd.DataFrame, mkt: str, feats: list, name: str):
    import lightgbm as lgb
    dm = P[(P["mkt"] == mkt) & (P["liq"] >= LIQ[mkt])].dropna(subset=["ft10_7_4"]).copy()
    picks = []
    for tm in TEST_MONTHS:
        t0 = pd.Timestamp(tm + "-01"); t1 = t0 + pd.offsets.MonthEnd(1)
        tr = dm[dm["date"] < t0]
        te = dm[(dm["date"] >= t0) & (dm["date"] <= t1)].copy()
        if len(tr) < 2500 or te.empty:
            continue
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.04, num_leaves=31, min_child_samples=60,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1)
        m.fit(tr[feats].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0), tr["ft10_7_4"])
        te["p"] = m.predict_proba(te[feats].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0))[:, 1]
        picks.append(te[["date", "code", "p", "ft10_7_4", "policy_ret", "liq"]].assign(month=tm))
    A = pd.concat(picks, ignore_index=True)
    tw = A["date"].dt.to_period("W").nunique()
    out = []
    for k in (1, 2):
        for pth in (0.0, 0.5, 0.55, 0.6):
            s = A[A["p"] >= pth].sort_values("p", ascending=False).groupby("date", group_keys=False).head(k)
            s = s.dropna(subset=["policy_ret"])
            if len(s) < 40:
                continue
            net = s["policy_ret"] - COST
            mo = s.groupby("month")["policy_ret"].mean()
            bs = [np.random.default_rng(x).choice(net.values, len(net), True).mean() for x in range(300)]
            dwk = s.groupby(s["date"].dt.to_period("W"))["date"].nunique().mean()
            out.append((name, mkt, k, pth, len(s), round(float(s["ft10_7_4"].mean()) * 100, 1),
                        round(float(net.mean()), 2),
                        (round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)),
                        round(dwk, 1), f"{int((mo < COST).sum())}/{len(mo)}"))
    return out


def main():
    P = assemble_swing()
    lbl = P.dropna(subset=["ft10_7_4"])
    print(f"panel rows={len(P)} labeled(ft10)={len(lbl)} span={lbl['date'].min().date()}..{lbl['date'].max().date()}")
    variants = {
        "DLF_ONLY": [c + "_d" for c in DLF],
        "DLF+ITF": ITF + [c + "_d" for c in DLF],
        "DLF+ITF+TAPE3": ITF + TAPE3 + [c + "_d" for c in DLF],
    }
    rows = []
    for mkt in ("KOSPI", "KOSDAQ"):
        for name, feats in variants.items():
            rows += run(P, mkt, feats, name)
    print(f"\n{'variant':>14} {'mkt':>6} {'k':>2} {'p>=':>4} {'n':>5} {'win7':>5} {'EV':>6} {'CI':>15} {'d/wk':>4} {'negMo':>5}")
    for r in sorted(rows, key=lambda x: (x[1], x[0], -x[6])):
        print(f"{r[0]:>14} {r[1]:>6} {r[2]:>2} {r[3]:>4} {r[4]:>5} {r[5]:>5} {r[6]:>6.2f} {str(r[7]):>15} {r[8]:>4} {r[9]:>5}")
    json.dump([list(r) for r in rows], open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "swing_tape_ranker.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
