#!/usr/bin/env python3
"""TP/SL parameter sweep on archive dataset.

Answers: what TP/SL/hold combination on archive data yields 75% win / 15% return?
Segments by scanner_timeframe_profile (swing vs intraday), decision bucket, and market.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ARCHIVE_PATH = Path(__file__).resolve().parents[2] / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"


def simulate(df: pd.DataFrame, tp: float, sl: float, hold_col: str) -> dict:
    max_ret = df["max_return_observed_pct"]
    min_ret = df["min_return_observed_pct"]
    hold_ret = df[hold_col] if hold_col in df.columns else pd.Series([float("nan")] * len(df))

    resolved_mask = max_ret.notna() | min_ret.notna() | hold_ret.notna()
    sub = df[resolved_mask].copy()
    if sub.empty:
        return {"n": 0}

    max_r = sub["max_return_observed_pct"]
    min_r = sub["min_return_observed_pct"]
    hold_r = sub[hold_col] if hold_col in sub.columns else pd.Series([float("nan")] * len(sub))

    sl_hit = min_r.notna() & (min_r <= sl)
    tp_hit = max_r.notna() & (max_r >= tp)

    exit_ret = pd.Series(index=sub.index, dtype=float)
    exit_ret[sl_hit] = sl
    tp_only = tp_hit & ~sl_hit
    exit_ret[tp_only] = tp
    hold_only = ~sl_hit & ~tp_hit & hold_r.notna()
    exit_ret[hold_only] = hold_r[hold_only]

    exit_ret = exit_ret.dropna()
    if exit_ret.empty:
        return {"n": 0}
    n = len(exit_ret)
    return {
        "n": int(n),
        "win_pct": round((exit_ret > 0).mean() * 100, 2),
        "avg": round(exit_ret.mean(), 3),
        "median": round(exit_ret.median(), 3),
        "tp_rate": round((exit_ret >= tp).mean() * 100, 2),
        "sl_rate": round((exit_ret <= sl).mean() * 100, 2),
        "hold_rate": round(((exit_ret > sl) & (exit_ret < tp)).mean() * 100, 2),
    }


def sweep(df: pd.DataFrame, label: str, tp_grid, sl_grid, hold_col: str) -> list[dict]:
    rows = []
    for tp in tp_grid:
        for sl in sl_grid:
            r = simulate(df, tp, sl, hold_col)
            if r.get("n", 0) == 0:
                continue
            r.update({"segment": label, "tp": tp, "sl": sl})
            rows.append(r)
    return rows


def print_table(rows: list[dict]) -> None:
    if not rows:
        print("(no rows)")
        return
    print(f"{'segment':<30} {'tp':>5} {'sl':>5} {'n':>7} {'win%':>7} {'avg%':>8} {'TP%':>6} {'SL%':>6} {'HOLD%':>6}")
    print("-" * 90)
    for r in rows:
        print(
            f"{r['segment']:<30} {r['tp']:>+5.1f} {r['sl']:>+5.1f} {r['n']:>7} "
            f"{r['win_pct']:>6.2f}% {r['avg']:>+7.3f}% {r['tp_rate']:>5.1f}% {r['sl_rate']:>5.1f}% {r['hold_rate']:>5.1f}%"
        )


def main() -> None:
    df = pd.read_csv(ARCHIVE_PATH, low_memory=False)
    print(f"Total rows: {len(df):,}")

    swing_df = df[df["scanner_timeframe_profile"].astype(str).isin(["DAILY_PRIMARY", "DAILY_PRIMARY_WITH_1H_REFRESH"])].copy()
    intraday_df = df[df["scanner_timeframe_profile"].astype(str) == "INTRADAY_1H"].copy()
    print(f"swing rows={len(swing_df):,}, intraday rows={len(intraday_df):,}")

    top_swing_kr = swing_df[(swing_df["market_type"] == "KR") & (swing_df["decision"].isin(["PRIORITY_WATCHLIST", "EXCEPTION_LEADER"]))]
    top_swing_us = swing_df[(swing_df["market_type"] == "US") & (swing_df["decision"].isin(["PRIORITY_WATCHLIST", "EXCEPTION_LEADER"]))]
    top_intraday_kr = intraday_df[(intraday_df["market_type"] == "KR") & (intraday_df["decision"].isin(["PRIORITY_WATCHLIST", "EXCEPTION_LEADER"]))]
    print(f"top-picks: swing_KR={len(top_swing_kr):,}, swing_US={len(top_swing_us):,}, intraday_KR={len(top_intraday_kr):,}")

    print("\n### Swing KR — 5d hold")
    rows = sweep(
        top_swing_kr,
        "SWING_KR_TOP",
        tp_grid=[8.0, 10.0, 12.0, 15.0, 20.0],
        sl_grid=[-3.0, -5.0, -7.0, -10.0, -15.0],
        hold_col="return_5d_pct",
    )
    print_table(rows)

    print("\n### Swing US — 5d hold")
    rows_us = sweep(
        top_swing_us,
        "SWING_US_TOP",
        tp_grid=[8.0, 12.0, 15.0, 20.0],
        sl_grid=[-3.0, -5.0, -7.0, -10.0],
        hold_col="return_5d_pct",
    )
    print_table(rows_us)

    print("\n### Intraday KR — close hold")
    rows_id = sweep(
        top_intraday_kr,
        "INTRADAY_KR_TOP",
        tp_grid=[2.0, 3.0, 3.5, 5.0, 7.0],
        sl_grid=[-1.5, -2.0, -3.0, -5.0],
        hold_col="return_close_pct",
    )
    print_table(rows_id)

    print("\n### Swing KR — ALL decisions (baseline — current prod)")
    rows_all = sweep(
        swing_df[swing_df["market_type"] == "KR"],
        "SWING_KR_ALL",
        tp_grid=[12.0],
        sl_grid=[-3.0, -5.0, -7.0, -10.0],
        hold_col="return_5d_pct",
    )
    print_table(rows_all)

    out = {
        "swing_kr_top": rows,
        "swing_us_top": rows_us,
        "intraday_kr_top": rows_id,
        "swing_kr_all": rows_all,
    }
    out_path = Path(__file__).resolve().parents[2] / "runtime_state/reports/learning/exit_rule_sweep.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
