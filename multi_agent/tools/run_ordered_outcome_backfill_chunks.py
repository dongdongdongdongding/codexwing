#!/usr/bin/env python3
"""Run ordered outcome-label backfill in resumable chunks.

The underlying updater fetches external OHLCV data. Large historical windows can
therefore look stalled before the first final JSON report is printed. This
wrapper keeps the operational unit small: it runs a few RUN-* artifacts at a
time, prints chunk progress, retries failed chunks, and writes a resumable state
file.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from multi_agent.tools.update_outcome_return_metrics import _iter_runs, run_update


DEFAULT_OUTPUT = PROJECT_ROOT / "runtime_state/reports/validation/ordered_outcome_backfill_chunks_latest.json"
COUNT_KEYS = (
    "runs_seen",
    "runs_with_file",
    "rows_seen",
    "rows_updated",
    "daily_rows_updated",
    "intraday_rows_attempted",
    "intraday_rows_updated",
    "rows_without_daily_history",
    "files_updated",
    "tickers_with_history",
    "db_rows_upserted",
    "scan_archive_rows_synced",
    "post_scan_ledger_rows_upserted",
)


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)


def _emit(event: str, payload: Dict[str, Any]) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=False, sort_keys=True), flush=True)


def chunk_run_ids(run_ids: Iterable[str], chunk_size: int) -> List[List[str]]:
    size = max(1, int(chunk_size))
    values = [str(run_id) for run_id in run_ids if str(run_id).strip()]
    return [values[idx : idx + size] for idx in range(0, len(values), size)]


def aggregate_reports(reports: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {key: 0 for key in COUNT_KEYS}
    out["intraday_fetch_failures"] = {"isoformat_parse": 0, "empty_response": 0, "other_exc": 0}
    for report in reports:
        if not isinstance(report, dict):
            continue
        for key in COUNT_KEYS:
            out[key] += int(report.get(key) or 0)
        failures = report.get("intraday_fetch_failures") if isinstance(report.get("intraday_fetch_failures"), dict) else {}
        for key in out["intraday_fetch_failures"]:
            out["intraday_fetch_failures"][key] += int(failures.get(key) or 0)
    return out


def _target_run_ids(shared_dir: Path, explicit_run_ids: List[str], limit_runs: int) -> List[str]:
    runs = _iter_runs(shared_dir=shared_dir, run_ids=explicit_run_ids, limit_runs=limit_runs)
    return [run_dir.name for run_dir in runs]


def run_chunks(
    *,
    shared_dir: Path,
    run_ids: List[str],
    limit_runs: int,
    chunk_size: int,
    max_chunks: int,
    retries: int,
    sleep_seconds: float,
    dry_run: bool,
    scan_mode_filter: str,
    output: Path,
    resume: bool,
) -> Dict[str, Any]:
    all_run_ids = _target_run_ids(shared_dir, run_ids, limit_runs)
    previous = _load_json(output) if resume and not dry_run else {}
    completed = set(previous.get("completed_run_ids") or [])
    pending_run_ids = [run_id for run_id in all_run_ids if run_id not in completed]
    chunks = chunk_run_ids(pending_run_ids, chunk_size)
    if max_chunks > 0:
        chunks = chunks[: max_chunks]

    chunk_reports: List[Dict[str, Any]] = list(previous.get("chunk_reports") or []) if resume and not dry_run else []
    failures: List[Dict[str, Any]] = list(previous.get("failures") or []) if resume and not dry_run else []
    started_at = datetime.now(timezone.utc).isoformat()
    _emit(
        "backfill_start",
        {
            "total_run_ids": len(all_run_ids),
            "pending_run_ids": len(pending_run_ids),
            "chunk_count": len(chunks),
            "chunk_size": max(1, int(chunk_size)),
            "dry_run": bool(dry_run),
            "resume": bool(resume),
        },
    )

    for idx, chunk in enumerate(chunks, start=1):
        attempt = 0
        while True:
            attempt += 1
            _emit("chunk_start", {"chunk_index": idx, "attempt": attempt, "run_ids": chunk})
            try:
                report = run_update(
                    shared_dir=shared_dir,
                    run_ids=chunk,
                    limit_runs=0,
                    dry_run=dry_run,
                    scan_mode_filter=scan_mode_filter,
                )
                chunk_record = {
                    "chunk_index": idx,
                    "attempt": attempt,
                    "run_ids": chunk,
                    "report": report,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
                chunk_reports.append(chunk_record)
                completed.update(chunk)
                _emit("chunk_done", chunk_record)
                if not dry_run:
                    _write_json(
                        output,
                        {
                            "started_at": started_at,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                            "dry_run": bool(dry_run),
                            "scan_mode_filter": scan_mode_filter,
                            "completed_run_ids": sorted(completed),
                            "pending_run_ids": [run_id for run_id in all_run_ids if run_id not in completed],
                            "chunk_reports": chunk_reports,
                            "failures": failures,
                            "summary": aggregate_reports([item.get("report", {}) for item in chunk_reports]),
                        },
                    )
                break
            except Exception as exc:
                failure = {
                    "chunk_index": idx,
                    "attempt": attempt,
                    "run_ids": chunk,
                    "error": str(exc),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                }
                _emit("chunk_failed", failure)
                if attempt > max(0, int(retries)):
                    failures.append(failure)
                    if not dry_run:
                        _write_json(
                            output,
                            {
                                "started_at": started_at,
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                                "dry_run": bool(dry_run),
                                "scan_mode_filter": scan_mode_filter,
                                "completed_run_ids": sorted(completed),
                                "pending_run_ids": [run_id for run_id in all_run_ids if run_id not in completed],
                                "chunk_reports": chunk_reports,
                                "failures": failures,
                                "summary": aggregate_reports([item.get("report", {}) for item in chunk_reports]),
                            },
                        )
                    break
                if sleep_seconds > 0:
                    time.sleep(float(sleep_seconds))

    summary = {
        "started_at": started_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": bool(dry_run),
        "scan_mode_filter": scan_mode_filter,
        "total_run_ids": len(all_run_ids),
        "completed_run_ids": sorted(completed),
        "pending_run_ids": [run_id for run_id in all_run_ids if run_id not in completed],
        "chunk_reports": chunk_reports,
        "failures": failures,
        "summary": aggregate_reports([item.get("report", {}) for item in chunk_reports]),
    }
    _emit("backfill_done", {"summary": summary["summary"], "failures": len(failures), "output": str(output)})
    if not dry_run:
        _write_json(output, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", type=str, default="runtime_state/shared_working")
    parser.add_argument("--run-id", action="append", default=[])
    parser.add_argument("--limit-runs", type=int, default=50)
    parser.add_argument("--chunk-size", type=int, default=3)
    parser.add_argument("--max-chunks", type=int, default=0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=float, default=2.0)
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="SWING")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    report = run_chunks(
        shared_dir=Path(args.shared_dir),
        run_ids=list(args.run_id or []),
        limit_runs=int(args.limit_runs),
        chunk_size=int(args.chunk_size),
        max_chunks=int(args.max_chunks),
        retries=int(args.retries),
        sleep_seconds=float(args.sleep_seconds),
        dry_run=bool(args.dry_run),
        scan_mode_filter=str(args.scan_mode).upper(),
        output=Path(args.output),
        resume=not bool(args.no_resume),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
