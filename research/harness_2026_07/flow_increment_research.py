#!/usr/bin/env python3
"""A-track flow(수급) increment research — KR intraday 3D+5% touch lanes (swing-main-ayu1).

Question: do foreigner/institution net-buy features add increment ON TOP OF the
production intraday feature set (ITF 13 + DLF 26) for the 3-day +5% MFE touch target?

Discipline:
- walk-forward monthly folds (8 OOS months 2025-11..2026-06), train strictly < test month
- identical folds/guards/selection for every variant (BASE / FLOW / FLOW_T1 / PLACEBO)
- placebo = flow feature block permuted across codes WITHIN each date (kills identity,
  keeps date-level distribution) — increment must vanish under placebo to be real
- realistic entry = scan-day close (production contract); flow t0 available post-close
  via provisional KIS data (lane scans after 15:40); t1 variant = strict d-1 robustness
- EV net of 0.3% round-trip cost; tail via forward 3d min-low
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

CACHE = os.path.expanduser("~/research_cache")
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow_increment_results.json")

ITF = ["day_ret", "or30_ret", "morning_ret", "afternoon_ret", "late30_ret", "day_range", "close_loc",
       "close_vwap", "up_min_frac", "intraday_vol", "accel", "gap", "vol_z"]
DLF = ["ret_1d", "ret_3d", "ret_5d", "ret_10d", "ret_20d", "ret_60d", "ma5_dist", "ma20_dist", "ma60_dist",
       "ma120_dist", "ma20_slope", "ma60_slope", "rsi14", "rsi_slope", "dist_hi20", "dist_hi60", "dist_lo20",
       "pos20", "bb_pctb", "atr_pct", "vol_ratio", "turn_z", "obv_slope", "cmf20", "idx_mom20", "idx_vol20"]
FLOWF = ["fr1", "or1", "fr5", "or5", "fr20", "or20", "fz20", "oz20", "fstreak", "ostreak", "smart5", "has_flow"]
COST = 0.3  # round-trip pct
TEST_MONTHS = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

GUARDS = {
    "KOSPI": {"min_liq": 100e8, "vwap": 0.0, "idx_vol_min": 8.0, "topn": 2},
    "KOSDAQ": {"min_liq": 30e8, "vwap": 0.0, "idx_vol_min": None, "topn": 2},
}


def build_flow_features(shift: int) -> pd.DataFrame:
    """shift=0: include day d (post-close provisional availability); shift=1: strict d-1."""
    f = pd.read_parquet(os.path.join(CACHE, "flow.parquet"))
    f["code"] = f["code"].astype(str).str.zfill(6)
    f["date"] = pd.to_datetime(f["date"])
    f = f.sort_values(["code", "date"]).reset_index(drop=True)
    g = f.groupby("code", group_keys=False)
    adv20 = g["acml_val"].apply(lambda s: s.rolling(20, min_periods=5).mean())
    fv, ov = f["frgn_val"], f["orgn_val"]
    out = pd.DataFrame({"code": f["code"], "date": f["date"]})
    out["fr1"] = fv / (adv20 + 1)
    out["or1"] = ov / (adv20 + 1)
    for w in (5, 20):
        fs = g["frgn_val"].apply(lambda s: s.rolling(w, min_periods=max(2, w // 4)).sum())
        os_ = g["orgn_val"].apply(lambda s: s.rolling(w, min_periods=max(2, w // 4)).sum())
        out[f"fr{w}"] = fs / (w * adv20 + 1)
        out[f"or{w}"] = os_ / (w * adv20 + 1)
    m20 = g["frgn_val"].apply(lambda s: s.rolling(20, min_periods=5).mean())
    s20 = g["frgn_val"].apply(lambda s: s.rolling(20, min_periods=5).std())
    out["fz20"] = (fv - m20) / (s20 + 1e-9)
    mo20 = g["orgn_val"].apply(lambda s: s.rolling(20, min_periods=5).mean())
    so20 = g["orgn_val"].apply(lambda s: s.rolling(20, min_periods=5).std())
    out["oz20"] = (ov - mo20) / (so20 + 1e-9)
    pos_f = (fv > 0).astype(int)
    pos_o = (ov > 0).astype(int)
    def streak(s):
        grp = (s == 0).cumsum()
        return s.groupby(grp).cumsum().clip(0, 10)
    out["fstreak"] = pos_f.groupby(f["code"]).apply(streak).reset_index(level=0, drop=True)
    out["ostreak"] = pos_o.groupby(f["code"]).apply(streak).reset_index(level=0, drop=True)
    out["smart5"] = out["fr5"] + out["or5"]
    feat_cols = [c for c in out.columns if c not in ("code", "date")]
    if shift > 0:
        out[feat_cols] = out.groupby("code")[feat_cols].shift(shift)
    out["has_flow"] = 1.0
    return out


def assemble() -> pd.DataFrame:
    P = pd.read_parquet(os.path.join(CACHE, "intraday_3d_panel.parquet"))
    P["code"] = P["code"].astype(str).str.zfill(6)
    P["date"] = pd.to_datetime(P["date"])
    px = pd.read_parquet(os.path.join(CACHE, "px_long.parquet"), columns=["code", "date", "liq"] + DLF)
    px["code"] = px["code"].astype(str).str.zfill(6)
    px["date"] = pd.to_datetime(px["date"])
    px = px.rename(columns={c: c + "_d" for c in DLF})
    P = P.merge(px, on=["code", "date"], how="left")
    # forward outcomes from ohlc_daily (close entry at d, 3 sessions)
    d = pd.read_parquet(os.path.join(CACHE, "ohlc_daily.parquet"))
    d["code"] = d["code"].astype(str).str.zfill(6)
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values(["code", "date"]).reset_index(drop=True)
    g = d.groupby("code")
    d["c3"] = g["close"].shift(-3)
    lo1 = g["low"].shift(-1); lo2 = g["low"].shift(-2); lo3 = g["low"].shift(-3)
    d["minlow3"] = pd.concat([lo1, lo2, lo3], axis=1).min(axis=1)
    d["ret3d"] = (d["c3"] / d["close"] - 1) * 100
    d["mae3"] = (d["minlow3"] / d["close"] - 1) * 100
    P = P.merge(d[["code", "date", "ret3d", "mae3"]], on=["code", "date"], how="left")
    return P


def run_variant(P: pd.DataFrame, name: str, feat: list, mkt: str, rng=None) -> dict:
    import lightgbm as lgb
    gd = GUARDS[mkt]
    dm = P[P["mkt"] == mkt].dropna(subset=ITF + ["y3"]).copy()
    monthly = []
    picks_all = []
    for tm in TEST_MONTHS:
        t0 = pd.Timestamp(tm + "-01")
        t1 = t0 + pd.offsets.MonthEnd(1)
        tr = dm[dm["date"] < t0]
        te = dm[(dm["date"] >= t0) & (dm["date"] <= t1)].copy()
        if len(tr) < 3000 or te.empty:
            continue
        Xtr = tr[feat].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
        Xte = te[feat].replace([np.inf, -np.inf], np.nan).clip(-1e4, 1e4).fillna(0)
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.04, num_leaves=31, min_child_samples=60,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1)
        m.fit(Xtr, tr["y3"])
        te["p"] = m.predict_proba(Xte)[:, 1]
        # guards + top-N per day
        q = te[(te["liq"] >= gd["min_liq"]) & (te["close_vwap"] >= gd["vwap"])]
        if gd["idx_vol_min"] is not None:
            q = q[q["idx_vol20_d"] >= gd["idx_vol_min"]]
        pk = q.sort_values("p", ascending=False).groupby("date", group_keys=False).head(gd["topn"])
        if pk.empty:
            monthly.append({"month": tm, "n": 0})
            continue
        monthly.append({
            "month": tm, "n": int(len(pk)),
            "hit": round(float(pk["y3"].mean()) * 100, 2),
            "ret3d": round(float(pk["ret3d"].mean()), 3) if pk["ret3d"].notna().any() else None,
            "mae3_avg": round(float(pk["mae3"].mean()), 3) if pk["mae3"].notna().any() else None,
        })
        picks_all.append(pk[["date", "code", "y3", "ret3d", "mae3", "p"]])
    pk = pd.concat(picks_all) if picks_all else pd.DataFrame()
    res = {"variant": name, "market": mkt, "monthly": monthly}
    if len(pk):
        r = pk["ret3d"].dropna()
        hits = [m_["hit"] for m_ in monthly if m_.get("n", 0) > 0 and m_.get("hit") is not None]
        # bootstrap CI on net EV over picked trades
        if len(r) >= 10:
            bs = [np.random.default_rng(s).choice(r.values, size=len(r), replace=True).mean() for s in range(500)]
            ci = (round(float(np.percentile(bs, 2.5)) - COST, 3), round(float(np.percentile(bs, 97.5)) - COST, 3))
        else:
            ci = None
        res.update({
            "n": int(len(pk)),
            "hit": round(float(pk["y3"].mean()) * 100, 2),
            "ret3d_avg": round(float(r.mean()), 3) if len(r) else None,
            "net_ev": round(float(r.mean()) - COST, 3) if len(r) else None,
            "net_ev_ci95": ci,
            "mae3_avg": round(float(pk["mae3"].dropna().mean()), 3) if pk["mae3"].notna().any() else None,
            "mae3_worst": round(float(pk["mae3"].dropna().min()), 3) if pk["mae3"].notna().any() else None,
            "monthly_hit_floor": round(min(hits), 2) if hits else None,
            "months_ge70": sum(1 for h in hits if h >= 70),
            "months_active": len(hits),
        })
    return res


def main():
    print("[assemble] panel + DLF + outcomes ...", flush=True)
    P = assemble()
    print(f"  rows={len(P)}  {P['date'].min().date()}..{P['date'].max().date()}", flush=True)
    print("[flow] building t0/t1 features ...", flush=True)
    fl0 = build_flow_features(0)
    fl1 = build_flow_features(1)

    P0 = P.merge(fl0, on=["code", "date"], how="left")
    P1 = P.merge(fl1, on=["code", "date"], how="left")
    for D in (P0, P1):
        D["has_flow"] = D["has_flow"].fillna(0.0)
    cov = P0[P0["liq"] >= 30e8]["has_flow"].mean()
    print(f"  flow coverage on liq>=30억 panel rows: {cov:.1%}", flush=True)

    # placebo: permute flow block across codes within each date (seed 0)
    PP = P0.copy()
    rng = np.random.default_rng(0)
    def perm(gr):
        idx = rng.permutation(len(gr))
        gr[FLOWF] = gr[FLOWF].values[idx]
        return gr
    PP = PP.groupby("date", group_keys=False).apply(perm)

    BASE = ITF + [c + "_d" for c in DLF]
    results = []
    for mkt in ("KOSPI", "KOSDAQ"):
        for name, D, feat in (
            ("BASE", P0, BASE),
            ("FLOW_t0", P0, BASE + FLOWF),
            ("FLOW_t1", P1, BASE + FLOWF),
            ("PLACEBO", PP, BASE + FLOWF),
        ):
            r = run_variant(D, name, feat, mkt)
            results.append(r)
            print(f"[{mkt} {name}] n={r.get('n')} hit={r.get('hit')}% ret3d={r.get('ret3d_avg')}% "
                  f"netEV={r.get('net_ev')} ci={r.get('net_ev_ci95')} floor={r.get('monthly_hit_floor')} "
                  f"({r.get('months_ge70')}/{r.get('months_active')} mo>=70) mae_avg={r.get('mae3_avg')}", flush=True)

    with open(OUT_JSON, "w") as fh:
        json.dump({"flow_coverage_liq30": round(float(cov), 4), "results": results}, fh, indent=1)
    print(f"[done] {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()
