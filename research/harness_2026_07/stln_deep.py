#!/usr/bin/env python3
"""T3 생존후보 심화: 대차잔고 급증 → 5d 시장초과 (swing-main-7m9y).

의심 우선: ①일내셔플 플라시보 ②연도분해 ③분위 단조성 ④공표지연 민감도(T+1/3/5)
⑤시장별 ⑥기존 스윙 랭커 p 위 '증분' (직교축 교훈 — 피처로 넣어 플라시보 대비 개선?)
"""
import os, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

CACHE = "/Users/dongdong/research_cache"
COST = 0.3
rng = np.random.default_rng(0)


def load():
    cols = ["code", "date", "market", "liq", "close", "ret_1d", "ft_5_5", "exec_5d"]
    px = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    px["exec_5d"] = px["exec_5d"].replace([np.inf, -np.inf], np.nan)
    liq_ok = ((px["market"] == "KOSPI") & (px["liq"] >= 100e8)) | ((px["market"] == "KOSDAQ") & (px["liq"] >= 30e8))
    px = px[liq_ok].copy()
    px["policy_ret"] = np.where(px["ft_5_5"] == 1, 5.0, px["exec_5d"])
    mkt = px.groupby("date")["policy_ret"].mean().rename("mkt_pol")
    px = px.join(mkt, on="date")
    px["pol_ex"] = px["policy_ret"] - px["mkt_pol"]
    cr = pd.read_parquet(f"{CACHE}/credit.parquet")
    cr["date"] = pd.to_datetime(cr["date"])
    cr = cr.sort_values(["code", "date"])
    cr["d_stln"] = cr.groupby("code")["stln_rate"].transform(lambda s: s - s.shift(20))
    return px, cr


def stat(d, name):
    v = d.dropna(subset=["pol_ex"])["pol_ex"]
    if len(v) < 100:
        print(f"  {name:40s} n={len(v)} 부족"); return
    bs = [rng.choice(v.values, len(v), True).mean() for _ in range(300)]
    print(f"  {name:40s} n={len(v):6d} 초과EV={v.mean():+.3f} CI[{np.percentile(bs,2.5):+.2f},{np.percentile(bs,97.5):+.2f}]")


def main():
    px, cr = load()
    for lag in (1, 3, 5):
        c = cr.copy()
        c["sig_date"] = c.groupby("code")["date"].shift(-lag)
        m = px.merge(c[["code", "sig_date", "d_stln"]].rename(columns={"sig_date": "date"}),
                     on=["code", "date"], how="inner").dropna(subset=["d_stln", "pol_ex"])
        q = m.groupby("date")["d_stln"].rank(pct=True)
        print(f"\n===== 지연 T+{lag} =====", flush=True)
        stat(m[q >= 0.9], "대차급증 상위10%")
        if lag == 3:
            M = m; Q = q
    print("\n===== 분위 단조성 (T+3) =====", flush=True)
    for a, b in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 1.01)):
        stat(M[(Q >= a) & (Q < b)], f"q{a:.1f}-{b:.1f}")
    print("\n===== 연도 분해 (상위10%, T+3) =====", flush=True)
    top = M[Q >= 0.9]
    for yr, g in top.groupby(top["date"].dt.year):
        v = g["pol_ex"].dropna()
        print(f"  {yr}: n={len(v):5d} 초과EV={v.mean():+.3f}")
    print("\n===== 시장별 (T+3) =====", flush=True)
    for mkt in ("KOSPI", "KOSDAQ"):
        stat(top[top["market"] == mkt], mkt)
    print("\n===== 플라시보 (일내 셔플, T+3) =====", flush=True)
    P = M.copy()
    P["d_stln"] = P.groupby("date")["d_stln"].transform(lambda s: rng.permutation(s.values))
    qp = P.groupby("date")["d_stln"].rank(pct=True)
    stat(P[qp >= 0.9], "플라시보 상위10%")

    print("\n===== 증분 검증: 스윙 랭커 p + d_stln (연도 walk-forward) =====", flush=True)
    import lightgbm as lgb
    FEATS_PX = ["ret_1d"]  # placeholder — 실제 증분은 랭커 재현으로
    cols = ["code", "date", "market", "liq", "ft_5_5"] + [
        "ret_3d", "ret_5d", "ret_10d", "ret_20d", "ret_60d", "ma5_dist", "ma20_dist", "ma60_dist",
        "ma120_dist", "ma20_slope", "ma60_slope", "rsi14", "rsi_slope", "accel", "consec_up", "dist_hi20",
        "dist_hi60", "dist_hi120", "dist_lo20", "dist_lo60", "pos20", "bb_pctb", "bb_bw", "atr_pct", "vol20",
        "close_loc", "gap", "vol_ratio", "vol_trend", "turn_z", "obv_slope", "cmf20", "idx_mom20", "idx_vol20"]
    fx = pd.read_parquet(f"{CACHE}/px_long.parquet", columns=list(dict.fromkeys(cols + ["ret_1d", "exec_5d"])))
    fx["date"] = pd.to_datetime(fx["date"])
    fx["exec_5d"] = fx["exec_5d"].replace([np.inf, -np.inf], np.nan)
    liq_ok = ((fx["market"] == "KOSPI") & (fx["liq"] >= 100e8)) | ((fx["market"] == "KOSDAQ") & (fx["liq"] >= 30e8))
    fx = fx[liq_ok]
    fx["policy_ret"] = np.where(fx["ft_5_5"] == 1, 5.0, fx["exec_5d"])
    c3 = cr.copy(); c3["sig_date"] = c3.groupby("code")["date"].shift(-3)
    fx = fx.merge(c3[["code", "sig_date", "d_stln"]].rename(columns={"sig_date": "date"}),
                  on=["code", "date"], how="left")
    FE = [c for c in cols if c not in ("code", "date", "market", "liq", "ft_5_5")] + ["ret_1d"]
    fx = fx.dropna(subset=["ft_5_5"])
    fx["d_stln_plc"] = fx.groupby("date")["d_stln"].transform(
        lambda s: rng.permutation(s.values) if len(s) > 1 else s)
    out = {}
    for tag, extra in (("베이스", []), ("+대차", ["d_stln"]), ("+대차플라시보", ["d_stln_plc"])):
        feats = FE + extra
        pools = []
        for yr in (2024, 2025, 2026):
            t0 = pd.Timestamp(f"{yr}-01-01")
            tr = fx[(fx["date"] < t0) & (fx["date"] >= t0 - pd.DateOffset(years=2))]
            te = fx[(fx["date"] >= t0) & (fx["date"] < t0 + pd.DateOffset(years=1))].copy()
            if len(tr) < 20000 or te.empty:
                continue
            mdl = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=63, min_child_samples=100,
                                     subsample=0.8, colsample_bytree=0.7, reg_lambda=5, random_state=0, verbose=-1)
            mdl.fit(tr[feats].clip(-1e4, 1e4), tr["ft_5_5"])
            te["p"] = mdl.predict_proba(te[feats].clip(-1e4, 1e4))[:, 1]
            pk = te.sort_values("p", ascending=False).groupby("date", group_keys=False).head(3)
            pools.append(pk)
        A = pd.concat(pools).dropna(subset=["policy_ret"])
        net = A["policy_ret"] - COST
        yrs = net.groupby(A["date"].dt.year).mean().round(3).to_dict()
        out[tag] = (round(net.mean(), 3), yrs)
        print(f"  {tag:12s} EV={net.mean():+.3f} 연도별 {yrs}")
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump({"done": True}, open(os.path.join(here, "stln_deep.done"), "w"))
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
