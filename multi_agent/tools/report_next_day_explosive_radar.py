#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.next_day_explosive_radar import backtest_next_day_radar
from modules.scan_artifact_archive import load_local_scan_archive_rows, merge_archive_rows_with_local_artifacts
from modules.signal_section_performance import DEFAULT_ARCHIVE_CSV, load_archive_rows


DEFAULT_OUT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "kr_next_day_explosive_radar.json"


def _load_rows(limit_runs: int, archive_csv: Path) -> List[Dict[str, Any]]:
    db_rows = load_archive_rows(archive_csv)
    local_rows = load_local_scan_archive_rows(limit_runs=limit_runs)
    return merge_archive_rows_with_local_artifacts(db_rows, local_rows)


def _metric_line(label: str, metrics: Dict[str, Any]) -> str:
    return (
        f"- {label}: n `{metrics.get('n')}` / +5정밀도 `{metrics.get('plus5_precision_pct')}`% / "
        f"+10정밀도 `{metrics.get('plus10_precision_pct')}`% / 평균 `{metrics.get('avg_return_1d_pct')}`% / "
        f"최저 `{metrics.get('worst_return_1d_pct')}`% / 음봉오탐 `{metrics.get('false_positive_pct')}`%"
    )


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# KR Next-Day Explosive Radar",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- version: `{report.get('version')}`",
        f"- source_rows: `{report.get('source_rows')}`",
        f"- top_n: `{report.get('top_n')}`",
        f"- promotion_status: `{report.get('promotion_status')}`",
        "",
        "## Metrics",
        _metric_line("radar", report.get("radar") or {}),
        _metric_line("baseline_priority", report.get("baseline_priority") or {}),
        "",
        "## Promotion Rule",
        str(report.get("promotion_rule") or "-"),
        "",
        "## Sample Candidates",
    ]
    for item in report.get("sample_candidates") or []:
        if not isinstance(item, dict):
            continue
        reasons = ", ".join(str(value) for value in item.get("feature_reasons") or []) or "-"
        lines.append(
            f"- `{item.get('ticker')}` {item.get('market')} · score `{item.get('radar_score')}` · "
            f"+5 `{item.get('next_day_plus5_prob')}` · +10 `{item.get('next_day_plus10_prob')}` · {reasons}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest shadow-only KR next-day explosive radar candidates.")
    parser.add_argument("--archive-csv", default=str(DEFAULT_ARCHIVE_CSV))
    parser.add_argument("--limit-runs", type=int, default=300)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    rows = _load_rows(int(args.limit_runs), Path(args.archive_csv))
    report = backtest_next_day_radar(rows, top_n=int(args.top_n))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    md = out.with_suffix(".md")
    md.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json_path": str(out),
                "md_path": str(md),
                "source_rows": report.get("source_rows"),
                "radar": report.get("radar"),
                "baseline_priority": report.get("baseline_priority"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
