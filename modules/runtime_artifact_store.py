from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


RUNTIME_ARTIFACT_VERSION = "runtime_artifact_v1"
ARTIFACT_TABLE = "runtime_artifacts"


def _env_enabled(name: str, default: str = "1") -> bool:
    value = os.getenv(name, default)
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    try:
        import numpy as np

        if isinstance(value, np.generic):
            return _jsonable(value.item())
    except Exception:
        pass
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False, default=str)
        return value
    except Exception:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False, default=str))


def _load_path_payload(path: Path) -> tuple[Any, str]:
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw), "application/json"
    except Exception:
        return raw, "text/plain"


def _payload_rows(payload: Any) -> int | None:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("results_sorted", "rows", "reports", "snapshots", "outcomes"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        scan_result = payload.get("scan_result") if isinstance(payload.get("scan_result"), dict) else {}
        results = scan_result.get("results")
        if isinstance(results, list):
            return len(results)
    return None


def _checksum_for_payload(payload: Any) -> str:
    raw = json.dumps(_jsonable(payload), ensure_ascii=False, sort_keys=True, allow_nan=False, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _artifact_type_for_key(key: str) -> str:
    if key.endswith("_handoff") or key in {"orchestrator_request", "orchestrator_report"}:
        return "agent_handoff"
    if key in {"raw_scan_results", "scan_pipeline_summary", "observed_factor_snapshots"}:
        return "scan_artifact"
    if key.endswith("_report") or key in {"top_deep_reports", "postmortem_report"}:
        return "report"
    if key in {"profile_diagnostics", "realized_outcomes", "post_scan_outcome_ledger"}:
        return "diagnostic"
    return "runtime_json"


def _db_manager():
    from modules.db_manager import DBManager

    return DBManager()


def build_runtime_artifact_row(
    *,
    run_id: str,
    artifact_key: str,
    payload: Any,
    market: str = "",
    scan_mode: str = "",
    source: str = "",
    source_path: str = "",
    content_type: str = "application/json",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    run_id = str(run_id or "").strip()
    artifact_key = str(artifact_key or "").strip()
    if not run_id or not artifact_key:
        raise ValueError("run_id and artifact_key are required")
    now_ts = datetime.now(timezone.utc).isoformat()
    is_json = str(content_type or "").startswith("application/json")
    return {
        "run_id": run_id,
        "artifact_key": artifact_key,
        "artifact_type": _artifact_type_for_key(artifact_key),
        "market": str(market or "").upper() or None,
        "scan_mode": str(scan_mode or "").upper() or None,
        "source": str(source or "") or None,
        "source_path": str(source_path or "") or None,
        "content_type": content_type or "application/json",
        "payload": _jsonable(payload) if is_json else None,
        "content_text": None if is_json else str(payload),
        "payload_rows": _payload_rows(payload),
        "size_bytes": len(json.dumps(_jsonable(payload), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")),
        "checksum": _checksum_for_payload(payload),
        "metadata": _jsonable(metadata or {}),
        "artifact_version": RUNTIME_ARTIFACT_VERSION,
        "updated_at": now_ts,
        "created_at": now_ts,
    }


def build_runtime_artifact_row_from_path(
    *,
    run_id: str,
    artifact_key: str,
    path: Path | str,
    market: str = "",
    scan_mode: str = "",
    source: str = "",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    path_obj = Path(str(path))
    payload, content_type = _load_path_payload(path_obj)
    file_meta = dict(metadata or {})
    try:
        file_meta["file_size_bytes"] = path_obj.stat().st_size
    except Exception:
        pass
    return build_runtime_artifact_row(
        run_id=run_id,
        artifact_key=artifact_key,
        payload=payload,
        market=market,
        scan_mode=scan_mode,
        source=source,
        source_path=str(path_obj),
        content_type=content_type,
        metadata=file_meta,
    )


def upsert_runtime_artifact_payload(
    *,
    run_id: str,
    artifact_key: str,
    payload: Any,
    market: str = "",
    scan_mode: str = "",
    source: str = "",
    source_path: str = "",
    content_type: str = "application/json",
    metadata: Dict[str, Any] | None = None,
    db: Any | None = None,
) -> Dict[str, Any]:
    if not _env_enabled("AG_RUNTIME_ARTIFACT_WRITE_DB", "1"):
        return {"ok": True, "enabled": False, "rows_upserted": 0, "reason": "disabled_by_env"}
    run_id = str(run_id or "").strip()
    artifact_key = str(artifact_key or "").strip()
    if not run_id or not artifact_key:
        return {"ok": False, "enabled": True, "rows_upserted": 0, "error": "run_id_and_artifact_key_required"}
    try:
        db = db or _db_manager()
        if not getattr(db, "client", None):
            return {"ok": False, "enabled": True, "rows_upserted": 0, "error": "db_client_unavailable"}
        row = build_runtime_artifact_row(
            run_id=run_id,
            artifact_key=artifact_key,
            payload=payload,
            market=market,
            scan_mode=scan_mode,
            source=source,
            source_path=source_path,
            content_type=content_type,
            metadata=metadata,
        )
        rows_upserted = db.upsert_runtime_artifact(row)
        return {"ok": rows_upserted == 1, "enabled": True, "rows_upserted": rows_upserted, "artifact_key": artifact_key}
    except Exception as exc:
        return {"ok": False, "enabled": True, "rows_upserted": 0, "artifact_key": artifact_key, "error": str(exc)}


def upsert_runtime_artifact_path(
    *,
    run_id: str,
    artifact_key: str,
    path: Path | str,
    market: str = "",
    scan_mode: str = "",
    source: str = "",
    metadata: Dict[str, Any] | None = None,
    db: Any | None = None,
) -> Dict[str, Any]:
    path_obj = Path(str(path))
    if not path_obj.exists() or not path_obj.is_file():
        return {"ok": False, "enabled": True, "rows_upserted": 0, "artifact_key": artifact_key, "error": "path_missing"}
    try:
        db = db or _db_manager()
        if not getattr(db, "client", None):
            return {"ok": False, "enabled": True, "rows_upserted": 0, "artifact_key": artifact_key, "error": "db_client_unavailable"}
        row = build_runtime_artifact_row_from_path(
            run_id=run_id,
            artifact_key=artifact_key,
            path=path_obj,
            market=market,
            scan_mode=scan_mode,
            source=source,
            metadata=metadata,
        )
        rows_upserted = db.upsert_runtime_artifact(row)
        return {"ok": rows_upserted == 1, "enabled": True, "rows_upserted": rows_upserted, "artifact_key": artifact_key}
    except Exception as exc:
        return {"ok": False, "enabled": True, "rows_upserted": 0, "artifact_key": artifact_key, "error": str(exc)}


def _candidate_artifact_paths(
    *,
    run_id: str,
    artifact_dir: Path,
    summary: Dict[str, Any],
    manifest_paths: Dict[str, Any],
) -> Dict[str, Path]:
    candidates: Dict[str, Path] = {
        "scan_pipeline_summary": artifact_dir / "scan_pipeline_summary.json",
        "raw_scan_results": artifact_dir / "raw_scan_results.json",
        "observed_factor_snapshots": artifact_dir / "observed_factor_snapshots.json",
        "scan_integrity_report": artifact_dir / "scan_integrity_report.json",
    }
    manifest = dict(manifest_paths or {})
    if isinstance(summary.get("manifest_paths"), dict):
        manifest.update(summary.get("manifest_paths") or {})
    top_deep = summary.get("top_deep_reports") if isinstance(summary.get("top_deep_reports"), dict) else {}
    if top_deep.get("local_path"):
        manifest["top_deep_reports"] = str(top_deep.get("local_path"))
    for key, raw_path in manifest.items():
        if not raw_path or str(key).endswith("_error"):
            continue
        path = Path(str(raw_path))
        if path.suffix.lower() in {".json", ".jsonl", ".md", ".txt", ".csv"}:
            candidates[str(key)] = path
    shared_dir = Path("runtime_state/shared_working") / str(run_id)
    for key in (
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
        "post_scan_outcome_ledger",
    ):
        candidates.setdefault(key, shared_dir / f"{key}.json")
    return candidates


def persist_run_runtime_artifacts(
    *,
    run_id: str,
    market: str,
    scan_mode: str,
    artifact_dir: Path | str,
    summary: Dict[str, Any],
    manifest_paths: Dict[str, Any] | None = None,
    source: str = "",
    db: Any | None = None,
) -> Dict[str, Any]:
    if not _env_enabled("AG_RUNTIME_ARTIFACT_WRITE_DB", "1"):
        return {"ok": True, "enabled": False, "artifacts_seen": 0, "artifacts_upserted": 0, "reason": "disabled_by_env"}
    artifact_dir = Path(str(artifact_dir))
    candidates = _candidate_artifact_paths(
        run_id=run_id,
        artifact_dir=artifact_dir,
        summary=summary if isinstance(summary, dict) else {},
        manifest_paths=manifest_paths if isinstance(manifest_paths, dict) else {},
    )
    db = db or _db_manager()
    if not getattr(db, "client", None):
        return {"ok": False, "enabled": True, "artifacts_seen": len(candidates), "artifacts_upserted": 0, "error": "db_client_unavailable"}
    details: List[Dict[str, Any]] = []
    upserted = 0
    seen = 0
    for key, path in candidates.items():
        if not path.exists() or not path.is_file():
            continue
        seen += 1
        result = upsert_runtime_artifact_path(
            run_id=run_id,
            artifact_key=key,
            path=path,
            market=market,
            scan_mode=scan_mode,
            source=source,
            metadata={"artifact_dir": str(artifact_dir), "source": source},
            db=db,
        )
        if result.get("ok"):
            upserted += 1
        details.append(result)
    return {
        "ok": seen > 0 and upserted == seen,
        "enabled": True,
        "artifacts_seen": seen,
        "artifacts_upserted": upserted,
        "target_table": ARTIFACT_TABLE,
        "details": details[:50],
    }


def load_runtime_artifact_payload(
    run_id: str,
    artifact_key: str,
    *,
    local_path: str | Path | None = None,
    db: Any | None = None,
) -> Any:
    if _env_enabled("AG_RUNTIME_ARTIFACT_READ_DB", "1"):
        try:
            db = db or _db_manager()
            if getattr(db, "client", None):
                row = db.fetch_runtime_artifact(run_id, artifact_key)
                if isinstance(row, dict):
                    if row.get("payload") is not None:
                        return row.get("payload")
                    if row.get("content_text") is not None:
                        text = str(row.get("content_text") or "")
                        try:
                            return json.loads(text)
                        except Exception:
                            return text
        except Exception:
            pass
    if local_path:
        try:
            payload, _content_type = _load_path_payload(Path(str(local_path)))
            return payload
        except Exception:
            return None
    return None


def list_runtime_artifact_payloads(
    *,
    artifact_key: str,
    market: str = "",
    limit: int = 100,
    db: Any | None = None,
) -> List[Dict[str, Any]]:
    if not _env_enabled("AG_RUNTIME_ARTIFACT_READ_DB", "1"):
        return []
    try:
        db = db or _db_manager()
        if not getattr(db, "client", None):
            return []
        rows = db.list_runtime_artifacts(artifact_key=artifact_key, market=market, limit=limit)
    except Exception:
        return []
    payloads: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        payload = row.get("payload")
        if isinstance(payload, dict):
            payload.setdefault("_artifact_created_at", row.get("created_at"))
            payload.setdefault("_artifact_updated_at", row.get("updated_at"))
            payloads.append(payload)
    return payloads


def iter_standard_run_artifact_paths(
    *,
    artifact_root: Path,
    shared_root: Path,
    top_deep_root: Path | None = None,
    limit_runs: int = 0,
) -> Iterable[tuple[str, Dict[str, Any], Dict[str, Path]]]:
    run_dirs = []
    if artifact_root.exists():
        run_dirs = [path for path in artifact_root.iterdir() if path.is_dir() and path.name.startswith("RUN-")]
        run_dirs = sorted(run_dirs, key=lambda path: path.stat().st_mtime, reverse=True)
    if limit_runs and limit_runs > 0:
        run_dirs = run_dirs[:limit_runs]
    for run_dir in run_dirs:
        summary_path = run_dir / "scan_pipeline_summary.json"
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            summary = {"run_id": run_dir.name, "artifact_dir": str(run_dir), "manifest_paths": {}}
        run_id = str(summary.get("run_id") or run_dir.name)
        paths = _candidate_artifact_paths(
            run_id=run_id,
            artifact_dir=run_dir,
            summary=summary,
            manifest_paths=summary.get("manifest_paths") if isinstance(summary.get("manifest_paths"), dict) else {},
        )
        shared_dir = shared_root / run_id
        if shared_dir.exists():
            for path in shared_dir.glob("*.json"):
                paths.setdefault(path.stem, path)
        if top_deep_root is not None:
            top_path = top_deep_root / f"{run_id}.json"
            if top_path.exists():
                paths.setdefault("top_deep_reports", top_path)
        yield run_id, summary, paths
