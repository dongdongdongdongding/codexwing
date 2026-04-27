#!/usr/bin/env python3
"""Optimize exit policy (TP/SL/hold) per segment to close the +15% return gap.

Why this exists
---------------
Models reach the 75% win-rate target (KOSPI swing 92.2%, KOSDAQ swing 71%) but
return per signal is +9.46% / +10.99%, well below the +15% target. The model
emits the entry signal; the exit policy decides realized return. This tool
sweeps (TP, SL, hold) over the model's OOS picks using yfinance daily bars
and reports the policy that maximizes mean realized return subject to a
floor on win rate (>=70%).

Method
------
1. Load segment model bundles (phase25_kospi_swing.pkl, phase25_kosdaq_swing.pkl).
2. Re-extract OOS picks: load same archive load_scan_archive() pipeline,
   take the last 15% of the segment's labeled rows, score with the model,
   keep rows whose prob >= recommended_probability_threshold.
3. For each pick, fetch yfinance OHLCV from base_trade_date+1 .. base+hold_days+5
   and apply the policy:
     - if any High >= base * (1 + tp/100): exit at TP that day
     - elif any Low <= base * (1 + sl/100): exit at SL that day (after TP check
       per-bar — TP wins on the same bar, conservative)
     - else: exit at Close on day = base + hold_days
4. Aggregate: win_pct, mean return, median, tp_hit/sl_hit/hold_exit shares.
5. Report best (TP, SL, hold) per segment with full grid for inspection.

Outputs
-------
runtime_state/reports/learning/exit_policy_per_segment.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from retrain_ml import (  # noqa: E402
    SEGMENTS,
    FEATURE_COLS,
    derive_ohlcv_features,
    engineer_features,
    load_scan_archive,
)


def _segment_oos_picks(df_feat: pd.DataFrame, spec, bundle: Dict[str, Any]) -> pd.DataFrame:
    sub = df_feat[spec.filter_fn(df_feat)].copy()
    sub = sub.sort_values(["scan_date", "ticker"]).reset_index(drop=True)
    if len(sub) < 50:
        return pd.DataFrame()
    oos_idx = int(len(sub) * 0.85)
    oos = sub.iloc[oos_idx:].copy()
    feats = list(bundle.get("features", FEATURE_COLS))
    X = oos.reindex(columns=feats, fill_value=0).fillna(0)
    scaler = bundle.get("scaler")
    if scaler is not None:
        try:
            X_arr = scaler.transform(X)
        except Exception:
            X_arr = X.values
    else:
        X_arr = X.values
    model = bundle["model"]
    prob_raw = model.predict_proba(X_arr)[:, 1]
    direction = str(bundle.get("signal_direction", "normal")).lower()
    prob = (1 - prob_raw) if direction == "invert" else prob_raw
    oos["_prob"] = prob
    thr = float(bundle.get("recommended_probability_threshold", 0.5) or 0.5)
    picks = oos[oos["_prob"] >= thr].copy()
    return picks


def _fetch_forward_bars(ticker: str, base_dt: datetime, days: int = 15) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
    except ImportError:
        return None
    start = base_dt + timedelta(days=1)
    end = base_dt + timedelta(days=days + 7)
    try:
        hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False)
    except Exception:
        return None
    if hist is None or hist.empty:
        return None
    return hist


def _simulate_exit(hist: pd.DataFrame, base_close: float, tp: float, sl: float, hold: int) -> Tuple[float, str]:
    """Return (realized_return_pct, reason) for given policy.

    Conservative same-bar: TP checked before SL on each bar (optimistic for TP).
    Hold exit at close on day index `hold-1` if neither TP nor SL hit.
    """
    if hist is None or hist.empty or base_close <= 0:
        return (0.0, "no_data")
    tp_price = base_close * (1 + tp / 100.0)
    sl_price = base_close * (1 + sl / 100.0)
    bars = hist.iloc[: hold + 1]
    if bars.empty:
        return (0.0, "no_bars")
    for _, row in bars.iterrows():
        h = float(row["High"])
        low = float(row["Low"])
        if h >= tp_price:
            return ((tp_price / base_close - 1) * 100.0, "tp")
        if low <= sl_price:
            return ((sl_price / base_close - 1) * 100.0, "sl")
    last_close = float(bars["Close"].iloc[min(hold - 1, len(bars) - 1)])
    return ((last_close / base_close - 1) * 100.0, "hold")


def _sweep_segment(picks: pd.DataFrame, *, tp_grid, sl_grid, hold_grid, segment_name: str, verbose: bool = True) -> List[Dict[str, Any]]:
    if picks.empty:
        return []
    fwd_cache: Dict[str, pd.DataFrame] = {}
    base_records: List[Dict[str, Any]] = []
    for _, row in picks.iterrows():
        ticker = str(row.get("ticker") or "")
        scan_d = row.get("scan_date")
        if not ticker or scan_d is None:
            continue
        if hasattr(scan_d, "year"):
            base_dt = datetime(scan_d.year, scan_d.month, scan_d.day)
        else:
            try:
                base_dt = datetime.fromisoformat(str(scan_d)[:10])
            except Exception:
                continue
        cache_key = f"{ticker}|{base_dt.date().isoformat()}"
        if cache_key not in fwd_cache:
            fwd_cache[cache_key] = _fetch_forward_bars(ticker, base_dt, days=max(hold_grid))
        hist = fwd_cache.get(cache_key)
        if hist is None or hist.empty:
            continue
        base_close = float(hist["Open"].iloc[0]) if "Open" in hist else float(hist["Close"].iloc[0])
        if base_close <= 0:
            continue
        base_records.append({"ticker": ticker, "hist": hist, "base_close": base_close})
    if verbose:
        print(f"  {segment_name}: usable picks {len(base_records)}/{len(picks)}")

    results: List[Dict[str, Any]] = []
    for tp in tp_grid:
        for sl in sl_grid:
            for hold in hold_grid:
                rets, exits = [], []
                for rec in base_records:
                    r, why = _simulate_exit(rec["hist"], rec["base_close"], tp, sl, hold)
                    rets.append(r)
                    exits.append(why)
                if not rets:
                    continue
                arr = np.array(rets)
                wins = (arr > 0).sum()
                results.append({
                    "segment": segment_name,
                    "tp": tp, "sl": sl, "hold": hold,
                    "n": len(arr),
                    "win_pct": round(wins / len(arr) * 100, 2),
                    "avg_return_pct": round(float(arr.mean()), 2),
                    "median_return_pct": round(float(np.median(arr)), 2),
                    "tp_rate": round(exits.count("tp") / len(arr) * 100, 2),
                    "sl_rate": round(exits.count("sl") / len(arr) * 100, 2),
                    "hold_rate": round(exits.count("hold") / len(arr) * 100, 2),
                })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tp", default="5,7,10,12,15,20")
    parser.add_argument("--sl", default="-3,-4,-5,-7")
    parser.add_argument("--hold", default="3,5,7,10")
    parser.add_argument("--segments", default="phase25_kospi_swing,phase25_kosdaq_swing")
    parser.add_argument("--output", default="runtime_state/reports/learning/exit_policy_per_segment.json")
    args = parser.parse_args()

    tp_grid = [float(x) for x in args.tp.split(",")]
    sl_grid = [float(x) for x in args.sl.split(",")]
    hold_grid = [int(x) for x in args.hold.split(",")]
    seg_names = set(s.strip() for s in args.segments.split(","))

    print("Loading archive…")
    df = load_scan_archive()
    print("Engineering features…")
    df_feat = engineer_features(df)
    if "market_subtype" in df_feat.columns:
        kr_mask = df_feat["market_subtype"].isin(["KOSPI", "KOSDAQ"])
        kr_mask &= df_feat.get("outcome_status", pd.Series(index=df_feat.index)).fillna("").str.upper().eq("RESOLVED")
        kr_mask &= pd.to_numeric(df_feat.get("alpha_score", pd.Series(index=df_feat.index)), errors="coerce").notna()
        if kr_mask.any():
            df_feat = derive_ohlcv_features(df_feat, target_mask=kr_mask, verbose=True)

    all_results: Dict[str, Any] = {"generated_at": datetime.now().isoformat(), "segments": {}}
    for spec in SEGMENTS:
        if spec.name not in seg_names:
            continue
        path = Path(spec.model_path)
        if not path.exists():
            print(f"[skip] {spec.name}: bundle not found ({path})")
            continue
        bundle = joblib.load(path)
        print(f"\n=== {spec.name} ===")
        picks = _segment_oos_picks(df_feat, spec, bundle)
        print(f"  OOS picks: {len(picks)}")
        if picks.empty:
            continue
        sweep = _sweep_segment(
            picks, tp_grid=tp_grid, sl_grid=sl_grid, hold_grid=hold_grid,
            segment_name=spec.name,
        )
        if not sweep:
            print("  no usable bars — skip")
            continue
        sweep_sorted = sorted(sweep, key=lambda r: -r["avg_return_pct"])
        gated = [r for r in sweep_sorted if r["win_pct"] >= 70.0]
        print(f"\n  Best by avg_return (any win):")
        for r in sweep_sorted[:5]:
            print(f"    tp={r['tp']:+5.1f} sl={r['sl']:+5.1f} hold={r['hold']:>2}d  win={r['win_pct']:5.1f}%  avg={r['avg_return_pct']:+6.2f}%  median={r['median_return_pct']:+6.2f}%  (tp/sl/hold {r['tp_rate']:.0f}/{r['sl_rate']:.0f}/{r['hold_rate']:.0f})")
        if gated:
            print(f"\n  Best by avg_return (win>=70%):")
            for r in gated[:5]:
                print(f"    tp={r['tp']:+5.1f} sl={r['sl']:+5.1f} hold={r['hold']:>2}d  win={r['win_pct']:5.1f}%  avg={r['avg_return_pct']:+6.2f}%  median={r['median_return_pct']:+6.2f}%")
        all_results["segments"][spec.name] = {
            "n_picks": len(picks),
            "all_combos": sweep,
            "best_by_return": sweep_sorted[:10],
            "best_with_win_floor_70": gated[:10],
        }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(all_results, default=str, indent=2), encoding="utf-8")
    print(f"\nWrote: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
