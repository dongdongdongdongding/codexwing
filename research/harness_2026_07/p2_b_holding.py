#!/usr/bin/env python3
"""P2 B-H2: 보유기간 프런티어 — HOLD 3/5/10일 α 및 α/보유일(자본효율) 비교.

- fH: 진입=익일종가(close.shift(-1)), exit=진입+H일 종가(close.shift(-(H+1))) — load_panel f5와 동일 방식.
  px_long 원시 close에서 전체 코드 시계열로 계산(패널 필터로 인한 shift 어긋남 방지) 후 병합.
- aH = fH - 당일 유니버스(패널 행) 평균 fH — a5 구성과 동일한 시장중립.
- 동일 24폴드: 각 H에 대해 aH 타깃으로 3-seed 앙상블 재학습(H-native) + a5 모델 픽의 aH 재채점(cross).
- 자본효율: 일일 topN 진입·H일 보유 → 동시보유 topN×H 슬롯 → 포트 일수익률 ≈ mean(aH)/H = α/일.
- 판정: α/일 기준 우월 구간 발견 여부. 5일 최적이면 그대로 확정.
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/dongdong/Projects/codex_swing/swing-main")
from b_engine import model_engine as E

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "p2_b_holding.json")
HORIZONS = (3, 5, 10)


def build_panel():
    px = E.load_panel()
    px["date"] = pd.to_datetime(px["date"])
    raw = pd.read_parquet(E.PX_LONG, columns=["code", "date", "close"])
    raw["code"] = raw["code"].astype(str)
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.sort_values(["code", "date"])
    g = raw.groupby("code")
    ent = g["close"].shift(-1)
    for H in HORIZONS:
        raw[f"f{H}x"] = (g["close"].shift(-(H + 1)) / ent - 1) * 100
    px = px.merge(raw[["code", "date"] + [f"f{H}x" for H in HORIZONS]], on=["code", "date"], how="left")
    # sanity: f5x vs 패널 f5 일치 확인
    chk = px.dropna(subset=["f5", "f5x"])
    md = (chk["f5"] - chk["f5x"]).abs().max()
    print(f"[sanity] |f5 - f5x| max = {md:.6f} (0이어야 함)", flush=True)
    for H in HORIZONS:
        px[f"a{H}x"] = px[f"f{H}x"] - px.groupby("date")[f"f{H}x"].transform("mean")
    return px


def fit_seeds(tr, target):
    import lightgbm as lgb
    models = []
    for sd in range(E.N_SEEDS):
        m = lgb.LGBMRegressor(**E.LGB, random_state=sd, verbose=-1)
        m.fit(tr[E.ALLF].fillna(0), tr[target])
        models.append(m)
    return models


def pred_seeds(models, te):
    return np.mean([m.predict(te[E.ALLF].fillna(0)) for m in models], axis=0)


def main():
    px = build_panel()
    months = pd.period_range("2024-07", "2026-06", freq="M")
    pools = []
    for tm in months:
        t0, t1 = tm.start_time, tm.end_time
        te = px[(px["date"] >= t0) & (px["date"] <= t1)].copy()
        trbase = px[(px["date"] < t0) & (px["date"] >= t0 - pd.DateOffset(months=E.TRAIN_MONTHS))]
        if te.empty:
            continue
        ok = True
        for H in HORIZONS:
            tr = trbase.dropna(subset=[f"a{H}x"])
            if len(tr) < 20000:
                ok = False
                break
            te[f"p_h{H}"] = pred_seeds(fit_seeds(tr, f"a{H}x"), te)
        if not ok:
            continue
        pools.append(te[["date", "code"] + [f"a{H}x" for H in HORIZONS] + [f"p_h{H}" for H in HORIZONS]]
                     .assign(month=str(tm)))
        print(f"[{tm}] pool={len(te)}", flush=True)

    A = pd.concat(pools, ignore_index=True)
    A["year"] = A["date"].dt.year
    results = []
    for topn in (3, 10):
        for H in HORIZONS:                       # H-native: aH 타깃 학습 모델
            for sel, tag in ((f"p_h{H}", "native"), ("p_h5", "a5model")):
                if tag == "a5model" and H == 5:
                    continue  # native와 동일
                s = A.sort_values(sel, ascending=False).groupby("date", group_keys=False).head(topn)
                s = s.dropna(subset=[f"a{H}x"])
                v = s[f"a{H}x"].values
                bs = [np.random.default_rng(x).choice(v, len(v), True).mean() for x in range(500)]
                yr = s.groupby("year")[f"a{H}x"].mean()
                row = dict(hold=H, selector=tag, topn=topn, n=int(len(s)),
                           alpha=round(float(v.mean()), 3),
                           ci=[round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2)],
                           alpha_per_day=round(float(v.mean()) / H, 3),
                           apd_ci=[round(float(np.percentile(bs, 2.5)) / H, 3),
                                   round(float(np.percentile(bs, 97.5)) / H, 3)],
                           alpha_win=round(float((v > 0).mean()) * 100, 1),
                           yr={int(y): round(float(x), 2) for y, x in yr.items()})
                results.append(row)
                print(f"  H={H:2d} {tag:8s} top{topn:2d} n={row['n']:5d} a={row['alpha']:+.3f} CI={row['ci']} "
                      f"a/day={row['alpha_per_day']:+.3f} {row['apd_ci']} win={row['alpha_win']}% yr={row['yr']}",
                      flush=True)
    # 페어드: 동일 픽(a5모델 top3)에서 H별 α/일 — 보유효과만 분리
    paired = []
    s5 = A.sort_values("p_h5", ascending=False).groupby("date", group_keys=False).head(3)
    for H in HORIZONS:
        d = s5.dropna(subset=[f"a{H}x"])
        v = d[f"a{H}x"].values / H
        bs = [np.random.default_rng(x).choice(v, len(v), True).mean() for x in range(500)]
        yr = (d.groupby("year")[f"a{H}x"].mean() / H)
        paired.append(dict(hold=H, n=int(len(d)), alpha_per_day=round(float(v.mean()), 3),
                           ci=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
                           yr={int(y): round(float(x), 3) for y, x in yr.items()}))
        print(f"  paired same-picks(top3,a5model) H={H:2d} a/day={paired[-1]['alpha_per_day']:+.3f} "
              f"CI={paired[-1]['ci']} yr={paired[-1]['yr']}", flush=True)
    json.dump({"frontier": results, "paired_same_picks_top3": paired}, open(OUT, "w"), indent=1)
    print(f"[done] {OUT}", flush=True)


if __name__ == "__main__":
    main()
