#!/usr/bin/env python3
"""P2 B-H1: credit(신용잔고) 피처의 시장중립(a5) 프레임 기여 검증.

- 동일 24폴드 월별 walk-forward (2024-07~2026-06, 학습=직전 E.TRAIN_MONTHS개월).
- BASE(ALLF, 프로덕션 3-seed 앙상블) vs CRED(ALLF+credit 8피처) vs PLC(일자내 셔플 플라시보).
- credit 공표 T+2 → 모든 credit 피처는 t-2 시프트(l2). 커버리지 ~60%(300/500), 결측=NaN→fillna(0),
  랭크 피처는 (일자내 pct rank - 0.5)로 중심화해 결측 0=중립.
- 플라시보: credit 8피처 블록을 일자내(패널 행 기준) 조인트 무작위 재배치 — 코드-연결만 파괴,
  일별 분포/결측률 보존. 학습·테스트 모두 셔플본 사용.
- 판정: top3 Δα(CRED-BASE)가 Δα(PLC-BASE)와 분리 + 연도별 2/3+ 일관.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
from b_engine import model_engine as E

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "p2_b_credit.json")
CREDIT = os.path.expanduser("~/research_cache/credit.parquet")

RAW = ["cr_lr_l2", "cr_lrd5_l2", "cr_lrd20_l2", "cr_gv_l2"]
RK = ["rk_" + c for c in RAW]
CR = RAW + RK


def build_panel():
    px = E.load_panel()
    px = px.dropna(subset=["a5"]).copy()
    px["date"] = pd.to_datetime(px["date"])

    c = pd.read_parquet(CREDIT, columns=["code", "date", "loan_rate", "loan_gvrt"])
    c["code"] = c["code"].astype(str)
    c["date"] = pd.to_datetime(c["date"])
    c = c.sort_values(["code", "date"])
    g = c.groupby("code")
    # T+2 공표 시차 → shift(2) (해당 종목의 거래일 기준)
    c["cr_lr_l2"] = g["loan_rate"].shift(2)
    c["cr_lrd5_l2"] = (c["loan_rate"] - g["loan_rate"].shift(5)).groupby(c["code"]).shift(2)
    c["cr_lrd20_l2"] = (c["loan_rate"] - g["loan_rate"].shift(20)).groupby(c["code"]).shift(2)
    c["cr_gv_l2"] = g["loan_gvrt"].shift(2)

    px = px.merge(c[["code", "date"] + RAW], on=["code", "date"], how="left")
    px = px.sort_values(["code", "date"])
    for col in RAW:
        px[col] = px.groupby("code")[col].ffill(limit=5)
    # 일자내 횡단면 랭크(중심화: 결측 fillna(0)=중립)
    for col in RAW:
        px["rk_" + col] = px.groupby("date")[col].rank(pct=True) - 0.5
    cov = px["cr_lr_l2"].notna().mean()
    print(f"[panel] rows={len(px)} credit coverage={cov:.3f}", flush=True)

    # 플라시보: 일자내 조인트 블록 셔플 (한 번, 고정 rng)
    rng = np.random.default_rng(42)
    plc = np.empty((len(px), len(CR)))
    vals = px[CR].values
    for _, idx in px.groupby("date").indices.items():
        perm = rng.permutation(idx)
        plc[idx] = vals[perm]
    for j, col in enumerate(CR):
        px["plc_" + col] = plc[:, j]
    return px


def fit_seeds(tr, feats, target="a5"):
    import lightgbm as lgb
    models = []
    for sd in range(E.N_SEEDS):
        m = lgb.LGBMRegressor(**E.LGB, random_state=sd, verbose=-1)
        m.fit(tr[feats].fillna(0), tr[target])
        models.append(m)
    return models


def pred_seeds(models, te, feats):
    return np.mean([m.predict(te[feats].fillna(0)) for m in models], axis=0)


def main():
    px = build_panel()
    F_CRED = E.ALLF + CR
    F_PLC = E.ALLF + ["plc_" + c for c in CR]
    months = pd.period_range("2024-07", "2026-06", freq="M")
    pools = []
    for tm in months:
        t0, t1 = tm.start_time, tm.end_time
        tr = px[(px["date"] < t0) & (px["date"] >= t0 - pd.DateOffset(months=E.TRAIN_MONTHS))]
        te = px[(px["date"] >= t0) & (px["date"] <= t1)].copy()
        if len(tr) < 20000 or te.empty:
            continue
        te["p_base"] = pred_seeds(fit_seeds(tr, E.ALLF), te, E.ALLF)
        te["p_cred"] = pred_seeds(fit_seeds(tr, F_CRED), te, F_CRED)
        te["p_plc"] = pred_seeds(fit_seeds(tr, F_PLC), te, F_PLC)
        pools.append(te[["date", "code", "a5", "f5", "p_base", "p_cred", "p_plc"]].assign(month=str(tm)))
        print(f"[{tm}] pool={len(te)} train={len(tr)}", flush=True)

    A = pd.concat(pools, ignore_index=True)
    A["year"] = A["date"].dt.year
    results = {"coverage_note": "credit covers ~300 codes / universe 500 (~60% rows)"}
    daily = {}   # (model, topn) -> daily mean series
    rows = []
    for nm in ("p_base", "p_cred", "p_plc"):
        for topn in (10, 3, 1):
            s = A.sort_values(nm, ascending=False).groupby("date", group_keys=False).head(topn)
            dm = s.groupby("date")["a5"].mean()
            daily[(nm, topn)] = dm
            yr = s.groupby("year")["a5"].mean()
            bs = [np.random.default_rng(x).choice(s["a5"].values, len(s), True).mean() for x in range(500)]
            row = dict(model=nm[2:], topn=topn, n=int(len(s)),
                       alpha=round(float(s["a5"].mean()), 3),
                       ci=[round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)],
                       alpha_win=round(float((s["a5"] > 0).mean()) * 100, 1),
                       yr={int(y): round(float(v), 2) for y, v in yr.items()})
            rows.append(row)
            print(f"  {row['model']:5s} top{topn:2d} n={row['n']:5d} a={row['alpha']:+.3f} CI={row['ci']} "
                  f"win={row['alpha_win']:.1f}% yr={row['yr']}", flush=True)
    # 페어드 일별 Δ (day-cluster bootstrap)
    deltas = []
    for other in ("p_cred", "p_plc"):
        for topn in (10, 3):
            d = (daily[(other, topn)] - daily[("p_base", topn)]).dropna()
            v = d.values
            bs = [np.random.default_rng(x).choice(v, len(v), True).mean() for x in range(1000)]
            dy = d.groupby(d.index.year).mean()
            drow = dict(pair=f"{other[2:]}-base", topn=topn, n_days=int(len(v)),
                        d_alpha=round(float(v.mean()), 3),
                        ci=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
                        yr={int(y): round(float(x), 3) for y, x in dy.items()},
                        yr_better=f"{int((dy > 0).sum())}/{len(dy)}")
            deltas.append(drow)
            print(f"  D {drow['pair']:10s} top{topn:2d} d_a={drow['d_alpha']:+.3f} CI={drow['ci']} "
                  f"yr={drow['yr']} better={drow['yr_better']}", flush=True)
    results["levels"] = rows
    results["paired_daily_deltas"] = deltas
    json.dump(results, open(OUT, "w"), indent=1)
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
