#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.realized_expectancy_admission import (
    compare_original_vs_expectancy_order,
    compare_unadjusted_vs_regime_theme_order,
    load_post_scan_ledger_rows,
)


DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"


def _markdown(report):
    original = report["original_order"]
    expectancy = report["expectancy_order"]
    lines = [
        "# KR Realized Expectancy Admission Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- policy_version: `{report['policy_version']}`",
        f"- top_n: `{report['top_n']}`",
        f"- comparison_groups: `{report['comparison_groups']}`",
        "",
        "## Original Top Order",
        f"- rows: `{original['rows']}`",
        f"- 3D win/avg/min/max: `{original['return_3d']['win_pct']}` / `{original['return_3d']['avg_pct']}` / `{original['return_3d']['min_pct']}` / `{original['return_3d']['max_pct']}`",
        f"- 5D win/avg/min/max: `{original['return_5d']['win_pct']}` / `{original['return_5d']['avg_pct']}` / `{original['return_5d']['min_pct']}` / `{original['return_5d']['max_pct']}`",
        f"- stop_first_5d_pct: `{original['stop_first_5d_pct']}`",
        "",
        "## Realized-Expectancy Order",
        f"- rows: `{expectancy['rows']}`",
        f"- 3D win/avg/min/max: `{expectancy['return_3d']['win_pct']}` / `{expectancy['return_3d']['avg_pct']}` / `{expectancy['return_3d']['min_pct']}` / `{expectancy['return_3d']['max_pct']}`",
        f"- 5D win/avg/min/max: `{expectancy['return_5d']['win_pct']}` / `{expectancy['return_5d']['avg_pct']}` / `{expectancy['return_5d']['min_pct']}` / `{expectancy['return_5d']['max_pct']}`",
        f"- stop_first_5d_pct: `{expectancy['stop_first_5d_pct']}`",
    ]
    regime_theme = report.get("regime_theme_comparison") if isinstance(report.get("regime_theme_comparison"), dict) else {}
    if regime_theme:
        unadjusted = regime_theme["unadjusted_order"]
        adjusted = regime_theme["regime_theme_order"]
        coverage = regime_theme.get("feature_coverage") if isinstance(regime_theme.get("feature_coverage"), dict) else {}
        lines.extend(
            [
                "",
                "## Regime/Theme Calibration Check",
                (
                    f"- feature coverage rows/market_gate/theme/same_scan_theme: "
                    f"`{coverage.get('rows')}` / `{coverage.get('market_gate_rows')}` / "
                    f"`{coverage.get('primary_theme_rows')}` / `{coverage.get('same_scan_theme_rows')}`"
                ),
                f"- unadjusted rows: `{unadjusted['rows']}` · applied rows: `{unadjusted['regime_theme_applied_rows']}`",
                f"- unadjusted 3D win/avg/min/max: `{unadjusted['return_3d']['win_pct']}` / `{unadjusted['return_3d']['avg_pct']}` / `{unadjusted['return_3d']['min_pct']}` / `{unadjusted['return_3d']['max_pct']}`",
                f"- unadjusted 5D win/avg/min/max: `{unadjusted['return_5d']['win_pct']}` / `{unadjusted['return_5d']['avg_pct']}` / `{unadjusted['return_5d']['min_pct']}` / `{unadjusted['return_5d']['max_pct']}`",
                f"- adjusted rows: `{adjusted['rows']}` · applied rows: `{adjusted['regime_theme_applied_rows']}`",
                f"- adjusted 3D win/avg/min/max: `{adjusted['return_3d']['win_pct']}` / `{adjusted['return_3d']['avg_pct']}` / `{adjusted['return_3d']['min_pct']}` / `{adjusted['return_3d']['max_pct']}`",
                f"- adjusted 5D win/avg/min/max: `{adjusted['return_5d']['win_pct']}` / `{adjusted['return_5d']['avg_pct']}` / `{adjusted['return_5d']['min_pct']}` / `{adjusted['return_5d']['max_pct']}`",
            ]
        )
    quality = report.get("data_quality_breakdown") if isinstance(report.get("data_quality_breakdown"), dict) else {}
    if quality:
        lines.extend(["", "## Data Quality Breakdown"])
        for level, metrics in sorted(quality.items()):
            lines.append(
                f"- {level}: rows `{metrics['rows']}` · 3D win/avg `{metrics['return_3d_win_pct']}` / `{metrics['return_3d_avg_pct']}` · "
                f"5D win/avg `{metrics['return_5d_win_pct']}` / `{metrics['return_5d_avg_pct']}`"
            )
    return "\n".join(lines) + "\n"


def _quality_breakdown(rows):
    groups = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        quality = row.get("candidate_data_quality") if isinstance(row.get("candidate_data_quality"), dict) else {}
        level = str(row.get("data_warning_level") or quality.get("display_warning_level") or "unknown")
        groups.setdefault(level, []).append(row)

    def _float(value):
        try:
            return float(value)
        except Exception:
            return None

    def _metrics(values):
        clean = [value for value in (_float(value) for value in values) if value is not None]
        if not clean:
            return {"win_pct": None, "avg_pct": None}
        return {
            "win_pct": round(sum(1 for value in clean if value > 0) / len(clean) * 100.0, 4),
            "avg_pct": round(sum(clean) / len(clean), 6),
        }

    out = {}
    for level, group in groups.items():
        ret3 = _metrics([row.get("return_3d_pct") for row in group])
        ret5 = _metrics([row.get("return_5d_pct") for row in group])
        out[level] = {
            "rows": len(group),
            "return_3d_win_pct": ret3["win_pct"],
            "return_3d_avg_pct": ret3["avg_pct"],
            "return_5d_win_pct": ret5["win_pct"],
            "return_5d_avg_pct": ret5["avg_pct"],
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare original Top order vs realized-expectancy admission order.")
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--limit-runs", type=int, default=200)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    rows = load_post_scan_ledger_rows(Path(args.shared_dir), limit_runs=int(args.limit_runs))
    report = compare_original_vs_expectancy_order(rows, top_n=int(args.top_n))
    report["regime_theme_comparison"] = compare_unadjusted_vs_regime_theme_order(rows, top_n=int(args.top_n))
    report["data_quality_breakdown"] = _quality_breakdown(rows)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "kr_realized_expectancy_admission.json"
    md_path = out_dir / "kr_realized_expectancy_admission.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "rows": len(rows)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
