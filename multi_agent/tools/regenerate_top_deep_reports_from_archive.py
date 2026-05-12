#!/usr/bin/env python3
"""Regenerate Top Deep Reports from Supabase archive rows for recent runs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager
from modules.top_deep_report import generate_and_store_top_deep_reports
from multi_agent.tools.verify_scan_archive_top_consistency import _load_planner


def _db_rows_for_run(db: DBManager, run_id: str, bucket: str) -> List[Dict[str, Any]]:
    q = db.client.table("market_scan_results").select("*").eq("run_id", run_id)
    db_bucket = "watchlist" if bucket == "watchlist_field" else bucket
    if db_bucket and db_bucket != "all":
        q = q.eq("decision_bucket", db_bucket)
    return q.order("priority_rank", desc=False).execute().data or []


def regenerate(*, shared_dir: Path, limit_runs: int, top_n: int, bucket: str, write_db: bool) -> Dict[str, Any]:
    db = DBManager()
    if not db.client:
        raise RuntimeError("Supabase client unavailable.")
    run_dirs = sorted(
        [d for d in shared_dir.iterdir() if d.is_dir() and d.name.startswith("RUN-")],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )[:limit_runs]
    stats: Dict[str, Any] = {"runs_seen": len(run_dirs), "runs_regenerated": 0, "reports": []}
    for run_dir in run_dirs:
        planner = _load_planner(run_dir)
        if not planner:
            continue
        ctx = planner.get("run_context") or {}
        run_id = str(ctx.get("run_id") or run_dir.name)
        rows = _db_rows_for_run(db, run_id, bucket=bucket)
        if not rows:
            continue
        market = str(ctx.get("market") or (rows[0].get("market") if rows else "") or "")
        scan_mode = str(ctx.get("scan_mode") or (rows[0].get("scan_mode") if rows else "") or "SWING")
        result = generate_and_store_top_deep_reports(
            scan_rows=rows,
            planner_payload=planner,
            run_id=run_id,
            market=market,
            scan_mode=scan_mode,
            top_n=top_n,
            write_db=write_db,
        )
        stats["runs_regenerated"] += 1
        stats["reports"].append({"run_id": run_id, **result})
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", default="runtime_state/shared_working")
    parser.add_argument("--limit-runs", type=int, default=10)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--bucket", default="watchlist_field")
    parser.add_argument("--no-db", action="store_true")
    args = parser.parse_args()
    result = regenerate(
        shared_dir=Path(args.shared_dir),
        limit_runs=int(args.limit_runs),
        top_n=int(args.top_n),
        bucket=str(args.bucket),
        write_db=not bool(args.no_db),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
