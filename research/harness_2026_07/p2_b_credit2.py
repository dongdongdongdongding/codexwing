#!/usr/bin/env python3
"""P2 B-H1 보강: credit vs placebo 직접 페어드 대조 (1차 p2_b_credit.py의 판정 결함 보완).

1차 발견: 노이즈 8피처 추가만으로 top3 α가 +0.32 상승(구조 아티팩트) → credit 기여 주장엔
cred-plc '직접' 페어드 CI + 복수 플라시보 드로우가 필요. 풀 저장 + 월별 부호표 추가.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
from b_engine import model_engine as E
from p2_b_credit import CR  # 피처 목록 재사용

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "p2_b_credit2.json")
POOL = os.path.join(HERE, "p2_b_credit2_pool.parquet")
N_PLC = 2


def fit_seeds(tr, feats):
    import lightgbm as lgb
    models = []
    for sd in range(E.N_SEEDS):
        m = lgb.LGBMRegressor(**E.LGB, random_state=sd, verbose=-1, n_jobs=4)
        m.fit(tr[feats].fillna(0), tr["a5"])
        models.append(m)
    return models


def pred_seeds(models, te, feats):
    return np.mean([m.predict(te[feats].fillna(0)) for m in models], axis=0)


def main():
    # build_panel: p2_b_credit.build_panel과 동일하되 플라시보 드로우 N_PLC개
    import p2_b_credit as C1
    px = C1.build_panel()          # plc_* (draw seed 42) 포함
    rng = np.random.default_rng(7)  # 2번째 드로우
    vals = px[CR].values
    plc2 = np.empty((len(px), len(CR)))
    for _, idx in px.groupby("date").indices.items():
        perm = rng.permutation(idx)
        plc2[idx] = vals[perm]
    for j, col in enumerate(CR):
        px["plcB_" + col] = plc2[:, j]

    F = {
        "base": E.ALLF,
        "cred": E.ALLF + CR,
        "plcA": E.ALLF + ["plc_" + c for c in CR],
        "plcB": E.ALLF + ["plcB_" + c for c in CR],
    }
    months = pd.period_range("2024-07", "2026-06", freq="M")
    pools = []
    for tm in months:
        t0, t1 = tm.start_time, tm.end_time
        tr = px[(px["date"] < t0) & (px["date"] >= t0 - pd.DateOffset(months=E.TRAIN_MONTHS))]
        te = px[(px["date"] >= t0) & (px["date"] <= t1)].copy()
        if len(tr) < 20000 or te.empty:
            continue
        for nm, feats in F.items():
            te["p_" + nm] = pred_seeds(fit_seeds(tr, feats), te, feats)
        pools.append(te[["date", "code", "a5", "f5"] + ["p_" + n for n in F]].assign(month=str(tm)))
        print(f"[{tm}] pool={len(te)}", flush=True)

    A = pd.concat(pools, ignore_index=True)
    A.to_parquet(POOL)
    A["year"] = A["date"].dt.year
    out = {"n_placebo_draws": N_PLC}
    daily = {}
    levels = []
    for nm in F:
        for topn in (10, 3):
            s = A.sort_values("p_" + nm, ascending=False).groupby("date", group_keys=False).head(topn)
            daily[(nm, topn)] = s.groupby("date")["a5"].mean()
            v = s["a5"].values
            bs = [np.random.default_rng(x).choice(v, len(v), True).mean() for x in range(500)]
            yr = s.groupby("year")["a5"].mean()
            row = dict(model=nm, topn=topn, n=int(len(s)), alpha=round(float(v.mean()), 3),
                       ci=[round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)],
                       yr={int(y): round(float(x), 2) for y, x in yr.items()})
            levels.append(row)
            print(f"  {nm:5s} top{topn:2d} a={row['alpha']:+.3f} CI={row['ci']} yr={row['yr']}", flush=True)
    deltas = []
    pairs = [("cred", "base"), ("plcA", "base"), ("plcB", "base"),
             ("cred", "plcA"), ("cred", "plcB")]
    for a, b in pairs:
        for topn in (3, 10):
            d = (daily[(a, topn)] - daily[(b, topn)]).dropna()
            v = d.values
            bs = [np.random.default_rng(x).choice(v, len(v), True).mean() for x in range(1000)]
            dy = d.groupby(d.index.year).mean()
            dm = d.groupby(d.index.to_period("M")).mean()
            drow = dict(pair=f"{a}-{b}", topn=topn, n_days=int(len(v)),
                        d_alpha=round(float(v.mean()), 3),
                        ci=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
                        yr={int(y): round(float(x), 3) for y, x in dy.items()},
                        yr_better=f"{int((dy > 0).sum())}/{len(dy)}",
                        months_pos=f"{int((dm > 0).sum())}/{len(dm)}")
            deltas.append(drow)
            print(f"  D {drow['pair']:11s} top{topn:2d} d={drow['d_alpha']:+.3f} CI={drow['ci']} "
                  f"yr={drow['yr']} {drow['yr_better']} mo+={drow['months_pos']}", flush=True)
    out["levels"] = levels
    out["paired_daily_deltas"] = deltas
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
