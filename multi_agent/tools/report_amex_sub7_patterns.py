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


def _price_band_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").map(_price_band)


def _metric_block(df: pd.DataFrame, column: str) -> Dict[str, Any]:
    if column not in df.columns:
        return {"samples": 0, "avg_return_pct": 0.0, "win_rate_pct": 0.0, "hit_20_pct": 0.0, "hit_50_pct": 0.0, "hit_100_pct": 0.0}
    clean = pd.to_numeric(df[column], errors="coerce").dropna()
    if clean.empty:
        return {"samples": 0, "avg_return_pct": 0.0, "win_rate_pct": 0.0, "hit_20_pct": 0.0, "hit_50_pct": 0.0, "hit_100_pct": 0.0}
    return {
        "samples": int(len(clean)),
        "avg_return_pct": round(float(clean.mean()), 4),
        "win_rate_pct": round(float((clean > 0).mean() * 100.0), 2),
        "hit_20_pct": round(float((clean >= 20).mean() * 100.0), 2),
        "hit_50_pct": round(float((clean >= 50).mean() * 100.0), 2),
        "hit_100_pct": round(float((clean >= 100).mean() * 100.0), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze AMEX moonshot patterns with focus on sub-$7 names.")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--output-dir", default="runtime_state/reports/us_research")
    args = parser.parse_args()

    from modules.db_manager import DBManager

    db = DBManager()
    if not db.client:
        raise SystemExit("Supabase client unavailable.")

    rows = (
        db.client.table("market_scan_results")
        .select("*")
        .eq("market_type", "AMEX")
        .eq("strategy_family", "AMEX_MOONSHOT")
        .order("created_at", desc=True)
        .limit(int(args.limit))
        .execute()
        .data
        or []
    )
    df = pd.DataFrame(rows)
    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(df)),
        "price_band_counts": {},
        "price_band_metrics": {},
    }
    if not df.empty:
        df["price_band"] = _price_band_series(df["entry_reference_price"]) if "entry_reference_price" in df.columns else "unknown"
        report["price_band_counts"] = {str(k): int(v) for k, v in df["price_band"].value_counts().to_dict().items()}
        metrics: Dict[str, Any] = {}
        for band in ["le_7", "7_15", "gt_15"]:
            band_df = df[df["price_band"] == band]
            if band_df.empty:
                continue
            metrics[band] = {
                "count": int(len(band_df)),
                "latest_return_pct": _metric_block(band_df, "latest_return_pct"),
                "return_1d_pct": _metric_block(band_df, "return_1d_pct"),
                "return_3d_pct": _metric_block(band_df, "return_3d_pct"),
                "return_5d_pct": _metric_block(band_df, "return_5d_pct"),
                "return_7d_pct": _metric_block(band_df, "return_7d_pct"),
            }
        report["price_band_metrics"] = metrics

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "amex_sub7_patterns.json"
    md_path = out_dir / "amex_sub7_patterns.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# AMEX Sub-$7 Pattern Report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- rows: {report['rows']}",
        f"- price_band_counts: {report.get('price_band_counts', {})}",
        "",
        "## Price Band Metrics",
    ]
    for band, metrics in (report.get("price_band_metrics") or {}).items():
        lines.append(f"- {band}: count={metrics.get('count', 0)}")
        for key in ["latest_return_pct", "return_1d_pct", "return_3d_pct", "return_5d_pct", "return_7d_pct"]:
            block = metrics.get(key, {})
            lines.append(
                f"  - {key}: n={block.get('samples', 0)} avg={block.get('avg_return_pct', 0.0):+.2f}% "
                f"win={block.get('win_rate_pct', 0.0):.1f}% "
                f"hit20={block.get('hit_20_pct', 0.0):.1f}% "
                f"hit50={block.get('hit_50_pct', 0.0):.1f}% "
                f"hit100={block.get('hit_100_pct', 0.0):.1f}%"
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "rows": report["rows"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
