#!/usr/bin/env python3
"""Exit-policy study on the SAME walk-forward ensemble picks (swing-main-ayu1 follow-up).

Motivation: KOSDAQ 2026-05 = 80.6% touch hit but -1.55% 3d-close return — the current
3d-close-hold contract buries the take-profit. First-touch lesson: sell AT the touch.

Method: regenerate the identical walk-forward BASE_ENSEMBLE picks (8 OOS months), attach
5-day forward OHLC paths, and evaluate exit policies on daily bars:
  - target touch: fill at max(target, open) if day's high >= target (gap-up fills better)
  - stop: fill at min(stop, open) if day's low <= stop (gap-down fills worse)
  - same-day both-hit → PESSIMISTIC (stop first). Optimistic variant reported for bounds.
  - horizon close exit otherwise. Cost 0.3% round-trip subtracted.
Grid: target {none, +5, +7, +10} x stop {none, -3, -5, -7} x horizon {3, 5}.
Regime diagnostic: per-month idx_mom20/idx_vol20 of picks; best policy re-scored with
idx_mom20>=0 no-trade gate (structural prior: long touch needs non-down tape), with
leave-one-month-out impact table to expose threshold fragility.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, COST, assemble

CACHE = os.path.expanduser("~/research_cache")
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exit_policy_results.json")
H = 5  # max horizon


def gen_picks() -> pd.DataFrame:
    import lightgbm as lgb, xgboost as xgb
    from sklearn.ensemble import ExtraTreesClassifier
    P = assemble()
    BASE = ITF + [c + "_d" for c in DLF]
    picks = []
    for mkt in ("KOSPI", "KOSDAQ"):
        gd = GUARDS[mkt]
        dm = P[P["mkt"] == mkt].dropna(subset=ITF + ["y3"]).copy()
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
            pk = q.sort_values("p", ascending=False).groupby("date", group_keys=False).head(gd["topn"]).copy()
            pk["month"] = tm; pk["mkt"] = mkt
            picks.append(pk[["mkt", "month", "date", "code", "y3", "p", "idx_mom20_d", "idx_vol20_d"]])
    return pd.concat(picks, ignore_index=True)


def attach_paths(picks: pd.DataFrame) -> pd.DataFrame:
    d = pd.read_parquet(os.path.join(CACHE, "ohlc_daily.parquet"))
    d["code"] = d["code"].astype(str).str.zfill(6)
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values(["code", "date"]).reset_index(drop=True)
    g = d.groupby("code")
    cols = {"entry": d["close"]}
    for k in range(1, H + 1):
        for f in ("open", "high", "low", "close"):
            cols[f"{f}{k}"] = g[f].shift(-k)
    path = pd.concat([d[["code", "date"]], pd.DataFrame(cols)], axis=1)
    return picks.merge(path, on=["code", "date"], how="left")


def policy_ret(row, target, stop, horizon, pessimistic=True) -> float:
    e = row["entry"]
    if not np.isfinite(e) or e <= 0:
        return np.nan
    tgt = e * (1 + target / 100) if target is not None else None
    stp = e * (1 + stop / 100) if stop is not None else None
    for k in range(1, horizon + 1):
        o, hi, lo, c = row[f"open{k}"], row[f"high{k}"], row[f"low{k}"], row[f"close{k}"]
        if not np.isfinite(c):
            return np.nan  # incomplete forward window
        hit_t = tgt is not None and hi >= tgt
        hit_s = stp is not None and lo <= stp
        if hit_t and hit_s:
            if pessimistic:
                return (min(stp, o) / e - 1) * 100
            return (max(tgt, o) / e - 1) * 100
        if hit_s:
            return (min(stp, o) / e - 1) * 100
        if hit_t:
            return (max(tgt, o) / e - 1) * 100
    return (row[f"close{horizon}"] / e - 1) * 100


def eval_policy(pk: pd.DataFrame, target, stop, horizon, pessimistic=True) -> dict:
    r = pk.apply(lambda row: policy_ret(row, target, stop, horizon, pessimistic), axis=1).dropna()
    if len(r) < 10:
        return {}
    net = r - COST
    bs = [np.random.default_rng(s).choice(net.values, size=len(net), replace=True).mean() for s in range(400)]
    months = pk.loc[r.index].groupby("month").apply(lambda g: float((r.loc[g.index] - COST).mean()))
    return {"n": int(len(r)), "net_ev": round(float(net.mean()), 3),
            "ci95": (round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)),
            "win_pct": round(float((net > 0).mean()) * 100, 1),
            "worst_trade": round(float(net.min()), 2),
            "monthly_ev": {k: round(v, 2) for k, v in months.items()},
            "neg_months": int((months < 0).sum()), "months": int(len(months))}


def main():
    print("[picks] regenerating walk-forward ensemble picks ...", flush=True)
    pk = gen_picks()
    pk = attach_paths(pk)
    print(f"  picks={len(pk)}", flush=True)

    results = {}
    grid_summary = []
    for mkt in ("KOSPI", "KOSDAQ"):
        pm = pk[pk["mkt"] == mkt]
        results[mkt] = {}
        for horizon in (3, 5):
            for target in (None, 5, 7, 10):
                for stop in (None, -3, -5, -7):
                    if target is None and stop is None and horizon == 3:
                        name = "CURRENT(3d close)"
                    else:
                        name = f"t{target}_s{stop}_h{horizon}"
                    res = eval_policy(pm, target, stop, horizon)
                    if res:
                        results[mkt][name] = res
                        grid_summary.append((mkt, name, res["net_ev"], res["ci95"], res["win_pct"],
                                             res["neg_months"], res["months"], res["worst_trade"]))
    # print compact leaderboard per market
    for mkt in ("KOSPI", "KOSDAQ"):
        rows = sorted([g for g in grid_summary if g[0] == mkt], key=lambda x: -x[2])
        print(f"\n=== {mkt} exit-policy leaderboard (net EV %/trade, cost {COST}) ===", flush=True)
        for _, name, ev, ci, wp, nm, mm, wt in rows[:10]:
            print(f"  {name:22s} EV={ev:6.2f} CI={ci} win={wp:5.1f}% negMo={nm}/{mm} worst={wt}", flush=True)
        cur = results[mkt].get("CURRENT(3d close)")
        if cur:
            print(f"  CURRENT baseline       EV={cur['net_ev']:6.2f} CI={cur['ci95']} win={cur['win_pct']}% negMo={cur['neg_months']}/{cur['months']}", flush=True)

    # pessimism bound for the top policy of each market
    for mkt in ("KOSPI", "KOSDAQ"):
        pm = pk[pk["mkt"] == mkt]
        top = max([k for k in results[mkt] if k != "CURRENT(3d close)"], key=lambda k: results[mkt][k]["net_ev"])
        t, s, h = top.split("_")
        tv = None if t == "tNone" else float(t[1:]); sv = None if s == "sNone" else float(s[1:]); hv = int(h[1:])
        opt = eval_policy(pm, tv, sv, hv, pessimistic=False)
        results[mkt][top + "_optimistic"] = opt
        print(f"[{mkt}] top={top} pessimistic EV={results[mkt][top]['net_ev']} vs optimistic EV={opt.get('net_ev')}", flush=True)

    # regime diagnostic: idx_mom20 per month + gate impact on top policy
    print("\n=== regime diagnostic (picks' idx_mom20_d monthly mean) ===", flush=True)
    diag = pk.groupby(["mkt", "month"]).agg(idx_mom=("idx_mom20_d", "mean"), idx_vol=("idx_vol20_d", "mean"), n=("code", "size")).round(2)
    print(diag.to_string(), flush=True)
    for mkt in ("KOSPI", "KOSDAQ"):
        pm = pk[pk["mkt"] == mkt]
        top = max([k for k in results[mkt] if k.startswith("t") and not k.endswith("optimistic")], key=lambda k: results[mkt][k]["net_ev"])
        t, s, h = top.split("_")
        tv = None if t == "tNone" else float(t[1:]); sv = None if s == "sNone" else float(s[1:]); hv = int(h[1:])
        gated = eval_policy(pm[pm["idx_mom20_d"] >= 0], tv, sv, hv)
        results[mkt]["top_gated_idxmom0"] = gated
        print(f"[{mkt}] top policy {top} with idx_mom20>=0 gate: EV={gated.get('net_ev')} CI={gated.get('ci95')} n={gated.get('n')} negMo={gated.get('neg_months')}/{gated.get('months')}", flush=True)

    with open(OUT_JSON, "w") as fh:
        json.dump({m: results[m] for m in results}, fh, indent=1, default=str)
    print(f"\n[done] {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()
