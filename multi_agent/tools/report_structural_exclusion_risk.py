from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.structural_exclusion_risk import summarize_structural_exclusion_risks


def _load_rows(report_dir: Path, *, limit_runs: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    paths = sorted(report_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)[: max(1, int(limit_runs or 50))]
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, list):
            rows.extend([row for row in payload if isinstance(row, dict)])
    return rows


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Structural Exclusion Risk Report",
        "",
        f"- version: `{report.get('version')}`",
        f"- rows: `{report.get('rows', 0)}`",
        f"- level_counts: `{report.get('level_counts', {})}`",
        f"- reason_counts: `{report.get('reason_counts', {})}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", default="runtime_state/reports/top_deep")
    parser.add_argument("--limit-runs", type=int, default=100)
    parser.add_argument("--output-dir", default="runtime_state/reports/validation")
    args = parser.parse_args()

    rows = _load_rows(Path(args.report_dir), limit_runs=args.limit_runs)
    report = summarize_structural_exclusion_risks(rows)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "structural_exclusion_risk_report.json"
    md_path = out_dir / "structural_exclusion_risk_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "rows": report.get("rows", 0)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
