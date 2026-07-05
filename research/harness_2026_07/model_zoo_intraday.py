#!/usr/bin/env python3
"""Model-architecture zoo for the promoted intraday lanes (swing-main-jszr).

Same 8 OOS monthly folds, same guards, rank-1/day, promoted contracts
(KOSPI: +5% touch/5d; KOSDAQ: +10% touch/5d), net 0.3 cost. Contestants:
  TREES    — production 3-model ensemble (LGBM+XGB+ET classifier, y3)      [baseline]
  RANKER   — LGBMRanker lambdarank, per-day groups, graded label            [objective change]
  EVREG    — LGBMRegressor on the contract policy return (rank by pred EV)  [objective change]
  MLP      — torch MLP (256-128, dropout, standardized), y3 BCE, MPS        [architecture change]
  BLEND    — mean rank of TREES + MLP                                        [diversity]
Metrics: rank-1 policy EV (net), win, bootstrap CI, monthly negatives, and
month-level paired diffs vs TREES (same days -> honest increment test).
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, COST, assemble
from exit_policy_research import attach_paths

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_zoo_intraday.json")
BASE = ITF + [c + "_d" for c in DLF]
CONTRACT = {"KOSPI": 5.0, "KOSDAQ": 10.0}


def policy_ret_frame(pool: pd.DataFrame, target: float) -> pd.Series:
    def pol(row):
        e = row["entry"]
        if not np.isfinite(e) or e <= 0:
            return np.nan
        tgt = e * (1 + target / 100)
        for k in range(1, 6):
            hi = row[f"high{k}"]; c = row[f"close{k}"]; o = row[f"open{k}"]
            if not np.isfinite(c):
                return np.nan
            if np.isfinite(hi) and hi >= tgt:
                return ((max(tgt, o) if np.isfinite(o) and o > 0 else tgt) / e - 1) * 100
        return (row["close5"] / e - 1) * 100
    return pool.apply(pol, axis=1)


def make_trees():
    import lightgbm as lgb, xgboost as xgb
    from sklearn.ensemble import ExtraTreesClassifier
    return [lgb.LGBMClassifier(n_estimators=400, learning_rate=0.04, num_leaves=31, min_child_samples=60,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1),
            xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.04, subsample=0.8,
                              colsample_bytree=0.7, reg_lambda=3, verbosity=0, n_jobs=-1),
            ExtraTreesClassifier(n_estimators=250, min_samples_leaf=40, random_state=0, n_jobs=-1)]


def fit_mlp(Xtr: np.ndarray, ytr: np.ndarray, Xte: np.ndarray, seed: int = 0) -> np.ndarray:
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    Xtr_, Xte_ = (Xtr - mu) / sd, (Xte - mu) / sd
    # temporal val split: last 15% of train (already time-ordered)
    ncut = int(len(Xtr_) * 0.85)
    Xt, yt = torch.tensor(Xtr_[:ncut], dtype=torch.float32), torch.tensor(ytr[:ncut], dtype=torch.float32)
    Xv, yv = torch.tensor(Xtr_[ncut:], dtype=torch.float32), torch.tensor(ytr[ncut:], dtype=torch.float32)
    net = nn.Sequential(nn.Linear(Xtr.shape[1], 256), nn.ReLU(), nn.Dropout(0.3),
                        nn.Linear(256, 128), nn.ReLU(), nn.Dropout(0.3),
                        nn.Linear(128, 1)).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-5)
    lossf = nn.BCEWithLogitsLoss()
    best, best_state, patience = 1e9, None, 0
    ds = torch.utils.data.TensorDataset(Xt, yt)
    dl = torch.utils.data.DataLoader(ds, batch_size=4096, shuffle=True)
    for ep in range(60):
        net.train()
        for xb, yb in dl:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad()
            loss = lossf(net(xb).squeeze(-1), yb)
            loss.backward(); opt.step()
        net.eval()
        with torch.no_grad():
            vl = float(lossf(net(Xv.to(dev)).squeeze(-1), yv.to(dev)))
        if vl < best - 1e-4:
            best, best_state, patience = vl, {k: v.detach().clone() for k, v in net.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 6:
                break
    if best_state:
        net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        p = torch.sigmoid(net(torch.tensor(Xte_, dtype=torch.float32).to(dev)).squeeze(-1)).cpu().numpy()
    return p


def run_market(P: pd.DataFrame, mkt: str) -> pd.DataFrame:
    import lightgbm as lgb
    gd = GUARDS[mkt]
    dm = P[P["mkt"] == mkt].dropna(subset=ITF + ["y3"]).sort_values("date").copy()
    pools = []
    for tm in TEST_MONTHS:
        t0 = pd.Timestamp(tm + "-01"); t1 = t0 + pd.offsets.MonthEnd(1)
        tr = dm[dm["date"] < t0]
        te = dm[(dm["date"] >= t0) & (dm["date"] <= t1)].copy()
        if len(tr) < 3000 or te.empty:
            continue
        Xtr = tr[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0).values
        Xte = te[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0).values
        ytr = tr["y3"].values.astype(float)

        # TREES
        ps = []
        for m in make_trees():
            m.fit(Xtr, ytr); ps.append(m.predict_proba(Xte)[:, 1])
        te["p_trees"] = np.mean(ps, axis=0)
        # RANKER (lambdarank, graded label from train policy return quartile within day)
        grade = tr.groupby("date")["train_pol"].rank(pct=True).fillna(0.5)
        ylab = np.clip((grade * 4).astype(int), 0, 3).values
        grp = tr.groupby("date", sort=False).size().values
        rk = lgb.LGBMRanker(objective="lambdarank", n_estimators=400, learning_rate=0.05, num_leaves=31,
                            min_child_samples=60, subsample=0.8, colsample_bytree=0.7, reg_lambda=3,
                            random_state=0, verbose=-1, label_gain=list(range(32)))
        rk.fit(Xtr, ylab, group=grp)
        te["p_rank"] = rk.predict(Xte)
        # EVREG (regress the contract policy return directly)
        rg = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=60,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1)
        okm = tr["train_pol"].notna().values
        rg.fit(Xtr[okm], tr.loc[okm, "train_pol"].values)
        te["p_evreg"] = rg.predict(Xte)
        # MLP
        te["p_mlp"] = fit_mlp(Xtr, ytr, Xte)
        # BLEND (rank-mean of trees & mlp)
        te["p_blend"] = (pd.Series(te["p_trees"]).rank(pct=True).values
                         + pd.Series(te["p_mlp"]).rank(pct=True).values) / 2
        q = te[(te["liq"] >= gd["min_liq"]) & (te["close_vwap"] >= gd["vwap"])]
        if gd["idx_vol_min"] is not None:
            q = q[q["idx_vol20_d"] >= gd["idx_vol_min"]]
        q = q.copy(); q["month"] = tm
        pools.append(q)
        print(f"  [{mkt} {tm}] pool={len(q)}", flush=True)
    return pd.concat(pools, ignore_index=True)


def evaluate(pool: pd.DataFrame, mkt: str) -> list:
    res = []
    base_monthly = None
    for name in ("p_trees", "p_rank", "p_evreg", "p_mlp", "p_blend"):
        s = pool.sort_values(name, ascending=False).groupby("date", group_keys=False).head(1)
        s = s.dropna(subset=["pret"])
        net = s["pret"]
        mo = s.groupby("month")["pret"].mean()
        bs = [np.random.default_rng(x).choice(net.values, len(net), True).mean() for x in range(400)]
        row = dict(model=name[2:], market=mkt, n=int(len(s)),
                   win=round(float((net > 0).mean()) * 100, 1),
                   ev=round(float(net.mean()), 2),
                   ci=(round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)),
                   negmo=f"{int((mo < 0).sum())}/{len(mo)}")
        if name == "p_trees":
            base_monthly = mo
        else:
            diff = (mo - base_monthly).dropna()
            row["paired_mo_diff"] = round(float(diff.mean()), 2)
            row["mo_better"] = f"{int((diff > 0).sum())}/{len(diff)}"
        res.append(row)
        print(f"  {mkt:6s} {row['model']:6s} n={row['n']:3d} win={row['win']:5.1f} EV={row['ev']:5.2f} CI={row['ci']} negMo={row['negmo']} "
              + (f"Δmo={row.get('paired_mo_diff')} better={row.get('mo_better')}" if name != "p_trees" else "[baseline]"), flush=True)
    return res


def main():
    print("[assemble]", flush=True)
    P = assemble()
    results = []
    for mkt in ("KOSPI", "KOSDAQ"):
        dm = P[P["mkt"] == mkt].dropna(subset=ITF + ["y3"]).sort_values("date").copy()
        dm = attach_paths(dm)
        dm["pret"] = policy_ret_frame(dm, CONTRACT[mkt]) - COST
        dm["train_pol"] = dm["pret"]  # same-contract policy return as training target for EVREG/RANKER
        print(f"[{mkt}] rows={len(dm)}", flush=True)
        pool = run_market(dm, mkt)
        results += evaluate(pool, mkt)
    json.dump(results, open(OUT, "w"), indent=1)
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
