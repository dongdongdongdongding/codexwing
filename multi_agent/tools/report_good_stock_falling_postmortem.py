#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.good_stock_falling_postmortem import build_good_stock_falling_postmortem
from modules.realized_expectancy_admission import load_post_scan_ledger_rows


DEFAULT_OUT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "good_stock_falling_postmortem.json"


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_merged_rows(shared_dir: Path, limit_runs: int):
    rows = []
    run_dirs = sorted(
        [path for path in shared_dir.glob("RUN-*") if (path / "post_scan_outcome_ledger.json").exists()],
        key=lambda path: (path / "post_scan_outcome_ledger.json").stat().st_mtime,
        reverse=True,
    )[: int(limit_runs)]
    for run_dir in run_dirs:
        ledger = _load_json(run_dir / "post_scan_outcome_ledger.json")
        outcomes = _load_json(run_dir / "realized_outcomes.json")
        outcome_by_ticker = {
            str(row.get("ticker") or ""): row
            for row in outcomes.get("outcomes", [])
            if isinstance(row, dict) and row.get("ticker")
        } if isinstance(outcomes, dict) else {}
        for row in ledger.get("rows", []) if isinstance(ledger, dict) else []:
            if not isinstance(row, dict):
                continue
            rows.append({**outcome_by_ticker.get(str(row.get("ticker") or ""), {}), **row})
    return rows


def _markdown(report):
    lines = [
        "# Good Stock Falling Postmortem",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- version: `{report.get('version')}`",
        f"- rows/high_score/losers: `{report.get('rows')}` / `{report.get('high_score_rows')}` / `{report.get('high_score_losers')}`",
        "",
        "## Cause Counts",
    ]
    for cause, count in sorted((report.get("cause_counts") or {}).items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- {cause}: `{count}`")
    lines.extend(["", "## Proposed Rule Deltas"])
    for item in report.get("proposed_rule_deltas") or []:
        lines.append(f"- `{item.get('rule_delta')}` · loser_share `{item.get('loser_share_pct')}`% · target `{item.get('target_layer')}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report why high-score KR candidates fell after scan.")
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--limit-runs", type=int, default=300)
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    rows = _load_merged_rows(Path(args.shared_dir), int(args.limit_runs))
    if not rows:
        rows = load_post_scan_ledger_rows(Path(args.shared_dir), limit_runs=int(args.limit_runs))
    report = build_good_stock_falling_postmortem(rows)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    md = out.with_suffix(".md")
    md.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps({"json_path": str(out), "md_path": str(md), "rows": len(rows), "losers": report.get("high_score_losers")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
