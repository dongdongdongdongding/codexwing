#!/usr/bin/env python3
"""Raw minute-sequence model vs hand-crafted ITF (swing-main-jszr Exp2).

Question: does a learned representation of the day's 5-min path (78x5) beat or complement
the 13 hand-crafted ITF features? Same 8 OOS folds, rank-1/day, promoted contracts, net 0.3.
Contestants: TREES (ITF+DLF baseline) | SEQ (CNN over 5-min bars + DLF context) | BLEND (rank-mean).
"""
import os, sys, json, warnings, time
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flow_increment_research import ITF, DLF, GUARDS, TEST_MONTHS, COST, assemble
from exit_policy_research import attach_paths
from model_zoo_intraday import policy_ret_frame, make_trees, CONTRACT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "seq_model_results.json")
BASE = ITF + [c + "_d" for c in DLF]
DLFC = [c + "_d" for c in DLF]


def train_seq(Xs_tr, Xd_tr, y_tr, Xs_te, Xd_te, seed=0):
    import torch
    import torch.nn as nn
    torch.manual_seed(seed)
    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    mu, sd = Xd_tr.mean(0), Xd_tr.std(0) + 1e-9
    Xd_tr = (Xd_tr - mu) / sd; Xd_te = (Xd_te - mu) / sd
    smu = Xs_tr.reshape(-1, Xs_tr.shape[-1]).mean(0)
    ssd = Xs_tr.reshape(-1, Xs_tr.shape[-1]).std(0) + 1e-9
    Xs_tr = (Xs_tr - smu) / ssd; Xs_te = (Xs_te - smu) / ssd

    class Net(nn.Module):
        def __init__(self, nd):
            super().__init__()
            self.conv = nn.Sequential(
                nn.Conv1d(5, 32, 5, padding=2), nn.ReLU(),
                nn.Conv1d(32, 64, 5, stride=2, padding=2), nn.ReLU(),
                nn.Conv1d(64, 64, 3, stride=2, padding=1), nn.ReLU(),
                nn.AdaptiveAvgPool1d(1))
            self.head = nn.Sequential(nn.Linear(64 + nd, 64), nn.ReLU(), nn.Dropout(0.3), nn.Linear(64, 1))
        def forward(self, xs, xd):
            z = self.conv(xs.transpose(1, 2)).squeeze(-1)
            return self.head(torch.cat([z, xd], dim=1)).squeeze(-1)

    ncut = int(len(y_tr) * 0.85)
    def T(a, dt=np.float32): return torch.tensor(np.asarray(a, dtype=dt))
    ds = torch.utils.data.TensorDataset(T(Xs_tr[:ncut]), T(Xd_tr[:ncut]), T(y_tr[:ncut]))
    dl = torch.utils.data.DataLoader(ds, batch_size=1024, shuffle=True)
    Xv_s, Xv_d, yv = T(Xs_tr[ncut:]).to(dev), T(Xd_tr[ncut:]).to(dev), T(y_tr[ncut:]).to(dev)
    net = Net(Xd_tr.shape[1]).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-5)
    lossf = nn.BCEWithLogitsLoss()
    best, best_state, pat = 1e9, None, 0
    for ep in range(40):
        net.train()
        for xs, xd, yb in dl:
            xs, xd, yb = xs.to(dev), xd.to(dev), yb.to(dev)
            opt.zero_grad(); lossf(net(xs, xd), yb).backward(); opt.step()
        net.eval()
        with torch.no_grad():
            vl = float(lossf(net(Xv_s, Xv_d), yv))
        if vl < best - 1e-4:
            best, best_state, pat = vl, {k: v.detach().clone() for k, v in net.state_dict().items()}, 0
        else:
            pat += 1
            if pat >= 5:
                break
    if best_state:
        net.load_state_dict(best_state)
    net.eval()
    outs = []
    with torch.no_grad():
        for i in range(0, len(Xs_te), 4096):
            outs.append(torch.sigmoid(net(T(Xs_te[i:i+4096]).to(dev), T(Xd_te[i:i+4096]).to(dev))).cpu().numpy())
    return np.concatenate(outs)


def main():
    print("[load] panel + seq", flush=True)
    P = assemble()
    z = np.load(os.path.join(HERE, "seq_dataset.npz"))
    key = pd.DataFrame({"code": z["code"], "date": pd.to_datetime(z["date"]), "seq_ix": np.arange(len(z["code"]))})
    P["code"] = P["code"].astype(str).str.zfill(6)
    P = P.merge(key, on=["code", "date"], how="inner")
    Xseq_all = z["X"]
    print(f"  aligned rows={len(P)}", flush=True)
    results = []
    for mkt in ("KOSPI", "KOSDAQ"):
        gd = GUARDS[mkt]
        dm = P[P["mkt"] == mkt].dropna(subset=ITF + ["y3"]).sort_values("date").copy()
        dm = attach_paths(dm)
        dm["pret"] = policy_ret_frame(dm, CONTRACT[mkt]) - COST
        pools = []
        for tm in TEST_MONTHS:
            t0 = pd.Timestamp(tm + "-01"); t1 = t0 + pd.offsets.MonthEnd(1)
            tr = dm[dm["date"] < t0]
            te = dm[(dm["date"] >= t0) & (dm["date"] <= t1)].copy()
            if len(tr) < 3000 or te.empty:
                continue
            tt0 = time.time()
            Xd_tr = tr[DLFC].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0).values.astype(np.float32)
            Xd_te = te[DLFC].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0).values.astype(np.float32)
            Xb_tr = tr[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0).values
            Xb_te = te[BASE].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0).values
            ytr = tr["y3"].values.astype(np.float32)
            # TREES baseline
            ps = []
            for m in make_trees():
                m.fit(Xb_tr, ytr); ps.append(m.predict_proba(Xb_te)[:, 1])
            te["p_trees"] = np.mean(ps, axis=0)
            # SEQ
            te["p_seq"] = train_seq(Xseq_all[tr["seq_ix"].values], Xd_tr, ytr,
                                    Xseq_all[te["seq_ix"].values], Xd_te)
            te["p_blend"] = (pd.Series(te["p_trees"]).rank(pct=True).values
                             + pd.Series(te["p_seq"]).rank(pct=True).values) / 2
            q = te[(te["liq"] >= gd["min_liq"]) & (te["close_vwap"] >= gd["vwap"])]
            if gd["idx_vol_min"] is not None:
                q = q[q["idx_vol20_d"] >= gd["idx_vol_min"]]
            q = q.copy(); q["month"] = tm
            pools.append(q)
            print(f"  [{mkt} {tm}] pool={len(q)} ({time.time()-tt0:.0f}s)", flush=True)
        A = pd.concat(pools, ignore_index=True)
        base_mo = None
        for nm in ("p_trees", "p_seq", "p_blend"):
            s = A.sort_values(nm, ascending=False).groupby("date", group_keys=False).head(1).dropna(subset=["pret"])
            net = s["pret"]; mo = s.groupby("month")["pret"].mean()
            bs = [np.random.default_rng(x).choice(net.values, len(net), True).mean() for x in range(400)]
            row = dict(model=nm[2:], market=mkt, n=int(len(s)), win=round(float((net > 0).mean()) * 100, 1),
                       ev=round(float(net.mean()), 2),
                       ci=(round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)),
                       negmo=f"{int((mo < 0).sum())}/{len(mo)}")
            if nm == "p_trees":
                base_mo = mo
            else:
                dd = (mo - base_mo).dropna()
                row["d_mo"] = round(float(dd.mean()), 2); row["mo_better"] = f"{int((dd > 0).sum())}/{len(dd)}"
            results.append(row)
            print(f"  {mkt} {row['model']:6s} n={row['n']} win={row['win']} EV={row['ev']} CI={row['ci']} negMo={row['negmo']} "
                  + (f"Δmo={row.get('d_mo')} better={row.get('mo_better')}" if nm != "p_trees" else "[baseline]"), flush=True)
    json.dump(results, open(OUT, "w"), indent=1)
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
