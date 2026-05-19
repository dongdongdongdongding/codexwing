#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.realized_expectancy_admission import load_post_scan_ledger_rows
from modules.section_performance_calibration import (
    DEFAULT_SECTION_CALIBRATION_PATH,
    build_section_performance_calibration,
    write_section_performance_calibration,
)


def _markdown(report):
    lines = [
        "# KR Section Performance Calibration",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- version: `{report.get('version')}`",
        f"- source_rows: `{report.get('source_rows')}`",
        f"- recent_n: `{report.get('recent_n')}`",
        "",
        "## Sections",
    ]
    for entry in report.get("entries") or []:
        ret3 = entry.get("return_3d") or {}
        ret5 = entry.get("return_5d") or {}
        lines.append(
            f"- {entry.get('market')} / {entry.get('section')}: n `{entry.get('sample_n')}` · "
            f"conf `{entry.get('confidence')}` · 3D win/avg/min/max `{ret3.get('win_pct')}` / `{ret3.get('avg_pct')}` / `{ret3.get('min_pct')}` / `{ret3.get('max_pct')}` · "
            f"5D win/avg/min/max `{ret5.get('win_pct')}` / `{ret5.get('avg_pct')}` / `{ret5.get('min_pct')}` / `{ret5.get('max_pct')}` · "
            f"stop-first `{entry.get('stop_first_5d_pct')}` · recent drift `{entry.get('recent_5d_avg_drift_pct')}`"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build KR section performance calibration artifact from post-scan ledgers.")
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--limit-runs", type=int, default=300)
    parser.add_argument("--recent-n", type=int, default=40)
    parser.add_argument("--output", default=str(DEFAULT_SECTION_CALIBRATION_PATH))
    args = parser.parse_args()

    rows = load_post_scan_ledger_rows(Path(args.shared_dir), limit_runs=int(args.limit_runs))
    report = build_section_performance_calibration(rows, recent_n=int(args.recent_n))
    path = write_section_performance_calibration(report, Path(args.output))
    md_path = path.with_suffix(".md")
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"json_path": str(path), "md_path": str(md_path), "rows": len(rows), "entries": len(report.get("entries") or [])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
