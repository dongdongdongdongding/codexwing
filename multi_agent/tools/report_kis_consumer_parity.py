#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_SHARED_DIR = PROJECT_ROOT / "runtime_state" / "shared_working"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "validation"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _nested_dict(source: Mapping[str, Any], *keys: str) -> Dict[str, Any]:
    current: Any = source
    for key in keys:
        if not isinstance(current, Mapping):
            return {}
        current = current.get(key)
    return dict(current) if isinstance(current, Mapping) else {}


def _sidecar_locations(candidate: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    feature_snapshot = _nested_dict(candidate, "feature_snapshot")
    return {
        "candidate.leader_metrics.kis_sidecar": _nested_dict(candidate, "leader_metrics", "kis_sidecar"),
        "feature_snapshot.leader_metrics.kis_sidecar": _nested_dict(feature_snapshot, "leader_metrics", "kis_sidecar"),
        "feature_snapshot.kis_sidecar": _nested_dict(feature_snapshot, "kis_sidecar"),
    }


def _non_empty_sidecars(candidate: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {key: value for key, value in _sidecar_locations(candidate).items() if value}


def _sidecar_model_ready(sidecar: Mapping[str, Any]) -> bool:
    coverage = sidecar.get("coverage") if isinstance(sidecar.get("coverage"), Mapping) else {}
    readiness = sidecar.get("replacement_readiness") if isinstance(sidecar.get("replacement_readiness"), Mapping) else {}
    return bool(readiness.get("model_sidecar_ready")) or bool(
        coverage.get("quote_snapshot") and coverage.get("daily_ohlcv")
    )


def _sidecar_production_ready(sidecar: Mapping[str, Any]) -> bool:
    readiness = sidecar.get("replacement_readiness") if isinstance(sidecar.get("replacement_readiness"), Mapping) else {}
    return bool(readiness.get("production_replacement_ready"))


def _scan_for_dummy_markers(payload: Any, *, path: str = "$") -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}"
            if key_text == "is_dummy_data" and _truthy(value):
                findings.append({"path": next_path, "reason": "is_dummy_data_true", "value": value})
            if isinstance(value, str):
                lower = value.strip().lower()
                source_like = any(token in key_text.lower() for token in ("source", "origin", "reason", "status"))
                if source_like and any(token in lower for token in ("dummy", "synthetic", "fake")):
                    findings.append({"path": next_path, "reason": "dummy_source_marker", "value": value})
            findings.extend(_scan_for_dummy_markers(value, path=next_path))
    elif isinstance(payload, list):
        for idx, value in enumerate(payload):
            findings.extend(_scan_for_dummy_markers(value, path=f"{path}[{idx}]"))
    return findings


def _run_dirs(shared_dir: Path, limit: int) -> List[Path]:
    if not shared_dir.exists():
        return []
    dirs = [path for path in shared_dir.iterdir() if path.is_dir() and path.name.startswith("RUN-")]
    dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return dirs[: max(0, int(limit))]


def _analyze_scanner_handoff(run_dir: Path) -> Dict[str, Any]:
    payload = _read_json(run_dir / "scanner_handoff.json")
    if not isinstance(payload, dict):
        return {"run_id": run_dir.name, "present": False, "candidate_count": 0, "issues": []}
    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    sidecar_candidates = 0
    model_ready_candidates = 0
    production_ready_candidates = 0
    location_mismatches: List[Dict[str, Any]] = []
    model_coverage_gaps: List[Dict[str, Any]] = []
    production_readiness_gaps: List[Dict[str, Any]] = []
    dummy_findings: List[Dict[str, Any]] = []
    sidecar_warnings = 0
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        sidecars = _non_empty_sidecars(candidate)
        if sidecars:
            sidecar_candidates += 1
            values = list(sidecars.values())
            if any(value != values[0] for value in values[1:]):
                location_mismatches.append(
                    {
                        "ticker": candidate.get("ticker"),
                        "locations": sorted(sidecars.keys()),
                    }
                )
            sidecar = values[0]
            if sidecar.get("warnings"):
                sidecar_warnings += 1
            if _sidecar_model_ready(sidecar):
                model_ready_candidates += 1
            else:
                model_coverage_gaps.append(
                    {
                        "ticker": candidate.get("ticker"),
                        "coverage": sidecar.get("coverage") if isinstance(sidecar.get("coverage"), Mapping) else {},
                        "warnings": list(sidecar.get("warnings") or [])[:8],
                    }
                )
            if _sidecar_production_ready(sidecar):
                production_ready_candidates += 1
            else:
                production_readiness_gaps.append(
                    {
                        "ticker": candidate.get("ticker"),
                        "replacement_readiness": (
                            sidecar.get("replacement_readiness")
                            if isinstance(sidecar.get("replacement_readiness"), Mapping)
                            else {}
                        ),
                        "warnings": list(sidecar.get("warnings") or [])[:8],
                    }
                )
        dummy_findings.extend(_scan_for_dummy_markers(candidate))
    issues = []
    if location_mismatches:
        issues.append({"severity": "error", "code": "KIS_SIDECAR_LOCATION_DRIFT", "items": location_mismatches[:10]})
    if model_coverage_gaps:
        issues.append({"severity": "error", "code": "KIS_SIDECAR_MINIMUM_COVERAGE_MISSING", "items": model_coverage_gaps[:10]})
    if production_readiness_gaps:
        issues.append({"severity": "warning", "code": "KIS_PRODUCTION_REPLACEMENT_NOT_READY", "items": production_readiness_gaps[:10]})
    if dummy_findings:
        issues.append({"severity": "error", "code": "DUMMY_MARKER_PRESENT", "items": dummy_findings[:20]})
    return {
        "run_id": ((payload.get("run_context") or {}).get("run_id") if isinstance(payload.get("run_context"), dict) else run_dir.name)
        or run_dir.name,
        "present": True,
        "candidate_count": len(candidates),
        "sidecar_candidate_count": sidecar_candidates,
        "sidecar_model_ready_candidate_count": model_ready_candidates,
        "sidecar_production_ready_candidate_count": production_ready_candidates,
        "sidecar_warning_candidate_count": sidecar_warnings,
        "sidecar_coverage_pct": round((sidecar_candidates / len(candidates) * 100.0) if candidates else 0.0, 3),
        "issues": issues,
    }


def _analyze_planner_handoff(run_dir: Path) -> Dict[str, Any]:
    payload = _read_json(run_dir / "planner_handoff.json")
    if not isinstance(payload, dict):
        return {"run_id": run_dir.name, "present": False, "decision_count": 0, "issues": []}
    decisions = payload.get("decisions") if isinstance(payload.get("decisions"), list) else []
    dummy_findings = _scan_for_dummy_markers(payload)
    issues = []
    if dummy_findings:
        issues.append({"severity": "error", "code": "DUMMY_MARKER_PRESENT", "items": dummy_findings[:20]})
    return {
        "run_id": ((payload.get("run_context") or {}).get("run_id") if isinstance(payload.get("run_context"), dict) else run_dir.name)
        or run_dir.name,
        "present": True,
        "decision_count": len(decisions),
        "issues": issues,
    }


def _db_contract_check() -> Dict[str, Any]:
    from modules.db_manager import LOCAL_SCHEMA_EXTENSION_COLUMNS
    from modules.db_schema import SCAN_RESULT_COLUMNS, build_scan_result_payload

    columns = {name for name, _source, _coerce in SCAN_RESULT_COLUMNS}
    payload = build_scan_result_payload(
        {
            "ticker": "005930.KS",
            "leader_metrics": {"kis_sidecar": {"feature_origin": "kis_openapi_sidecar"}},
            "feature_snapshot": {"kis_sidecar": {"feature_origin": "kis_openapi_sidecar"}},
        },
        overrides={"market": "KOSPI"},
    )
    local_extensions = LOCAL_SCHEMA_EXTENSION_COLUMNS.get("market_scan_results", set())
    issues = []
    for required in ("leader_metrics", "feature_snapshot"):
        if required not in columns:
            issues.append({"severity": "error", "code": "DB_SCHEMA_MAPPING_MISSING", "field": required})
        if required not in payload or payload.get(required) is None:
            issues.append({"severity": "error", "code": "DB_PAYLOAD_FIELD_DROPPED", "field": required})
        if required not in local_extensions:
            issues.append({"severity": "warning", "code": "LOCAL_SCHEMA_EXTENSION_MISSING", "field": required})
    return {
        "mapped_fields": sorted(field for field in ("leader_metrics", "feature_snapshot") if field in columns),
        "payload_preserves_feature_snapshot": bool(payload.get("feature_snapshot")),
        "payload_preserves_leader_metrics": bool(payload.get("leader_metrics")),
        "local_schema_extensions": sorted(field for field in ("leader_metrics", "feature_snapshot") if field in local_extensions),
        "issues": issues,
    }


def build_report(
    *,
    shared_dir: Path = DEFAULT_SHARED_DIR,
    limit_runs: int = 20,
) -> Dict[str, Any]:
    run_results = []
    for run_dir in _run_dirs(shared_dir, limit_runs):
        run_results.append(
            {
                "run_dir": str(run_dir),
                "scanner": _analyze_scanner_handoff(run_dir),
                "planner": _analyze_planner_handoff(run_dir),
            }
        )
    scanner_present = [item["scanner"] for item in run_results if item["scanner"].get("present")]
    scanner_candidate_count = sum(int(item.get("candidate_count") or 0) for item in scanner_present)
    scanner_sidecar_count = sum(int(item.get("sidecar_candidate_count") or 0) for item in scanner_present)
    scanner_model_ready_count = sum(int(item.get("sidecar_model_ready_candidate_count") or 0) for item in scanner_present)
    scanner_production_ready_count = sum(int(item.get("sidecar_production_ready_candidate_count") or 0) for item in scanner_present)
    issues: List[Dict[str, Any]] = []
    db_contract = _db_contract_check()
    issues.extend(db_contract.get("issues") or [])
    for item in run_results:
        issues.extend(item["scanner"].get("issues") or [])
        issues.extend(item["planner"].get("issues") or [])
    if scanner_candidate_count > 0 and scanner_sidecar_count == 0:
        issues.append(
            {
                "severity": "warning",
                "code": "NO_LIVE_KIS_SIDECAR_ARTIFACTS_YET",
                "message": "Recent scanner_handoff artifacts do not yet contain KIS sidecar data; run a KIS-first sidecar scan before promotion.",
            }
        )
    error_count = sum(1 for item in issues if item.get("severity") == "error")
    warning_count = sum(1 for item in issues if item.get("severity") == "warning")
    return {
        "tool": "report_kis_consumer_parity",
        "source": {
            "shared_dir": str(shared_dir),
            "run_count": len(run_results),
            "limit_runs": int(limit_runs),
        },
        "summary": {
            "dummy_policy": "No dummy, synthetic, or fabricated KIS data is allowed. Missing KIS values must stay missing with warnings.",
            "promotion_ready": bool(error_count == 0 and warning_count == 0 and scanner_candidate_count > 0 and scanner_sidecar_count > 0),
            "scanner_candidate_count": scanner_candidate_count,
            "scanner_sidecar_candidate_count": scanner_sidecar_count,
            "scanner_sidecar_model_ready_candidate_count": scanner_model_ready_count,
            "scanner_sidecar_production_ready_candidate_count": scanner_production_ready_count,
            "scanner_sidecar_coverage_pct": round((scanner_sidecar_count / scanner_candidate_count * 100.0) if scanner_candidate_count else 0.0, 3),
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "db_contract": db_contract,
        "runs": run_results,
        "issues": issues,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    issues = report.get("issues") if isinstance(report.get("issues"), list) else []
    db_contract = report.get("db_contract") if isinstance(report.get("db_contract"), dict) else {}
    lines = [
        "# KIS Consumer Parity Report",
        "",
        "## Summary",
        f"- promotion_ready: `{summary.get('promotion_ready')}`",
        f"- dummy_policy: {summary.get('dummy_policy')}",
        f"- scanner_candidate_count: `{summary.get('scanner_candidate_count')}`",
        f"- scanner_sidecar_candidate_count: `{summary.get('scanner_sidecar_candidate_count')}`",
        f"- scanner_sidecar_model_ready_candidate_count: `{summary.get('scanner_sidecar_model_ready_candidate_count')}`",
        f"- scanner_sidecar_production_ready_candidate_count: `{summary.get('scanner_sidecar_production_ready_candidate_count')}`",
        f"- scanner_sidecar_coverage_pct: `{summary.get('scanner_sidecar_coverage_pct')}`",
        f"- error_count: `{summary.get('error_count')}`",
        f"- warning_count: `{summary.get('warning_count')}`",
        "",
        "## DB Contract",
        f"- mapped_fields: `{db_contract.get('mapped_fields')}`",
        f"- local_schema_extensions: `{db_contract.get('local_schema_extensions')}`",
        f"- payload_preserves_feature_snapshot: `{db_contract.get('payload_preserves_feature_snapshot')}`",
        f"- payload_preserves_leader_metrics: `{db_contract.get('payload_preserves_leader_metrics')}`",
        "",
        "## Issues",
    ]
    if not issues:
        lines.append("- none")
    else:
        for item in issues[:30]:
            lines.append(
                f"- `{item.get('severity')}` `{item.get('code')}` "
                f"{item.get('field') or item.get('message') or ''}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report KIS sidecar consumer parity and no-dummy violations.")
    parser.add_argument("--shared-dir", default=str(DEFAULT_SHARED_DIR))
    parser.add_argument("--limit-runs", type=int, default=20)
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    report = build_report(shared_dir=Path(args.shared_dir), limit_runs=int(args.limit_runs))
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "kis_consumer_parity.json"
    md_path = report_dir / "kis_consumer_parity.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if int((report.get("summary") or {}).get("error_count") or 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
