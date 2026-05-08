#!/usr/bin/env python3
"""Validate ML inference / expected_return / regime instrumentation in archive.

Checks:
  1. ml_prob=50 constant fallback rate — should decrease after inference_failed fix.
  2. expected_return vs actual return correlation — should be positive (was -0.145).
  3. inference_failed column presence — requires Supabase schema migration + new scans.
  4. Regime flags (volatility_20d, breadth_pct) — require schema migration.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


ARCHIVE_PATH = Path(__file__).resolve().parents[2] / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"


def main() -> None:
    df = pd.read_csv(ARCHIVE_PATH, low_memory=False)
    total = len(df)
    print(f"Archive: {ARCHIVE_PATH.name} ({total:,} rows)")

    print("\n[1] ml_prob=50 fallback rate")
    if "ml_prob" in df.columns:
        const_50 = ((df["ml_prob"] >= 49.5) & (df["ml_prob"] <= 50.5)).sum()
        rate = const_50 / total * 100
        verdict = "OK" if rate < 2.0 else ("WARN" if rate < 10.0 else "FAIL")
        print(f"  ml_prob ~= 50: {const_50:,} / {total:,} ({rate:.2f}%) [{verdict}]")
        print(f"  (target: <2% once new scans dominate archive)")

    print("\n[2] expected_return vs return_3d_pct correlation")
    for er_col in ["expected_return_1d_pct", "expected_return_3d_pct"]:
        if er_col not in df.columns or "return_3d_pct" not in df.columns:
            continue
        sub = df.dropna(subset=[er_col, "return_3d_pct"])
        if len(sub) < 50:
            print(f"  {er_col}: n={len(sub)} (too few)")
            continue
        corr = sub[er_col].corr(sub["return_3d_pct"])
        verdict = "OK" if corr > 0.0 else "FAIL"
        print(f"  {er_col}: corr={corr:+.4f} (n={len(sub):,}) [{verdict}]")

    print("\n[3] inference_failed column")
    if "inference_failed" in df.columns:
        count = df["inference_failed"].fillna(False).astype(bool).sum()
        print(f"  present. inference_failed=True: {count:,} ({count/total*100:.2f}%)")
    else:
        print("  MISSING — requires Supabase schema migration (add_columns.sql) + new scans")

    print("\n[4] Regime flags")
    for col in ["regime_volatility_20d", "regime_breadth_pct", "kosdaq_chg", "target_tp_pct", "stop_sl_pct"]:
        if col in df.columns:
            nn = df[col].notna().sum()
            print(f"  {col}: present, non-null={nn:,}")
        else:
            print(f"  {col}: MISSING")

    print("\n[5] inference_failed planner downgrade (runtime_state/long_term/runs/agent_runs.jsonl)")
    runs_path = Path(__file__).resolve().parents[2] / "runtime_state/long_term/runs/agent_runs.jsonl"
    if not runs_path.exists():
        print(f"  {runs_path} not found")
        return
    import json
    ml_fail_count = 0
    downgrade_count = 0
    total_lines = 0
    with runs_path.open() as f:
        for line in f:
            total_lines += 1
            try:
                row = json.loads(line)
            except Exception:
                continue
            rationale = str(row.get("rationale") or "")
            risk = str(row.get("theme_risk") or "")
            if "ML_INFERENCE_FAILED" in rationale or "ML_INFERENCE_FAILED" in risk:
                ml_fail_count += 1
            if "ML_INFERENCE_FAILED_DOWNGRADE" in rationale:
                downgrade_count += 1
    print(f"  scanned {total_lines:,} runs")
    print(f"  ML_INFERENCE_FAILED mentions: {ml_fail_count:,}")
    print(f"  ML_INFERENCE_FAILED_DOWNGRADE events: {downgrade_count:,}")


if __name__ == "__main__":
    main()
