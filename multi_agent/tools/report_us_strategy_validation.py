#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

HORIZON_COLUMNS = [
    ("30m", "return_30m_pct"),
    ("1h", "return_1h_pct"),
    ("close", "return_close_pct"),
    ("1d", "return_1d_pct"),
    ("3d", "return_3d_pct"),
    ("5d", "return_5d_pct"),
    ("7d", "return_7d_pct"),
]
HIT_THRESHOLDS = [5, 10, 20, 50, 100]


def _decision_bucket_series(df: pd.DataFrame) -> pd.Series:
    if "decision" in df.columns:
        decision = df["decision"].fillna("").astype(str).str.upper()
        inferred = pd.Series("unknown", index=df.index, dtype="object")
        inferred = inferred.mask(decision.eq("EXCEPTION_LEADER"), "exception_leader")
        inferred = inferred.mask(decision.isin(["WATCHLIST_ONLY", "FALLBACK_WATCHLIST", "WATCHLIST", "OBSERVE"]), "watchlist")
        inferred = inferred.mask(decision.isin(["PRIORITY_WATCHLIST"]), "picked")
        return inferred.fillna("unknown").astype(str)
    if "decision_bucket" in df.columns:
        return df["decision_bucket"].fillna("unknown").astype(str)
    return pd.Series("unknown", index=df.index, dtype="object")


def _metric_block(series: pd.Series) -> Dict[str, Any]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {
            "samples": 0,
            "avg_return_pct": 0.0,
            "median_return_pct": 0.0,
            "win_rate_pct": 0.0,
            "hit_rates": {f">{thr}%": 0.0 for thr in HIT_THRESHOLDS},
        }
    return {
        "samples": int(len(clean)),
        "avg_return_pct": round(float(clean.mean()), 4),
        "median_return_pct": round(float(clean.median()), 4),
        "win_rate_pct": round(float((clean > 0).mean() * 100.0), 2),
        "hit_rates": {f">{thr}%": round(float((clean >= thr).mean() * 100.0), 2) for thr in HIT_THRESHOLDS},
    }


def _price_band(value: Any) -> str:
    try:
        price = float(value)
    except Exception:
        return "unknown"
    if price <= 0:
        return "unknown"
    if price <= 7:
        return "le_7"
    if price <= 15:
        return "7_15"
    return "gt_15"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate NASDAQ/AMEX archive before model finalization.")
    parser.add_argument("--market", choices=["NASDAQ", "AMEX"], required=True)
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="ALL")
    parser.add_argument("--strategy-family", default=None)
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--output-dir", default="runtime_state/reports/us_research")
    args = parser.parse_args()

    from modules.db_manager import DBManager

    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")

    market_type = "AMEX" if args.market == "AMEX" else "US"
    query = (
        db.client.table("market_scan_results")
        .select("*")
        .eq("market_type", market_type)
        .order("created_at", desc=True)
        .limit(int(args.limit))
    )
    if args.strategy_family:
        query = query.eq("strategy_family", str(args.strategy_family))
    rows = query.execute().data or []
    df = pd.DataFrame(rows)
    if not df.empty and args.scan_mode != "ALL" and "scan_mode" in df.columns:
        df = df[df["scan_mode"].fillna("SWING").str.upper() == str(args.scan_mode).upper()]

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": str(args.market),
        "market_type_filter": market_type,
        "scan_mode": str(args.scan_mode).upper(),
        "strategy_family": args.strategy_family,
        "rows": int(len(df)),
        "decision_bucket_counts": {},
        "strategy_family_counts": {},
        "price_band_counts": {},
        "price_band_horizons": {},
        "moonshot": {},
        "horizons": {},
    }
    if not df.empty:
        report["decision_bucket_counts"] = {
            str(k): int(v) for k, v in _decision_bucket_series(df).value_counts().to_dict().items()
        }
        if "strategy_family" in df.columns:
            report["strategy_family_counts"] = {
                str(k): int(v) for k, v in df["strategy_family"].fillna("unknown").value_counts().to_dict().items()
            }
        if "entry_reference_price" in df.columns:
            bands = df["entry_reference_price"].apply(_price_band)
            report["price_band_counts"] = {str(k): int(v) for k, v in bands.value_counts().to_dict().items()}
            band_metrics: Dict[str, Dict[str, Any]] = {}
            for band in ["le_7", "7_15", "gt_15"]:
                band_df = df[bands == band]
                if band_df.empty:
                    continue
                band_metrics[band] = {}
                for label, column in HORIZON_COLUMNS:
                    if column in band_df.columns:
                        band_metrics[band][label] = _metric_block(band_df[column])
            report["price_band_horizons"] = band_metrics
        for label, column in HORIZON_COLUMNS:
            if column in df.columns:
                report["horizons"][label] = _metric_block(df[column])

        present_return_cols = [column for _, column in HORIZON_COLUMNS if column in df.columns]
        if present_return_cols:
            numeric = df[present_return_cols].apply(pd.to_numeric, errors="coerce")
            max_return = numeric.max(axis=1, skipna=True)
            best_horizon = pd.Series("unknown", index=df.index, dtype="object")
            valid_numeric = numeric.dropna(how="all")
            if not valid_numeric.empty:
                best_horizon.loc[valid_numeric.index] = valid_numeric.idxmax(axis=1, skipna=True)
            valid_max = max_return.dropna()
            report["moonshot"] = {
                "samples": int(len(valid_max)),
                "avg_max_return_pct": round(float(valid_max.mean()), 4) if not valid_max.empty else 0.0,
                "median_max_return_pct": round(float(valid_max.median()), 4) if not valid_max.empty else 0.0,
                "hit_rates": {
                    f">{thr}%": round(float((valid_max >= thr).mean() * 100.0), 2) if not valid_max.empty else 0.0
                    for thr in [20, 50, 100]
                },
                "best_horizon_counts": {str(k): int(v) for k, v in best_horizon.value_counts().to_dict().items()},
            }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"{args.market.lower()}_{str(args.scan_mode).lower()}"
    json_path = out_dir / f"validation_{suffix}.json"
    md_path = out_dir / f"validation_{suffix}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        f"# Validation Report ({args.market} / {str(args.scan_mode).upper()})",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- rows: {report['rows']}",
        f"- decision_bucket_counts: {report.get('decision_bucket_counts', {})}",
        f"- strategy_family_counts: {report.get('strategy_family_counts', {})}",
        f"- price_band_counts: {report.get('price_band_counts', {})}",
        "",
        "## Moonshot Summary",
    ]
    moonshot = report.get("moonshot") or {}
    if moonshot:
        lines.extend(
            [
                f"- samples: {moonshot.get('samples', 0)}",
                f"- avg_max_return_pct: {moonshot.get('avg_max_return_pct', 0.0):+.2f}%",
                f"- median_max_return_pct: {moonshot.get('median_max_return_pct', 0.0):+.2f}%",
                f"- hit_rates: {moonshot.get('hit_rates', {})}",
                f"- best_horizon_counts: {moonshot.get('best_horizon_counts', {})}",
                "",
            ]
        )
    lines.extend([
        "## Horizon Metrics",
    ])
    for label, metrics in report.get("horizons", {}).items():
        lines.append(
            f"- {label}: n={metrics.get('samples', 0)} avg={metrics.get('avg_return_pct', 0.0):+.2f}% "
            f"median={metrics.get('median_return_pct', 0.0):+.2f}% win={metrics.get('win_rate_pct', 0.0):.1f}% "
            f"hits={metrics.get('hit_rates', {})}"
        )
    price_band_horizons = report.get("price_band_horizons", {})
    if isinstance(price_band_horizons, dict) and price_band_horizons:
        lines.append("")
        lines.append("## Price Band Metrics")
        for band, band_metrics in price_band_horizons.items():
            lines.append(f"- {band}:")
            if not isinstance(band_metrics, dict):
                continue
            for label, metrics in band_metrics.items():
                if not isinstance(metrics, dict):
                    continue
                lines.append(
                    f"  - {label}: n={metrics.get('samples', 0)} avg={metrics.get('avg_return_pct', 0.0):+.2f}% "
                    f"win={metrics.get('win_rate_pct', 0.0):.1f}% hits={metrics.get('hit_rates', {})}"
                )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "rows": int(len(df))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
