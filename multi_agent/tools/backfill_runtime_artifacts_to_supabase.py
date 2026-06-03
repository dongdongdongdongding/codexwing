from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_ARTIFACT_ROOT = PROJECT_ROOT / "runtime_state" / "artifacts"
DEFAULT_SHARED_ROOT = PROJECT_ROOT / "runtime_state" / "shared_working"
DEFAULT_TOP_DEEP_ROOT = PROJECT_ROOT / "runtime_state" / "reports" / "top_deep"


def _load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.local")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _verify_supabase_reads(db: Any, market_filter: str = "", limit_runs: int = 5) -> Dict[str, Any]:
    market = str(market_filter or "").upper()
    summary_rows = db.list_runtime_artifacts(
        artifact_key="scan_pipeline_summary",
        market=market or None,
        limit=max(1, int(limit_runs or 5)),
    )
    samples = []
    for row in summary_rows:
        run_id = row.get("run_id")
        sample: Dict[str, Any] = {
            "run_id": run_id,
            "market": row.get("market"),
            "scan_mode": row.get("scan_mode"),
            "summary_payload_type": type(row.get("payload")).__name__,
            "summary_has_payload": isinstance(row.get("payload"), dict),
            "summary_updated_at": row.get("updated_at"),
        }
        for key in ["raw_scan_results", "top_deep_reports", "scanner_handoff", "planner_handoff"]:
            artifact = db.fetch_runtime_artifact(run_id, key)
            payload = artifact.get("payload") if isinstance(artifact, dict) else None
            sample[f"{key}_present"] = bool(artifact)
            sample[f"{key}_payload_type"] = type(payload).__name__ if artifact else ""
        samples.append(sample)
    return {
        "ok": bool(summary_rows),
        "market": market or "ALL",
        "summary_rows_checked": len(summary_rows),
        "samples": samples,
    }


def main() -> int:
    _load_env()
    parser = argparse.ArgumentParser(description="Backfill local runtime artifacts into Supabase runtime_artifacts.")
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--shared-root", default=str(DEFAULT_SHARED_ROOT))
    parser.add_argument("--top-deep-root", default=str(DEFAULT_TOP_DEEP_ROOT))
    parser.add_argument("--limit-runs", type=int, default=0, help="0 means all runs.")
    parser.add_argument("--market", default="", help="Optional KOSPI/KOSDAQ/NASDAQ filter.")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("AG_RUNTIME_ARTIFACT_BACKFILL_BATCH_SIZE", "25") or 25))
    parser.add_argument(
        "--max-batch-bytes",
        type=int,
        default=int(os.getenv("AG_RUNTIME_ARTIFACT_BACKFILL_MAX_BATCH_BYTES", "1500000") or 1500000),
        help="Flush before one HTTP upsert body gets too large.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-read", action="store_true", help="Only verify Supabase runtime_artifacts read path.")
    args = parser.parse_args()

    from modules.db_manager import DBManager
    from modules.runtime_artifact_store import build_runtime_artifact_row_from_path, iter_standard_run_artifact_paths

    artifact_root = Path(args.artifact_root)
    shared_root = Path(args.shared_root)
    top_deep_root = Path(args.top_deep_root)
    market_filter = str(args.market or "").upper()
    db = None if args.dry_run else DBManager()
    if not args.dry_run and not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable. Check SUPABASE_URL/SUPABASE_KEY in .env.local.")
    if args.verify_read:
        result = _verify_supabase_reads(db, market_filter=market_filter, limit_runs=max(1, int(args.limit_runs or 5)))
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result.get("ok") else 2

    summary: Dict[str, Any] = {
        "dry_run": bool(args.dry_run),
        "artifact_root": str(artifact_root),
        "shared_root": str(shared_root),
        "top_deep_root": str(top_deep_root),
        "limit_runs": int(args.limit_runs or 0),
        "batch_size": max(1, int(args.batch_size or 25)),
        "max_batch_bytes": max(100_000, int(args.max_batch_bytes or 1_500_000)),
        "market": market_filter or "ALL",
        "runs_seen": 0,
        "runs_matched": 0,
        "artifacts_seen": 0,
        "artifacts_upserted": 0,
        "artifacts_failed": 0,
        "batches_attempted": 0,
        "batches_succeeded": 0,
        "batches_failed": 0,
        "failed": [],
    }
    batch = []
    batch_bytes = 0

    def flush_batch() -> None:
        nonlocal batch, batch_bytes
        if not batch:
            return
        summary["batches_attempted"] += 1
        if args.dry_run:
            batch = []
            batch_bytes = 0
            return
        started = time.time()
        try:
            upserted = db.upsert_runtime_artifacts(batch)
            summary["artifacts_upserted"] += _safe_int(upserted, 0)
            if upserted != len(batch):
                summary["artifacts_failed"] += len(batch) - _safe_int(upserted, 0)
                summary["batches_failed"] += 1
            else:
                summary["batches_succeeded"] += 1
            print(
                json.dumps(
                    {
                        "event": "runtime_artifact_batch_upserted",
                        "batch": summary["batches_attempted"],
                        "rows": len(batch),
                        "upserted": upserted,
                        "bytes": batch_bytes,
                        "elapsed_sec": round(time.time() - started, 2),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )
        except Exception as exc:
            summary["artifacts_failed"] += len(batch)
            summary["batches_failed"] += 1
            if len(summary["failed"]) < 20:
                summary["failed"].append({"batch_size": len(batch), "error": str(exc)})
            print(
                json.dumps(
                    {
                        "event": "runtime_artifact_batch_failed",
                        "batch": summary["batches_attempted"],
                        "rows": len(batch),
                        "bytes": batch_bytes,
                        "elapsed_sec": round(time.time() - started, 2),
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )
        batch = []
        batch_bytes = 0

    for run_id, run_summary, paths in iter_standard_run_artifact_paths(
        artifact_root=artifact_root,
        shared_root=shared_root,
        top_deep_root=top_deep_root,
        limit_runs=max(0, int(args.limit_runs or 0)),
    ):
        summary["runs_seen"] += 1
        market = str(run_summary.get("market") or "").upper()
        if market_filter and market != market_filter:
            continue
        summary["runs_matched"] += 1
        scan_mode = str(run_summary.get("scan_mode") or "SWING").upper()
        for key, path in sorted(paths.items()):
            if not path.exists() or not path.is_file():
                continue
            summary["artifacts_seen"] += 1
            if not args.dry_run:
                try:
                    row = build_runtime_artifact_row_from_path(
                        run_id=run_id,
                        artifact_key=key,
                        path=path,
                        market=market,
                        scan_mode=scan_mode,
                        source="runtime_backfill",
                        metadata={"backfill_tool": "backfill_runtime_artifacts_to_supabase"},
                    )
                    row_bytes = _safe_int(row.get("size_bytes"), 0)
                    if batch and (
                        len(batch) >= summary["batch_size"]
                        or batch_bytes + row_bytes > summary["max_batch_bytes"]
                    ):
                        flush_batch()
                    batch.append(row)
                    batch_bytes += row_bytes
                except Exception as exc:
                    summary["artifacts_failed"] += 1
                    if len(summary["failed"]) < 20:
                        summary["failed"].append(
                            {
                                "run_id": run_id,
                                "artifact_key": key,
                                "path": str(path),
                                "error": str(exc),
                            }
                        )
                if len(batch) >= summary["batch_size"] or batch_bytes >= summary["max_batch_bytes"]:
                    flush_batch()

    flush_batch()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["artifacts_failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
