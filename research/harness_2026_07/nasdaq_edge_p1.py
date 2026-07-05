#!/usr/bin/env python3
"""NASDAQ edge hunt P1 (swing-main-x1vj): selective issuance + touch-exit policy EV
on the 8y daily panel, with self-computed realistic entries/fills and overnight decomposition.

Contract: signal at close t -> BUY next open (t+1). Exit: +T% touch within 5 sessions
(fill max(open, target); entry-day touch counts, fill=target) else 5d close. Cost 0.25% RT.
Discipline: quarterly walk-forward 2019Q1..2026Q2, rolling 2y train, liq-matched pool skill,
per-year table, label-shuffle placebo, survivorship caveat (current-listings universe).
Overnight decomposition on picks: close(t)->open(t+1) vs open(t+1)->close within horizon.
"""
import os, sys, json, glob, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.expanduser("~/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet")
OUT = os.path.join(HERE, "nasdaq_edge_p1.json")
COST = 0.25
MIN_LIQ = 1e8      # $100M ADV20 (tradeable)
MIN_PRICE = 5.0
EXCLUDE = {"open", "high", "low", "close", "raw_close", "adj_close", "volume", "dollar_volume",
           "ma5", "ma10", "ma20", "ma50", "ma60", "ma120", "ma200", "ema12", "ema26", "atr14",
           "date", "symbol", "name", "market", "feature_version", "year", "month", "feature_ready", "liq60"}


def load():
    import pyarrow.parquet as pq
    allcols = pq.ParquetFile(PANEL).schema.names
    path_excl = {"raw_close", "adj_close", "dollar_volume", "ma5", "ma10", "ma20", "ma50", "ma60",
                 "ma120", "ma200", "ema12", "ema26", "atr14", "name", "market", "feature_version", "liq60"}
    need = [c for c in allcols if c not in path_excl and not c.startswith(("fwd_high", "fwd_low", "touch5_1", "touch10_", "dd10_", "touch5_10d", "touch5_20d", "dd5_1d", "dd5_10d", "dd5_20d", "first_"))]
    df = pd.read_parquet(PANEL, columns=need)
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["feature_ready"] == 1) & (df["close"] >= MIN_PRICE) & (df["liq20"] >= MIN_LIQ)].copy()
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    g = df.groupby("symbol")
    # forward path (next 5 sessions) for policy returns + overnight decomposition
    for k in range(1, 6):
        df[f"o{k}"] = g["open"].shift(-k)
        df[f"h{k}"] = g["high"].shift(-k)
        df[f"c{k}"] = g["close"].shift(-k)
    path_cols = {f"{f}{k}" for f in "ohc" for k in range(1, 6)}
    feats = [c for c in df.columns
             if c not in EXCLUDE and c not in path_cols
             and not c.startswith(("fwd_", "touch5", "touch10", "dd5", "dd10", "ft_", "first_"))
             and df[c].dtype.kind in "fi"]
    return df, feats


def policy_returns(df: pd.DataFrame, target: float):
    e = df["o1"].values  # next-open entry
    ok = np.isfinite(e) & (e > 0) & np.isfinite(df["c5"].values)
    tgt = e * (1 + target / 100)
    out = np.full(len(df), np.nan)
    done = np.zeros(len(df), dtype=bool)
    for k in range(1, 6):
        hi = df[f"h{k}"].values
        op = df[f"o{k}"].values
        hit = ok & ~done & np.isfinite(hi) & (hi >= tgt)
        fill = np.where((k > 1) & np.isfinite(op) & (op > 0), np.maximum(tgt, op), tgt)
        out[hit] = (fill[hit] / e[hit] - 1) * 100
        done |= hit
    rest = ok & ~done
    out[rest] = (df["c5"].values[rest] / e[rest] - 1) * 100
    return out


def main():
    import lightgbm as lgb
    df, feats = load()
    print(f"panel: {len(df)} rows, {df['symbol'].nunique()} symbols, {df['date'].min().date()}..{df['date'].max().date()}, feats={len(feats)}", flush=True)
    df["pol5"] = policy_returns(df, 5.0)
    df["pol10"] = policy_returns(df, 10.0)
    # overnight vs intraday decomposition components (close t -> open t+1; open t+1 -> close t+5)
    df["ovn"] = (df["o1"] / df["close"] - 1) * 100
    df["intr5"] = (df["c5"] / df["o1"] - 1) * 100
    d = df.dropna(subset=["ft_5_5"]).copy()
    quarters = pd.period_range("2019Q1", "2026Q2", freq="Q")
    rng = np.random.default_rng(0)
    pools = []
    for q in quarters:
        t0, t1 = q.start_time, q.end_time
        tr = d[(d["date"] < t0) & (d["date"] >= t0 - pd.DateOffset(years=2))]
        te = d[(d["date"] >= t0) & (d["date"] <= t1)].copy()
        if len(tr) < 20000 or te.empty:
            continue
        X = tr[feats].clip(-1e6, 1e6)
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0, verbose=-1)
        m.fit(X, tr["ft_5_5"])
        te["p"] = m.predict_proba(te[feats].clip(-1e6, 1e6))[:, 1]
        mpl = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                                 subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=1, verbose=-1)
        mpl.fit(X, rng.permutation(tr["ft_5_5"].values))
        te["p_plc"] = mpl.predict_proba(te[feats].clip(-1e6, 1e6))[:, 1]
        pools.append(te[["date", "symbol", "p", "p_plc", "ft_5_5", "pol5", "pol10", "ovn", "intr5",
                         "fwd_close_ret_5d", "liq20"]])
        print(f"[{q}] pool={len(te)}", flush=True)
    A = pd.concat(pools, ignore_index=True)
    A["year"] = A["date"].dt.year
    tw = A["date"].dt.to_period("W").nunique()
    results = []
    print(f"\n== frontier (rank-k by p, thresholds; net {COST}) ==", flush=True)
    for score, tag in (("p", "REAL"), ("p_plc", "PLACEBO")):
        for k in (1, 3):
            for pth in ([0.0, 0.55, 0.6, 0.65] if tag == "REAL" else [0.0]):
                s = A[A[score] >= pth].sort_values(score, ascending=False).groupby("date", group_keys=False).head(k)
                for polcol, cname in (("pol5", "t5"), ("pol10", "t10")):
                    ss = s.dropna(subset=[polcol])
                    if len(ss) < 200:
                        continue
                    net = ss[polcol] - COST
                    yr = ss.groupby("year")[polcol].mean() - COST
                    bs = [np.random.default_rng(x).choice(net.values, len(net), True).mean() for x in range(300)]
                    # same-day liq-matched pool control
                    pool_same = A[A["date"].isin(ss["date"].unique())].dropna(subset=[polcol])
                    skill = float(net.mean() - (pool_same[polcol] - COST).mean())
                    dwk = ss.groupby(ss["date"].dt.to_period("W"))["date"].nunique().mean()
                    row = dict(tag=tag, k=k, pth=pth, contract=cname, n=int(len(ss)),
                               win=round(float((net > 0).mean()) * 100, 1), ev=round(float(net.mean()), 2),
                               ci=(round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)),
                               skill=round(skill, 2), dwk=round(float(dwk), 1),
                               yr_pos=f"{int((yr > 0).sum())}/{len(yr)}",
                               ovn=round(float(ss["ovn"].mean()), 2), intr=round(float(ss["intr5"].mean()), 2))
                    results.append(row)
                    print(f" {tag:7s} k={k} p>={pth:4} {cname:3s} n={row['n']:5d} win={row['win']:5.1f} EV={row['ev']:5.2f} CI={row['ci']} skill={row['skill']:+.2f} d/wk={row['dwk']} yr+={row['yr_pos']} ovn={row['ovn']:+.2f} intr={row['intr']:+.2f}", flush=True)
    json.dump(results, open(OUT, "w"), indent=1)
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
