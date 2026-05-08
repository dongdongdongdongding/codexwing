#!/usr/bin/env python3
"""Exit rule backtest for TP/SL/hold policy on archive learning dataset.

Simulates TP/SL/hold exit per ticker using max/min return within observed window.
Assumption: when both TP and SL would trigger, SL hits first (conservative).
Hold exit uses return_5d_pct when available, else return_close_pct/return_7d_pct.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import pandas as pd


ARCHIVE_PATH = Path(__file__).resolve().parents[2] / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"


def simulate_exit(row: pd.Series, tp_pct: float, sl_pct: float, hold_col: str) -> Optional[float]:
    max_ret = row.get("max_return_observed_pct")
    min_ret = row.get("min_return_observed_pct")
    hold_ret = row.get(hold_col)

    if pd.isna(max_ret) and pd.isna(min_ret) and pd.isna(hold_ret):
        return None

    sl_hit = (pd.notna(min_ret) and float(min_ret) <= sl_pct)
    tp_hit = (pd.notna(max_ret) and float(max_ret) >= tp_pct)

    if sl_hit and tp_hit:
        return float(sl_pct)
    if sl_hit:
        return float(sl_pct)
    if tp_hit:
        return float(tp_pct)
    if pd.notna(hold_ret):
        return float(hold_ret)
    return None


def summarize(df: pd.DataFrame, label: str, tp: float, sl: float, hold_col: str) -> dict:
    df = df.copy()
    df["exit_ret"] = df.apply(lambda r: simulate_exit(r, tp, sl, hold_col), axis=1)
    resolved = df.dropna(subset=["exit_ret"])
    if resolved.empty:
        return {"segment": label, "n": 0}
    wins = (resolved["exit_ret"] > 0).sum()
    n = len(resolved)
    return {
        "segment": label,
        "tp_pct": tp,
        "sl_pct": sl,
        "hold_col": hold_col,
        "n": int(n),
        "win_rate_pct": round(wins / n * 100, 2),
        "avg_return_pct": round(resolved["exit_ret"].mean(), 3),
        "median_return_pct": round(resolved["exit_ret"].median(), 3),
        "tp_hit_rate_pct": round((resolved["exit_ret"] >= tp).mean() * 100, 2),
        "sl_hit_rate_pct": round((resolved["exit_ret"] <= sl).mean() * 100, 2),
        "hold_exit_rate_pct": round(((resolved["exit_ret"] > sl) & (resolved["exit_ret"] < tp)).mean() * 100, 2),
    }


def run(strategies: list[str], tp: float, sl: float, hold_col: str, top_decision_only: bool) -> None:
    print(f"Loading archive: {ARCHIVE_PATH}")
    df = pd.read_csv(ARCHIVE_PATH, low_memory=False)
    print(f"Total rows: {len(df):,}")
    print(f"Columns present: min_return={('min_return_observed_pct' in df.columns)}, max_return={('max_return_observed_pct' in df.columns)}")

    results = []
    results.append(summarize(df, "ALL", tp, sl, hold_col))

    for strat in strategies:
        sub = df[df["strategy"].astype(str).str.contains(strat, case=False, na=False)]
        results.append(summarize(sub, f"strategy~{strat}", tp, sl, hold_col))

    if "market_type" in df.columns:
        for mt in ["KR", "US"]:
            sub = df[df["market_type"] == mt]
            results.append(summarize(sub, f"market={mt}", tp, sl, hold_col))

    if "market" in df.columns:
        for mk in ["KOSPI", "KOSDAQ", "NASDAQ", "AMEX"]:
            sub = df[df["market"] == mk]
            results.append(summarize(sub, f"market={mk}", tp, sl, hold_col))

    if top_decision_only and "decision" in df.columns:
        sub = df[df["decision"].isin(["BUY", "ACCUMULATE"])]
        results.append(summarize(sub, "decision=BUY/ACCUMULATE", tp, sl, hold_col))

    print("\n=== Exit rule backtest results ===")
    print(f"TP={tp:+.1f}% / SL={sl:+.1f}% / hold_col={hold_col}")
    print("-" * 100)
    for r in results:
        if r.get("n", 0) == 0:
            continue
        print(
            f"{r['segment']:<40} n={r['n']:>6} | "
            f"win={r.get('win_rate_pct', 0):>6.2f}% avg={r.get('avg_return_pct', 0):>+7.3f}% "
            f"| TP={r.get('tp_hit_rate_pct', 0):>5.2f}% SL={r.get('sl_hit_rate_pct', 0):>5.2f}% HOLD={r.get('hold_exit_rate_pct', 0):>5.2f}%"
        )

    out_path = Path(__file__).resolve().parents[2] / "runtime_state/reports/learning/exit_rule_backtest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"tp_pct": tp, "sl_pct": sl, "hold_col": hold_col, "results": results}, indent=2, ensure_ascii=False))
    print(f"\nReport saved: {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tp", type=float, default=12.0)
    ap.add_argument("--sl", type=float, default=-3.0)
    ap.add_argument("--hold-col", default="return_5d_pct")
    ap.add_argument("--strategies", nargs="*", default=["swing", "intraday"])
    ap.add_argument("--decision-top", action="store_true", default=True)
    args = ap.parse_args()
    run(args.strategies, args.tp, args.sl, args.hold_col, args.decision_top)


if __name__ == "__main__":
    main()
