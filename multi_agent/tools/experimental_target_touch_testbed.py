#!/usr/bin/env python3
"""Internal shadow report for target-before-stop win-rate experiments.

This tool does not change scanner ranking, model files, Supabase rows, or
Discord/web outputs. It reads an archive learning dataset and writes a report
under ``runtime_state/reports/experimental`` for offline review.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.experimental_target_touch import (
    EXPERIMENT_VERSION,
    TargetTouchPolicy,
    derive_proxy_label_from_archive_row,
    summarize_shadow_rows,
)


DEFAULT_INPUT = Path("runtime_state/reports/archive/scan_archive_learning_dataset_all.json")
DEFAULT_OUTPUT = Path("runtime_state/reports/experimental/target_touch_testbed.json")


def _load_rows(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("rows", "data", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise ValueError(f"Unsupported dataset shape: {path}")


def build_report(
    rows: List[Dict[str, Any]],
    *,
    policy: TargetTouchPolicy,
    min_samples: int,
) -> Dict[str, Any]:
    shadow_rows: List[Dict[str, Any]] = []
    status_counts: Dict[str, int] = {}
    warning_counts: Dict[str, int] = {}
    for row in rows:
        label = derive_proxy_label_from_archive_row(row, policy=policy)
        status = str(label.get("terminal_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        for warning in label.get("warnings") or []:
            warning_counts[str(warning)] = warning_counts.get(str(warning), 0) + 1
        merged = {
            "market": row.get("market") or row.get("market_type"),
            "scan_mode": row.get("scan_mode") or "SWING",
            "decision_bucket": row.get("decision_bucket") or row.get("decision"),
            "ticker": row.get("ticker"),
            "run_id": row.get("run_id"),
            **label,
        }
        shadow_rows.append(merged)

    return {
        "report_version": EXPERIMENT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow_only_not_production",
        "policy": policy.__dict__,
        "rows_seen": len(rows),
        "rows_labeled": len(shadow_rows),
        "status_counts": dict(sorted(status_counts.items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "cohort_summary": summarize_shadow_rows(shadow_rows, min_samples=min_samples),
        "notes": [
            "This report is an internal testbed only.",
            "Proxy labels from archive rows are not a production replacement for OHLCV path-order labels.",
            "target_before_stop remains null when target/stop order cannot be determined.",
        ],
    }


def write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# Target Before Stop Shadow Testbed",
        "",
        f"- version: `{report.get('report_version')}`",
        f"- mode: `{report.get('mode')}`",
        f"- rows_seen: `{report.get('rows_seen')}`",
        f"- policy: `{report.get('policy')}`",
        "",
        "## Status Counts",
    ]
    for key, value in (report.get("status_counts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Cohort Summary", ""])
    rows = report.get("cohort_summary") if isinstance(report.get("cohort_summary"), list) else []
    if rows:
        headers = [
            "market",
            "scan_mode",
            "decision_bucket",
            "n",
            "ordered_label_n",
            "target_before_stop_win_pct",
            "target_touch_proxy_pct",
            "stop_touch_proxy_pct",
            "avg_close_return_pct",
            "avg_mfe_pct",
            "avg_mae_pct",
        ]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in rows:
            lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
    else:
        lines.append("No cohorts met min_samples.")
    lines.extend(["", "## Notes"])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--target-pct", type=float, default=5.0)
    parser.add_argument("--stop-pct", type=float, default=5.0)
    parser.add_argument("--horizon-days", type=int, default=5)
    parser.add_argument("--min-samples", type=int, default=8)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    rows = _load_rows(input_path)
    report = build_report(
        rows,
        policy=TargetTouchPolicy(
            horizon_days=int(args.horizon_days),
            target_pct=float(args.target_pct),
            stop_pct=float(args.stop_pct),
        ),
        min_samples=int(args.min_samples),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, output_path.with_suffix(".md"))
    print(json.dumps({"output": str(output_path), "rows_seen": report["rows_seen"], "cohorts": len(report["cohort_summary"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
