#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.db_manager import DBManager
from modules.db_schema import DEFAULT_FALLBACK_KEYS, build_scan_result_payload


REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"
DEFAULT_VALIDATION_FILES = (
    REPORT_DIR / "kis_operational_scan_all_swing_latest.json",
    REPORT_DIR / "kis_operational_scan_all_intraday_latest.json",
)
MARKET_REQUIRED_FIELDS = (
    "ticker",
    "stock_name",
    "market",
    "market_type",
    "scan_mode",
    "run_id",
    "alpha_score",
    "tech_score",
    "ml_prob",
    "whale_score",
    "decision_score",
    "volume_ratio",
    "entry_reference_price",
    "feature_origin",
    "feature_quality",
    "feature_completeness",
    "validation_excluded",
    "is_dummy_data",
    "foreigner_1d",
    "institution_1d",
    "retail_1d",
    "foreigner_3d",
    "institution_3d",
    "retail_3d",
    "foreigner_10d",
    "institution_10d",
    "retail_10d",
    "flow_asof",
)
SNAPSHOT_REQUIRED_FIELDS = (
    "snapshot_key",
    "run_id",
    "ticker",
    "market",
    "scan_mode",
    "row_role",
    "passed_current_model",
    "base_trade_date",
    "feature_snapshot",
    "normalized_feature_version",
)
RUNTIME_REQUIRED_ARTIFACTS = (
    "scan_pipeline_summary",
    "raw_scan_results",
    "observed_factor_snapshots",
    "scan_integrity_report",
    "scanner_handoff",
    "aggregation_handoff",
    "backtest_handoff",
    "market_context_handoff",
    "planner_handoff",
    "run_manifest",
    "top_deep_reports",
)
DEEP_REQUIRED_FIELDS = (
    "report_id",
    "report_version",
    "run_id",
    "market",
    "scan_mode",
    "ticker",
    "candidate_data_quality",
    "entry_readiness_contract",
    "scan_universe_admission",
    "trade_plan",
)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {"none", "null", "nan"}
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def _missing_counts(rows: Iterable[Dict[str, Any]], fields: Iterable[str]) -> Dict[str, int]:
    counts = {field: 0 for field in fields}
    for row in rows:
        for field in fields:
            if not _present(row.get(field)):
                counts[field] += 1
    return counts


def _validation_summaries(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload["_validation_path"] = str(path)
            summaries.append(payload)
    return summaries


def _runs_from_summaries(summaries: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for summary in summaries:
        for market_run in summary.get("market_runs") or []:
            run_summary = market_run.get("summary") if isinstance(market_run.get("summary"), dict) else {}
            run_id = str(run_summary.get("run_id") or market_run.get("run_id") or "").strip()
            if not run_id or run_id in seen:
                continue
            seen.add(run_id)
            runs.append(
                {
                    "run_id": run_id,
                    "market": str(run_summary.get("market") or market_run.get("market") or "").upper(),
                    "scan_mode": str(run_summary.get("scan_mode") or summary.get("scan_mode") or "").upper(),
                    "result_count": int(run_summary.get("result_count") or 0),
                    "total_scans": int(run_summary.get("total_scans") or 0),
                    "filtered_count": int(run_summary.get("filtered_count") or 0),
                    "validation_path": summary.get("_validation_path"),
                }
            )
    return runs


def _fetch_in_batches(db: DBManager, table: str, run_ids: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx in range(0, len(run_ids), 20):
        chunk = run_ids[idx : idx + 20]
        if not chunk:
            continue
        batch = db.client.table(table).select("*").in_("run_id", chunk).execute().data or []
        rows.extend([row for row in batch if isinstance(row, dict)])
    return rows


def _fetch_recent_kr_archive_rows(db: DBManager, exclude_run_ids: set[str], limit: int) -> List[Dict[str, Any]]:
    rows = (
        db.client.table("market_scan_results")
        .select("*")
        .eq("market_type", "KR")
        .order("created_at", desc=True)
        .limit(max(1, int(limit)))
        .execute()
        .data
        or []
    )
    return [row for row in rows if isinstance(row, dict) and str(row.get("run_id") or "") not in exclude_run_ids]


def _raw_artifact_rows(run_id: str) -> Dict[str, Dict[str, Any]]:
    path = PROJECT_ROOT / "runtime_state" / "artifacts" / str(run_id) / "raw_scan_results.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("results") or payload.get("rows") or payload.get("results_sorted") or []
        if not rows and isinstance(payload.get("scan_result"), dict):
            rows = payload["scan_result"].get("results") or []
    else:
        rows = []
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or row.get("티커") or "").strip().upper()
        if ticker:
            indexed[ticker] = row
    return indexed


def _market_row_needs_repair(row: Dict[str, Any]) -> bool:
    for field in MARKET_REQUIRED_FIELDS:
        if not _present(row.get(field)):
            return True
    if _truthy(row.get("validation_excluded")):
        return True
    if str(row.get("feature_quality") or "").lower() != "complete":
        return True
    return False


def _repair_market_scan_rows(db: DBManager, market_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    repaired = 0
    skipped: List[Dict[str, Any]] = []
    raw_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for existing in market_rows:
        if not _market_row_needs_repair(existing):
            continue
        run_id = str(existing.get("run_id") or "").strip()
        ticker = str(existing.get("ticker") or "").strip().upper()
        if not run_id or not ticker or not existing.get("id"):
            skipped.append({"run_id": run_id, "ticker": ticker, "reason": "missing_identity"})
            continue
        if run_id not in raw_cache:
            raw_cache[run_id] = _raw_artifact_rows(run_id)
        raw_row = raw_cache.get(run_id, {}).get(ticker)
        if not raw_row:
            skipped.append({"run_id": run_id, "ticker": ticker, "reason": "raw_artifact_row_missing"})
            continue
        schema_data = {
            **raw_row,
            "ticker": raw_row.get("ticker") or raw_row.get("티커") or existing.get("ticker"),
            "name": raw_row.get("name") or raw_row.get("stock_name") or raw_row.get("종목명") or existing.get("stock_name"),
            "market_type": existing.get("market_type") or raw_row.get("market_type") or "KR",
            "scan_mode": existing.get("scan_mode") or raw_row.get("scan_mode"),
            "run_id": run_id,
            "initial_trend": raw_row.get("initial_trend") or raw_row.get("trend") or raw_row.get("추세"),
            "ml_prob": raw_row.get("ml_prob") or raw_row.get("_prob_5"),
            "prob_clean": raw_row.get("prob_clean") or raw_row.get("_prob_clean"),
            "position": raw_row.get("position") or raw_row.get("위치"),
            "tier": raw_row.get("tier") or raw_row.get("Tier"),
            "note": raw_row.get("note") or raw_row.get("전략"),
            "leader_metrics": raw_row.get("leader_metrics") or raw_row.get("_leader_metrics"),
            "feature_snapshot": raw_row.get("feature_snapshot")
            or (
                {
                    "ticker": raw_row.get("ticker") or raw_row.get("티커"),
                    "stock_name": raw_row.get("stock_name") or raw_row.get("종목명"),
                    "market": existing.get("market") or raw_row.get("market"),
                    "scan_mode": existing.get("scan_mode") or raw_row.get("scan_mode"),
                    "kis_sidecar": raw_row.get("_kis_sidecar"),
                    "leader_metrics": raw_row.get("_leader_metrics"),
                }
                if raw_row.get("_kis_sidecar") or raw_row.get("_leader_metrics")
                else None
            ),
        }
        overrides = {
            "run_id": run_id,
            "market": existing.get("market"),
            "market_type": existing.get("market_type") or "KR",
            "recommended_at": existing.get("recommended_at"),
            "is_dummy_data": False,
        }
        payload = build_scan_result_payload(schema_data, overrides=overrides, fallback_keys=DEFAULT_FALLBACK_KEYS)
        payload.update(db._feature_quality_payload(payload, origin=payload.get("feature_origin") or "scanner_full"))
        payload = db._filter_payload_to_existing_columns("market_scan_results", payload)
        if not payload:
            skipped.append({"run_id": run_id, "ticker": ticker, "reason": "payload_empty"})
            continue
        db._update_by_id_with_schema_drift_retry("market_scan_results", existing["id"], payload)
        repaired += 1
    return {"repaired_rows": repaired, "skipped": skipped}


def _type_profile(rows: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    profile: Dict[str, set[str]] = defaultdict(set)
    for row in rows:
        for key, value in row.items():
            if value is not None:
                profile[key].add(_type_name(value))
    return {key: sorted(values) for key, values in sorted(profile.items())}


def _type_mismatches(kis_rows: List[Dict[str, Any]], legacy_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    kis_profile = _type_profile(kis_rows)
    legacy_profile = _type_profile(legacy_rows)
    mismatches: List[Dict[str, Any]] = []
    for key in sorted(set(kis_profile) & set(legacy_profile)):
        kis_types = set(kis_profile.get(key) or [])
        legacy_types = set(legacy_profile.get(key) or [])
        if kis_types and legacy_types and kis_types.isdisjoint(legacy_types):
            mismatches.append(
                {
                    "column": key,
                    "kis_types": sorted(kis_types),
                    "legacy_types": sorted(legacy_types),
                }
            )
    return mismatches


def _market_scan_report(kis_rows: List[Dict[str, Any]], legacy_rows: List[Dict[str, Any]], expected_result_rows: int) -> Dict[str, Any]:
    missing = _missing_counts(kis_rows, MARKET_REQUIRED_FIELDS)
    missing_nonzero = {key: value for key, value in missing.items() if value}
    dummy_rows = [row for row in kis_rows if _truthy(row.get("is_dummy_data"))]
    excluded_rows = [row for row in kis_rows if _truthy(row.get("validation_excluded"))]
    incomplete_rows = [row for row in kis_rows if str(row.get("feature_quality") or "").lower() != "complete"]
    type_mismatches = _type_mismatches(kis_rows, legacy_rows)
    return {
        "table": "market_scan_results",
        "expected_result_rows": expected_result_rows,
        "kis_rows": len(kis_rows),
        "legacy_compare_rows": len(legacy_rows),
        "row_count_ok": len(kis_rows) >= expected_result_rows,
        "required_missing_counts": missing_nonzero,
        "dummy_rows": len(dummy_rows),
        "validation_excluded_rows": len(excluded_rows),
        "feature_incomplete_rows": len(incomplete_rows),
        "type_mismatches": type_mismatches,
        "ok": (
            len(kis_rows) >= expected_result_rows
            and not missing_nonzero
            and not dummy_rows
            and not excluded_rows
            and not incomplete_rows
            and not type_mismatches
        ),
    }


def _snapshot_report(rows: List[Dict[str, Any]], runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    expected = sum(int(run.get("total_scans") or 0) for run in runs)
    missing = _missing_counts(rows, SNAPSHOT_REQUIRED_FIELDS)
    missing_nonzero = {key: value for key, value in missing.items() if value}
    by_run = Counter(str(row.get("run_id") or "") for row in rows)
    role_counts = Counter(str(row.get("row_role") or "") for row in rows)
    empty_feature_snapshot_rows = [row for row in rows if not isinstance(row.get("feature_snapshot"), dict) or not row.get("feature_snapshot")]
    return {
        "table": "scan_universe_snapshots",
        "expected_rows": expected,
        "kis_rows": len(rows),
        "rows_by_run": dict(by_run),
        "rows_by_role": dict(role_counts),
        "row_count_ok": len(rows) >= expected,
        "required_missing_counts": missing_nonzero,
        "empty_feature_snapshot_rows": len(empty_feature_snapshot_rows),
        "ok": len(rows) >= expected and not missing_nonzero and not empty_feature_snapshot_rows,
    }


def _runtime_report(rows: List[Dict[str, Any]], run_ids: List[str]) -> Dict[str, Any]:
    by_run: Dict[str, set[str]] = defaultdict(set)
    bad_payload_rows = 0
    for row in rows:
        by_run[str(row.get("run_id") or "")].add(str(row.get("artifact_key") or ""))
        if not _present(row.get("payload")) and not _present(row.get("content_text")):
            bad_payload_rows += 1
    missing_by_run = {
        run_id: sorted(set(RUNTIME_REQUIRED_ARTIFACTS) - by_run.get(run_id, set()))
        for run_id in run_ids
    }
    missing_by_run = {key: value for key, value in missing_by_run.items() if value}
    return {
        "table": "runtime_artifacts",
        "kis_rows": len(rows),
        "artifacts_by_run": {key: len(value) for key, value in sorted(by_run.items())},
        "missing_required_artifacts_by_run": missing_by_run,
        "empty_payload_rows": bad_payload_rows,
        "ok": not missing_by_run and bad_payload_rows == 0,
    }


def _deep_report(rows: List[Dict[str, Any]], runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    missing = _missing_counts(rows, DEEP_REQUIRED_FIELDS)
    missing_nonzero = {key: value for key, value in missing.items() if value}
    by_run = Counter(str(row.get("run_id") or "") for row in rows)
    expected_min = sum(1 for run in runs if int(run.get("total_scans") or 0) > 0)
    return {
        "table": "scan_deep_reports",
        "kis_rows": len(rows),
        "rows_by_run": dict(by_run),
        "required_missing_counts": missing_nonzero,
        "row_count_ok": len(rows) >= expected_min,
        "ok": len(rows) >= expected_min and not missing_nonzero,
    }


def build_report(validation_files: Iterable[Path], legacy_limit: int, *, repair_market_scan_results: bool = False) -> Dict[str, Any]:
    summaries = _validation_summaries(validation_files)
    runs = _runs_from_summaries(summaries)
    run_ids = [run["run_id"] for run in runs]
    if not run_ids:
        raise SystemExit("No KIS validation run ids found.")
    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")

    market_rows = _fetch_in_batches(db, "market_scan_results", run_ids)
    repair_result = {"repaired_rows": 0, "skipped": []}
    if repair_market_scan_results:
        repair_result = _repair_market_scan_rows(db, market_rows)
        market_rows = _fetch_in_batches(db, "market_scan_results", run_ids)

    snapshot_rows = _fetch_in_batches(db, "scan_universe_snapshots", run_ids)
    runtime_rows = _fetch_in_batches(db, "runtime_artifacts", run_ids)
    deep_rows = _fetch_in_batches(db, "scan_deep_reports", run_ids)
    legacy_rows = _fetch_recent_kr_archive_rows(db, set(run_ids), legacy_limit)
    expected_result_rows = sum(int(run.get("result_count") or 0) for run in runs)

    market_report = _market_scan_report(market_rows, legacy_rows, expected_result_rows)
    snapshot_report = _snapshot_report(snapshot_rows, runs)
    runtime_report = _runtime_report(runtime_rows, run_ids)
    deep_report = _deep_report(deep_rows, runs)
    table_reports = [market_report, snapshot_report, runtime_report, deep_report]
    compatibility_ok = all(report.get("ok") for report in table_reports)

    warnings: List[str] = []
    if any(int(run.get("result_count") or 0) == 0 for run in runs):
        warnings.append("some_kis_market_runs_had_zero_pass_results_but_snapshot_rejected_rows_persisted")
    if snapshot_report.get("kis_rows", 0) > 0 and snapshot_report.get("rows_by_role", {}).get("rejected", 0) > 0:
        warnings.append("scan_universe_snapshots_contains_rejected_rows_as_expected_for_learning")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "verify_kis_supabase_compatibility",
        "validation_files": [str(path) for path in validation_files],
        "kis_runs": runs,
        "run_ids": run_ids,
        "compatibility_ok": compatibility_ok,
        "repair": repair_result,
        "warnings": warnings,
        "tables": {
            "market_scan_results": market_report,
            "scan_universe_snapshots": snapshot_report,
            "runtime_artifacts": runtime_report,
            "scan_deep_reports": deep_report,
        },
    }


def _write_markdown(report: Dict[str, Any], path: Path) -> None:
    lines = [
        "# KIS Supabase Compatibility",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- compatibility_ok: `{report.get('compatibility_ok')}`",
        f"- run_ids: `{', '.join(report.get('run_ids') or [])}`",
        f"- warnings: `{', '.join(report.get('warnings') or []) or 'none'}`",
        "",
        "## Tables",
    ]
    for table, payload in (report.get("tables") or {}).items():
        lines.extend(
            [
                f"### {table}",
                f"- ok: `{payload.get('ok')}`",
                f"- kis_rows: `{payload.get('kis_rows')}`",
            ]
        )
        for key in (
            "expected_result_rows",
            "expected_rows",
            "row_count_ok",
            "required_missing_counts",
            "dummy_rows",
            "validation_excluded_rows",
            "feature_incomplete_rows",
            "type_mismatches",
            "missing_required_artifacts_by_run",
            "empty_payload_rows",
            "rows_by_run",
            "rows_by_role",
            "artifacts_by_run",
        ):
            if key in payload:
                lines.append(f"- {key}: `{payload.get(key)}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify live KIS scan rows are compatible with existing Supabase data contracts.")
    parser.add_argument("--output", default=str(REPORT_DIR / "kis_supabase_compatibility.json"))
    parser.add_argument("--legacy-limit", type=int, default=500)
    parser.add_argument("--validation-file", action="append", default=[])
    parser.add_argument("--repair-market-scan-results", action="store_true")
    args = parser.parse_args()

    validation_files = [Path(item) for item in args.validation_file] if args.validation_file else list(DEFAULT_VALIDATION_FILES)
    report = build_report(
        validation_files,
        legacy_limit=max(1, int(args.legacy_limit)),
        repair_market_scan_results=bool(args.repair_market_scan_results),
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown(report, out.with_suffix(".md"))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
