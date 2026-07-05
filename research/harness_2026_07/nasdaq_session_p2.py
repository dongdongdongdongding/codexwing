#!/usr/bin/env python3
"""P2: NASDAQ session-tape ranker (hourly, ~2y) — the KR-ITF analog (swing-main-x1vj).

Session features per (symbol, day) from regular-session hourly bars; daily context merged
from the 8y panel; contract = close(t) entry -> +5%/+10% touch within 5 sessions else 5d close.
Gates (§12-A lesson: US placebo first): label-shuffle placebo, same-day pool contrast,
monthly walk-forward on ~18 usable months. Thin-window caveat applies (single regime-ish).
"""
import os, glob, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
HOURD = os.path.expanduser("~/research_cache/us_daily/hourly")
PANEL = os.path.expanduser("~/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet")
COST = 0.25
DLF = ["ret_1d", "ret_3d", "ret_5d", "ret_10d", "ret_20d", "ret_60d", "ma5_dist", "ma20_dist", "ma60_dist",
       "ma200_dist", "ma20_slope", "ma60_slope", "rsi14", "rsi_slope", "dist_hi20", "dist_hi60", "dist_lo20",
       "pos20", "bb_pctb", "atr_pct", "vol_ratio", "turn_z", "obv_slope", "cmf20", "gap", "liq20"]
STF = ["s_day_ret", "s_h1_ret", "s_last_ret", "s_close_loc", "s_range", "s_vwap_dist", "s_up_frac", "s_accel", "s_vol_z"]


def session_features():
    rows = []
    files = sorted(glob.glob(os.path.join(HOURD, "*.parquet")))
    print(f"hourly files: {len(files)}", flush=True)
    for fp in files:
        sym = os.path.basename(fp).replace(".parquet", "")
        try:
            h = pd.read_parquet(fp)
        except Exception:
            continue
        if h.empty or "Close" not in h.columns:
            continue
        h.index = pd.to_datetime(h.index)
        try:
            h.index = h.index.tz_convert("America/New_York")
        except Exception:
            pass
        tt = h.index.time
        h = h[(tt >= pd.Timestamp("09:30").time()) & (tt <= pd.Timestamp("16:00").time())]
        h["_d"] = h.index.normalize().tz_localize(None)
        volhist = h.groupby("_d")["Volume"].sum()
        for day, g in h.groupby("_d"):
            if len(g) < 5:
                continue
            o = float(g["Open"].iloc[0]); c = float(g["Close"].iloc[-1])
            hi = float(g["High"].max()); lo = float(g["Low"].min())
            if o <= 0 or c <= 0:
                continue
            v = g["Volume"].values.astype(float)
            vwap = float((g["Close"].values * v).sum() / (v.sum() + 1))
            r = g["Close"].pct_change().dropna()
            vh = volhist.loc[:day].iloc[-21:-1]
            vz = float((v.sum() - vh.mean()) / (vh.std() + 1e-9)) if len(vh) >= 5 else 0.0
            h1 = float(g["Close"].iloc[0])
            pm = float(g["Close"].iloc[len(g) // 2])
            rows.append({"symbol": sym, "date": day,
                         "s_day_ret": (c / o - 1) * 100, "s_h1_ret": (h1 / o - 1) * 100,
                         "s_last_ret": (c / float(g["Close"].iloc[-2]) - 1) * 100 if len(g) >= 2 else 0.0,
                         "s_close_loc": (c - lo) / (hi - lo + 1e-9), "s_range": (hi / lo - 1) * 100,
                         "s_vwap_dist": (c / vwap - 1) * 100, "s_up_frac": float((r > 0).mean()),
                         "s_accel": ((c / pm - 1) - (pm / o - 1)) * 100, "s_vol_z": vz})
    return pd.DataFrame(rows)


def main():
    import lightgbm as lgb
    S = session_features()
    print(f"session rows: {len(S)} ({S['symbol'].nunique()} syms, {S['date'].min().date()}..{S['date'].max().date()})", flush=True)
    cols = ["date", "symbol", "open", "high", "close", "ft_5_5"] + DLF
    px = pd.read_parquet(PANEL, columns=list(dict.fromkeys(cols)))
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["symbol", "date"]).reset_index(drop=True)
    g = px.groupby("symbol")
    for k in range(1, 6):
        px[f"h{k}"] = g["high"].shift(-k)
        px[f"o{k}"] = g["open"].shift(-k)
    px["c5"] = g["close"].shift(-5)
    D = S.merge(px, on=["symbol", "date"], how="inner")
    print(f"merged: {len(D)}", flush=True)

    def pol(target):
        e = D["close"].values
        ok = np.isfinite(e) & (e > 0) & np.isfinite(D["c5"].values)
        tgt = e * (1 + target / 100)
        out = np.full(len(D), np.nan); done = np.zeros(len(D), dtype=bool)
        for k in range(1, 6):
            hi = D[f"h{k}"].values; op = D[f"o{k}"].values
            hit = ok & ~done & np.isfinite(hi) & (hi >= tgt)
            fill = np.where(np.isfinite(op) & (op > 0), np.maximum(tgt, op), tgt)
            out[hit] = (fill[hit] / e[hit] - 1) * 100
            done |= hit
        rest = ok & ~done
        out[rest] = (D["c5"].values[rest] / e[rest] - 1) * 100
        return out
    D["pol5"] = pol(5.0); D["pol10"] = pol(10.0)
    # label: +5% touch within 5 sessions from close entry (race vs -5 not available cheaply; use panel ft_5_5 as proxy label)
    d = D.dropna(subset=["ft_5_5"] + STF).sort_values("date").copy()
    FEAT = STF + DLF
    months = sorted(d["date"].dt.to_period("M").unique())
    rng = np.random.default_rng(0)
    pools = []
    for tm in months[6:]:
        t0, t1 = tm.start_time, tm.end_time
        tr = d[d["date"] < t0]; te = d[(d["date"] >= t0) & (d["date"] <= t1)].copy()
        if len(tr) < 15000 or te.empty:
            continue
        X = tr[FEAT].clip(-1e6, 1e6)
        m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=60,
                               subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1)
        m.fit(X, tr["ft_5_5"])
        te["p"] = m.predict_proba(te[FEAT].clip(-1e6, 1e6))[:, 1]
        mp = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=60,
                                subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=1, verbose=-1)
        mp.fit(X, rng.permutation(tr["ft_5_5"].values))
        te["p_plc"] = mp.predict_proba(te[FEAT].clip(-1e6, 1e6))[:, 1]
        # DLF-only ablation (does the session tape add anything?)
        md = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=60,
                                subsample=0.8, colsample_bytree=0.7, reg_lambda=3, random_state=0, verbose=-1)
        md.fit(tr[DLF].clip(-1e6, 1e6), tr["ft_5_5"])
        te["p_dlf"] = md.predict_proba(te[DLF].clip(-1e6, 1e6))[:, 1]
        pools.append(te[["date", "symbol", "p", "p_plc", "p_dlf", "ft_5_5", "pol5", "pol10"]].assign(month=str(tm)))
        print(f"[{tm}] pool={len(te)}", flush=True)
    A = pd.concat(pools, ignore_index=True)
    print(f"\n== frontier (net {COST}) ==", flush=True)
    for score in ("p", "p_dlf", "p_plc"):
        for k in (1, 3):
            s = A.sort_values(score, ascending=False).groupby("date", group_keys=False).head(k)
            for polcol in ("pol5", "pol10"):
                ss = s.dropna(subset=[polcol]); net = ss[polcol] - COST
                if len(ss) < 100:
                    continue
                mo = ss.groupby("month")[polcol].mean() - COST
                bs = [np.random.default_rng(x).choice(net.values, len(net), True).mean() for x in range(300)]
                pool_same = A[A["date"].isin(ss["date"].unique())].dropna(subset=[polcol])
                skill = float(net.mean() - (pool_same[polcol] - COST).mean())
                print(f" {score:6s} k={k} {polcol:5s} n={len(ss):4d} win={(net>0).mean()*100:5.1f}% EV={net.mean():5.2f} "
                      f"CI=({np.percentile(bs,2.5):.2f},{np.percentile(bs,97.5):.2f}) skill={skill:+.2f} negMo={int((mo<0).sum())}/{mo.nunique() if hasattr(mo,'nunique') else len(mo)}", flush=True)


if __name__ == "__main__":
    main()
