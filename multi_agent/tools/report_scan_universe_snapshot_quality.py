#!/usr/bin/env python3
"""Report Supabase scan_universe_snapshots coverage and distribution."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_OUT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "scan_universe_snapshot_quality.json"
TARGET_TABLE = "scan_universe_snapshots"


def _fetch_rows(page_size: int) -> tuple[int | None, List[Dict[str, Any]]]:
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")
    count_res = db.client.table(TARGET_TABLE).select("snapshot_key", count="exact").limit(1).execute()
    exact_count = getattr(count_res, "count", None)
    cols = "id,run_id,market,scan_mode,row_role,passed_current_model,outcome_available,reject_reason"
    rows: List[Dict[str, Any]] = []
    page = 0
    while True:
        batch = (
            db.client.table(TARGET_TABLE)
            .select(cols)
            .order("id")
            .range(page * page_size, page * page_size + page_size - 1)
            .execute()
            .data
            or []
        )
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
    return exact_count, rows


def build_report(page_size: int) -> Dict[str, Any]:
    exact_count, rows = _fetch_rows(page_size)
    by_market = Counter(str(row.get("market") or "") for row in rows)
    by_scan_mode = Counter(str(row.get("scan_mode") or "") for row in rows)
    by_role = Counter(str(row.get("row_role") or "") for row in rows)
    top_reject = Counter(
        str(row.get("reject_reason") or "")
        for row in rows
        if str(row.get("row_role") or "") == "rejected"
    ).most_common(15)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "table": TARGET_TABLE,
        "exact_count": exact_count,
        "fetched_rows": len(rows),
        "unique_ids": len({row.get("id") for row in rows}),
        "unique_runs": len({row.get("run_id") for row in rows if row.get("run_id")}),
        "by_market": dict(by_market),
        "by_scan_mode": dict(by_scan_mode),
        "by_role": dict(by_role),
        "passed_current_model_rows": sum(1 for row in rows if row.get("passed_current_model") is True),
        "outcome_available_rows": sum(1 for row in rows if row.get("outcome_available") is True),
        "top_reject_reasons": dict(top_reject),
    }


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Scan Universe Snapshot Quality",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- table: `{report.get('table')}`",
        f"- exact_count: `{report.get('exact_count')}`",
        f"- fetched_rows: `{report.get('fetched_rows')}`",
        f"- unique_ids: `{report.get('unique_ids')}`",
        f"- unique_runs: `{report.get('unique_runs')}`",
        f"- passed_current_model_rows: `{report.get('passed_current_model_rows')}`",
        f"- outcome_available_rows: `{report.get('outcome_available_rows')}`",
        "",
        "## Distribution",
        f"- by_market: `{report.get('by_market')}`",
        f"- by_scan_mode: `{report.get('by_scan_mode')}`",
        f"- by_role: `{report.get('by_role')}`",
        "",
        "## Top Reject Reasons",
    ]
    for reason, count in (report.get("top_reject_reasons") or {}).items():
        lines.append(f"- `{reason or 'UNKNOWN'}`: `{count}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()

    report = build_report(page_size=max(1, int(args.page_size)))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    out.with_suffix(".md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
