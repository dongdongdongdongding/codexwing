#!/usr/bin/env python3
"""B(시장중립) model zoo — untried levers on B's OWN panel/engine (swing-main B research).

Walk-forward monthly (train = trailing TRAIN_MONTHS, exactly like production train()):
  BASE      — production seed-ensemble LGBMRegressor on a5 (market-neutral 5d alpha), top-N by pred
  RANKER    — LGBMRanker lambdarank, per-day groups, graded by within-day a5 quartile
Selection depths: top10 (production) / top3 (concentration) / top1.
Metrics per config: mean realized a5 (alpha/trade), alpha win, abs f5, by-year, RISK_OFF split.
Also: touch-exit overlay measured on BASE top3 picks (+5%/+10% touch within 5d from next-open entry
approximated by ft_5_5-style path from ohlc? -> px_long lacks High; use exec/f5 only -> skip absolute
touch overlay here; alpha frame only). Placebo: label-shuffle on BASE top3.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
from b_engine import model_engine as E

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "b_model_zoo.json")


def main():
    import lightgbm as lgb
    px = E.load_panel()
    px = px.dropna(subset=["a5"]).copy()
    px["date"] = pd.to_datetime(px["date"])
    months = pd.period_range("2024-07", "2026-06", freq="M")
    pools = []
    rng = np.random.default_rng(0)
    for tm in months:
        t0, t1 = tm.start_time, tm.end_time
        tr = px[(px["date"] < t0) & (px["date"] >= t0 - pd.DateOffset(months=E.TRAIN_MONTHS))]
        te = px[(px["date"] >= t0) & (px["date"] <= t1)].copy()
        if len(tr) < 20000 or te.empty:
            continue
        models = E._fit_ensemble(tr)
        te["p_base"] = E._predict(models, te)
        # placebo: shuffled-label ensemble (one seed for cost)
        trs = tr.copy(); trs["a5"] = rng.permutation(trs["a5"].values)
        mpl = lgb.LGBMRegressor(**E.LGB, random_state=0, verbose=-1)
        mpl.fit(trs[E.ALLF].fillna(0), trs["a5"])
        te["p_plc"] = mpl.predict(te[E.ALLF].fillna(0))
        # lambdarank
        grade = tr.groupby("date")["a5"].rank(pct=True)
        ylab = np.clip((grade * 4).fillna(2).astype(int), 0, 3).values
        grp = tr.groupby("date", sort=False).size().values
        rk = lgb.LGBMRanker(objective="lambdarank", n_estimators=E.LGB.get("n_estimators", 300),
                            learning_rate=E.LGB.get("learning_rate", 0.05),
                            num_leaves=E.LGB.get("num_leaves", 31),
                            min_child_samples=E.LGB.get("min_child_samples", 50),
                            subsample=0.8, colsample_bytree=0.7, reg_lambda=3,
                            random_state=0, verbose=-1, label_gain=list(range(32)))
        rk.fit(tr[E.ALLF].fillna(0), ylab, group=grp)
        te["p_rank"] = rk.predict(te[E.ALLF].fillna(0))
        pools.append(te[["date", "code", "a5", "f5", "p_base", "p_rank", "p_plc"]].assign(month=str(tm)))
        print(f"[{tm}] pool={len(te)}", flush=True)
    A = pd.concat(pools, ignore_index=True)
    A["year"] = A["date"].dt.year
    # RISK_OFF state (equal-weight universe daily mean of f5-derived? use §6 construction from px_long)
    st = pd.read_parquet(os.path.expanduser("~/research_cache/px_long.parquet"),
                         columns=["date", "market", "liq", "ret_1d"])
    st["date"] = pd.to_datetime(st["date"])
    d = st[(st["market"] == "KOSDAQ") & (st["liq"] >= 30e8)]
    mret = d.groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1 + mret / 100).cumprod()
    risk_off = (((lvl / lvl.rolling(20).max() - 1) * 100 < -5) | ((lvl / lvl.shift(5) - 1) * 100 < -3))
    A["risk_off"] = A["date"].map(risk_off).fillna(False)

    results = []
    base_yr = {}
    for nm in ("p_base", "p_rank", "p_plc"):
        for topn in (10, 3, 1):
            s = A.sort_values(nm, ascending=False).groupby("date", group_keys=False).head(topn)
            yr = s.groupby("year")["a5"].mean()
            bs = [np.random.default_rng(x).choice(s["a5"].values, len(s), True).mean() for x in range(300)]
            row = dict(model=nm[2:], topn=topn, n=int(len(s)),
                       alpha=round(float(s["a5"].mean()), 3),
                       ci=(round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)),
                       alpha_win=round(float((s["a5"] > 0).mean()) * 100, 1),
                       abs_mean=round(float(s["f5"].mean()), 2),
                       yr={int(y): round(float(v), 2) for y, v in yr.items()},
                       alpha_off=round(float(s.loc[s["risk_off"], "a5"].mean()), 2) if s["risk_off"].any() else None,
                       alpha_norm=round(float(s.loc[~s["risk_off"], "a5"].mean()), 2))
            if nm == "p_base":
                base_yr[topn] = yr
            else:
                dd = (yr - base_yr[topn]).dropna()
                row["yr_better"] = f"{int((dd > 0).sum())}/{len(dd)}"
            results.append(row)
            print(f"  {row['model']:5s} top{topn:2d} n={row['n']:5d} α={row['alpha']:+.3f} CI={row['ci']} win={row['alpha_win']:.1f}% abs={row['abs_mean']:+.2f} off/norm={row['alpha_off']}/{row['alpha_norm']} yr={row['yr']} {row.get('yr_better','')}", flush=True)
    json.dump(results, open(OUT, "w"), indent=1)
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
