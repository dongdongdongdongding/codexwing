from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_label(ret_3d: float) -> str:
    if ret_3d > 0:
        return "WIN"
    if ret_3d < 0:
        return "LOSS"
    return "FLAT"


def _classify_decision_bucket(decision: Any) -> str:
    value = str(decision or "").strip().upper()
    if value == "EXCEPTION_LEADER":
        return "exception_leader"
    if value in {"WATCHLIST_ONLY", "FALLBACK_WATCHLIST", "WATCHLIST", "OBSERVE"}:
        return "watchlist"
    if value in {"PRIORITY_WATCHLIST"}:
        return "picked"
    return "ignored"


def _iter_target_runs(shared_dir: Path, run_ids: List[str], limit_runs: int) -> List[Path]:
    if run_ids:
        runs = [shared_dir / rid for rid in run_ids]
        return [p for p in runs if p.exists()]

    runs = [p for p in shared_dir.iterdir() if p.is_dir() and p.name.startswith("RUN-")]
    runs = sorted(runs, key=lambda p: p.name)
    if limit_runs > 0:
        runs = runs[-limit_runs:]
    return runs


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)


def _is_eligible_pending(outcome: Dict[str, Any], now_dt: datetime, min_age_days: int, resolve_all: bool) -> bool:
    if str(outcome.get("status", "")).upper() != "PENDING":
        return False
    if resolve_all:
        return True

    rec_dt = _parse_iso(outcome.get("recommended_at"))
    if rec_dt is None:
        return True
    return now_dt >= (rec_dt + timedelta(days=max(0, int(min_age_days))))


def _parse_horizon_days(value: Any, default: int = 3) -> int:
    if value is None:
        return max(1, int(default))
    text = str(value).strip().upper()
    if not text:
        return max(1, int(default))
    if text.startswith("T+"):
        text = text[2:]
    if text.endswith("D"):
        text = text[:-1]
    try:
        return max(1, int(float(text)))
    except Exception:
        return max(1, int(default))


def _is_expired_pending(outcome: Dict[str, Any], now_dt: datetime) -> bool:
    if str(outcome.get("status", "")).upper() != "PENDING":
        return False
    rec_dt = _parse_iso(outcome.get("recommended_at"))
    if rec_dt is None:
        return False
    horizon_days = _parse_horizon_days(outcome.get("horizon"), default=3)
    expiry_dt = rec_dt + timedelta(days=horizon_days)
    return now_dt >= expiry_dt


def _get_local_horizon_return(outcome: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Resolve from locally-computed return metrics when the matching horizon
    metric already exists in realized_outcomes.json.
    """
    horizon_days = _parse_horizon_days(outcome.get("horizon"), default=3)
    metric_map = {
        1: "return_1d_pct",
        2: "return_2d_pct",
        3: "return_3d_pct",
        5: "return_5d_pct",
        7: "return_7d_pct",
        14: "return_14d_pct",
        30: "return_30d_pct",
    }
    metric_name = metric_map.get(horizon_days)
    if not metric_name:
        return None

    value = outcome.get(metric_name)
    if value is None:
        return None
    try:
        ret = float(value)
    except Exception:
        return None

    updated_at = outcome.get("performance_updated_at") or outcome.get("outcome_recorded_at")
    if not updated_at:
        return None

    return {
        "result_pct": ret,
        "metric_name": metric_name,
        "recorded_at": updated_at,
        "horizon_days": horizon_days,
    }


def _append_update_log(base_dir: Path, row: Dict[str, Any]) -> None:
    log_dir = base_dir / "outcomes"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "realized_outcomes_updates.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_update(
    shared_dir: Path,
    run_ids: List[str],
    dry_run: bool,
    min_age_days: int,
    resolve_all: bool,
    limit_runs: int,
    refresh_signal_performance: bool,
    long_term_base_dir: Path,
    allow_expire_without_db: bool,
) -> Dict[str, Any]:
    now_dt = datetime.now(timezone.utc)
    db = None
    db_error = ""
    try:
        from modules.db_manager import DBManager

        db = DBManager()
    except Exception as e:
        db = None
        db_error = str(e)

    if refresh_signal_performance and db is not None:
        try:
            db.update_performance()
        except Exception:
            pass

    db_lookup_ready = False
    if db is not None and getattr(db, "client", None) is not None:
        try:
            db.client.table("signals").select("id").limit(1).execute()
            db_lookup_ready = True
        except Exception as e:
            db_lookup_ready = False
            if not db_error:
                db_error = f"lookup_unavailable:{e}"

    targets = _iter_target_runs(shared_dir=shared_dir, run_ids=run_ids, limit_runs=limit_runs)

    stats: Dict[str, Any] = {
        "runs_seen": len(targets),
        "runs_with_file": 0,
        "outcomes_total": 0,
        "outcomes_pending_checked": 0,
        "outcomes_resolved": 0,
        "outcomes_expired": 0,
        "outcomes_still_pending": 0,
        "outcomes_closed": 0,
        "files_updated": 0,
        "db_rows_upserted": 0,
        "dry_run": bool(dry_run),
        "db_available": bool(db is not None and getattr(db, "client", None) is not None),
        "db_lookup_ready": bool(db_lookup_ready),
        "db_import_error": db_error,
        "pending_skipped_no_db": 0,
        "updated_at": _now_iso(),
        "run_stats": [],
    }

    for run_dir in targets:
        path = run_dir / "realized_outcomes.json"
        payload = _load_json(path)
        if payload is None:
            continue

        stats["runs_with_file"] += 1
        outcomes = payload.get("outcomes", []) if isinstance(payload.get("outcomes"), list) else []

        run_changed = False
        run_total = len(outcomes)
        run_checked = 0
        run_resolved = 0
        run_expired = 0

        for row in outcomes:
            if not isinstance(row, dict):
                continue
            stats["outcomes_total"] += 1
            recalculated_bucket = _classify_decision_bucket(row.get("decision"))
            if row.get("decision_bucket") != recalculated_bucket:
                row["decision_bucket"] = recalculated_bucket
                run_changed = True
            status_value = str(row.get("status", "")).upper()

            # Backfill correction: older runs may have been expired before
            # local horizon returns were computed. Promote them to RESOLVED
            # once the matching horizon metric exists.
            if status_value == "EXPIRED":
                local_resolved = _get_local_horizon_return(row)
                if local_resolved:
                    ret = float(local_resolved["result_pct"])
                    row["status"] = "RESOLVED"
                    row["realized_return_pct"] = round(ret, 6)
                    row["outcome_label"] = _resolve_label(ret)
                    row["outcome_recorded_at"] = _now_iso()
                    row["source_ref"] = f"local_returns:{local_resolved['metric_name']}"
                    row["resolved_signal_created_at"] = row.get("recommended_at")
                    row["resolved_signal_type"] = f"LOCAL_{str(row.get('scan_mode') or 'SCAN').upper()}"
                    row["resolved_stock_name"] = row.get("stock_name")
                    row["local_resolution_metric"] = local_resolved["metric_name"]
                    row["local_resolution_recorded_at"] = local_resolved["recorded_at"]
                    row["local_resolution_horizon_days"] = local_resolved["horizon_days"]
                    row.pop("expiry_reason", None)
                    row.pop("expiry_horizon_days", None)
                    run_changed = True
                    run_resolved += 1
                    stats["outcomes_resolved"] += 1
                continue

            if status_value != "PENDING":
                continue

            expired_pending = _is_expired_pending(row, now_dt=now_dt)
            eligible_pending = _is_eligible_pending(
                row,
                now_dt=now_dt,
                min_age_days=min_age_days,
                resolve_all=resolve_all,
            )
            if not eligible_pending and not expired_pending:
                continue

            if eligible_pending:
                run_checked += 1
                stats["outcomes_pending_checked"] += 1

            ticker = str(row.get("ticker") or "").strip()
            if not ticker:
                continue

            local_resolved = _get_local_horizon_return(row) if eligible_pending else None
            if local_resolved:
                ret = float(local_resolved["result_pct"])
                row["status"] = "RESOLVED"
                row["realized_return_pct"] = round(ret, 6)
                row["outcome_label"] = _resolve_label(ret)
                row["outcome_recorded_at"] = _now_iso()
                row["source_ref"] = f"local_returns:{local_resolved['metric_name']}"
                row["resolved_signal_created_at"] = row.get("recommended_at")
                row["resolved_signal_type"] = f"LOCAL_{str(row.get('scan_mode') or 'SCAN').upper()}"
                row["resolved_stock_name"] = row.get("stock_name")
                row["local_resolution_metric"] = local_resolved["metric_name"]
                row["local_resolution_recorded_at"] = local_resolved["recorded_at"]
                row["local_resolution_horizon_days"] = local_resolved["horizon_days"]
                run_changed = True
                run_resolved += 1
                stats["outcomes_resolved"] += 1
                continue

            if not db_lookup_ready and not bool(allow_expire_without_db):
                stats["pending_skipped_no_db"] += 1
                continue

            recommended_at = row.get("recommended_at")
            resolved = None
            if eligible_pending and db_lookup_ready and db is not None and hasattr(db, "get_latest_resolved_signal_outcome"):
                resolved = db.get_latest_resolved_signal_outcome(ticker=ticker, since_iso=recommended_at)
                if not resolved:
                    # Fallback once without since filter (legacy data may predate this field)
                    resolved = db.get_latest_resolved_signal_outcome(ticker=ticker, since_iso=None)

            if resolved:
                ret_3d = float(resolved.get("result_3d", 0.0) or 0.0)
                row["status"] = "RESOLVED"
                row["realized_return_pct"] = round(ret_3d, 6)
                row["outcome_label"] = _resolve_label(ret_3d)
                row["outcome_recorded_at"] = _now_iso()
                row["source_ref"] = f"signals:{resolved.get('signal_id')}"
                row["resolved_signal_created_at"] = resolved.get("created_at")
                row["resolved_signal_type"] = resolved.get("signal_type")
                row["resolved_stock_name"] = resolved.get("stock_name")

                run_changed = True
                run_resolved += 1
                stats["outcomes_resolved"] += 1
                continue

            if expired_pending and (db_lookup_ready or bool(allow_expire_without_db)):
                row["status"] = "EXPIRED"
                row["outcome_label"] = "EXPIRED"
                row["outcome_recorded_at"] = _now_iso()
                row["realized_return_pct"] = None
                row["expiry_reason"] = "HORIZON_ELAPSED_NO_RESOLUTION"
                row["expiry_horizon_days"] = _parse_horizon_days(row.get("horizon"), default=3)
                run_changed = True
                run_expired += 1
                stats["outcomes_expired"] += 1

        pending_count = 0
        resolved_count = 0
        expired_count = 0
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            status = str(row.get("status", "")).upper()
            if status == "RESOLVED":
                resolved_count += 1
            elif status == "EXPIRED":
                expired_count += 1
            elif status == "PENDING":
                pending_count += 1

        payload["summary"] = {
            "pending_count": pending_count,
            "resolved_count": resolved_count,
            "expired_count": expired_count,
            "last_updated_at": _now_iso(),
        }

        if run_changed and not dry_run:
            _write_json(path, payload)
            stats["files_updated"] += 1
            _append_update_log(
                base_dir=long_term_base_dir,
                row={
                    "run_id": run_dir.name,
                    "resolved_count": run_resolved,
                    "expired_count": run_expired,
                    "checked_pending": run_checked,
                    "updated_at": _now_iso(),
                    "source": "update_realized_outcomes",
                },
            )

        if not dry_run and db is not None and hasattr(db, "save_agent_realized_outcomes"):
            try:
                upserted = int(
                    db.save_agent_realized_outcomes(
                        run_id=run_dir.name,
                        outcomes=outcomes,
                    )
                    or 0
                )
                stats["db_rows_upserted"] += upserted
            except Exception:
                pass

        stats["run_stats"].append(
            {
                "run_id": run_dir.name,
                "outcomes_total": run_total,
                "pending_checked": run_checked,
                "resolved": run_resolved,
                "expired": run_expired,
                "pending_after": pending_count,
                "resolved_after": resolved_count,
                "expired_after": expired_count,
                "changed": bool(run_changed),
            }
        )

    pending_after_sum = 0
    for row in stats.get("run_stats", []):
        if isinstance(row, dict):
            pending_after_sum += int(row.get("pending_after", 0) or 0)
    stats["outcomes_still_pending"] = max(0, int(pending_after_sum))
    stats["outcomes_closed"] = int(stats.get("outcomes_resolved", 0) or 0) + int(stats.get("outcomes_expired", 0) or 0)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Update realized_outcomes.json from resolved signal results.")
    parser.add_argument(
        "--shared-dir",
        type=str,
        default="runtime_state/shared_working",
        help="Shared working directory containing RUN-* folders.",
    )
    parser.add_argument(
        "--run-id",
        action="append",
        default=[],
        help="Target run id(s). Can be specified multiple times.",
    )
    parser.add_argument(
        "--limit-runs",
        type=int,
        default=0,
        help="Limit number of latest runs when --run-id is not provided.",
    )
    parser.add_argument(
        "--min-age-days",
        type=int,
        default=3,
        help="Only resolve PENDING rows older than N days unless --resolve-all is set.",
    )
    parser.add_argument(
        "--resolve-all",
        action="store_true",
        help="Ignore age gate and try resolving all pending rows.",
    )
    parser.add_argument(
        "--refresh-signal-performance",
        action="store_true",
        help="Run DBManager.update_performance() before resolving outcomes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; only print resolution stats.",
    )
    parser.add_argument(
        "--long-term-base-dir",
        type=str,
        default="runtime_state/long_term",
        help="Base dir for outcome update JSONL logs.",
    )
    parser.add_argument(
        "--allow-expire-without-db",
        action="store_true",
        help="Allow horizon-based EXPIRED transitions even when DB lookup health check is unavailable.",
    )
    args = parser.parse_args()

    result = run_update(
        shared_dir=Path(args.shared_dir),
        run_ids=list(args.run_id or []),
        dry_run=bool(args.dry_run),
        min_age_days=int(args.min_age_days),
        resolve_all=bool(args.resolve_all),
        limit_runs=int(args.limit_runs),
        refresh_signal_performance=bool(args.refresh_signal_performance),
        long_term_base_dir=Path(args.long_term_base_dir),
        allow_expire_without_db=bool(args.allow_expire_without_db),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
