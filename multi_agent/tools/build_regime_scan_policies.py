#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def _optimize_policy(sub: pd.DataFrame, min_samples: int) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for alpha_min in range(20, 81, 5):
        for ai_min in range(0, 71, 5):
            cand = sub[(sub["alpha_score"] >= alpha_min) & (sub["ai_prediction"] >= ai_min)]
            if len(cand) < min_samples:
                continue
            ret5 = pd.to_numeric(cand["return_5d"], errors="coerce").dropna()
            if ret5.empty:
                continue
            win5 = float((ret5 > 0).mean() * 100.0)
            avg5 = float(ret5.mean())
            samples = int(len(ret5))
            # Favor higher win/return, but penalize tiny sets.
            objective = (win5 * 0.55) + (avg5 * 5.0) + min(samples, 80) * 0.08
            rows.append(
                {
                    "alpha_min": alpha_min,
                    "ai_min": ai_min,
                    "samples": samples,
                    "win_5d_pct": win5,
                    "avg_5d_pct": avg5,
                    "objective": objective,
                }
            )

    if not rows:
        return {
            "mode": "avoid",
            "alpha_min": 999.0,
            "ai_min": 999.0,
            "samples": 0,
            "win_5d_pct": 0.0,
            "avg_5d_pct": -999.0,
            "objective": -999.0,
        }

    best = max(rows, key=lambda r: (r["objective"], r["avg_5d_pct"], r["win_5d_pct"], r["samples"]))
    if best["avg_5d_pct"] >= 5.0 and best["win_5d_pct"] >= 60.0:
        mode = "favorable"
    elif best["avg_5d_pct"] >= 0.0 and best["win_5d_pct"] >= 50.0:
        mode = "cautious"
    else:
        mode = "avoid"
    best["mode"] = mode
    return best


def build_policies(df: pd.DataFrame, min_samples: int) -> Dict[str, Any]:
    out: Dict[str, Dict[str, Any]] = {}
    summary: Dict[str, Dict[str, Any]] = {}

    for (market, regime), sub in df.groupby(["market", "regime"], dropna=False):
        if pd.isna(market) or pd.isna(regime):
            continue
        policy = _optimize_policy(sub.copy(), min_samples=min_samples)
        out.setdefault(str(market), {})[str(regime)] = policy
        summary.setdefault(str(market), {})[str(regime)] = {
            "mode": policy["mode"],
            "samples": policy["samples"],
            "avg_5d_pct": round(float(policy["avg_5d_pct"]), 2),
            "win_5d_pct": round(float(policy["win_5d_pct"]), 2),
            "alpha_min": float(policy["alpha_min"]),
            "ai_min": float(policy["ai_min"]),
        }

    return {
        "version": "2026-03-31-regime-scan-policy-v1",
        "source": "runtime_state/reports/external_signals/signals_rows_enriched.csv",
        "min_samples": min_samples,
        "policies": out,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build regime/market scan policies from enriched external signals CSV.")
    parser.add_argument("--enriched-csv", type=str, default="runtime_state/reports/external_signals/signals_rows_enriched.csv")
    parser.add_argument("--output", type=str, default="models/regime_scan_policies.json")
    parser.add_argument("--min-samples", type=int, default=20)
    args = parser.parse_args()

    df = pd.read_csv(args.enriched_csv)
    df["alpha_score"] = pd.to_numeric(df["alpha_score"], errors="coerce")
    df["ai_prediction"] = pd.to_numeric(df["ai_prediction"], errors="coerce").clip(lower=0, upper=100)
    payload = build_policies(df, min_samples=args.min_samples)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": payload["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
