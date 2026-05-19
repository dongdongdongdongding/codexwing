#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.missed_winner_postmortem import (
    attach_reject_outcomes,
    build_missed_winner_postmortem,
    build_reject_rows_from_diagnostics,
)
from modules.rejected_outcome_backfill import DEFAULT_REJECT_OUTCOME_CSV
from modules.scan_artifact_archive import load_local_scan_archive_rows, merge_archive_rows_with_local_artifacts
from modules.signal_section_performance import DEFAULT_ARCHIVE_CSV, load_archive_rows


DEFAULT_OUT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "kr_missed_winner_postmortem.json"


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_diagnostics(artifact_dir: Path, limit_runs: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not artifact_dir.exists():
        return rows
    run_dirs = sorted(
        [path for path in artifact_dir.iterdir() if path.is_dir() and path.name.startswith("RUN-")],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[: max(1, int(limit_runs or 300))]
    for run_dir in run_dirs:
        raw = _load_json(run_dir / "raw_scan_results.json")
        summary = _load_json(run_dir / "scan_pipeline_summary.json")
        if not isinstance(raw, dict):
            continue
        run_context = raw.get("run_context") if isinstance(raw.get("run_context"), dict) else {}
        diagnostics = raw.get("diagnostics") if isinstance(raw.get("diagnostics"), dict) else {}
        if not diagnostics:
            continue
        rows.append(
            {
                "run_id": str(run_context.get("run_id") or summary.get("run_id") or run_dir.name),
                "market": str(run_context.get("market") or summary.get("market") or ""),
                "base_trade_date": str(run_context.get("as_of_date") or run_context.get("created_at") or summary.get("created_at") or "")[:10],
                **diagnostics,
            }
        )
    return rows


def _load_outcome_csv(path: Path) -> List[Dict[str, Any]]:
    if not path or not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _load_rows(limit_runs: int, archive_csv: Path) -> List[Dict[str, Any]]:
    db_rows = load_archive_rows(archive_csv)
    local_rows = load_local_scan_archive_rows(limit_runs=limit_runs)
    return merge_archive_rows_with_local_artifacts(db_rows, local_rows)


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# KR Missed Winner Postmortem",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- version: `{report.get('version')}`",
        f"- source_rows: `{report.get('source_rows')}`",
        f"- emitted_rows: `{report.get('emitted_rows')}`",
        f"- reject_rows: `{report.get('reject_rows')}`",
        f"- reject_rows_without_outcomes: `{report.get('reject_rows_without_outcomes')}`",
        "",
        "## Capture Metrics",
    ]
    for key, metric in sorted((report.get("metrics") or {}).items()):
        lines.append(
            f"- {key}: winners `{metric.get('winner_count')}` · "
            f"Top5 capture `{metric.get('top5_capture_rate_pct')}`% · "
            f"emitted capture `{metric.get('emitted_capture_rate_pct')}`% · "
            f"missed `{metric.get('missed_rate_pct')}`% · reasons `{metric.get('miss_reason_counts')}`"
        )
    lines.extend(["", "## Proposed Rule Changes"])
    for item in report.get("proposed_rule_changes") or []:
        lines.append(f"- `{item.get('reason')}` count `{item.get('count')}`: {item.get('proposal')}")
    limitations = report.get("data_limitations") or []
    if limitations:
        lines.extend(["", "## Data Limitations"])
        for item in limitations:
            lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report KR winners missed by Top5 and rejected-symbol data gaps.")
    parser.add_argument("--archive-csv", default=str(DEFAULT_ARCHIVE_CSV))
    parser.add_argument("--artifact-dir", default="runtime_state/artifacts")
    parser.add_argument("--limit-runs", type=int, default=300)
    parser.add_argument("--reject-outcomes-csv", default=str(DEFAULT_REJECT_OUTCOME_CSV))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    emitted_rows = _load_rows(int(args.limit_runs), Path(args.archive_csv))
    diagnostics = _load_diagnostics(Path(args.artifact_dir), int(args.limit_runs))
    reject_rows = build_reject_rows_from_diagnostics(diagnostics)
    if args.reject_outcomes_csv and Path(args.reject_outcomes_csv).exists():
        reject_rows = attach_reject_outcomes(reject_rows, _load_outcome_csv(Path(args.reject_outcomes_csv)))
    report = build_missed_winner_postmortem(emitted_rows, reject_rows=reject_rows)
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
                "reject_rows_without_outcomes": report.get("reject_rows_without_outcomes"),
                "top_proposals": (report.get("proposed_rule_changes") or [])[:3],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
