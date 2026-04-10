from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.workflows.outcome_buckets import (
    MEASURED_OUTCOME_BUCKETS,
    finalize_bucket_stats,
    init_bucket_stats,
    resolve_outcome_bucket,
)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _iter_runs(shared_dir: Path, limit_runs: int) -> List[Path]:
    runs = [p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")]
    runs = sorted(runs, key=lambda p: p.name)
    if limit_runs > 0:
        runs = runs[-limit_runs:]
    return runs


def build_report(shared_dir: Path, limit_runs: int) -> Dict[str, Any]:
    runs = _iter_runs(shared_dir, limit_runs)
    total_rows = 0
    pending_rows = 0
    resolved_rows = 0
    expired_rows = 0
    bucket_stats = init_bucket_stats()
    run_rows: List[Dict[str, Any]] = []

    for run_dir in runs:
        path = run_dir / "realized_outcomes.json"
        if not path.exists():
            continue
        payload = _load_json(path)
        outcomes = payload.get("outcomes", []) if isinstance(payload.get("outcomes"), list) else []

        run_total = 0
        run_pending = 0
        run_resolved = 0
        run_expired = 0
        run_bucket_stats = init_bucket_stats()
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            run_total += 1
            status = str(row.get("status", "")).upper()
            bucket = resolve_outcome_bucket(row)
            if status == "RESOLVED":
                run_resolved += 1
            elif status == "EXPIRED":
                run_expired += 1
            elif status == "PENDING":
                run_pending += 1
            if bucket in MEASURED_OUTCOME_BUCKETS:
                bucket_row = bucket_stats[bucket]
                bucket_row["total"] += 1
                run_bucket_row = run_bucket_stats[bucket]
                run_bucket_row["total"] += 1
                if status == "RESOLVED":
                    bucket_row["resolved"] += 1
                    run_bucket_row["resolved"] += 1
                elif status == "EXPIRED":
                    bucket_row["expired"] += 1
                    run_bucket_row["expired"] += 1
                elif status == "PENDING":
                    bucket_row["pending"] += 1
                    run_bucket_row["pending"] += 1

        total_rows += run_total
        pending_rows += run_pending
        resolved_rows += run_resolved
        expired_rows += run_expired
        if run_total > 0:
            finalize_bucket_stats(run_bucket_stats)
            run_rows.append(
                {
                    "run_id": run_dir.name,
                    "total": run_total,
                    "resolved": run_resolved,
                    "expired": run_expired,
                    "pending": run_pending,
                    "conversion_rate_pct": round((run_resolved / run_total * 100.0), 2) if run_total > 0 else 0.0,
                    "closure_rate_pct": round(((run_resolved + run_expired) / run_total * 100.0), 2)
                    if run_total > 0
                    else 0.0,
                    "bucket_breakdown": run_bucket_stats,
                }
            )

    conversion_rate_pct = round((resolved_rows / total_rows * 100.0), 2) if total_rows > 0 else 0.0
    pending_ratio_pct = round((pending_rows / total_rows * 100.0), 2) if total_rows > 0 else 0.0
    closure_rate_pct = round(((resolved_rows + expired_rows) / total_rows * 100.0), 2) if total_rows > 0 else 0.0
    finalize_bucket_stats(bucket_stats)
    return {
        "runs_scanned": len(runs),
        "runs_with_outcomes": len(run_rows),
        "total_outcomes": total_rows,
        "resolved_outcomes": resolved_rows,
        "expired_outcomes": expired_rows,
        "pending_outcomes": pending_rows,
        "conversion_rate_pct": conversion_rate_pct,
        "closure_rate_pct": closure_rate_pct,
        "pending_ratio_pct": pending_ratio_pct,
        "bucket_breakdown": bucket_stats,
        "run_breakdown": run_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report realized outcome conversion metrics.")
    parser.add_argument(
        "--shared-dir",
        type=str,
        default="runtime_state/shared_working",
        help="Shared working directory containing RUN-* folders.",
    )
    parser.add_argument(
        "--limit-runs",
        type=int,
        default=200,
        help="Limit number of latest runs to scan.",
    )
    args = parser.parse_args()

    report = build_report(
        shared_dir=Path(args.shared_dir),
        limit_runs=int(args.limit_runs),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
