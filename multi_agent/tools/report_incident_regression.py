#!/usr/bin/env python3
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

from modules.incident_regression import IncidentPolicy, build_incident_regression_report, load_incident_fixtures

DEFAULT_FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "incident_regression_cases.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _ledger_rows_from_run(run_id: str) -> List[Dict[str, Any]]:
    path = PROJECT_ROOT / "runtime_state" / "shared_working" / str(run_id) / "post_scan_outcome_ledger.json"
    payload = _load_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return [row for row in payload["rows"] if isinstance(row, dict)]
    return []


def _markdown(report: Dict[str, Any]) -> str:
    current = report.get("current", {})
    candidate = report.get("candidate", {})
    lines = [
        "# Incident Regression Report",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- rows: `{report.get('rows')}`",
        f"- current_status: `{current.get('status')}` unprotected={current.get('unprotected_elevation_count')}",
        f"- candidate_status: `{candidate.get('status')}` unprotected={candidate.get('unprotected_elevation_count')}",
        "",
        "## Current Failures",
    ]
    failures = [row for row in current.get("results", []) if row.get("status") == "FAIL"]
    if not failures:
        lines.append("- none")
    for row in failures:
        lines.append(
            f"- {row.get('incident_id') or '-'} {row.get('ticker')} worst={row.get('worst_path_return_pct')} "
            f"decision={row.get('decision')} reasons={','.join(row.get('failure_risk_reason_codes') or []) or '-'}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run severe failed-candidate incident regression checks.")
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    parser.add_argument("--run-id", action="append", default=[])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--candidate-name", default="candidate")
    parser.add_argument("--candidate-severe-loss-pct", type=float, default=-7.0)
    parser.add_argument("--candidate-elevated-score", type=float, default=60.0)
    parser.add_argument("--accepted-tradeoff", action="store_true")
    parser.add_argument("--accepted-tradeoff-reason", default="")
    args = parser.parse_args()

    rows: List[Dict[str, Any]] = []
    fixture_path = Path(args.fixtures)
    if fixture_path.exists():
        rows.extend(load_incident_fixtures(fixture_path))
    for run_id in args.run_id or []:
        rows.extend(_ledger_rows_from_run(run_id))

    candidate_policy = IncidentPolicy(
        name=str(args.candidate_name),
        severe_loss_pct=float(args.candidate_severe_loss_pct),
        elevated_score_threshold=float(args.candidate_elevated_score),
        accepted_tradeoff=bool(args.accepted_tradeoff),
        accepted_tradeoff_reason=str(args.accepted_tradeoff_reason or ""),
    )
    report = build_incident_regression_report(rows, candidate_policy=candidate_policy)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["sources"] = {
        "fixtures": str(fixture_path),
        "run_ids": list(args.run_id or []),
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "incident_regression_report.json"
    md_path = out_dir / "incident_regression_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"json_path": str(json_path), "md_path": str(md_path), "status": report["candidate"]["status"], "rows": report["rows"]}, ensure_ascii=False, indent=2))
    return 1 if report["candidate"]["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
