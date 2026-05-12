#!/usr/bin/env python3
"""Validate KOSPI SWING soft-gate holdout performance from archive export."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"
DEFAULT_DATASET = PROJECT_ROOT / "runtime_state" / "reports" / "archive" / "scan_archive_learning_dataset_all.csv"

SOFT_MARKERS = (
    "KOSPI_SWING_PRIORITY_GUARD_SOFT",
    "EXPECTED_EDGE_WATCH_GUARD_SOFT",
    "EXPECTED_EDGE_PRIORITY_GUARD_SOFT",
)
HARD_MARKERS = (
    "KOSPI_SWING_PRIORITY_GUARD",
    "EXPECTED_EDGE_WATCH_GUARD",
    "EXPECTED_EDGE_PRIORITY_GUARD",
)


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _contains_marker(series: pd.Series, marker: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(marker, regex=False)


def _pct(mask: pd.Series) -> float | None:
    if len(mask) == 0:
        return None
    return round(float(mask.mean() * 100.0), 3)


def _metric_group(group: pd.DataFrame) -> Dict[str, Any]:
    ret3 = _num(group.get("return_3d_pct", pd.Series(dtype=float))).dropna()
    ret5 = _num(group.get("return_5d_pct", pd.Series(dtype=float))).dropna()
    high5 = _num(group.get("max_high_return_5d_pct", pd.Series(dtype=float))).dropna()
    return {
        "n": int(len(group)),
        "n_resolved_3d": int(len(ret3)),
        "avg_3d_pct": round(float(ret3.mean()), 4) if len(ret3) else None,
        "win_3d_pct": _pct(ret3.gt(0)) if len(ret3) else None,
        "n_resolved_5d": int(len(ret5)),
        "avg_5d_pct": round(float(ret5.mean()), 4) if len(ret5) else None,
        "win_5d_pct": _pct(ret5.gt(0)) if len(ret5) else None,
        "n_high_touch_5d": int(len(high5)),
        "hit_5pct_within_5d_high_pct": _pct(high5.ge(5.0)) if len(high5) else None,
        "avg_max_high_return_5d_pct": round(float(high5.mean()), 4) if len(high5) else None,
    }


def build_report(dataset: Path, holdout_start: str, min_priority_30d: int) -> Dict[str, Any]:
    df = pd.read_csv(dataset, low_memory=False)
    if "recommended_at" not in df.columns:
        raise SystemExit("dataset missing recommended_at")
    rec = pd.to_datetime(df["recommended_at"], errors="coerce", utc=True)
    kospi = df[
        df.get("market", "").astype(str).str.upper().eq("KOSPI")
        & df.get("scan_mode", "").astype(str).str.upper().eq("SWING")
    ].copy()
    kospi["_recommended_dt"] = rec.loc[kospi.index]
    start_dt = pd.Timestamp(holdout_start)
    if start_dt.tzinfo is None:
        start_dt = start_dt.tz_localize("UTC")
    holdout = kospi[kospi["_recommended_dt"] >= start_dt].copy()

    generated_at = datetime.now(timezone.utc)
    thirty_day_start = generated_at - timedelta(days=30)
    recent_30d = kospi[kospi["_recommended_dt"] >= pd.Timestamp(thirty_day_start)]
    decision = kospi.get("decision", pd.Series("", index=kospi.index)).fillna("").astype(str)
    decision_holdout = holdout.get("decision", pd.Series("", index=holdout.index)).fillna("").astype(str)
    priority_30d = recent_30d[
        recent_30d.get("decision", pd.Series("", index=recent_30d.index)).fillna("").astype(str).eq("PRIORITY_WATCHLIST")
    ]
    priority_holdout = holdout[decision_holdout.eq("PRIORITY_WATCHLIST")]

    theme_risk = holdout.get("theme_risk", pd.Series("", index=holdout.index))
    marker_counts = {
        marker: int(_contains_marker(theme_risk, marker).sum())
        for marker in (*SOFT_MARKERS, *HARD_MARKERS)
    }
    by_decision = {
        str(name): _metric_group(group)
        for name, group in holdout.groupby(decision_holdout, dropna=False)
    }
    priority_metrics = _metric_group(priority_holdout)
    accepted = {
        "priority_watchlist_30d_rows_ge_min": int(len(priority_30d)) >= int(min_priority_30d),
        "priority_holdout_win_3d_ge_65": (priority_metrics.get("win_3d_pct") or 0) >= 65.0,
        "priority_holdout_avg_3d_ge_3_5": (priority_metrics.get("avg_3d_pct") or 0) >= 3.5,
        "soft_marker_present": any(marker_counts.get(marker, 0) > 0 for marker in SOFT_MARKERS),
        "high_touch_goal_ge_70": (priority_metrics.get("hit_5pct_within_5d_high_pct") or 0) >= 70.0,
        "high_touch_avg_ge_5": (priority_metrics.get("avg_max_high_return_5d_pct") or 0) >= 5.0,
    }
    accepted["passes_acceptance"] = all(accepted.values())
    return {
        "generated_at": generated_at.isoformat(),
        "dataset": str(dataset),
        "holdout_start": holdout_start,
        "market": "KOSPI",
        "scan_mode": "SWING",
        "kospi_swing_rows": int(len(kospi)),
        "holdout_rows": int(len(holdout)),
        "priority_watchlist_30d_rows": int(len(priority_30d)),
        "priority_watchlist_holdout": priority_metrics,
        "marker_counts": marker_counts,
        "by_decision": by_decision,
        "acceptance": accepted,
    }


def _write_markdown(report: Dict[str, Any], path: Path) -> None:
    priority = report["priority_watchlist_holdout"]
    lines = [
        "# KOSPI SWING Soft-Gate Holdout",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- holdout_start: `{report['holdout_start']}`",
        f"- kospi_swing_rows: `{report['kospi_swing_rows']}`",
        f"- holdout_rows: `{report['holdout_rows']}`",
        f"- priority_watchlist_30d_rows: `{report['priority_watchlist_30d_rows']}`",
        f"- passes_acceptance: `{report['acceptance']['passes_acceptance']}`",
        "",
        "## Priority Watchlist Holdout",
        "",
        f"- n: `{priority['n']}`",
        f"- win_3d_pct: `{priority['win_3d_pct']}`",
        f"- avg_3d_pct: `{priority['avg_3d_pct']}`",
        f"- win_5d_pct: `{priority['win_5d_pct']}`",
        f"- avg_5d_pct: `{priority['avg_5d_pct']}`",
        f"- hit_5pct_within_5d_high_pct: `{priority['hit_5pct_within_5d_high_pct']}`",
        f"- avg_max_high_return_5d_pct: `{priority['avg_max_high_return_5d_pct']}`",
        "",
        "## Marker Counts",
        "",
    ]
    for marker, count in report["marker_counts"].items():
        lines.append(f"- {marker}: `{count}`")
    lines.extend(["", "## By Decision", ""])
    for decision, metrics in report["by_decision"].items():
        lines.append(
            f"- {decision}: n={metrics['n']}, win3={metrics['win_3d_pct']}%, "
            f"avg3={metrics['avg_3d_pct']}%, hit5high={metrics['hit_5pct_within_5d_high_pct']}%, "
            f"avgHigh5={metrics['avg_max_high_return_5d_pct']}%"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--holdout-start", default="2026-05-06T13:30:00Z")
    parser.add_argument("--min-priority-30d", type=int, default=100)
    args = parser.parse_args()
    report = build_report(args.dataset, args.holdout_start, args.min_priority_30d)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "kospi_swing_gate_holdout.json"
    md_path = REPORT_DIR / "kospi_swing_gate_holdout.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, md_path)
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), **report}, ensure_ascii=False, indent=2))
    return 0 if report["acceptance"]["passes_acceptance"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
