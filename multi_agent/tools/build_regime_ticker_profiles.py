#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd


def build_profiles(
    df: pd.DataFrame,
    ticker_policy_df: pd.DataFrame,
    min_signals: int,
    min_win_5d: float,
    min_avg_5d: float,
) -> Dict[str, Any]:
    profiles: Dict[str, Dict[str, Dict[str, Any]]] = {}
    selected_counts: Dict[str, Dict[str, int]] = {}
    policy_map = (
        ticker_policy_df.set_index("ticker")[
            [
                "adaptive_stop_pct",
                "safe_take_profit_pct",
                "risk_reward_ratio",
            ]
        ].to_dict("index")
        if not ticker_policy_df.empty
        else {}
    )

    grouped = df.groupby(["market", "regime", "ticker", "stock_name"], dropna=False)
    for (market, regime, ticker, stock_name), sub in grouped:
        if pd.isna(market) or pd.isna(regime) or pd.isna(ticker):
            continue
        signals = int(len(sub))
        ret1 = pd.to_numeric(sub["return_1d"], errors="coerce")
        ret3 = pd.to_numeric(sub["return_3d"], errors="coerce")
        ret5 = pd.to_numeric(sub["return_5d"], errors="coerce")
        if ret5.dropna().empty:
            continue

        policy = policy_map.get(str(ticker).upper(), {}) or policy_map.get(str(ticker), {})
        payload = {
            "ticker": str(ticker).upper(),
            "stock_name": stock_name,
            "signals": signals,
            "avg_1d_pct": float(ret1.mean()) if ret1.notna().any() else None,
            "avg_3d_pct": float(ret3.mean()) if ret3.notna().any() else None,
            "avg_5d_pct": float(ret5.mean()) if ret5.notna().any() else None,
            "win_3d_pct": float((ret3.dropna() > 0).mean() * 100.0) if ret3.notna().any() else None,
            "win_5d_pct": float((ret5.dropna() > 0).mean() * 100.0) if ret5.notna().any() else None,
            "adaptive_stop_pct": float(policy.get("adaptive_stop_pct", 0.0) or 0.0),
            "safe_take_profit_pct": float(policy.get("safe_take_profit_pct", 0.0) or 0.0),
            "risk_reward_ratio": float(policy.get("risk_reward_ratio", 0.0) or 0.0),
        }

        profiles.setdefault(str(market), {}).setdefault(str(regime), {})[str(ticker).upper()] = payload

    selected: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for market, regime_map in profiles.items():
        for regime, ticker_map in regime_map.items():
            accepted = {
                ticker: item
                for ticker, item in ticker_map.items()
                if int(item.get("signals", 0) or 0) >= min_signals
                and float(item.get("win_5d_pct", 0.0) or 0.0) >= min_win_5d
                and float(item.get("avg_5d_pct", 0.0) or 0.0) >= min_avg_5d
            }
            ordered = dict(
                sorted(
                    accepted.items(),
                    key=lambda kv: (
                        float(kv[1].get("avg_5d_pct", 0.0) or 0.0),
                        float(kv[1].get("win_5d_pct", 0.0) or 0.0),
                        int(kv[1].get("signals", 0) or 0),
                    ),
                    reverse=True,
                )
            )
            selected.setdefault(market, {})[regime] = ordered
            selected_counts.setdefault(market, {})[regime] = len(ordered)

    return {
        "version": "2026-03-31-regime-profile-v1",
        "source": "runtime_state/reports/external_signals/signals_rows_enriched.csv",
        "selection_thresholds": {
            "min_signals": min_signals,
            "min_win_5d_pct": min_win_5d,
            "min_avg_5d_pct": min_avg_5d,
        },
        "profiles": profiles,
        "selected_profiles": selected,
        "selected_counts": selected_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build regime/ticker profile artifact from enriched external signals CSV.")
    parser.add_argument("--enriched-csv", type=str, default="runtime_state/reports/external_signals/signals_rows_enriched.csv")
    parser.add_argument("--ticker-policy-csv", type=str, default="runtime_state/reports/external_signals/ticker_risk_policy.csv")
    parser.add_argument("--output", type=str, default="models/regime_ticker_profiles.json")
    parser.add_argument("--min-signals", type=int, default=3)
    parser.add_argument("--min-win-5d", type=float, default=60.0)
    parser.add_argument("--min-avg-5d", type=float, default=5.0)
    args = parser.parse_args()

    df = pd.read_csv(args.enriched_csv)
    ticker_policy_df = pd.read_csv(args.ticker_policy_csv) if Path(args.ticker_policy_csv).exists() else pd.DataFrame()
    payload = build_profiles(
        df,
        ticker_policy_df=ticker_policy_df,
        min_signals=args.min_signals,
        min_win_5d=args.min_win_5d,
        min_avg_5d=args.min_avg_5d,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "selected_counts": payload["selected_counts"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
