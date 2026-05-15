from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from modules.scan_integrity import write_scan_integrity_artifacts
from multi_agent.contracts.serialization import write_json
from multi_agent.storage.memory_layers import MemoryManager


SHARED_ARTIFACT_KEYS = [
    "scanner_handoff",
    "aggregation_handoff",
    "backtest_handoff",
    "market_context_handoff",
    "planner_handoff",
    "profile_diagnostics",
    "postmortem_report",
    "realized_outcomes",
    "orchestrator_request",
    "orchestrator_report",
    "orchestrator_compact_summary",
    "top_deep_reports",
]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _artifact_manifest(bridge_info: Dict[str, Any] | None) -> Dict[str, Any]:
    info = bridge_info if isinstance(bridge_info, dict) else {}
    manifest = {}
    for key in SHARED_ARTIFACT_KEYS:
        value = info.get(key)
        if value:
            manifest[key] = str(value)
    if info.get("shared_working_dir"):
        manifest["shared_working_dir"] = str(info.get("shared_working_dir"))
    return manifest


def persist_scan_run_artifacts(
    *,
    run_id: str,
    market: str,
    scan_mode: str,
    results: List[Dict[str, Any]],
    total_scans: int,
    diagnostics: Dict[str, Any] | None = None,
    bridge_info: Dict[str, Any] | None = None,
    top_deep_reports: Dict[str, Any] | None = None,
    warnings: List[Dict[str, Any]] | None = None,
    source: str = "web_streamlit",
    memory: MemoryManager | None = None,
) -> Dict[str, Any]:
    """Persist a completed scan into the same run-scoped artifact contract.

    The web scanner, Discord scanner, and non-UI pipeline must all leave the
    same durable minimum set: raw scan rows plus a summary file. The archive UI
    can then recover even when Supabase writes are delayed or rejected.
    """

    run_id = str(run_id or "").strip()
    if not run_id:
        raise ValueError("run_id is required for scan persistence")

    diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
    bridge_info = bridge_info if isinstance(bridge_info, dict) else {}
    top_deep_reports = top_deep_reports if isinstance(top_deep_reports, dict) else {}
    result_rows = [dict(row) for row in (results or []) if isinstance(row, dict)]
    total_scans_int = _safe_int(total_scans, len(result_rows))
    filtered_count = _safe_int(diagnostics.get("filtered_count"), max(total_scans_int - len(result_rows), 0))
    error_count = _safe_int(diagnostics.get("worker_error_count")) + _safe_int(diagnostics.get("executor_exception_count"))
    warning_rows = list(warnings or [])
    if error_count:
        warning_rows.append(
            {
                "code": "SCAN_WORKER_ERRORS",
                "message": f"Worker reported {error_count} errors during scan execution.",
                "severity": "warning",
            }
        )

    memory = memory or MemoryManager()
    artifact_dir = memory.artifact_store(run_id)
    created_at = datetime.now(timezone.utc).isoformat()
    manifest_paths = _artifact_manifest(bridge_info)
    if top_deep_reports.get("local_path"):
        manifest_paths["top_deep_reports"] = str(top_deep_reports.get("local_path"))

    raw_path = artifact_dir / "raw_scan_results.json"
    write_json(
        raw_path,
        {
            "source": source,
            "results_sorted": result_rows,
            "scan_result": {
                "results": result_rows,
                "total_scans": total_scans_int,
                "error_count": error_count,
            },
            "diagnostics": diagnostics,
            "scan_mode": str(scan_mode or "SWING").upper(),
            "warnings": warning_rows,
            "bridge_info": bridge_info,
        },
    )

    integrity_result = write_scan_integrity_artifacts(
        artifact_dir=artifact_dir,
        run_id=run_id,
        market=market,
        scan_mode=str(scan_mode or "SWING").upper(),
        results=result_rows,
        total_scans=total_scans_int,
        diagnostics=diagnostics,
        bridge_info=bridge_info,
        top_deep_reports=top_deep_reports,
        created_at=created_at,
    )
    if integrity_result.get("observed_factor_snapshots"):
        manifest_paths["observed_factor_snapshots"] = str(integrity_result.get("observed_factor_snapshots"))
    if integrity_result.get("scan_integrity_report"):
        manifest_paths["scan_integrity_report"] = str(integrity_result.get("scan_integrity_report"))

    summary_path = artifact_dir / "scan_pipeline_summary.json"
    summary = {
        "run_id": run_id,
        "market": str(market or ""),
        "scan_mode": str(scan_mode or "SWING").upper(),
        "source": source,
        "created_at": created_at,
        "result_count": len(result_rows),
        "total_scans": total_scans_int,
        "filtered_count": filtered_count,
        "error_count": error_count,
        "worker_error_count": _safe_int(diagnostics.get("worker_error_count")),
        "executor_exception_count": _safe_int(diagnostics.get("executor_exception_count")),
        "warnings": warning_rows,
        "manifest_paths": manifest_paths,
        "artifact_dir": str(artifact_dir),
        "raw_scan_results": str(raw_path),
        "top_deep_reports": top_deep_reports,
        "scan_integrity": integrity_result,
        "persistence_contract": {
            "raw_scan_results": raw_path.exists(),
            "scan_pipeline_summary": True,
            "observed_factor_snapshots": bool(integrity_result.get("ok")),
            "scan_integrity_report": bool(integrity_result.get("ok")),
            "top_deep_local": bool(top_deep_reports.get("local_path") and Path(str(top_deep_reports.get("local_path"))).exists()),
        },
    }
    write_json(summary_path, summary)
    return {
        "ok": raw_path.exists() and summary_path.exists(),
        "artifact_dir": str(artifact_dir),
        "raw_scan_results": str(raw_path),
        "scan_pipeline_summary": str(summary_path),
        "summary": summary,
    }


__all__ = ["persist_scan_run_artifacts"]
