#!/usr/bin/env python3
"""8-year swing first-touch(+5%) ranker with abstention (swing-main-zls0).

Contract (honest manual-trading): signal at close t -> BUY next open (t+1).
Exit: +5% touch within 5 sessions (take profit) else 5d close. No stop (stops halve EV).
policy_ret = ft_5_5==1 ? +5.0 : exec_5d   (conservative: ignores gap-up fill bonus)
net of COST round-trip.

Validation: rolling-window walk-forward quarterly folds 2019Q1..2026Q2, per-year table,
label-shuffle placebo, pool(same-day) skill control, pick-liquidity distribution
(low-liq trap check), RISK_OFF split (dd20<-5|ret5<-3 equal-weight pool state).
Selection: per-day top-k by calibrated p with abstention threshold -> coverage-EV frontier.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

CACHE = os.path.expanduser("~/research_cache")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swing_ft_ranker_8y.json")
COST = 0.3
FEATS = ["ret_1d","ret_3d","ret_5d","ret_10d","ret_20d","ret_60d","ma5_dist","ma20_dist","ma60_dist",
         "ma120_dist","ma20_slope","ma60_slope","rsi14","rsi_slope","accel","consec_up","dist_hi20",
         "dist_hi60","dist_hi120","dist_lo20","dist_lo60","pos20","bb_pctb","bb_bw","atr_pct","vol20",
         "close_loc","gap","vol_ratio","vol_trend","turn_z","obv_slope","cmf20","idx_mom20","idx_vol20"]
LIQ = {"KOSPI": 100e8, "KOSDAQ": 30e8}
TRAIN_YEARS = 2.0   # rolling window (B-engine lesson: adaptive beats static)


def load(mkt: str) -> pd.DataFrame:
    cols = ["code","date","market","liq","ft_5_5","exec_5d","ret_1d"] + [c for c in FEATS if c not in ("ret_1d",)]
    px = pd.read_parquet(os.path.join(CACHE, "px_long.parquet"), columns=list(dict.fromkeys(cols)))
    px = px[px["market"] == mkt].copy()
    px["date"] = pd.to_datetime(px["date"])
    px["exec_5d"] = px["exec_5d"].replace([np.inf, -np.inf], np.nan)
    # RISK_OFF state from equal-weight liquid pool (validated construction, §6)
    pool = px[px["liq"] >= LIQ[mkt]]
    mret = pool.groupby("date")["ret_1d"].mean().sort_index()
    lvl = (1 + mret / 100).cumprod()
    risk_off = (((lvl / lvl.rolling(20).max() - 1) * 100 < -5) | ((lvl / lvl.shift(5) - 1) * 100 < -3))
    px = px[px["liq"] >= LIQ[mkt]].copy()
    px["risk_off"] = px["date"].map(risk_off).fillna(False)
    px["policy_ret"] = np.where(px["ft_5_5"] == 1, 5.0, px["exec_5d"])
    return px


def run(mkt: str, placebo: bool = False, seed: int = 0):
    import lightgbm as lgb
    px = load(mkt)
    d = px.dropna(subset=["ft_5_5"] + FEATS[:6]).copy()  # require label + core features
    quarters = pd.period_range("2019Q1", "2026Q2", freq="Q")
    rng = np.random.default_rng(seed)
    picks = []
    for q in quarters:
        t0, t1 = q.start_time, q.end_time
        tr = d[(d["date"] < t0) & (d["date"] >= t0 - pd.DateOffset(years=int(TRAIN_YEARS)))]
        te = d[(d["date"] >= t0) & (d["date"] <= t1)].copy()
        if len(tr) < 20000 or te.empty:
            continue
        ytr = tr["ft_5_5"].values
        if placebo:
            ytr = rng.permutation(ytr)
        X = tr[FEATS].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4)
        Xt = te[FEATS].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4)
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0, verbose=-1)
        m.fit(X, ytr)
        te["p"] = m.predict_proba(Xt)[:, 1]
        picks.append(te[["date","code","p","ft_5_5","policy_ret","exec_5d","liq","risk_off"]])
    allte = pd.concat(picks, ignore_index=True)
    return allte


def frontier(allte: pd.DataFrame, mkt: str, tag: str):
    out = []
    total_weeks = allte["date"].dt.to_period("W").nunique()
    for topk in (1, 2, 3):
        for pth in (0.0, 0.55, 0.60, 0.65, 0.70, 0.75):
            sel = allte[allte["p"] >= pth].sort_values("p", ascending=False).groupby("date", group_keys=False).head(topk)
            sel = sel.dropna(subset=["policy_ret"])
            if len(sel) < 100:
                continue
            net = sel["policy_ret"] - COST
            wk = sel.groupby(sel["date"].dt.to_period("W"))["date"].nunique()
            weeks3 = float((wk >= 3).sum()) / total_weeks * 100
            yr = sel.groupby(sel["date"].dt.year).apply(lambda g: float((g["policy_ret"] - COST).mean()))
            pool_same = allte[allte["date"].isin(sel["date"].unique())].dropna(subset=["policy_ret"])
            skill = float(net.mean() - (pool_same["policy_ret"] - COST).mean())
            bs = [np.random.default_rng(s).choice(net.values, len(net), replace=True).mean() for s in range(300)]
            row = dict(market=mkt, tag=tag, topk=topk, pth=pth, n=int(len(sel)),
                       win_ft=round(float(sel["ft_5_5"].mean()) * 100, 1),
                       ev=round(float(net.mean()), 3),
                       ci=(round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)),
                       skill_vs_pool=round(skill, 2),
                       weeks_ge3=round(weeks3, 1),
                       picks_per_week=round(len(sel) / total_weeks, 1),
                       med_liq_eok=round(float(sel["liq"].median()) / 1e8, 0),
                       yr_pos=f"{int((yr > 0).sum())}/{len(yr)}",
                       ev_riskoff=round(float((sel.loc[sel['risk_off'], 'policy_ret'] - COST).mean()), 2) if sel["risk_off"].any() else None,
                       ev_normal=round(float((sel.loc[~sel['risk_off'], 'policy_ret'] - COST).mean()), 2))
            out.append(row)
    return out


def main():
    results = []
    for mkt in ("KOSDAQ", "KOSPI"):
        print(f"[{mkt}] walk-forward ...", flush=True)
        allte = run(mkt)
        rows = frontier(allte, mkt, "REAL")
        results += rows
        print(f"  {'k':>2} {'p>=':>5} {'n':>6} {'win':>5} {'EV':>6} {'CI':>16} {'skill':>6} {'wk3%':>5} {'pk/wk':>5} {'liq':>5} {'yr+':>5} {'EVoff':>6} {'EVnorm':>6}")
        for r in sorted(rows, key=lambda x: -x["ev"])[:12]:
            print(f"  {r['topk']:>2} {r['pth']:>5} {r['n']:>6} {r['win_ft']:>5} {r['ev']:>6.2f} {str(r['ci']):>16} {r['skill_vs_pool']:>6.2f} {r['weeks_ge3']:>5.1f} {r['picks_per_week']:>5} {r['med_liq_eok']:>5.0f} {r['yr_pos']:>5} {str(r['ev_riskoff']):>6} {r['ev_normal']:>6.2f}", flush=True)
        # placebo on the best config
        best = max(rows, key=lambda x: x["ev"])
        pl = run(mkt, placebo=True)
        plrows = [r for r in frontier(pl, mkt, "PLACEBO") if r["topk"] == best["topk"] and r["pth"] == best["pth"]]
        if not plrows:  # placebo p-dist differs; take closest available
            cand = [r for r in frontier(pl, mkt, "PLACEBO") if r["topk"] == best["topk"]]
            plrows = sorted(cand, key=lambda r: abs(r["pth"] - best["pth"]))[:1]
        for r in plrows:
            results.append(r)
            print(f"  PLACEBO(best cfg k={r['topk']},p={r['pth']}): n={r['n']} win={r['win_ft']} EV={r['ev']} CI={r['ci']}", flush=True)
    json.dump(results, open(OUT, "w"), indent=1)
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
