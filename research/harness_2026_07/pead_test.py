#!/usr/bin/env python3
"""P3 US PEAD event study (swing-main-x1vj).

Events: earnings with surprise%, 2018-2026 (yfinance). Entry: AMC (>=16:00 ET) -> next
session OPEN; BMO (<=09:00) -> same-day OPEN; mid-day -> next session. Outcomes from the
8y panel raw OHLC (entry-day open anchored): 5d/20d close drift, +5%/+10% touch-exit/5d.
Controls: same-WEEK event-pool contrast (cross-sectional PEAD), surprise shuffle placebo
(within week), per-year table. Survivorship caveat applies to both sides of contrasts.
"""
import os, json, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.expanduser("~/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet")
EARN = os.path.expanduser("~/research_cache/us_daily/earnings_dates.parquet")
COST = 0.25


def main():
    ev = pd.read_parquet(EARN).dropna(subset=["surprise_pct"])
    ts = pd.to_datetime(ev["ann_ts"], errors="coerce", utc=True).dt.tz_convert("America/New_York")
    ev["ann_date"] = ts.dt.normalize().dt.tz_localize(None)
    ev["hour"] = ts.dt.hour
    ev = ev.dropna(subset=["ann_date"])
    ev = ev[ev["ann_date"] >= pd.Timestamp("2018-06-01")]
    print(f"events with surprise: {len(ev)} ({ev['symbol'].nunique()} syms, {ev['ann_date'].min().date()}..{ev['ann_date'].max().date()})", flush=True)

    cols = ["date", "symbol", "open", "high", "close", "liq20", "feature_ready"]
    px = pd.read_parquet(PANEL, columns=cols)
    px["date"] = pd.to_datetime(px["date"])
    px = px[px["liq20"] >= 2e7].sort_values(["symbol", "date"]).reset_index(drop=True)  # $20M ADV floor
    g = px.groupby("symbol")
    for k in range(0, 5):
        px[f"h{k}"] = g["high"].shift(-k)
    px["c4"] = g["close"].shift(-4)
    px["c19"] = g["close"].shift(-19)
    # entry session mapping: for each symbol, sessions sorted
    sess = {s: gg["date"].values for s, gg in px.groupby("symbol")}
    pxi = px.set_index(["symbol", "date"])

    rows = []
    for r in ev.itertuples():
        dates = sess.get(r.symbol)
        if dates is None:
            continue
        d = np.datetime64(r.ann_date)
        if r.hour >= 16:
            i = int(np.searchsorted(dates, d, side="right"))      # next session
        elif r.hour <= 9:
            i = int(np.searchsorted(dates, d, side="left"))       # same day if session exists
        else:
            i = int(np.searchsorted(dates, d, side="right"))
        if i >= len(dates):
            continue
        entry_day = pd.Timestamp(dates[i])
        if (entry_day - pd.Timestamp(r.ann_date)).days > 5:
            continue
        try:
            row = pxi.loc[(r.symbol, entry_day)]
        except KeyError:
            continue
        e = float(row["open"])
        if not np.isfinite(e) or e <= 0 or not np.isfinite(row["c4"]):
            continue
        # touch-exit t5/t10 within 5 sessions incl entry day
        def pol(tp):
            tgt = e * (1 + tp / 100)
            for k in range(0, 5):
                hi = row[f"h{k}"]
                if np.isfinite(hi) and hi >= tgt:
                    return (tgt / e - 1) * 100  # conservative fill at target
            return (float(row["c4"]) / e - 1) * 100
        rows.append({"symbol": r.symbol, "entry_day": entry_day, "surprise": float(r.surprise_pct),
                     "ret5": (float(row["c4"]) / e - 1) * 100,
                     "ret20": (float(row["c19"]) / e - 1) * 100 if np.isfinite(row["c19"]) else np.nan,
                     "pol5": pol(5.0), "pol10": pol(10.0)})
    E = pd.DataFrame(rows)
    E["week"] = E["entry_day"].dt.to_period("W")
    E["year"] = E["entry_day"].dt.year
    print(f"resolved events: {len(E)} | per week: {E.groupby('week').size().median():.0f}", flush=True)
    # within-week surprise quintiles (cross-sectional, min 10 events/week)
    wk_ok = E.groupby("week")["symbol"].transform("size") >= 10
    D = E[wk_ok].copy()
    D["sq"] = D.groupby("week")["surprise"].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False))
    rng = np.random.default_rng(0)
    D["sq_sh"] = D.groupby("week")["sq"].transform(lambda s: pd.Series(rng.permutation(s.values), index=s.index))
    print("\n== within-week surprise quintiles (net of week mean = cross-sectional drift) ==", flush=True)
    for col in ("ret5", "ret20", "pol10"):
        DD = D.dropna(subset=[col]).copy()
        DD["excess"] = DD[col] - DD.groupby("week")[col].transform("mean")
        t = DD.groupby("sq")["excess"].agg(["mean", "count"]).round(3)
        hi = DD[DD["sq"] == 4]; lo = DD[DD["sq"] == 0]
        yr = DD.groupby("year").apply(lambda x: x.loc[x["sq"] == 4, "excess"].mean() - x.loc[x["sq"] == 0, "excess"].mean()).dropna()
        hs = DD[DD["sq_sh"] == 4]; ls = DD[DD["sq_sh"] == 0]
        print(f" {col:6s} q0..q4 excess: {list(t['mean'])} | Q5-Q1={hi['excess'].mean()-lo['excess'].mean():+.2f} "
              f"| yrs+ {int((yr>0).sum())}/{len(yr)} | placebo Q5-Q1={hs['excess'].mean()-ls['excess'].mean():+.2f}", flush=True)
    # absolute deployable check: top-quintile positive surprise, policy EV
    print("\n== deployable check: sq==4 & surprise>0, absolute policy EV (net) ==", flush=True)
    S = D[(D["sq"] == 4) & (D["surprise"] > 0)]
    for col in ("pol5", "pol10", "ret5", "ret20"):
        ss = S.dropna(subset=[col]); net = ss[col] - COST
        if len(ss) < 100: continue
        yr = ss.groupby("year")[col].mean() - COST
        bs = [np.random.default_rng(x).choice(net.values, len(net), True).mean() for x in range(300)]
        dwk = ss.groupby("week")["symbol"].size().mean()
        print(f" {col:6s} n={len(ss):5d} win={(net>0).mean()*100:5.1f}% EV={net.mean():5.2f} CI=({np.percentile(bs,2.5):.2f},{np.percentile(bs,97.5):.2f}) ev/wk={dwk:.1f} yr+={int((yr>0).sum())}/{len(yr)}", flush=True)
    E.to_parquet(os.path.join(HERE, "pead_events.parquet"), index=False)


if __name__ == "__main__":
    main()
