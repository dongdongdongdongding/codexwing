#!/usr/bin/env python3
"""Follow-up to flow_increment_research (swing-main-ayu1):
1) VALIDATOR CHECK — does the shipped KOSPI intraday claim (85% hit, floor 71%) reproduce
   with the production 3-model ensemble (LGBM+XGB+ET) on the same walk-forward months?
2) EVENT increment — DART event-direction features on top of ITF+DLF, with within-date
   permutation placebo. Same folds/guards/selection as flow study.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, COST, assemble

CACHE = os.path.expanduser("~/research_cache")
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "event_ensemble_results.json")
EVF = ["ev_pos5", "ev_neg5", "ev_pos20", "ev_neg20", "ev_any20", "days_since_ev"]


def build_event_features(panel: pd.DataFrame) -> pd.DataFrame:
    ev = pd.read_parquet(os.path.join(CACHE, "dart_events.parquet"))
    ev["code"] = ev["code"].astype(str).str.zfill(6)
    ev["date"] = pd.to_datetime(ev["ann"], format="%Y%m%d", errors="coerce")
    ev = ev.dropna(subset=["date"]).sort_values(["code", "date"])
    pos = {c: g["date"].values for c, g in ev[ev["edir"] == "+"].groupby("code")}
    neg = {c: g["date"].values for c, g in ev[ev["edir"] == "-"].groupby("code")}
    allv = {c: g["date"].values for c, g in ev.groupby("code")}
    rows = np.zeros((len(panel), len(EVF)), dtype=float)
    codes = panel["code"].values
    dates = panel["date"].values
    for i in range(len(panel)):
        c, d = codes[i], dates[i]
        d5 = d - np.timedelta64(5, "D"); d20 = d - np.timedelta64(20, "D")
        pv = pos.get(c); nv = neg.get(c); av = allv.get(c)
        p5 = ((pv > d5) & (pv <= d)).sum() if pv is not None else 0
        n5 = ((nv > d5) & (nv <= d)).sum() if nv is not None else 0
        p20 = ((pv > d20) & (pv <= d)).sum() if pv is not None else 0
        n20 = ((nv > d20) & (nv <= d)).sum() if nv is not None else 0
        a20 = ((av > d20) & (av <= d)).sum() if av is not None else 0
        if av is not None and (av <= d).any():
            dse = min(60.0, (d - av[av <= d].max()) / np.timedelta64(1, "D"))
        else:
            dse = 60.0
        rows[i] = (p5, n5, p20, n20, a20, dse)
    out = panel[["code", "date"]].copy()
    for j, c in enumerate(EVF):
        out[c] = rows[:, j]
    return out


def run_variant(P, name, feat, mkt, ensemble=False):
    import lightgbm as lgb
    if ensemble:
        import xgboost as xgb
        from sklearn.ensemble import ExtraTreesClassifier
    gd = GUARDS[mkt]
    dm = P[P["mkt"] == mkt].dropna(subset=ITF + ["y3"]).copy()
    monthly, picks_all = [], []
    for tm in TEST_MONTHS:
        t0 = pd.Timestamp(tm + "-01"); t1 = t0 + pd.offsets.MonthEnd(1)
        tr = dm[dm["date"] < t0]
        te = dm[(dm["date"] >= t0) & (dm["date"] <= t1)].copy()
        if len(tr) < 3000 or te.empty:
            continue
        Xtr = tr[feat].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
        Xte = te[feat].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
        models = [lgb.LGBMClassifier(n_estimators=400, learning_rate=0.04, num_leaves=31, min_child_samples=60,
                                     subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1)]
        if ensemble:
            models += [xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.04, subsample=0.8,
                                         colsample_bytree=0.7, reg_lambda=3, verbosity=0, n_jobs=-1),
                       ExtraTreesClassifier(n_estimators=250, min_samples_leaf=40, random_state=0, n_jobs=-1)]
        ps = []
        for m in models:
            m.fit(Xtr, tr["y3"])
            ps.append(m.predict_proba(Xte)[:, 1])
        te["p"] = np.mean(ps, axis=0)
        q = te[(te["liq"] >= gd["min_liq"]) & (te["close_vwap"] >= gd["vwap"])]
        if gd["idx_vol_min"] is not None:
            q = q[q["idx_vol20_d"] >= gd["idx_vol_min"]]
        pk = q.sort_values("p", ascending=False).groupby("date", group_keys=False).head(gd["topn"])
        if pk.empty:
            monthly.append({"month": tm, "n": 0}); continue
        monthly.append({"month": tm, "n": int(len(pk)), "hit": round(float(pk["y3"].mean()) * 100, 2),
                        "ret3d": round(float(pk["ret3d"].mean()), 3) if pk["ret3d"].notna().any() else None})
        picks_all.append(pk[["date", "code", "y3", "ret3d", "mae3", "p"]])
    pk = pd.concat(picks_all) if picks_all else pd.DataFrame()
    res = {"variant": name, "market": mkt, "monthly": monthly}
    if len(pk):
        r = pk["ret3d"].dropna()
        hits = [m_["hit"] for m_ in monthly if m_.get("n", 0) > 0 and m_.get("hit") is not None]
        bs = [np.random.default_rng(s).choice(r.values, size=len(r), replace=True).mean() for s in range(500)] if len(r) >= 10 else None
        res.update({"n": int(len(pk)), "hit": round(float(pk["y3"].mean()) * 100, 2),
                    "ret3d_avg": round(float(r.mean()), 3) if len(r) else None,
                    "net_ev": round(float(r.mean()) - COST, 3) if len(r) else None,
                    "net_ev_ci95": (round(float(np.percentile(bs, 2.5)) - COST, 3), round(float(np.percentile(bs, 97.5)) - COST, 3)) if bs else None,
                    "mae3_avg": round(float(pk["mae3"].dropna().mean()), 3) if pk["mae3"].notna().any() else None,
                    "monthly_hit_floor": round(min(hits), 2) if hits else None,
                    "months_ge70": sum(1 for h in hits if h >= 70), "months_active": len(hits)})
    return res


def main():
    print("[assemble] ...", flush=True)
    P = assemble()
    ev = build_event_features(P)
    P0 = P.merge(ev, on=["code", "date"], how="left")
    print(f"  event coverage: any20>0 on {float((P0['ev_any20'] > 0).mean()):.1%} of panel rows", flush=True)

    # placebo for events
    PP = P0.copy()
    rng = np.random.default_rng(0)
    def perm(gr):
        idx = rng.permutation(len(gr)); gr[EVF] = gr[EVF].values[idx]; return gr
    PP = PP.groupby("date", group_keys=False).apply(perm)

    BASE = ITF + [c + "_d" for c in DLF]
    results = []
    # 1) validator: production ensemble reproduction (both markets)
    for mkt in ("KOSPI", "KOSDAQ"):
        r = run_variant(P0, "BASE_ENSEMBLE", BASE, mkt, ensemble=True)
        results.append(r)
        print(f"[{mkt} BASE_ENSEMBLE] n={r.get('n')} hit={r.get('hit')}% ret3d={r.get('ret3d_avg')}% "
              f"netEV={r.get('net_ev')} ci={r.get('net_ev_ci95')} floor={r.get('monthly_hit_floor')} "
              f"({r.get('months_ge70')}/{r.get('months_active')} mo>=70)", flush=True)
        print("   monthly:", [(m['month'], m.get('n'), m.get('hit')) for m in r["monthly"]], flush=True)
    # 2) event increment (LGBM, same harness as flow study)
    for mkt in ("KOSPI", "KOSDAQ"):
        for name, D, feat in (("EVENT", P0, BASE + EVF), ("EVENT_PLACEBO", PP, BASE + EVF)):
            r = run_variant(D, name, feat, mkt)
            results.append(r)
            print(f"[{mkt} {name}] n={r.get('n')} hit={r.get('hit')}% ret3d={r.get('ret3d_avg')}% "
                  f"netEV={r.get('net_ev')} ci={r.get('net_ev_ci95')} floor={r.get('monthly_hit_floor')} "
                  f"({r.get('months_ge70')}/{r.get('months_active')} mo>=70)", flush=True)

    with open(OUT_JSON, "w") as fh:
        json.dump({"results": results}, fh, indent=1)
    print(f"[done] {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()
