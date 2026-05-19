from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import streamlit as st


def load_scan_context_for_run(run_id: str) -> Dict[str, Any]:
    if not run_id:
        return {}
    summary = _load_json_safe(f"runtime_state/artifacts/{run_id}/scan_pipeline_summary.json")
    scanner_payload: Dict[str, Any] = {}
    manifest = summary.get("manifest_paths") if isinstance(summary.get("manifest_paths"), dict) else {}
    scanner_path = manifest.get("scanner_handoff")
    if scanner_path:
        scanner_payload = _load_json_safe(scanner_path)
    if not scanner_payload:
        scanner_payload = _load_json_safe(f"runtime_state/shared_working/{run_id}/scanner_handoff.json")
    scanner_summary = scanner_payload.get("summary") if isinstance(scanner_payload.get("summary"), dict) else {}
    market_gate = scanner_summary.get("market_gate")
    if not isinstance(market_gate, dict):
        input_meta = scanner_summary.get("input_meta") if isinstance(scanner_summary.get("input_meta"), dict) else {}
        market_gate = input_meta.get("market_gate") if isinstance(input_meta.get("market_gate"), dict) else {}
    return {
        "summary": summary,
        "scanner_summary": scanner_summary,
        "market_gate": market_gate if isinstance(market_gate, dict) else {},
    }


def scan_integrity_report_for_context(scan_context: Dict[str, Any]) -> Dict[str, Any]:
    summary = scan_context.get("summary") if isinstance(scan_context, dict) and isinstance(scan_context.get("summary"), dict) else {}
    integrity = summary.get("scan_integrity") if isinstance(summary.get("scan_integrity"), dict) else {}
    report = integrity.get("report") if isinstance(integrity.get("report"), dict) else {}
    if report:
        return report
    manifest = summary.get("manifest_paths") if isinstance(summary.get("manifest_paths"), dict) else {}
    report_path = manifest.get("scan_integrity_report")
    if not report_path and summary.get("artifact_dir"):
        report_path = str(Path(str(summary.get("artifact_dir"))) / "scan_integrity_report.json")
    if report_path:
        payload = _load_json_safe(str(report_path))
        return payload if isinstance(payload, dict) else {}
    return {}


def render_scan_integrity_panel(report: Dict[str, Any], *, compact: bool = False) -> None:
    if not isinstance(report, dict) or not report:
        st.info("데이터 무결성 리포트가 아직 없습니다. 다음 스캔부터 자동 생성됩니다.")
        return
    completeness = report.get("feature_completeness")
    try:
        completeness_pct = float(completeness) * 100.0
    except Exception:
        completeness_pct = None
    flags = report.get("quality_flags") if isinstance(report.get("quality_flags"), list) else []
    if flags:
        st.warning("데이터 무결성 경고: " + " / ".join(str(flag) for flag in flags[:5]))
    elif compact:
        st.caption("데이터 무결성: OK")
    else:
        st.success("데이터 무결성: OK")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Factor 완성도", "-" if completeness_pct is None else f"{completeness_pct:.1f}%")
    c2.metric("Snapshot", int(report.get("snapshot_count") or 0))
    c3.metric("Top5", int(report.get("picked_count") or 0))
    c4.metric("Exception", int(report.get("exception_leader_count") or 0))
    if not compact:
        missing = report.get("field_missing_counts") if isinstance(report.get("field_missing_counts"), dict) else {}
        missing = {k: v for k, v in missing.items() if int(v or 0) > 0}
        if missing:
            ordered = sorted(missing.items(), key=lambda item: int(item[1] or 0), reverse=True)
            st.caption("누락 상위: " + " / ".join(f"{key} {value}" for key, value in ordered[:8]))


def _load_json_safe(path_str: str | None) -> Dict[str, Any]:
    if not path_str:
        return {}
    try:
        path = Path(str(path_str))
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


__all__ = [
    "load_scan_context_for_run",
    "render_scan_integrity_panel",
    "scan_integrity_report_for_context",
]
