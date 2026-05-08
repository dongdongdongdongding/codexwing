#!/usr/bin/env python3
"""Report strategy_family performance by market and horizon."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
OUT_JSON = ROOT / "runtime_state/reports/learning/strategy_family_matrix.json"
OUT_MD = ROOT / "runtime_state/reports/learning/strategy_family_matrix.md"
HORIZONS = ["return_1d_pct", "return_3d_pct", "return_5d_pct"]


def _metrics(group: pd.DataFrame, return_col: str) -> dict:
    returns = pd.to_numeric(group.get(return_col), errors="coerce").dropna()
    if returns.empty:
        return {"samples": 0}
    return {
        "samples": int(len(returns)),
        "win_rate_pct": round(float((returns > 0).mean() * 100.0), 2),
        "avg_return_pct": round(float(returns.mean()), 4),
        "median_return_pct": round(float(returns.median()), 4),
        "std_return_pct": round(float(returns.std(ddof=0)), 4),
        "hit_5pct_pct": round(float((returns >= 5.0).mean() * 100.0), 2),
        "negative_family": bool((returns > 0).mean() < 0.5 or returns.mean() < 0),
    }


def build_report() -> dict:
    df = pd.read_csv(ARCHIVE, low_memory=False)
    df["strategy_family"] = df.get("strategy_family", "").fillna("UNKNOWN").astype(str).str.upper()
    df["market"] = df.get("market_type", "").fillna("UNKNOWN").astype(str).str.upper()
    if "market_subtype" in df.columns:
        subtype = df["market_subtype"].fillna("").astype(str).str.upper()
        df["market"] = subtype.where(subtype.ne(""), df["market"])
    df["scan_mode"] = df.get("scan_mode", "").fillna("UNKNOWN").astype(str).str.upper()
    if "outcome_status" in df.columns:
        df = df[df["outcome_status"].fillna("").astype(str).str.upper().eq("RESOLVED")]

    rows = []
    for keys, group in df.groupby(["strategy_family", "market", "scan_mode"], dropna=False):
        family, market, mode = keys
        row = {
            "strategy_family": str(family),
            "market": str(market),
            "scan_mode": str(mode),
        }
        for horizon in HORIZONS:
            row[horizon] = _metrics(group, horizon)
        rows.append(row)

    def sort_key(row: dict) -> tuple:
        best_samples = max(int(row[h].get("samples", 0) or 0) for h in HORIZONS)
        best_avg = max(float(row[h].get("avg_return_pct", -999) or -999) for h in HORIZONS)
        return (-best_samples, -best_avg)

    rows = sorted(rows, key=sort_key)
    negative_rows = [
        row for row in rows
        if any(int(row[h].get("samples", 0) or 0) >= 30 and row[h].get("negative_family") for h in HORIZONS)
    ]
    return {
        "generated_at": datetime.now().isoformat(),
        "source": str(ARCHIVE.relative_to(ROOT)),
        "rows_loaded": int(len(df)),
        "matrix": rows,
        "negative_candidates": negative_rows,
    }


def write_report(report: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Strategy Family Matrix",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- source: `{report['source']}`",
        f"- rows_loaded: `{report['rows_loaded']}`",
        "",
        "## Negative Candidates",
    ]
    if not report["negative_candidates"]:
        lines.append("- none")
    else:
        for row in report["negative_candidates"][:30]:
            parts = []
            for horizon in HORIZONS:
                metric = row[horizon]
                if int(metric.get("samples", 0) or 0) >= 30 and metric.get("negative_family"):
                    parts.append(
                        f"{horizon.replace('return_', '').replace('_pct', '')}: "
                        f"n={metric['samples']} win={metric['win_rate_pct']}% avg={metric['avg_return_pct']:+.2f}%"
                    )
            if parts:
                lines.append(
                    f"- `{row['strategy_family']}` / `{row['market']}` / `{row['scan_mode']}`: "
                    + "; ".join(parts)
                )
    lines.extend(["", "## Top Sample Rows"])
    for row in report["matrix"][:30]:
        lines.append(f"- `{row['strategy_family']}` / `{row['market']}` / `{row['scan_mode']}`")
        for horizon in HORIZONS:
            metric = row[horizon]
            if int(metric.get("samples", 0) or 0) == 0:
                continue
            lines.append(
                f"  - {horizon.replace('return_', '').replace('_pct', '')}: "
                f"n={metric['samples']} win={metric['win_rate_pct']}% "
                f"avg={metric['avg_return_pct']:+.2f}% med={metric['median_return_pct']:+.2f}%"
            )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    report = build_report()
    write_report(report)
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"negative_candidates={len(report['negative_candidates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
