#!/usr/bin/env python3
"""Tail-veto research (swing-main-kdpl): do disaster picks (policy_ret <= -10) carry
a leak-free entry-time signature enabling a pre-entry VETO (not a stop)?

Picks: 8y quarterly walk-forward rank-1..3 of the deployed ft_5_5 ranker (both markets,
~10k picks). Tail label: policy_ret <= -10. Veto model: LGBM on leak-free pick-time
features (overheat/gap/liquidity/market-state). Yearly walk-forward; veto curve
(refuse worst X% by tail-prob) -> EV / tail frequency / CVaR10; label-shuffle placebo.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
import lightgbm as lgb
from swing_firsttouch_ranker_8y import FEATS, LIQ, COST

CACHE = "/Users/dongdong/research_cache"
HERE = os.path.dirname(os.path.abspath(__file__))
# veto features: overheat (dist_hi, consec_up, ret_20d, rsi), gap/vol structure, liquidity,
# conviction, causal market state — all knowable at pick time
VETO_F = ["dist_hi20", "dist_hi60", "consec_up", "ret_5d", "ret_20d", "rsi14", "atr_pct",
          "gap", "vol_ratio", "turn_z", "bb_bw", "liq_log", "p", "mkt_dd20", "mkt_ret5"]


def gen_picks(mkt: str) -> pd.DataFrame:
    cols = list(dict.fromkeys(["code", "date", "market", "liq", "ft_5_5", "exec_5d", "ret_1d"] + FEATS))
    px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
    px = px[px["market"] == mkt].copy()
    px["date"] = pd.to_datetime(px["date"])
    px["exec_5d"] = px["exec_5d"].replace([np.inf, -np.inf], np.nan)
    px = px[px["liq"] >= LIQ[mkt]]
    px["policy_ret"] = np.where(px["ft_5_5"] == 1, 5.0, px["exec_5d"])
    d = px.dropna(subset=["ft_5_5"] + FEATS[:6]).copy()
    # causal market state
    mret = d.groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1 + mret / 100).cumprod()
    st = pd.DataFrame({"mkt_dd20": (lvl / lvl.rolling(20).max() - 1) * 100,
                       "mkt_ret5": (lvl / lvl.shift(5) - 1) * 100})
    picks = []
    for q in pd.period_range("2019Q1", "2026Q2", freq="Q"):
        t0, t1 = q.start_time, q.end_time
        tr = d[(d["date"] < t0) & (d["date"] >= t0 - pd.DateOffset(years=2))]
        te = d[(d["date"] >= t0) & (d["date"] <= t1)].copy()
        if len(tr) < 20000 or te.empty:
            continue
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0, verbose=-1)
        m.fit(tr[FEATS].clip(-1e4, 1e4), tr["ft_5_5"])
        te["p"] = m.predict_proba(te[FEATS].clip(-1e4, 1e4))[:, 1]
        pk = te.sort_values("p", ascending=False).groupby("date", group_keys=False).head(3)
        picks.append(pk)
    P = pd.concat(picks, ignore_index=True)
    P = P.join(st, on="date")
    P["liq_log"] = np.log10(P["liq"].clip(1))
    P["market"] = mkt
    return P


def main():
    P = pd.concat([gen_picks(m) for m in ("KOSDAQ", "KOSPI")], ignore_index=True)
    P = P.dropna(subset=["policy_ret"] + VETO_F).sort_values("date").reset_index(drop=True)
    P["tail"] = (P["policy_ret"] <= -10).astype(int)
    print(f"picks={len(P)} tail_rate={P['tail'].mean()*100:.1f}% ({P['tail'].sum()} events)", flush=True)
    years = sorted(P["date"].dt.year.unique())
    rng = np.random.default_rng(0)
    rows = []
    for yr in years:
        if yr < years[0] + 2:
            continue
        tr = P[P["date"].dt.year < yr]
        te = P[P["date"].dt.year == yr].copy()
        if tr["tail"].sum() < 50 or te.empty:
            continue
        m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=50,
                               subsample=0.8, colsample_bytree=0.8, reg_lambda=3, random_state=0,
                               scale_pos_weight=5, verbose=-1)
        m.fit(tr[VETO_F].fillna(0), tr["tail"])
        te["tail_p"] = m.predict_proba(te[VETO_F].fillna(0))[:, 1]
        mp = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=50,
                                subsample=0.8, colsample_bytree=0.8, reg_lambda=3, random_state=1,
                                scale_pos_weight=5, verbose=-1)
        mp.fit(tr[VETO_F].fillna(0), rng.permutation(tr["tail"].values))
        te["tail_plc"] = mp.predict_proba(te[VETO_F].fillna(0))[:, 1]
        rows.append(te)
        imp = m
    T = pd.concat(rows, ignore_index=True)
    print(f"OOS picks: {len(T)} ({T['date'].dt.year.min()}..{T['date'].dt.year.max()}), tails {T['tail'].sum()}", flush=True)

    def cvar10(x):
        q = np.percentile(x, 10)
        return float(x[x <= q].mean())

    for score, tag in (("tail_p", "VETO"), ("tail_plc", "PLACEBO")):
        print(f"\n== {tag}: worst-X% 거부 곡선 (net {COST}) ==", flush=True)
        for veto in (0.0, 0.1, 0.2, 0.3):
            th = T[score].quantile(1 - veto) if veto > 0 else np.inf
            keep = T[T[score] < th]
            net = keep["policy_ret"] - COST
            yr = keep.groupby(keep["date"].dt.year).apply(lambda g: (g["policy_ret"] - COST).mean())
            print(f" veto={veto:.0%} n={len(keep):5d} EV={net.mean():+.3f} tail율={keep['tail'].mean()*100:.2f}% "
                  f"CVaR10={cvar10(net.values):+.2f} worst={net.min():.1f} yr+={int((yr>0).sum())}/{len(yr)}", flush=True)
    fi = sorted(zip(VETO_F, imp.feature_importances_), key=lambda x: -x[1])[:6]
    print("\ntail 서명(중요도):", [(f, int(v)) for f, v in fi], flush=True)
    json.dump({"n": len(T)}, open(os.path.join(HERE, "tail_veto.done"), "w"))


if __name__ == "__main__":
    main()
