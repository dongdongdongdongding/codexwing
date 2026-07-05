#!/usr/bin/env python3
"""P4 meta-labeling (swing-main-jhd8): does a secondary model predicting PICK success from
CONTEXT enable profitable abstention/sizing? Multi-regime proof on 8y swing rank-1 picks.

Primary: ft_5_5 ranker (as deployed, quarterly walk-forward) -> rank-1/day picks with
policy returns (+5 touch-exit / 5d). Meta: P(pick success | context) where context =
market state (dd20/ret5), regime-event phase (library), pick style (momentum-ness rank,
rsi), conviction (p), liquidity — trained walk-forward on PAST picks only (yearly folds).
Gates: coverage-EV curve must beat take-all baseline; context-shuffle placebo must not.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
from swing_firsttouch_ranker_8y import run, COST

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "p4_meta_results.json")
LIB = "/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/long_term/learning/regime_event_library.json"
CTX = ["mkt_dd20", "mkt_ret5", "in_crash", "in_meltup", "event_day", "mom_rank", "rsi14",
       "p", "liq_log", "picks_gap"]


def market_state(mkt: str) -> pd.DataFrame:
    px = pd.read_parquet(os.path.expanduser("~/research_cache/px_long.parquet"),
                         columns=["date", "market", "liq", "ret_1d"])
    px["date"] = pd.to_datetime(px["date"])
    floor = 100e8 if mkt == "KOSPI" else 30e8
    d = px[(px["market"] == mkt) & (px["liq"] >= floor)]
    mret = d.groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1 + mret / 100).cumprod()
    return pd.DataFrame({"mkt_dd20": (lvl / lvl.rolling(20).max() - 1) * 100,
                         "mkt_ret5": (lvl / lvl.shift(5) - 1) * 100})


def event_phase(mkt: str, dates: pd.Series) -> pd.DataFrame:
    lib = json.load(open(LIB))["events"]
    rows = {"in_crash": np.zeros(len(dates)), "in_meltup": np.zeros(len(dates)),
            "event_day": np.zeros(len(dates))}
    dv = pd.to_datetime(dates).values
    for e in lib:
        if e["market"] != mkt:
            continue
        s, t = np.datetime64(e["start"]), np.datetime64(e["end"])
        m = (dv >= s) & (dv <= t)
        key = "in_crash" if e["type"] == "CRASH" else "in_meltup"
        rows[key][m] = 1.0
        rows["event_day"][m] = ((dv[m] - s) / np.timedelta64(1, "D")).astype(float)
    return pd.DataFrame(rows, index=dates.index)


def build_meta_set(mkt: str) -> pd.DataFrame:
    A = run(mkt)  # walk-forward pool scores (date, code, p, ft_5_5, policy_ret, liq, risk_off...)
    # rank-1 pick per day + extra context columns from px_long (mom rank/rsi need pool context)
    px = pd.read_parquet(os.path.expanduser("~/research_cache/px_long.parquet"),
                         columns=["code", "date", "market", "liq", "ret_20d", "rsi14"])
    px["code"] = px["code"].astype(str).str.zfill(6)
    px["date"] = pd.to_datetime(px["date"])
    px = px[px["market"] == mkt]
    px["mom_rank"] = px.groupby("date")["ret_20d"].rank(pct=True)
    A["code"] = A["code"].astype(str).str.zfill(6)
    A = A.merge(px[["code", "date", "mom_rank", "rsi14"]], on=["code", "date"], how="left")
    pk = A.sort_values("p", ascending=False).groupby("date", group_keys=False).head(1)
    pk = pk.dropna(subset=["policy_ret"]).sort_values("date").reset_index(drop=True)
    st = market_state(mkt)
    pk = pk.join(st, on="date")
    pk = pd.concat([pk, event_phase(mkt, pk["date"])], axis=1)
    pk["liq_log"] = np.log10(pk["liq"].clip(1))
    # conviction gap: rank-1 p minus daily pool p mean (relative conviction)
    pool_mean = A.groupby("date")["p"].mean()
    pk["picks_gap"] = pk["p"].values - pool_mean.reindex(pk["date"]).values
    pk["success"] = (pk["policy_ret"] - COST > 0).astype(int)
    pk["market"] = mkt
    return pk


def main():
    import lightgbm as lgb
    parts = [build_meta_set(m) for m in ("KOSDAQ", "KOSPI")]
    P = pd.concat(parts, ignore_index=True).sort_values("date").reset_index(drop=True)
    print(f"meta set: {len(P)} picks, {P['date'].min().date()}..{P['date'].max().date()}, "
          f"base success {P['success'].mean()*100:.1f}%", flush=True)
    years = sorted(P["date"].dt.year.unique())
    rng = np.random.default_rng(0)
    rows = []
    for yr in years:
        if yr < years[0] + 2:
            continue
        tr = P[P["date"].dt.year < yr]
        te = P[P["date"].dt.year == yr].copy()
        if len(tr) < 400 or te.empty:
            continue
        m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=40,
                               subsample=0.8, colsample_bytree=0.8, reg_lambda=3, random_state=0, verbose=-1)
        m.fit(tr[CTX].fillna(0), tr["success"])
        te["meta_p"] = m.predict_proba(te[CTX].fillna(0))[:, 1]
        trs = tr.copy()
        # context-shuffle placebo: permute context rows against labels
        idx = rng.permutation(len(trs))
        mp = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.05, num_leaves=15, min_child_samples=40,
                                subsample=0.8, colsample_bytree=0.8, reg_lambda=3, random_state=1, verbose=-1)
        mp.fit(trs[CTX].fillna(0).values[idx], trs["success"].values)
        te["meta_plc"] = mp.predict_proba(te[CTX].fillna(0))[:, 1]
        rows.append(te)
    T = pd.concat(rows, ignore_index=True)
    print(f"meta OOS picks: {len(T)} ({T['date'].dt.year.min()}..{T['date'].dt.year.max()})", flush=True)
    results = {}
    for score, tag in (("meta_p", "META"), ("meta_plc", "PLACEBO")):
        curve = []
        for keep in (1.0, 0.8, 0.6, 0.4):
            th = T[score].quantile(1 - keep)
            s = T[T[score] >= th]
            net = s["policy_ret"] - COST
            yrs = s.groupby(s["date"].dt.year).apply(lambda g: (g["policy_ret"] - COST).mean())
            bs = [np.random.default_rng(x).choice(net.values, len(net), True).mean() for x in range(300)]
            curve.append({"keep": keep, "n": int(len(s)), "ev": round(float(net.mean()), 3),
                          "ci": [round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)],
                          "win": round(float((net > 0).mean()) * 100, 1),
                          "yr_pos": f"{int((yrs > 0).sum())}/{len(yrs)}"})
            print(f" {tag:8s} keep={keep:.0%} n={len(s):4d} EV={net.mean():+.3f} CI=({np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}) "
                  f"win={(net>0).mean()*100:.1f}% yr+={int((yrs>0).sum())}/{len(yrs)}", flush=True)
        results[tag] = curve
    # feature importance for interpretation
    imp = sorted(zip(CTX, m.feature_importances_), key=lambda x: -x[1])
    results["last_fold_importance"] = [(f, int(v)) for f, v in imp]
    print("importance:", imp[:6], flush=True)
    json.dump(results, open(OUT, "w"), indent=1)
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
