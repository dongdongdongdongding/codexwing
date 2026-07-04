#!/usr/bin/env python3
"""Daily retrainer for the KOSDAQ 15:00 VWAP-guard bundle (swing-main-67zc, P1-H2).

Evidence (15:00 panel, 8 OOS months): the static bundle decays — win 65.5%, EV CI incl 0,
its calibrator rarely clears p_cal 0.75 on future months (the zero-pick days). Monthly
retraining restores win 71.2% / EV 2.85 CI(0.65,4.80) at p_cal>=0.70 with 3 picks/week.

Rebuilds the 15:00 panel with the PRODUCTION feature functions (compute_pre_entry_features /
compute_daily_prev_context) from the daily-refreshed minute cache + ohlc_daily + px_long,
refits LGBM + isotonic, and atomically swaps the bundle (previous kept as .bak).
selection_policy.min_calibrated_probability set to 0.70 per the frontier evidence.

  python3 multi_agent/tools/train_kosdaq_1500_bundle.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from modules.kosdaq_intraday_vwap_guard import compute_pre_entry_features, compute_daily_prev_context

CACHE = Path(os.path.expanduser("~/research_cache"))
BUNDLE = PROJECT_ROOT / "models" / "kr_intraday_3d_t5" / "kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl"
REPORT = PROJECT_ROOT / "runtime_state" / "reports" / "learning" / "kosdaq_1500_bundle_retrain_latest.json"
MIN_LIQ_EOK = 30.0
MIN_PCAL = 0.70   # P1 frontier: 3.0 picks/wk, win 71.2%, EV 2.85 CI(0.65,4.80)


def build_panel() -> pd.DataFrame:
    px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "market", "liq", "idx_mom20", "idx_vol20"])
    px["code"] = px["code"].astype(str).str.zfill(6)
    px["date"] = pd.to_datetime(px["date"])
    kq = px[px["market"] == "KOSDAQ"]
    liq_map = kq.set_index(["code", "date"])["liq"]
    idx_map = kq.drop_duplicates("date").set_index("date")[["idx_mom20", "idx_vol20"]]
    ohlc = pd.read_parquet(CACHE / "ohlc_daily.parquet")
    ohlc["code"] = ohlc["code"].astype(str).str.zfill(6)
    ohlc["date"] = pd.to_datetime(ohlc["date"])
    ohlc = ohlc.sort_values(["code", "date"])
    og = {c: g.reset_index(drop=True) for c, g in ohlc.groupby("code")}
    codes = sorted(set(kq["code"].unique()) & set(og.keys()))
    rows = []
    t0 = time.time()
    for code in codes:
        fp = CACHE / "intraday" / f"{code}.parquet"
        if not fp.exists():
            continue
        try:
            m = pd.read_parquet(fp)
        except Exception:
            continue
        m.index = pd.to_datetime(m.index)
        tt = m.index.time
        m = m[(tt >= pd.Timestamp("09:00").time()) & (tt <= pd.Timestamp("15:30").time())]
        if m.empty:
            continue
        m["_d"] = m.index.normalize()
        dd = og[code]
        dframe = dd.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}).copy()
        dframe["Volume"] = 0.0
        dframe = dframe.set_index("date")
        didx = {d: i for i, d in enumerate(dd["date"])}
        for day, g in m.groupby("_d"):
            i = didx.get(day)
            if i is None or i == 0 or len(g) < 60:
                continue
            liq_prev = liq_map.get((code, dd["date"].iloc[i - 1]), np.nan)
            if not np.isfinite(liq_prev) or liq_prev < MIN_LIQ_EOK * 1e8:
                continue
            tstr = day.strftime("%Y%m%d")
            try:
                idxrow = idx_map.loc[day] if day in idx_map.index else None
                ctx = compute_daily_prev_context(
                    dframe.loc[:day], trade_date=tstr,
                    index_context={"idx_mom20_prev": (float(idxrow["idx_mom20"]) if idxrow is not None else None),
                                   "idx_vol20_prev": (float(idxrow["idx_vol20"]) if idxrow is not None else None)})
                feat = compute_pre_entry_features(g, prev_close=float(dd["close"].iloc[i - 1]),
                                                  liq_prev_eok=liq_prev / 1e8, trade_date=tstr)
            except Exception:
                continue
            if not isinstance(feat, dict) or feat.get("entry_reference_price") is None:
                continue
            entry = float(feat["entry_reference_price"])
            if entry <= 0:
                continue
            fut = dd.iloc[i + 1:i + 4]
            if len(fut) < 3:
                continue
            rec = {"code": code, "date": day,
                   "touch3d_t5": 1.0 if float(fut["high"].max()) >= entry * 1.05 else 0.0}
            rec.update({k: v for k, v in ctx.items() if isinstance(v, (int, float))})
            rec.update({k: v for k, v in feat.items() if isinstance(v, (int, float))})
            rows.append(rec)
    P = pd.DataFrame(rows)
    print(f"[panel] rows={len(P)} codes={P['code'].nunique() if len(P) else 0} ({time.time()-t0:.0f}s)", flush=True)
    return P


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    import joblib
    import lightgbm as lgb
    from sklearn.isotonic import IsotonicRegression

    old = joblib.load(BUNDLE)
    feats = old["features"]
    lgbp = {k: v for k, v in (old.get("lgbm_params") or {}).items() if k not in ("random_state", "verbose")}
    P = build_panel()
    # fill the two volume-context features from px_long (ohlc_daily lacks volume)
    px = pd.read_parquet(CACHE / "px_long.parquet", columns=["code", "date", "vol_ratio", "vol_trend"])
    px["code"] = px["code"].astype(str).str.zfill(6)
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["code", "date"])
    g = px.groupby("code")
    px["vol_ratio_prev"] = g["vol_ratio"].shift(1)
    px["vol_trend_prev"] = g["vol_trend"].shift(1)
    P = P.merge(px[["code", "date", "vol_ratio_prev", "vol_trend_prev"]], on=["code", "date"], how="left")
    d = P.dropna(subset=["touch3d_t5"]).sort_values("date")
    if len(d) < 10000:
        print(json.dumps({"error": f"panel too small ({len(d)}) — bundle kept"}))
        return
    X = d[feats].fillna(0).values
    y = d["touch3d_t5"].values
    ncut = int(len(d) * 0.85)
    m = lgb.LGBMClassifier(**lgbp, random_state=0, verbose=-1)
    m.fit(X[:ncut], y[:ncut])
    iso = IsotonicRegression(out_of_bounds="clip").fit(m.predict_proba(X[ncut:])[:, 1], y[ncut:])
    val_pcal = iso.predict(m.predict_proba(X[ncut:])[:, 1])
    mf = lgb.LGBMClassifier(**lgbp, random_state=0, verbose=-1)
    mf.fit(X, y)
    new = dict(old)
    new["model"] = mf
    new["calibrator"] = iso
    new["model_version"] = f"kosdaq_liq30_1500_lgbm_isotonic_vwapguard_daily_{datetime.now().strftime('%Y%m%d')}"
    new["created_from"] = "train_kosdaq_1500_bundle.py (daily retrain, P1-H2 swing-main-67zc)"
    pol = dict(new.get("selection_policy") or {})
    pol["min_calibrated_probability"] = MIN_PCAL
    new["selection_policy"] = pol
    new["validation"] = {
        "retrained_at": datetime.now(timezone.utc).isoformat(),
        "train_rows": int(len(d)), "train_span": f"{d['date'].min().date()}..{d['date'].max().date()}",
        "val_pcal_ge_070_frac": round(float((val_pcal >= 0.70).mean()), 4),
        "basis": "P1 frontier (8 OOS mo): monthly-retrain pcal>=0.70 -> win 71.2%, EV 2.85 CI(0.65,4.80), "
                 "3.0 picks/wk vs static bundle win 65.5%/EV CI incl 0 (RESEARCH_LOG P1)"}
    if args.dry_run:
        print(json.dumps({"dry_run": True, "train_rows": len(d), "span": new["validation"]["train_span"]}))
        return
    shutil.copy2(BUNDLE, str(BUNDLE) + ".bak")
    tmp = str(BUNDLE) + ".tmp"
    joblib.dump(new, tmp)
    os.replace(tmp, BUNDLE)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(new["validation"], indent=2), encoding="utf-8")
    print(json.dumps({"retrained": True, **new["validation"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
