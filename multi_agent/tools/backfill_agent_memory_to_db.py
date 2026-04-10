from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _read_jsonl(path: Path, limit: int = 0) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except Exception:
                continue
            if limit > 0 and len(rows) >= limit:
                break
    return rows


def run_backfill(base_dir: Path, dry_run: bool = True, limit: int = 0) -> Dict[str, int]:
    runs_path = base_dir / "runs" / "agent_runs.jsonl"
    posts_path = base_dir / "postmortems" / "postmortems.jsonl"
    tickets_path = base_dir / "tickets" / "improvement_tickets.jsonl"
    profiles_path = base_dir / "profile_diagnostics" / "profile_diagnostics.jsonl"
    outcome_health_path = base_dir / "outcome_health" / "outcome_health.jsonl"

    runs = _read_jsonl(runs_path, limit=limit)
    postmortems = _read_jsonl(posts_path, limit=limit)
    tickets = _read_jsonl(tickets_path, limit=limit)
    profiles = _read_jsonl(profiles_path, limit=limit)
    outcome_health_rows = _read_jsonl(outcome_health_path, limit=limit)

    stats = {
        "runs_read": len(runs),
        "postmortems_read": len(postmortems),
        "tickets_read": len(tickets),
        "profiles_read": len(profiles),
        "outcome_health_read": len(outcome_health_rows),
        "runs_written": 0,
        "postmortems_written": 0,
        "tickets_written": 0,
        "profiles_written": 0,
        "outcome_health_written": 0,
    }

    if dry_run:
        return stats

    from modules.db_manager import DBManager

    db = DBManager()
    if not db.client:
        raise RuntimeError("Supabase client unavailable. Check SUPABASE_URL / SUPABASE_KEY.")

    for row in runs:
        ok = db.save_agent_run_summary(row)
        if ok:
            stats["runs_written"] += 1
    run_ids_written = {
        str(row.get("run_id"))
        for row in runs
        if isinstance(row, dict) and row.get("run_id")
    }

    for row in postmortems:
        ok = db.save_agent_postmortem(row)
        if ok:
            stats["postmortems_written"] += 1

    for row in profiles:
        ok = db.save_agent_profile_diagnostics(row)
        if ok:
            stats["profiles_written"] += 1

    for row in outcome_health_rows:
        run_id = str(row.get("run_id") or "").strip()
        if run_id and run_id not in run_ids_written:
            stub_ok = db.save_agent_run_summary(
                {
                    "run_id": run_id,
                    "market": row.get("market"),
                    "strategy_version": "backfill-stub",
                    "model_version": "backfill-stub",
                    "code_version": "backfill-stub",
                    "artifact_refs": {},
                }
            )
            if stub_ok:
                run_ids_written.add(run_id)
                stats["runs_written"] += 1
        ok = db.save_agent_outcome_health(row)
        if ok:
            stats["outcome_health_written"] += 1

    if tickets:
        stats["tickets_written"] = int(db.save_agent_improvement_tickets(tickets) or 0)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill long-term agent memory JSONL into Supabase tables.")
    parser.add_argument(
        "--base-dir",
        type=str,
        default="runtime_state/long_term",
        help="Base directory containing runs/postmortems/tickets JSONL files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and count only. Do not write to DB.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional per-file limit for staged backfill testing.",
    )
    args = parser.parse_args()

    result = run_backfill(
        base_dir=Path(args.base_dir),
        dry_run=bool(args.dry_run),
        limit=int(args.limit),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
