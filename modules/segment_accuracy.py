"""Segment historical OOS win rate — live 계산 버전.

Why this exists
---------------
Card UI 'accuracy' 가 이전엔 raw model probability (phase25_prob, prob_clean) 를
보여줘서 "0~50% 사이의 정렬용 score" 를 적중률로 오인하게 만들었다. 사용자가
"카드 정확성이 너무 낮다"고 지적했고, 그래서 historical OOS win rate 로
바꾸려 했지만, 첫 번째 시도는 ``_SEGMENT_WIN_RATE`` 라는 **하드코딩 dict**
(2026-05-08 horizon_full_diagnosis 스냅샷) 를 코드에 박아둔 dummy 데이터였다.
같은 segment 면 어떤 픽이든 같은 정적 숫자가 나오는 문제 → 이번에 폐기.

What this does (2026-05-10)
---------------------------
``runtime_state/reports/archive/scan_archive_learning_dataset_all.json`` 을
파일 mtime 캐시로 한 번 로드하고, ``(market, scan_mode, decision_bucket)`` 별로
``return_5d_pct > 0`` 비율을 집계해 live segment win rate table 을 만든다.
이 dataset 은 ``run_daily_ops.sh`` 의 emit step 에서 매일 갱신된다.

Bucket 정규화
-------------
Dataset 의 ``decision_bucket`` 은 ``picked / watchlist / exception_leader``
3 분류 (multi_agent.workflows.outcome_buckets.classify_decision_bucket 와 동일).
스캐너 row 가 ``decision = "PRIORITY_WATCHLIST"`` 같은 raw 결정으로 오면 같은
classifier 를 통과시켜 bucket 을 맞춘 뒤 lookup → 학습 데이터의 분류 체계와
정렬을 강제한다.

Market resolution
-----------------
Dataset 안에는 ``market`` 컬럼이 ``KOSPI / KOSDAQ / NASDAQ / KR / US``
등 혼재. 정밀 키 (KOSPI) 로 먼저 lookup, 실패 시 region 키 (KR) 로 fallback.

Sample threshold
----------------
표본 < ``_MIN_SAMPLE_SIZE`` (8) → None 반환. UI 는 fallback 으로 ``-`` 또는
``phase25_oos_win_rate_pct`` / ``prob_clean`` 으로 떨어진다.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional, Tuple

# 표본이 너무 작으면 사용자에게 표시 안 하는 임계값
_MIN_SAMPLE_SIZE = 8

# Dataset 위치 (run_daily_ops 의 emit_archive_learning_dataset 가 생성)
_DATASET_PATH = Path("runtime_state/reports/archive/scan_archive_learning_dataset_all.json")
_SOURCE_TTL_SECONDS = int(os.getenv("AG_SEGMENT_ACCURACY_TTL_SECONDS", "600") or "600")
_MAX_SUPABASE_ROWS = int(os.getenv("AG_SEGMENT_ACCURACY_MAX_ROWS", "25000") or "25000")
_HORIZON_COLS = (
    (1, "return_1d_pct"),
    (3, "return_3d_pct"),
    (5, "return_5d_pct"),
    (7, "return_7d_pct"),
    (14, "return_14d_pct"),
    (30, "return_30d_pct"),
)
_SUPABASE_SELECT_COLS = ",".join(
    [
        "ticker",
        "market",
        "market_type",
        "scan_mode",
        "decision",
        "decision_bucket",
        "outcome_status",
        "created_at",
        "recommended_at",
        *[col for _, col in _HORIZON_COLS],
    ]
)

# 모듈 레벨 캐시: (mtime, table). table = {(market, scan_mode, bucket): {h: (n, win_pct)}}
_CACHE_LOCK = Lock()
_CACHE: Dict[str, Any] = {"signature": None, "table": None, "snapshot": None}


def _classify_bucket(decision: Any) -> str:
    """decision (raw 또는 bucket) 을 dataset 분류 체계 (picked/watchlist/exception_leader)
    로 정규화. 매칭 안 되면 'ignored'.
    """
    value = str(decision or "").strip().upper()
    if value == "EXCEPTION_LEADER":
        return "exception_leader"
    if value in {"WATCHLIST_ONLY", "FALLBACK_WATCHLIST", "WATCHLIST", "OBSERVE"}:
        return "watchlist"
    if value in {"PRIORITY_WATCHLIST", "PICKED"}:
        return "picked"
    # dataset 자체가 소문자 bucket 으로 들어오는 케이스
    lower = value.lower()
    if lower in {"picked", "watchlist", "exception_leader"}:
        return lower
    return "ignored"


def _resolve_market_keys(market: str | None, ticker: str | None) -> Tuple[Optional[str], Optional[str]]:
    """precise (KOSPI/KOSDAQ/NASDAQ/AMEX) + region (KR/US) 두 단계 키.

    Lookup 은 precise → region 순서로 시도한다.
    """
    raw = str(market or "").upper().strip()
    if raw in {"KOSPI", "KOSDAQ"}:
        return raw, "KR"
    if raw in {"NASDAQ", "S&P500", "SP500", "AMEX"}:
        return raw, "US"
    if raw in {"KR", "US"}:
        return None, raw

    t = str(ticker or "").upper()
    if t.endswith(".KS"):
        return "KOSPI", "KR"
    if t.endswith(".KQ"):
        return "KOSDAQ", "KR"
    return None, None


def _build_table_from_dataset(rows: list) -> Dict[Tuple[str, str, str], Dict[int, Tuple[int, float]]]:
    """raw rows → segment win rate table.

    horizon: 1d / 3d / 5d / 7d / 14d / 30d 를 모두 집계.
    UI 가 horizon_days 인자로 선택.
    """
    counts: Dict[Tuple[str, str, str], Dict[int, list]] = {}

    for r in rows:
        if not isinstance(r, dict):
            continue
        outcome_status = str(r.get("outcome_status") or "").upper().strip()
        if outcome_status and outcome_status != "RESOLVED":
            continue
        market_raw = r.get("market") or r.get("market_type") or r.get("market_subtype")
        scan_mode = r.get("scan_mode")
        bucket_raw = r.get("decision_bucket") or r.get("decision")
        if not market_raw or not scan_mode:
            continue
        bucket = _classify_bucket(bucket_raw)
        if bucket == "ignored":
            continue
        market_u = str(market_raw).upper().strip()
        scan_u = str(scan_mode).upper().strip()
        if scan_u not in {"SWING", "INTRADAY"}:
            continue
        key = (market_u, scan_u, bucket)
        cell = counts.setdefault(key, {h: [0, 0] for h, _ in _HORIZON_COLS})
        for h, col in _HORIZON_COLS:
            value = r.get(col)
            if value is None:
                continue
            try:
                v = float(value)
            except (TypeError, ValueError):
                continue
            cell[h][0] += 1
            if v > 0:
                cell[h][1] += 1

    table: Dict[Tuple[str, str, str], Dict[int, Tuple[int, float]]] = {}
    for key, cell in counts.items():
        horizon_map: Dict[int, Tuple[int, float]] = {}
        for h, (n, wins) in cell.items():
            if n <= 0:
                continue
            horizon_map[h] = (n, round(wins / n * 100.0, 2))
        if horizon_map:
            table[key] = horizon_map
    return table


def _load_archive_rows() -> Tuple[list, Dict[str, Any]]:
    """Load real archived rows generated from Supabase export."""
    try:
        mtime = _DATASET_PATH.stat().st_mtime
    except FileNotFoundError:
        return [], {
            "source": "archive",
            "source_status": "missing",
            "source_path": str(_DATASET_PATH),
            "source_signature": "archive:missing",
            "warning": "archive learning dataset not found",
        }
    try:
        with _DATASET_PATH.open("r", encoding="utf-8") as fp:
            rows = json.load(fp)
    except Exception as exc:
        return [], {
            "source": "archive",
            "source_status": "error",
            "source_path": str(_DATASET_PATH),
            "source_signature": f"archive:{mtime}",
            "warning": str(exc),
        }
    return rows if isinstance(rows, list) else [], {
        "source": "archive",
        "source_status": "ok",
        "source_path": str(_DATASET_PATH),
        "source_signature": f"archive:{mtime}",
        "archive_mtime": mtime,
    }


def _load_supabase_rows() -> Tuple[list, Dict[str, Any]]:
    """Load real accumulated rows directly from Supabase market_scan_results.

    This is the operational SSOT. Network/credential failures are returned as
    metadata so the UI can show the fallback source instead of silently
    pretending the DB is healthy.
    """
    try:
        from modules.db_manager import DBManager

        db = DBManager()
        if not db.client:
            return [], {
                "source": "supabase",
                "source_status": "unavailable",
                "warning": "Supabase credentials/client unavailable",
            }
        rows: list = []
        batch_size = 1000
        offset = 0
        max_rows = max(1, int(_MAX_SUPABASE_ROWS))
        while offset < max_rows:
            end = min(offset + batch_size - 1, max_rows - 1)
            response = (
                db.client.table("market_scan_results")
                .select(_SUPABASE_SELECT_COLS)
                .order("created_at", desc=True)
                .range(offset, end)
                .execute()
            )
            batch = list(response.data or [])
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < batch_size:
                break
            offset += batch_size
        return rows, {
            "source": "supabase",
            "source_status": "ok",
            "source_signature": f"supabase:{int(time.time() // max(1, _SOURCE_TTL_SECONDS))}",
            "max_rows": max_rows,
        }
    except Exception as exc:
        return [], {
            "source": "supabase",
            "source_status": "error",
            "warning": str(exc),
        }


def _latest_timestamp(rows: list) -> Optional[str]:
    latest = ""
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = str(row.get("recommended_at") or row.get("created_at") or "").strip()
        if value and value > latest:
            latest = value
    return latest or None


def _build_snapshot(rows: list, meta: Dict[str, Any], table: Dict[Tuple[str, str, str], Dict[int, Tuple[int, float]]]) -> Dict[str, Any]:
    resolved_rows = 0
    horizon_counts = {h: 0 for h, _ in _HORIZON_COLS}
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("outcome_status") or "").upper().strip()
        if status and status != "RESOLVED":
            continue
        if status == "RESOLVED" or any(row.get(col) is not None for _, col in _HORIZON_COLS):
            resolved_rows += 1
        for h, col in _HORIZON_COLS:
            if row.get(col) is not None:
                horizon_counts[h] += 1
    return {
        "source": meta.get("source"),
        "source_status": meta.get("source_status"),
        "source_path": meta.get("source_path"),
        "warning": meta.get("warning"),
        "loaded_at_epoch": time.time(),
        "rows_loaded": len(rows),
        "resolved_rows": resolved_rows,
        "latest_timestamp": _latest_timestamp(rows),
        "segment_count": len(table),
        "horizon_counts": horizon_counts,
    }


def _load_rows_by_policy() -> Tuple[list, Dict[str, Any]]:
    source = os.getenv("AG_SEGMENT_ACCURACY_SOURCE", "supabase").strip().lower()
    if source == "archive":
        return _load_archive_rows()
    if source == "supabase":
        rows, meta = _load_supabase_rows()
        if rows:
            return rows, meta
        archive_rows, archive_meta = _load_archive_rows()
        archive_meta["fallback_from"] = "supabase"
        archive_meta["warning"] = meta.get("warning") or meta.get("source_status")
        return archive_rows, archive_meta
    # auto mode currently means Supabase first, archive fallback.
    rows, meta = _load_supabase_rows()
    if rows:
        return rows, meta
    archive_rows, archive_meta = _load_archive_rows()
    archive_meta["fallback_from"] = "supabase"
    archive_meta["warning"] = meta.get("warning") or meta.get("source_status")
    return archive_rows, archive_meta


def _load_table_cached() -> Dict[Tuple[str, str, str], Dict[int, Tuple[int, float]]]:
    """Source-policy cache. Supabase is TTL cached; archive is mtime cached."""
    with _CACHE_LOCK:
        source = os.getenv("AG_SEGMENT_ACCURACY_SOURCE", "supabase").strip().lower()
        if source == "archive":
            try:
                signature = f"archive:{_DATASET_PATH.stat().st_mtime}"
            except FileNotFoundError:
                signature = "archive:missing"
        else:
            signature = f"{source}:{int(time.time() // max(1, _SOURCE_TTL_SECONDS))}"
        if _CACHE["signature"] == signature and _CACHE["table"] is not None:
            return _CACHE["table"]
        rows, meta = _load_rows_by_policy()
        source_signature = meta.get("source_signature") or signature
        table = _build_table_from_dataset(rows)
        _CACHE["signature"] = source_signature
        _CACHE["table"] = table
        _CACHE["snapshot"] = _build_snapshot(rows, meta, table)
        return table


def _lookup_with_fallback(
    table: Dict[Tuple[str, str, str], Dict[int, Tuple[int, float]]],
    market_keys: Tuple[Optional[str], Optional[str]],
    scan_key: str,
    bucket: str,
    horizon_days: int,
) -> Optional[Tuple[int, float]]:
    """precise market → region market 순으로 시도. horizon 은 요청값 우선."""
    horizon_priority = [horizon_days] + [h for h in (5, 3, 7, 1, 14, 30) if h != horizon_days]
    for mk in market_keys:
        if not mk:
            continue
        cell = table.get((mk, scan_key, bucket))
        if not cell:
            continue
        for h in horizon_priority:
            v = cell.get(h)
            if v is not None:
                return v
    return None


def lookup_segment_win_rate(
    decision: str | None,
    market: str | None,
    scan_mode: str | None,
    horizon_days: int = 5,
    ticker: str | None = None,
) -> Optional[float]:
    """Return historical OOS win rate (%) for the segment, or None when sample
    is too small or segment is not measured.

    Source: live computation from scan_archive_learning_dataset_all.json
    (mtime cached). 이전의 하드코딩 dummy 값 (_SEGMENT_WIN_RATE) 은 폐기.

    Args:
        decision: PRIORITY_WATCHLIST / EXCEPTION_LEADER / WATCHLIST / OBSERVE / picked / ...
                  내부적으로 dataset 분류 체계 (picked/watchlist/exception_leader) 로 정규화.
        market: KOSPI / KOSDAQ / NASDAQ / AMEX / KR / US (또는 ticker suffix 추론).
        scan_mode: SWING / INTRADAY.
        horizon_days: 5 (default) / 7 / 3. fallback 순서: 요청값 → 5 → 7 → 3.
        ticker: market 추론용 fallback (.KS / .KQ).
    """
    bucket = _classify_bucket(decision)
    if bucket == "ignored":
        return None
    market_keys = _resolve_market_keys(market, ticker)
    if not any(market_keys):
        return None
    scan_key = str(scan_mode or "").upper().strip()
    if scan_key not in {"SWING", "INTRADAY"}:
        return None

    table = _load_table_cached()
    if not table:
        return None
    cell = _lookup_with_fallback(table, market_keys, scan_key, bucket, int(horizon_days))
    if cell is None:
        return None
    n, win_pct = cell
    if n < _MIN_SAMPLE_SIZE:
        return None
    return float(win_pct)


def lookup_segment_avg_return(
    decision: str | None,
    market: str | None,
    scan_mode: str | None,
    horizon_days: int = 5,
    ticker: str | None = None,
) -> Optional[float]:
    """Placeholder for future avg_return lookup. 현재는 None — UI 가 필요할 때
    별도 집계 컬럼을 추가해 활성화한다.
    """
    return None


def get_segment_sample_size(
    decision: str | None,
    market: str | None,
    scan_mode: str | None,
    horizon_days: int = 5,
    ticker: str | None = None,
) -> Optional[int]:
    """UI 에서 'n=X' 라벨을 보여주고 싶을 때 표본 크기 제공."""
    bucket = _classify_bucket(decision)
    if bucket == "ignored":
        return None
    market_keys = _resolve_market_keys(market, ticker)
    if not any(market_keys):
        return None
    scan_key = str(scan_mode or "").upper().strip()
    if scan_key not in {"SWING", "INTRADAY"}:
        return None
    table = _load_table_cached()
    cell = _lookup_with_fallback(table, market_keys, scan_key, bucket, int(horizon_days))
    if cell is None:
        return None
    return int(cell[0])


def force_reload() -> None:
    """테스트/관리 용도. 다음 lookup 시 dataset 을 재로드하게 만든다."""
    with _CACHE_LOCK:
        _CACHE["signature"] = None
        _CACHE["table"] = None
        _CACHE["snapshot"] = None


def get_segment_accuracy_snapshot() -> Dict[str, Any]:
    """Return source/coverage metadata for operational UI and diagnostics."""
    _load_table_cached()
    with _CACHE_LOCK:
        return dict(_CACHE.get("snapshot") or {})
