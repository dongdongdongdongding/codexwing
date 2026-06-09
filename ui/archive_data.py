from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import streamlit as st

from modules.db_manager import DBManager
from modules.scan_artifact_archive import load_local_scan_archive_rows, merge_archive_rows_with_local_artifacts


def ui_data_cache_ttl_seconds() -> int:
    try:
        return max(1, int(os.getenv("AG_UI_DATA_CACHE_TTL_SECONDS", "180") or "180"))
    except Exception:
        return 180


def archive_query_defaults() -> Dict[str, int]:
    def _int_env(name: str, default: int) -> int:
        try:
            return max(1, int(os.getenv(name, str(default)) or str(default)))
        except Exception:
            return default

    return {
        "batch_size": _int_env("AG_SCAN_ARCHIVE_BATCH_SIZE", 1000),
        "max_rows": _int_env("AG_SCAN_ARCHIVE_MAX_ROWS", 8000),
        "local_limit_runs": _int_env("AG_SCAN_ARCHIVE_LOCAL_LIMIT_RUNS", 80),
    }


def fetch_market_scan_archive_rows(
    *,
    max_rows: int,
    batch_size: int,
    include_supabase: bool = True,
    include_local_fallback: bool,
    local_limit_runs: int,
    db_factory: Callable[[], Any] = DBManager,
    local_loader: Callable[..., List[Dict[str, Any]]] = load_local_scan_archive_rows,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    db_rows: List[Dict[str, Any]] = []
    local_rows: List[Dict[str, Any]] = []
    warnings: List[str] = []
    db_client_available = False
    db_query_ok = False

    if include_supabase:
        try:
            db = db_factory()
            if getattr(db, "client", None):
                db_client_available = True
                offset = 0
                max_rows = max(1, int(max_rows or 1))
                batch_size = max(1, int(batch_size or 1))
                while offset < max_rows:
                    end = min(offset + batch_size - 1, max_rows - 1)
                    response = (
                        db.client.table("market_scan_results")
                        .select("*")
                        .order("created_at", desc=True)
                        .range(offset, end)
                        .execute()
                    )
                    batch = list(response.data or [])
                    if not batch:
                        break
                    db_rows.extend(batch)
                    if len(batch) < batch_size:
                        break
                    offset += batch_size
                db_query_ok = True
            else:
                warnings.append("supabase_client_unavailable")
        except Exception as exc:
            warnings.append(str(exc))

    if include_local_fallback:
        try:
            local_rows = local_loader(limit_runs=max(1, int(local_limit_runs or 1)))
        except TypeError:
            local_rows = local_loader(artifact_dir=Path("runtime_state/artifacts"), limit_runs=max(1, int(local_limit_runs or 1)))
        except Exception as exc:
            warnings.append(f"local_artifact_load_failed:{exc}")

    if db_rows and local_rows:
        rows = merge_archive_rows_with_local_artifacts(db_rows, local_rows)
    elif db_rows:
        rows = db_rows
    else:
        rows = local_rows

    source_parts: List[str] = []
    if db_rows:
        source_parts.append("supabase")
    elif db_query_ok:
        source_parts.append("supabase_empty")
    if local_rows:
        source_parts.append("local_artifact")
    if not source_parts:
        source_parts.append("empty")

    return rows, {
        "source": "+".join(source_parts),
        "db_available": db_query_ok,
        "db_client_available": db_client_available,
        "supabase_enabled": bool(include_supabase),
        "db_rows": len(db_rows),
        "local_rows": len(local_rows),
        "rows": len(rows),
        "warnings": warnings,
    }


@st.cache_data(ttl=ui_data_cache_ttl_seconds(), show_spinner=False)
def load_cached_market_scan_archive_rows(
    *,
    max_rows: int,
    batch_size: int,
    include_supabase: bool,
    include_local_fallback: bool,
    local_limit_runs: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    return fetch_market_scan_archive_rows(
        max_rows=max_rows,
        batch_size=batch_size,
        include_supabase=include_supabase,
        include_local_fallback=include_local_fallback,
        local_limit_runs=local_limit_runs,
    )


__all__ = [
    "archive_query_defaults",
    "fetch_market_scan_archive_rows",
    "load_cached_market_scan_archive_rows",
    "ui_data_cache_ttl_seconds",
]
