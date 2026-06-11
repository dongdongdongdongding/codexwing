#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/codex_swing_matplotlib")

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from sklearn.preprocessing import OneHotEncoder
except Exception:  # pragma: no cover
    OneHotEncoder = None

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover
    LGBMClassifier = None

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.db_manager import DBManager
from modules.kis_model_features import (
    KIS_CATEGORICAL_FEATURES,
    KIS_NUMERIC_FEATURES,
    KIS_PREFILTER_CATEGORICAL_FEATURES,
    KIS_PREFILTER_NUMERIC_FEATURES,
    KIS_SIDECAR_CATEGORICAL_FEATURES,
    KIS_SIDECAR_DIAGNOSTIC_NUMERIC_FEATURES,
    KIS_SIDECAR_MODEL_NUMERIC_FEATURES,
    KIS_THEME_NEWS_CATEGORICAL_FEATURES,
    KIS_THEME_NEWS_NUMERIC_FEATURES,
    flatten_kis_model_features,
)
from modules.kis_model_gate import evaluate_kis_model_gate
from modules.operational_candidate_scoring import DEFAULT_BUY_PREMIUM_PCT, adjust_return_for_buy_premium


warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

TARGET_TABLE = "scan_universe_snapshots"
REPORT_VERSION = "scan_universe_admission_challenger_v4_touch5_dd10"
PREPARED_DATASET_CACHE_VERSION = "scan_universe_admission_prepared_v4_buy_premium_sanity"
LEGACY_PREPARED_DATASET_CACHE_VERSIONS: set[str] = set()
REPORT_DIR = ROOT / "runtime_state" / "reports" / "learning"
MODEL_DIR = ROOT / "models" / "scan_universe_challengers"
OPERATIONAL_BUY_PREMIUM_PCT = DEFAULT_BUY_PREMIUM_PCT
PRIMARY_TARGET_RETURN_PCT = 5.0
EXTENDED_TARGET_RETURN_PCT = 10.0
MIN_RETRY_PAGE_SIZE = 5
MIN_PROMOTION_RUNS = 12
MIN_PROMOTION_DAYS = 6
MIN_PROMOTION_ROWS = 15
MIN_KIS_TRAIN_DAYS = 10
MAX_PROMOTION_STOP5_PCT = 35.0
MAX_PROMOTION_BAD_PATH_PCT = 45.0
MAX_PROMOTION_STOP_BEFORE_TARGET_5D_PCT = 35.0
MAX_PROMOTION_FOLD_STOP5_PCT = 50.0
MIN_PROMOTION_TARGET_BEFORE_STOP_5D_PCT = 50.0
MIN_PROMOTION_FOLD_TARGET_BEFORE_STOP_5D_PCT = 35.0
MIN_PROMOTION_TOUCH10_GUARD_PCT = 45.0
MIN_PROMOTION_TOUCH5_GUARD_PCT = 55.0
MIN_PROMOTION_GUARD_RAW_RATIO = 0.70
MIN_PROMOTION_MIN_LOW_5D_PCT = -10.0

KR_RETURN_SANITY_BOUNDS = {
    "return_1d_pct": (-35.0, 35.0),
    "return_3d_pct": (-75.0, 130.0),
    "return_5d_pct": (-90.0, 300.0),
    "max_high_return_1d_pct": (-35.0, 35.0),
    "max_high_return_3d_pct": (-75.0, 130.0),
    "max_high_return_5d_pct": (-90.0, 300.0),
    "min_low_return_1d_pct": (-35.0, 35.0),
    "min_low_return_3d_pct": (-75.0, 130.0),
    "min_low_return_5d_pct": (-90.0, 300.0),
}

NUMERIC_FEATURES = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "whale_score",
    "decision_score",
    "day_return_pct",
    "volume_ratio",
    "turnover",
    "foreigner_1d",
    "institution_1d",
    "retail_1d",
    "foreigner_3d",
    "institution_3d",
    "retail_3d",
    "foreigner_10d",
    "institution_10d",
    "retail_10d",
    "whale_flow_1d",
    "whale_flow_3d",
    "whale_flow_10d",
    "feature_coverage_score",
    "entry_reference_price",
    "priority_rank",
    "total_scans",
    "filtered_count",
]

CORE_NUMERIC = [
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "whale_score",
    "decision_score",
    "day_return_pct",
    "volume_ratio",
    "turnover",
    "feature_coverage_score",
    "entry_reference_price",
]

FLOW_NUMERIC = [
    "foreigner_1d",
    "institution_1d",
    "retail_1d",
    "foreigner_3d",
    "institution_3d",
    "retail_3d",
    "foreigner_10d",
    "institution_10d",
    "retail_10d",
    "whale_flow_1d",
    "whale_flow_3d",
    "whale_flow_10d",
]

CATEGORICAL_FEATURES = [
    "market",
    "row_role",
    "passed_current_model",
    "decision",
    "decision_bucket",
    "reject_stage",
    "reject_reason",
    "primary_theme",
    "theme_source",
    "theme_inference_status",
    "kr_universe_role",
    "scanner_timeframe_profile",
    "has_actual_flow",
    "flow_consensus_buying",
    "retail_dominant",
    "dominant",
    "whale_trend",
]

GATE_CATEGORICAL = [
    "row_role",
    "passed_current_model",
    "decision",
    "decision_bucket",
    "reject_stage",
    "reject_reason",
]

THEME_CATEGORICAL = [
    "primary_theme",
    "theme_source",
    "theme_inference_status",
]

CLOSE_FAILURE_RISK_GROUPS = [
    ("ticker", "ticker"),
    ("theme", "primary_theme"),
    ("kis_theme", "kis_theme_news_primary_theme"),
    ("kis_sector", "kis_stock_sector_name"),
    ("market", "market"),
]

CLOSE_FAILURE_RISK_METRICS = [
    "touch5_n",
    "failure_rate_pct",
    "clean_defense_rate_pct",
    "stop5_rate_pct",
    "avg_close_5d_pct",
    "avg_mfe_5d_pct",
    "avg_mae_5d_pct",
    "risk_score",
]

CLOSE_FAILURE_RISK_NUMERIC = [
    f"close_failure_prior_{prefix}_{metric}"
    for prefix, _column in CLOSE_FAILURE_RISK_GROUPS
    for metric in CLOSE_FAILURE_RISK_METRICS
]

CLOSE_FAILURE_RISK_CATEGORICAL = [
    f"close_failure_prior_{prefix}_risk_bucket"
    for prefix, _column in CLOSE_FAILURE_RISK_GROUPS
]

LABEL_RETURN_COLUMNS = [
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "max_high_return_1d_pct",
    "max_high_return_3d_pct",
    "max_high_return_5d_pct",
    "min_low_return_1d_pct",
    "min_low_return_3d_pct",
    "min_low_return_5d_pct",
]

BUY_PREMIUM_RETURN_COLUMNS = [f"buy_premium_{column}" for column in LABEL_RETURN_COLUMNS]
BUY_PREMIUM_RETURN_SANITY_BOUNDS = {
    f"buy_premium_{column}": bounds for column, bounds in KR_RETURN_SANITY_BOUNDS.items()
}

PATH_COLUMNS = [
    "target_hit_1d",
    "target_hit_3d",
    "target_hit_5d",
    "stop_hit_1d",
    "stop_hit_3d",
    "stop_hit_5d",
    "target_before_stop_1d",
    "target_before_stop_3d",
    "target_before_stop_5d",
    "stop_before_target_1d",
    "stop_before_target_3d",
    "stop_before_target_5d",
    "first_touch_1d",
    "first_touch_3d",
    "first_touch_5d",
]

BUY_PREMIUM_PATH_COLUMNS = [f"buy_premium_{column}" for column in PATH_COLUMNS]

SELECT_COLUMNS = [
    "id",
    "snapshot_key",
    "run_id",
    "ticker",
    "stock_name",
    "market",
    "scan_mode",
    "base_trade_date",
    "scanned_at",
    "row_role",
    "passed_current_model",
    "priority_rank",
    "decision",
    "decision_bucket",
    "reject_stage",
    "reject_reason",
    "feature_snapshot",
    "feature_origin",
    "total_scans",
    "filtered_count",
    "alpha_score",
    "tech_score",
    "ml_prob",
    "prob_clean",
    "whale_score",
    "decision_score",
    "day_return_pct",
    "volume_ratio",
    "turnover",
    "foreigner_1d",
    "institution_1d",
    "retail_1d",
    "foreigner_3d",
    "institution_3d",
    "retail_3d",
    "foreigner_10d",
    "institution_10d",
    "retail_10d",
    "whale_flow_1d",
    "whale_flow_3d",
    "whale_flow_10d",
    "feature_coverage_score",
    "feature_missing_keys",
    "has_actual_flow",
    "flow_consensus_buying",
    "retail_dominant",
    "dominant",
    "whale_trend",
    "flow_source",
    "flow_warnings",
    "primary_theme",
    "theme_source",
    "theme_inference_status",
    "kr_universe_role",
    "scanner_timeframe_profile",
    "entry_reference_price",
    "operational_buy_premium_pct",
    "buy_premium_entry_price",
    "buy_premium_path_label_version",
    *LABEL_RETURN_COLUMNS,
    *BUY_PREMIUM_RETURN_COLUMNS,
    *PATH_COLUMNS,
    *BUY_PREMIUM_PATH_COLUMNS,
]


@dataclass(frozen=True)
class LabelSpec:
    name: str
    horizon: str
    description: str


@dataclass(frozen=True)
class CandidateJob:
    market: str
    label_spec: LabelSpec
    feature_name: str
    numeric: Tuple[str, ...]
    categorical: Tuple[str, ...]
    model_name: str
    topn: int
    prob_threshold: float | None


LABEL_SPECS = [
    LabelSpec("pos_1d", "1d", "1D defensive close return > 0 (not an operational win objective)"),
    LabelSpec("pos_3d", "3d", "3D defensive close return > 0 (not an operational win objective)"),
    LabelSpec("pos_5d", "5d", "5D defensive close return > 0 (not an operational win objective)"),
    LabelSpec("clean_3d", "3d", "3D defensive close > 0, 1D not worse than -2%, and 3D low above -5%"),
    LabelSpec("clean_5d", "5d", "5D defensive close > 0, 1D not worse than -3%, and 5D low above -5%"),
    LabelSpec("sustain_1_3_5_lowdd", "5d", "1D/3D/5D defensive closes positive and 5D low above -5%"),
    LabelSpec("target_first_5d", "5d", "5D target touched before stop"),
    LabelSpec("target_first_sustain_5d", "5d", "5D target touched before stop, 3D and 5D closes positive"),
    LabelSpec("target_hit_no_stop_5d", "5d", "5D target hit and stop not hit"),
    LabelSpec("touch5_5d", "5d", "5D high touches entry +5% at least once"),
    LabelSpec("touch10_5d", "5d", "5D high touches entry +10% at least once"),
    LabelSpec("touch5_guard_5d", "5d", "5D high touches +5% while 5D low stays above -5%"),
    LabelSpec("touch5_dd10_5d", "5d", "5D high touches +5% while 5D low stays at or above -10%"),
    LabelSpec("touch10_guard_5d", "5d", "5D high touches +10% while 5D low stays above -5%"),
]

TOPNS = [1, 3, 5]


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return str(value)


def _round(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return round(number, digits)
    except Exception:
        return None


def _pct(value: Any) -> float | None:
    number = _round(value, 8)
    return round(number * 100.0, 4) if number is not None else None


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        number = float(value)
    except Exception:
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _metric_float(metrics_map: Dict[str, Any], key: str, default: float) -> float:
    value = metrics_map.get(key)
    if value is None:
        return default
    try:
        number = float(value)
    except Exception:
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _append_unique(values: List[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _premium_col(column: str) -> str:
    return f"buy_premium_{column}"


def _adjusted_return_series(df: pd.DataFrame, column: str) -> pd.Series:
    raw = pd.to_numeric(df.get(column, pd.Series(index=df.index, dtype=float)), errors="coerce")
    computed = raw.map(lambda value: adjust_return_for_buy_premium(value, OPERATIONAL_BUY_PREMIUM_PCT))
    if _premium_col(column) in df.columns:
        exact = pd.to_numeric(df[_premium_col(column)], errors="coerce")
        return exact.where(exact.notna(), computed)
    return computed


def attach_operational_outcome_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in LABEL_RETURN_COLUMNS:
        if column in out.columns:
            computed = pd.to_numeric(out[column], errors="coerce").map(
                lambda value: adjust_return_for_buy_premium(value, OPERATIONAL_BUY_PREMIUM_PCT)
            )
            premium = _premium_col(column)
            if premium in out.columns:
                exact = pd.to_numeric(out[premium], errors="coerce")
                out[premium] = exact.where(exact.notna(), computed)
            else:
                out[premium] = computed
    out["operational_buy_premium_pct"] = float(OPERATIONAL_BUY_PREMIUM_PCT)
    return out


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    clean = series.astype("object").where(series.notna(), "")
    return clean.astype(str).str.strip().str.lower().isin({"1", "true", "yes", "y"})


def _operational_path_column(df: pd.DataFrame, column: str) -> pd.Series:
    fallback = df.get(column, pd.Series(index=df.index, dtype=object))
    premium = _premium_col(column)
    if premium in df.columns:
        exact = df[premium]
        return exact.where(exact.notna(), fallback)
    return fallback


def _operational_bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    return _bool_series(_operational_path_column(df, column))


def _onehot_encoder() -> Any:
    if OneHotEncoder is None:
        raise RuntimeError("sklearn OneHotEncoder unavailable")
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False, min_frequency=3)
    except TypeError:  # pragma: no cover - older sklearn
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _date_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    try:
        return pd.to_datetime(text).date().isoformat()
    except Exception:
        return ""


def _log(enabled: bool, message: str) -> None:
    if enabled:
        print(message, flush=True)


def _date_chunks(min_base_date: str, max_base_date: str, chunk_days: int) -> List[Tuple[str, str]]:
    if chunk_days <= 0 or not min_base_date or not max_base_date:
        return []
    start = date.fromisoformat(min_base_date)
    end = date.fromisoformat(max_base_date)
    if end < start:
        return []
    chunks: List[Tuple[str, str]] = []
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + timedelta(days=max(1, int(chunk_days)) - 1))
        chunks.append((cursor.isoformat(), chunk_end.isoformat()))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def _id_chunks(min_id: int, max_id: int, chunk_size: int) -> List[Tuple[int, int]]:
    if chunk_size <= 0 or max_id <= 0:
        return []
    start = max(1, int(min_id or 1))
    if start > max_id:
        return []
    chunks: List[Tuple[int, int]] = []
    cursor = start
    while cursor <= max_id:
        chunk_end = min(max_id, cursor + int(chunk_size) - 1)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + 1
    return chunks


def _combine_frames(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if frame is not None and not frame.empty]
    if not non_empty:
        return pd.DataFrame()
    out = pd.concat(non_empty, ignore_index=True)
    if "id" in out.columns:
        out = out.drop_duplicates(subset=["id"], keep="last").sort_values("id")
    return out.reset_index(drop=True)


def _matches_fetch_filters(
    row: Mapping[str, Any],
    *,
    market: str,
    scan_mode: str,
    base_date: str,
    min_base_date: str,
    max_base_date: str,
) -> bool:
    if market != "ALL" and str(row.get("market") or "") != market:
        return False
    if scan_mode != "ALL" and str(row.get("scan_mode") or "") != scan_mode:
        return False
    row_date = _date_text(row.get("base_trade_date") or row.get("scanned_at"))
    if base_date and row_date != base_date:
        return False
    if min_base_date and row_date < min_base_date:
        return False
    if max_base_date and row_date > max_base_date:
        return False
    return True


def _execute_query(query: Any, *, timeout_sec: float = 0.0) -> Any:
    timeout = float(timeout_sec or 0.0)
    if timeout <= 0 or not hasattr(signal, "SIGALRM"):
        return query.execute()

    previous_handler = signal.getsignal(signal.SIGALRM)

    def _timeout_handler(_signum: int, _frame: Any) -> None:
        raise TimeoutError(f"Supabase query exceeded fetch_timeout_sec={timeout:g}")

    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return query.execute()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def fetch_rows(
    *,
    market: str,
    scan_mode: str,
    page_size: int,
    min_id: int = 0,
    max_id: int = 0,
    base_date: str = "",
    min_base_date: str = "",
    max_base_date: str = "",
    limit: int = 0,
    client_filter: bool = False,
    fetch_timeout_sec: float = 0.0,
) -> pd.DataFrame:
    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")
    rows: List[Dict[str, Any]] = []
    last_id = max(0, int(min_id or 0) - 1)
    cols = ",".join(SELECT_COLUMNS)
    safe_page_size = min(max(1, int(page_size or 1000)), 1000)
    while True:
        query = db.client.table(TARGET_TABLE).select(cols).order("id").gt("id", last_id).limit(safe_page_size)
        if max_id and int(max_id) > 0:
            query = query.lte("id", int(max_id))
        if not client_filter and market != "ALL":
            query = query.eq("market", market)
        if not client_filter and scan_mode != "ALL":
            query = query.eq("scan_mode", scan_mode)
        if not client_filter and base_date:
            query = query.eq("base_trade_date", base_date)
        if not client_filter and min_base_date:
            query = query.gte("base_trade_date", min_base_date)
        if not client_filter and max_base_date:
            query = query.lte("base_trade_date", max_base_date)
        try:
            batch = _execute_query(query, timeout_sec=fetch_timeout_sec).data or []
        except Exception as exc:
            message = str(exc)
            if safe_page_size > MIN_RETRY_PAGE_SIZE and (
                "statement timeout" in message or "57014" in message or "fetch_timeout_sec" in message
            ):
                next_page_size = max(MIN_RETRY_PAGE_SIZE, safe_page_size // 2)
                print(
                    f"[WARN] Supabase fetch timed out at page_size={safe_page_size}; retrying with page_size={next_page_size}",
                    flush=True,
                )
                safe_page_size = next_page_size
                continue
            raise
        accepted_batch = (
            [
                row
                for row in batch
                if _matches_fetch_filters(
                    row,
                    market=market,
                    scan_mode=scan_mode,
                    base_date=base_date,
                    min_base_date=min_base_date,
                    max_base_date=max_base_date,
                )
            ]
            if client_filter
            else batch
        )
        rows.extend(accepted_batch)
        if limit and len(rows) >= int(limit):
            return pd.DataFrame(rows[: int(limit)])
        if batch:
            last_id = max(int(row.get("id") or last_id) for row in batch)
        if len(batch) < safe_page_size:
            break
        if max_id and last_id >= int(max_id):
            break
    return pd.DataFrame(rows)


def fetch_rows_chunked(
    *,
    market: str,
    scan_mode: str,
    page_size: int,
    min_id: int = 0,
    max_id: int = 0,
    base_date: str = "",
    min_base_date: str = "",
    max_base_date: str = "",
    limit: int = 0,
    fetch_chunk_days: int = 0,
    fetch_id_chunk_size: int = 0,
    client_filter: bool = False,
    fetch_timeout_sec: float = 0.0,
    max_fetch_chunks: int = 0,
    progress: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    base_filters = {
        "market": market,
        "scan_mode": scan_mode,
        "page_size": page_size,
        "min_id": min_id,
        "max_id": max_id,
        "base_date": base_date,
        "min_base_date": min_base_date,
        "max_base_date": max_base_date,
        "limit": limit,
        "client_filter": client_filter,
        "fetch_timeout_sec": fetch_timeout_sec,
    }
    date_windows = _date_chunks(min_base_date, max_base_date, fetch_chunk_days) if not base_date and not client_filter else []
    id_windows = _id_chunks(min_id, max_id, fetch_id_chunk_size)
    fetch_meta: Dict[str, Any] = {
        "mode": "single",
        "chunks": [],
        "requested_limit": int(limit or 0),
        "fetch_chunk_days": int(fetch_chunk_days or 0),
        "fetch_id_chunk_size": int(fetch_id_chunk_size or 0),
        "fetch_timeout_sec": _round(fetch_timeout_sec),
        "max_fetch_chunks": int(max_fetch_chunks or 0),
        "truncated_by_max_fetch_chunks": False,
    }
    started = perf_counter()
    if date_windows:
        frames: List[pd.DataFrame] = []
        fetch_meta["mode"] = "date_chunks"
        for idx, (start, end) in enumerate(date_windows, start=1):
            if max_fetch_chunks and idx > int(max_fetch_chunks):
                fetch_meta["truncated_by_max_fetch_chunks"] = True
                break
            _log(progress, f"[INFO] fetching date chunk {idx}/{len(date_windows)}: {start}..{end}")
            chunk_dates = {
                "base_date": start,
                "min_base_date": "",
                "max_base_date": "",
            } if start == end else {
                "base_date": "",
                "min_base_date": start,
                "max_base_date": end,
            }
            chunk = fetch_rows(
                **{
                    **base_filters,
                    **chunk_dates,
                    "limit": max(0, int(limit or 0) - sum(len(frame) for frame in frames)) if limit else 0,
                }
            )
            frames.append(chunk)
            fetch_meta["chunks"].append({"type": "date", "min_base_date": start, "max_base_date": end, "rows": int(len(chunk))})
            if limit and sum(len(frame) for frame in frames) >= int(limit):
                break
        out = _combine_frames(frames)
        if limit and len(out) > int(limit):
            out = out.head(int(limit)).copy()
        fetch_meta["elapsed_sec"] = _round(perf_counter() - started, 3)
        fetch_meta["rows"] = int(len(out))
        return out, fetch_meta
    if id_windows:
        frames = []
        fetch_meta["mode"] = "id_chunks"
        for idx, (start_id, end_id) in enumerate(id_windows, start=1):
            if max_fetch_chunks and idx > int(max_fetch_chunks):
                fetch_meta["truncated_by_max_fetch_chunks"] = True
                break
            _log(progress, f"[INFO] fetching id chunk {idx}/{len(id_windows)}: {start_id}..{end_id}")
            chunk = fetch_rows(
                **{
                    **base_filters,
                    "min_id": start_id,
                    "max_id": end_id,
                    "limit": max(0, int(limit or 0) - sum(len(frame) for frame in frames)) if limit else 0,
                }
            )
            frames.append(chunk)
            fetch_meta["chunks"].append({"type": "id", "min_id": start_id, "max_id": end_id, "rows": int(len(chunk))})
            if limit and sum(len(frame) for frame in frames) >= int(limit):
                break
        out = _combine_frames(frames)
        if limit and len(out) > int(limit):
            out = out.head(int(limit)).copy()
        fetch_meta["elapsed_sec"] = _round(perf_counter() - started, 3)
        fetch_meta["rows"] = int(len(out))
        return out, fetch_meta

    out = fetch_rows(**base_filters)
    fetch_meta["elapsed_sec"] = _round(perf_counter() - started, 3)
    fetch_meta["rows"] = int(len(out))
    return out, fetch_meta


def apply_return_sanity(df: pd.DataFrame, *, mode: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if df.empty or mode == "off":
        return df.copy(), {"mode": mode, "removed_rows": 0, "column_violations": {}}
    if mode != "kr_price_limit":
        raise ValueError(f"unknown return sanity mode: {mode}")
    mask = pd.Series(True, index=df.index)
    violations: Dict[str, int] = {}
    bounds = {**KR_RETURN_SANITY_BOUNDS, **BUY_PREMIUM_RETURN_SANITY_BOUNDS}
    for col, (low, high) in bounds.items():
        if col not in df.columns:
            continue
        values = pd.to_numeric(df[col], errors="coerce")
        bad = values.notna() & (~values.between(low, high, inclusive="both"))
        violations[col] = int(bad.sum())
        mask &= ~bad
    clean = df.loc[mask].copy()
    return clean, {
        "mode": mode,
        "removed_rows": int((~mask).sum()),
        "remaining_rows": int(len(clean)),
        "column_violations": {key: value for key, value in violations.items() if value},
        "bounds": bounds,
    }


def _attach_kis_features(out: pd.DataFrame) -> pd.DataFrame:
    if out.empty:
        return out
    flattened = [flatten_kis_model_features(row) for row in out.to_dict(orient="records")]
    if not flattened:
        return out
    kis_columns = list(KIS_NUMERIC_FEATURES) + list(KIS_CATEGORICAL_FEATURES)
    kis_frame = pd.DataFrame(flattened, index=out.index).reindex(columns=kis_columns)
    existing_kis = [col for col in kis_columns if col in out.columns]
    base = out.drop(columns=existing_kis) if existing_kis else out
    return pd.concat([base, kis_frame], axis=1)


def _risk_bucket(count: float, score: float | None) -> str:
    if count < 3 or score is None or not math.isfinite(float(score)):
        return "INSUFFICIENT_HISTORY"
    if score >= 80.0:
        return "EXTREME"
    if score >= 60.0:
        return "HIGH"
    if score >= 40.0:
        return "MODERATE"
    return "LOW"


def _attach_close_failure_prior_for_group(
    out: pd.DataFrame,
    *,
    group_col: str,
    prefix: str,
    touch_base: pd.Series,
    failure: pd.Series,
    clean_defense: pd.Series,
    stop5: pd.Series,
    close5: pd.Series,
    mfe5: pd.Series,
    mae5: pd.Series,
) -> pd.DataFrame:
    if group_col not in out.columns:
        for metric in CLOSE_FAILURE_RISK_METRICS:
            out[f"close_failure_prior_{prefix}_{metric}"] = np.nan
        out[f"close_failure_prior_{prefix}_risk_bucket"] = "INSUFFICIENT_HISTORY"
        return out

    order = out.sort_values(["trade_date", "run_id", "ticker"]).index
    frame = pd.DataFrame(index=order)
    frame["group"] = out.loc[order, group_col].fillna("UNKNOWN").astype(str).str.strip().replace("", "UNKNOWN")
    frame["trade_date"] = out.loc[order, "trade_date"].fillna("").astype(str)
    frame["touch"] = touch_base.loc[order].astype(float)
    frame["failure"] = failure.loc[order].astype(float)
    frame["clean"] = clean_defense.loc[order].astype(float)
    frame["stop"] = stop5.loc[order].astype(float)
    frame["close_sum"] = pd.to_numeric(close5.loc[order], errors="coerce").where(touch_base.loc[order], 0.0).fillna(0.0)
    frame["mfe_sum"] = pd.to_numeric(mfe5.loc[order], errors="coerce").where(touch_base.loc[order], 0.0).fillna(0.0)
    frame["mae_sum"] = pd.to_numeric(mae5.loc[order], errors="coerce").where(touch_base.loc[order], 0.0).fillna(0.0)

    daily = (
        frame.groupby(["group", "trade_date"], sort=True)[
            ["touch", "failure", "clean", "stop", "close_sum", "mfe_sum", "mae_sum"]
        ]
        .sum()
        .sort_index()
    )
    prior_daily = daily.groupby(level=0).cumsum() - daily
    row_keys = pd.MultiIndex.from_frame(frame[["group", "trade_date"]])
    prior_touch = prior_daily["touch"].reindex(row_keys).to_numpy(dtype=float)
    prior_failure = prior_daily["failure"].reindex(row_keys).to_numpy(dtype=float)
    prior_clean = prior_daily["clean"].reindex(row_keys).to_numpy(dtype=float)
    prior_stop = prior_daily["stop"].reindex(row_keys).to_numpy(dtype=float)
    prior_close_sum = prior_daily["close_sum"].reindex(row_keys).to_numpy(dtype=float)
    prior_mfe_sum = prior_daily["mfe_sum"].reindex(row_keys).to_numpy(dtype=float)
    prior_mae_sum = prior_daily["mae_sum"].reindex(row_keys).to_numpy(dtype=float)

    prior_touch_series = pd.Series(prior_touch, index=order)
    denom = prior_touch_series.replace(0.0, np.nan)
    failure_rate = (prior_failure / denom) * 100.0
    clean_rate = (prior_clean / denom) * 100.0
    stop_rate = (prior_stop / denom) * 100.0
    risk_score = (failure_rate.fillna(0.0) * 0.7 + stop_rate.fillna(0.0) * 0.35 - clean_rate.fillna(0.0) * 0.25).clip(0.0, 100.0)

    result = pd.DataFrame(index=order)
    result[f"close_failure_prior_{prefix}_touch5_n"] = prior_touch_series
    result[f"close_failure_prior_{prefix}_failure_rate_pct"] = failure_rate
    result[f"close_failure_prior_{prefix}_clean_defense_rate_pct"] = clean_rate
    result[f"close_failure_prior_{prefix}_stop5_rate_pct"] = stop_rate
    result[f"close_failure_prior_{prefix}_avg_close_5d_pct"] = prior_close_sum / denom
    result[f"close_failure_prior_{prefix}_avg_mfe_5d_pct"] = prior_mfe_sum / denom
    result[f"close_failure_prior_{prefix}_avg_mae_5d_pct"] = prior_mae_sum / denom
    result[f"close_failure_prior_{prefix}_risk_score"] = risk_score.where(prior_touch_series.gt(0), np.nan)
    result[f"close_failure_prior_{prefix}_risk_bucket"] = [
        _risk_bucket(float(count), _safe_float(score))
        for count, score in zip(
            result[f"close_failure_prior_{prefix}_touch5_n"].tolist(),
            result[f"close_failure_prior_{prefix}_risk_score"].tolist(),
        )
    ]
    for column in result.columns:
        out[column] = result[column].reindex(out.index)
    return out


def attach_close_failure_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    required_order_cols = {"trade_date", "run_id", "ticker"}
    if not required_order_cols.issubset(out.columns):
        return out
    return1 = _adjusted_return_series(out, "return_1d_pct")
    return5 = _adjusted_return_series(out, "return_5d_pct")
    mfe5 = _adjusted_return_series(out, "max_high_return_5d_pct")
    mae5 = _adjusted_return_series(out, "min_low_return_5d_pct")
    touch_base = mfe5.ge(PRIMARY_TARGET_RETURN_PCT).fillna(False) & return5.notna()
    failure = touch_base & return5.lt(0.0).fillna(False)
    stop5 = touch_base & mae5.le(-5.0).fillna(False)
    stop5 = stop5 | (touch_base & _operational_bool_series(out, "stop_before_target_5d").fillna(False).astype(bool))
    clean_defense = touch_base & return5.gt(0.0).fillna(False) & mae5.gt(-5.0).fillna(False) & return1.ge(-3.0).fillna(False)
    for prefix, group_col in CLOSE_FAILURE_RISK_GROUPS:
        out = _attach_close_failure_prior_for_group(
            out,
            group_col=group_col,
            prefix=prefix,
            touch_base=touch_base,
            failure=failure,
            clean_defense=clean_defense,
            stop5=stop5,
            close5=return5,
            mfe5=mfe5,
            mae5=mae5,
        )
    return out


def prepare_dataset(df: pd.DataFrame, *, return_sanity: str = "kr_price_limit") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if df.empty:
        return df.copy(), {"mode": return_sanity, "removed_rows": 0}
    out = df.copy()
    ticker = out.get("ticker", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    market = out.get("market", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    scan_mode = out.get("scan_mode", pd.Series("", index=out.index)).fillna("").astype(str).str.upper()
    out = out[(ticker.str.endswith(".KS") | ticker.str.endswith(".KQ") | market.isin(["KOSPI", "KOSDAQ"])) & scan_mode.eq("SWING")].copy()
    if out.empty:
        return out, {"mode": return_sanity, "removed_rows": 0}
    out = _attach_kis_features(out)
    numeric_for_coercion = list(NUMERIC_FEATURES) + list(KIS_NUMERIC_FEATURES)
    categorical_for_coercion = list(CATEGORICAL_FEATURES) + list(KIS_CATEGORICAL_FEATURES)
    for col in sorted(
        set(numeric_for_coercion + LABEL_RETURN_COLUMNS + BUY_PREMIUM_RETURN_COLUMNS + ["priority_rank", "total_scans", "filtered_count"])
    ):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    bool_columns: Dict[str, pd.Series] = {}
    for col in PATH_COLUMNS + BUY_PREMIUM_PATH_COLUMNS + ["passed_current_model", "has_actual_flow", "flow_consensus_buying", "retail_dominant"]:
        if col in out.columns:
            bool_columns[f"{col}_bool"] = _bool_series(out[col])
    if bool_columns:
        out = pd.concat([out, pd.DataFrame(bool_columns, index=out.index)], axis=1)
    categorical_columns: Dict[str, pd.Series] = {}
    for col in categorical_for_coercion:
        if col in out.columns:
            categorical_columns[col] = out[col].fillna("UNKNOWN").astype(str)
        else:
            categorical_columns[col] = pd.Series("UNKNOWN", index=out.index, dtype="object")
    if categorical_columns:
        out = pd.concat(
            [
                out.drop(columns=[col for col in categorical_columns if col in out.columns]),
                pd.DataFrame(categorical_columns, index=out.index),
            ],
            axis=1,
        )
    rec = out.get("base_trade_date", pd.Series(index=out.index, dtype=object))
    scanned = out.get("scanned_at", pd.Series(index=out.index, dtype=object))
    rec = rec.where(rec.notna() & rec.astype(str).str.strip().ne(""), scanned)
    out["trade_date"] = pd.to_datetime(rec, errors="coerce", utc=True).dt.strftime("%Y-%m-%d")
    out = out[out["trade_date"].fillna("").astype(str).str.len().ge(8)].copy()
    if "run_id" not in out.columns:
        out["run_id"] = out["trade_date"]
    out["run_id"] = out["run_id"].fillna(out["trade_date"]).astype(str)
    if "market" not in out.columns:
        out["market"] = np.where(ticker.loc[out.index].str.endswith(".KS"), "KOSPI", "KOSDAQ")
    out.loc[out["market"].fillna("").astype(str).str.upper().eq(""), "market"] = np.where(
        ticker.loc[out.index].str.endswith(".KS"),
        "KOSPI",
        "KOSDAQ",
    )
    out["market"] = out["market"].fillna("").astype(str).str.upper()
    out, sanity = apply_return_sanity(out, mode=return_sanity)
    out = attach_operational_outcome_columns(out)
    return1 = _adjusted_return_series(out, "return_1d_pct")
    return5 = _adjusted_return_series(out, "return_5d_pct")
    low5 = _adjusted_return_series(out, "min_low_return_5d_pct")
    out["stop5_proxy"] = _operational_bool_series(out, "stop_before_target_5d").fillna(False)
    out["stop5_proxy"] |= low5.le(-5.0).fillna(False)
    out["bad_path"] = out["stop5_proxy"] | return1.lt(-3.0).fillna(False) | return5.lt(0.0).fillna(False)
    out = attach_close_failure_risk_features(out)
    return out.sort_values(["trade_date", "run_id", "ticker"]).copy(), sanity


def _cache_meta_path(cache_path: Path) -> Path:
    return cache_path.with_suffix(cache_path.suffix + ".meta.json")


def _dataset_cache_signature(fetch_filters: Mapping[str, Any], *, return_sanity: str) -> Dict[str, Any]:
    return {
        "source": TARGET_TABLE,
        "fetch_filters": {key: fetch_filters.get(key) for key in sorted(fetch_filters)},
        "return_sanity": return_sanity,
        "version": PREPARED_DATASET_CACHE_VERSION,
    }


def _cache_signature_compatible(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    actual_dict = dict(actual)
    expected_dict = dict(expected)
    if actual_dict == expected_dict:
        return True
    actual_version = str(actual_dict.get("version") or "")
    expected_version = str(expected_dict.get("version") or "")
    if expected_version != PREPARED_DATASET_CACHE_VERSION:
        return False
    if actual_version not in LEGACY_PREPARED_DATASET_CACHE_VERSIONS:
        return False
    actual_no_version = {key: value for key, value in actual_dict.items() if key != "version"}
    expected_no_version = {key: value for key, value in expected_dict.items() if key != "version"}
    return actual_no_version == expected_no_version


def load_prepared_dataset_cache(cache_path: Path, *, signature: Mapping[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]] | None:
    meta_path = _cache_meta_path(cache_path)
    if not cache_path.exists() or not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not _cache_signature_compatible(meta.get("signature") or {}, signature):
        return None
    try:
        frame = pd.read_pickle(cache_path)
    except Exception:
        return None
    frame = attach_close_failure_risk_features(frame)
    cache_info = {
        "enabled": True,
        "mode": "hit",
        "path": str(cache_path),
        "meta_path": str(meta_path),
        "prepared_rows": int(len(frame)),
        "raw_rows": meta.get("raw_rows"),
        "return_sanity": meta.get("return_sanity") or {},
        "created_at": meta.get("created_at"),
    }
    return frame, cache_info


def write_prepared_dataset_cache(
    cache_path: Path,
    *,
    signature: Mapping[str, Any],
    data: pd.DataFrame,
    raw_rows: int,
    return_sanity: Mapping[str, Any],
) -> Dict[str, Any]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_pickle(cache_path)
    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "signature": dict(signature),
        "raw_rows": int(raw_rows),
        "prepared_rows": int(len(data)),
        "return_sanity": dict(return_sanity),
    }
    meta_path = _cache_meta_path(cache_path)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
    return {
        "enabled": True,
        "mode": "write",
        "path": str(cache_path),
        "meta_path": str(meta_path),
        "prepared_rows": int(len(data)),
        "raw_rows": int(raw_rows),
    }


def label_series(df: pd.DataFrame, spec: LabelSpec) -> Tuple[pd.Series, pd.Series]:
    false = pd.Series(False, index=df.index)
    if spec.name == "pos_1d":
        ret1 = _adjusted_return_series(df, "return_1d_pct")
        valid = ret1.notna()
        return ret1.gt(0).fillna(False), valid
    if spec.name == "pos_3d":
        ret3 = _adjusted_return_series(df, "return_3d_pct")
        valid = ret3.notna()
        return ret3.gt(0).fillna(False), valid
    if spec.name == "pos_5d":
        ret5 = _adjusted_return_series(df, "return_5d_pct")
        valid = ret5.notna()
        return ret5.gt(0).fillna(False), valid
    if spec.name == "clean_3d":
        ret1 = _adjusted_return_series(df, "return_1d_pct")
        ret3 = _adjusted_return_series(df, "return_3d_pct")
        low3 = _adjusted_return_series(df, "min_low_return_3d_pct")
        valid = ret1.notna() & ret3.notna() & low3.notna()
        return (
            ret3.gt(0)
            & ret1.ge(-2.0)
            & low3.gt(-5.0)
        ).fillna(False), valid
    if spec.name == "clean_5d":
        ret1 = _adjusted_return_series(df, "return_1d_pct")
        ret5 = _adjusted_return_series(df, "return_5d_pct")
        low5 = _adjusted_return_series(df, "min_low_return_5d_pct")
        valid = ret1.notna() & ret5.notna() & low5.notna()
        return (
            ret5.gt(0)
            & ret1.ge(-3.0)
            & low5.gt(-5.0)
        ).fillna(False), valid
    if spec.name == "sustain_1_3_5_lowdd":
        ret1 = _adjusted_return_series(df, "return_1d_pct")
        ret3 = _adjusted_return_series(df, "return_3d_pct")
        ret5 = _adjusted_return_series(df, "return_5d_pct")
        low5 = _adjusted_return_series(df, "min_low_return_5d_pct")
        valid = ret1.notna() & ret3.notna() & ret5.notna() & low5.notna()
        return (
            ret1.gt(0)
            & ret3.gt(0)
            & ret5.gt(0)
            & low5.gt(-5.0)
        ).fillna(False), valid
    if spec.name == "target_first_5d":
        mfe = _adjusted_return_series(df, "max_high_return_5d_pct")
        mae = _adjusted_return_series(df, "min_low_return_5d_pct")
        target_first = _operational_path_column(df, "target_before_stop_5d")
        stop_first = _operational_path_column(df, "stop_before_target_5d")
        valid = target_first.notna() & stop_first.notna() & mfe.notna() & mae.notna()
        return (
            _bool_series(target_first).fillna(False)
            & mfe.ge(5.0).fillna(False)
            & mae.gt(-5.0).fillna(False)
        ).fillna(False), valid
    if spec.name == "target_first_sustain_5d":
        ret3 = _adjusted_return_series(df, "return_3d_pct")
        ret5 = _adjusted_return_series(df, "return_5d_pct")
        mfe = _adjusted_return_series(df, "max_high_return_5d_pct")
        mae = _adjusted_return_series(df, "min_low_return_5d_pct")
        valid = (
            _operational_path_column(df, "target_before_stop_5d").notna()
            & _operational_path_column(df, "stop_before_target_5d").notna()
            & ret3.notna()
            & ret5.notna()
            & mfe.notna()
            & mae.notna()
        )
        return (
            _operational_bool_series(df, "target_before_stop_5d").fillna(False)
            & ret3.gt(0)
            & ret5.gt(0)
            & mfe.ge(5.0).fillna(False)
            & mae.gt(-5.0).fillna(False)
        ).fillna(False), valid
    if spec.name == "target_hit_no_stop_5d":
        mfe = _adjusted_return_series(df, "max_high_return_5d_pct")
        mae = _adjusted_return_series(df, "min_low_return_5d_pct")
        target_hit = _operational_path_column(df, "target_hit_5d")
        stop_hit = _operational_path_column(df, "stop_hit_5d")
        valid = target_hit.notna() & stop_hit.notna() & mfe.notna() & mae.notna()
        return (
            _bool_series(target_hit).fillna(False)
            & mfe.ge(5.0).fillna(False)
            & mae.gt(-5.0).fillna(False)
        ).fillna(False), valid
    if spec.name in {"touch5_5d", "touch10_5d", "touch5_guard_5d", "touch5_dd10_5d", "touch10_guard_5d"}:
        target = 10.0 if spec.name.startswith("touch10") else 5.0
        mfe = _adjusted_return_series(df, "max_high_return_5d_pct")
        mae = _adjusted_return_series(df, "min_low_return_5d_pct")
        valid = mfe.notna()
        hit = mfe.ge(target).fillna(False)
        if spec.name == "touch5_dd10_5d":
            valid &= mae.notna()
            hit &= mae.ge(MIN_PROMOTION_MIN_LOW_5D_PCT).fillna(False)
        elif "guard" in spec.name:
            valid &= mae.notna()
            hit &= mae.gt(-5.0).fillna(False)
        return hit, valid
    raise KeyError(spec.name)


def feature_sets(df: pd.DataFrame) -> Dict[str, Tuple[List[str], List[str]]]:
    core = [col for col in CORE_NUMERIC if col in df.columns]
    flow = [col for col in CORE_NUMERIC + FLOW_NUMERIC if col in df.columns]
    all_num = [col for col in NUMERIC_FEATURES if col in df.columns]
    failure_risk_num = [col for col in CLOSE_FAILURE_RISK_NUMERIC if col in df.columns]
    failure_risk_cat = [col for col in CLOSE_FAILURE_RISK_CATEGORICAL if col in df.columns]
    non_gate_cats = [col for col in CATEGORICAL_FEATURES if col in df.columns and col not in set(GATE_CATEGORICAL + THEME_CATEGORICAL)]
    gate_cats = [col for col in CATEGORICAL_FEATURES if col in df.columns and col not in set(THEME_CATEGORICAL)]
    theme_cats = [col for col in CATEGORICAL_FEATURES if col in df.columns]
    kis_sidecar_num = [
        col
        for col in list(KIS_SIDECAR_DIAGNOSTIC_NUMERIC_FEATURES)
        + list(KIS_SIDECAR_MODEL_NUMERIC_FEATURES)
        + list(KIS_THEME_NEWS_NUMERIC_FEATURES)
        if col in df.columns
    ]
    kis_sidecar_cat = [
        col
        for col in list(KIS_SIDECAR_CATEGORICAL_FEATURES) + list(KIS_THEME_NEWS_CATEGORICAL_FEATURES)
        if col in df.columns
    ]
    kis_prefilter_num = [
        col
        for col in list(KIS_PREFILTER_NUMERIC_FEATURES) + list(KIS_THEME_NEWS_NUMERIC_FEATURES)
        if col in df.columns
    ]
    kis_prefilter_cat = [
        col
        for col in list(KIS_PREFILTER_CATEGORICAL_FEATURES) + list(KIS_THEME_NEWS_CATEGORICAL_FEATURES)
        if col in df.columns
    ]
    kis_all_num = [col for col in KIS_NUMERIC_FEATURES if col in df.columns]
    kis_all_cat = [col for col in KIS_CATEGORICAL_FEATURES if col in df.columns]
    return {
        "core_no_gate": (core, non_gate_cats),
        "flow_no_gate": (flow, non_gate_cats),
        "wide_no_theme": (all_num, gate_cats),
        "wide_theme": (all_num, theme_cats),
        "failure_risk_augmented": (
            list(dict.fromkeys(all_num + failure_risk_num)),
            list(dict.fromkeys(theme_cats + failure_risk_cat)),
        ),
        "failure_risk_numeric": (
            list(dict.fromkeys(all_num + failure_risk_num)),
            [],
        ),
        "kis_sidecar_only": (kis_sidecar_num, kis_sidecar_cat),
        "kis_prefilter_only": (kis_prefilter_num, kis_prefilter_cat),
        "kis_sidecar_augmented": (list(dict.fromkeys(flow + kis_sidecar_num)), list(dict.fromkeys(non_gate_cats + kis_sidecar_cat))),
        "kis_sidecar_failure_risk_numeric": (
            list(dict.fromkeys(flow + kis_sidecar_num + failure_risk_num)),
            [],
        ),
        "kis_sidecar_failure_risk_augmented": (
            list(dict.fromkeys(flow + kis_sidecar_num + failure_risk_num)),
            list(dict.fromkeys(non_gate_cats + kis_sidecar_cat + failure_risk_cat)),
        ),
        "kis_prefilter_augmented": (list(dict.fromkeys(flow + kis_prefilter_num)), list(dict.fromkeys(non_gate_cats + kis_prefilter_cat))),
        "kis_full_augmented": (list(dict.fromkeys(all_num + kis_all_num)), list(dict.fromkeys(theme_cats + kis_all_cat))),
        "kis_failure_risk_augmented": (
            list(dict.fromkeys(all_num + kis_all_num + failure_risk_num)),
            list(dict.fromkeys(theme_cats + kis_all_cat + failure_risk_cat)),
        ),
        "kis_failure_risk_numeric": (
            list(dict.fromkeys(all_num + kis_all_num + failure_risk_num)),
            [],
        ),
    }


def kis_feature_family(feature_name: str) -> str:
    name = str(feature_name or "")
    if name.startswith("kis_sidecar"):
        return "sidecar"
    if name.startswith("kis_prefilter"):
        return "prefilter"
    if name.startswith("kis_full"):
        return "any_kis"
    return ""


def kis_presence_mask(frame: pd.DataFrame, feature_name: str) -> pd.Series:
    false = pd.Series(False, index=frame.index)
    sidecar = pd.to_numeric(frame.get("kis_sidecar_present", pd.Series(0, index=frame.index)), errors="coerce").fillna(0).gt(0)
    prefilter = pd.to_numeric(frame.get("kis_prefilter_present", pd.Series(0, index=frame.index)), errors="coerce").fillna(0).gt(0)
    family = kis_feature_family(feature_name)
    if family == "sidecar":
        return sidecar
    if family == "prefilter":
        return prefilter
    if family == "any_kis":
        return sidecar | prefilter
    return false


def preprocessor(numeric: Sequence[str], categorical: Sequence[str], *, scale_numeric: bool) -> ColumnTransformer:
    num_steps: List[Tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scaler", StandardScaler()))
    return ColumnTransformer(
        [
            ("num", Pipeline(num_steps), list(numeric)),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                        ("onehot", _onehot_encoder()),
                    ]
                ),
                list(categorical),
            ),
        ],
        remainder="drop",
    )


def model_candidate(name: str) -> Any | None:
    if name == "logistic":
        return LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs", random_state=42)
    if name == "hist_gb":
        return HistGradientBoostingClassifier(max_iter=160, max_depth=3, learning_rate=0.05, l2_regularization=0.2, random_state=42)
    if name == "extra_trees":
        return ExtraTreesClassifier(n_estimators=260, max_depth=8, min_samples_leaf=5, class_weight="balanced", random_state=42, n_jobs=-1)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=260, max_depth=8, min_samples_leaf=5, class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    if name == "xgboost" and XGBClassifier is not None:
        return XGBClassifier(
            n_estimators=180,
            max_depth=3,
            learning_rate=0.045,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
    if name == "lightgbm" and LGBMClassifier is not None:
        return LGBMClassifier(
            n_estimators=220,
            max_depth=5,
            learning_rate=0.04,
            num_leaves=24,
            subsample=0.85,
            colsample_bytree=0.85,
            class_weight="balanced",
            random_state=42,
            verbose=-1,
            n_jobs=-1,
        )
    return None


def split_windows(df: pd.DataFrame, *, min_train_days: int, test_days: int, max_folds: int) -> List[Tuple[set[str], set[str]]]:
    days = sorted(df["trade_date"].dropna().astype(str).unique().tolist())
    if len(days) < min_train_days + 1:
        return []
    windows: List[Tuple[set[str], set[str]]] = []
    end = len(days)
    while end > min_train_days and len(windows) < max_folds:
        start = max(min_train_days, end - test_days)
        train_days = set(days[:start])
        test = set(days[start:end])
        if train_days and test:
            windows.append((train_days, test))
        end = start
    return list(reversed(windows))


def top_indices_by_run(frame: pd.DataFrame, score: pd.Series, topn: int, *, min_score: float | None = None) -> pd.Index:
    scored = frame.copy()
    scored["_score"] = pd.to_numeric(score.reindex(frame.index), errors="coerce")
    chunks: List[pd.Index] = []
    for _run_id, run_df in scored.groupby("run_id", dropna=False):
        if min_score is not None:
            run_df = run_df[run_df["_score"].ge(min_score)]
            if run_df.empty:
                continue
        top = run_df.sort_values("_score", ascending=False, na_position="last").head(topn)
        if not top.empty:
            chunks.append(top.index)
    if not chunks:
        return pd.Index([])
    return chunks[0].append(chunks[1:]) if len(chunks) > 1 else chunks[0]


def current_top_indices(frame: pd.DataFrame, topn: int, *, include_exception: bool) -> pd.Index:
    rank = pd.to_numeric(frame.get("priority_rank", pd.Series(index=frame.index, dtype=float)), errors="coerce")
    emitted = frame.get("row_role", pd.Series("", index=frame.index)).fillna("").astype(str).eq("emitted")
    exception = (
        frame.get("decision_bucket", pd.Series("", index=frame.index)).fillna("").astype(str).str.lower().eq("exception_leader")
        | frame.get("decision", pd.Series("", index=frame.index)).fillna("").astype(str).str.upper().eq("EXCEPTION_LEADER")
    )
    mask = emitted & rank.between(1, topn, inclusive="both")
    if include_exception:
        mask |= exception
    return frame.index[mask]


def metrics(frame: pd.DataFrame, idx: pd.Index, label: pd.Series) -> Dict[str, Any]:
    sub = frame.loc[idx]
    if sub.empty:
        return {"n": 0, "active_runs": 0, "active_days": 0}
    wins = label.loc[idx].astype(bool)
    out: Dict[str, Any] = {
        "n": int(len(sub)),
        "active_runs": int(sub["run_id"].nunique()) if "run_id" in sub.columns else 0,
        "active_days": int(sub["trade_date"].nunique()) if "trade_date" in sub.columns else 0,
        "label_win_pct": _pct(wins.mean()) if len(wins) else None,
        "bad_path_pct": _pct(sub.get("bad_path", pd.Series(False, index=sub.index)).fillna(False).mean()),
        "stop5_pct": _pct(sub.get("stop5_proxy", pd.Series(False, index=sub.index)).fillna(False).mean()),
        "buy_premium_pct": float(OPERATIONAL_BUY_PREMIUM_PCT),
        "win_metric_semantics": "target_touch_mfe_ge_5pct_after_buy_premium",
        "close_win_metric_semantics": "defensive_close_return_gt_0_after_buy_premium",
    }
    for horizon, col in [("1d", "return_1d_pct"), ("3d", "return_3d_pct"), ("5d", "return_5d_pct")]:
        ret = _adjusted_return_series(sub, col).dropna()
        out[f"close_win_{horizon}_pct"] = _pct(ret.gt(0).mean()) if len(ret) else None
        out[f"defense_close_win_{horizon}_pct"] = out[f"close_win_{horizon}_pct"]
        out[f"avg_{horizon}_pct"] = _round(ret.mean()) if len(ret) else None
        out[f"median_{horizon}_pct"] = _round(ret.median()) if len(ret) else None
        out[f"min_{horizon}_pct"] = _round(ret.min()) if len(ret) else None
        out[f"max_{horizon}_pct"] = _round(ret.max()) if len(ret) else None
        mfe_horizon = _adjusted_return_series(sub, f"max_high_return_{horizon}_pct").dropna()
        out[f"win_{horizon}_pct"] = _pct(mfe_horizon.ge(PRIMARY_TARGET_RETURN_PCT).mean()) if len(mfe_horizon) else None
        out[f"hit5_{horizon}_pct"] = out[f"win_{horizon}_pct"]
        out[f"hit10_{horizon}_pct"] = _pct(mfe_horizon.ge(EXTENDED_TARGET_RETURN_PCT).mean()) if len(mfe_horizon) else None
        scan_ret = pd.to_numeric(sub.get(col, pd.Series(index=sub.index, dtype=float)), errors="coerce").dropna()
        out[f"scan_reference_avg_{horizon}_pct"] = _round(scan_ret.mean()) if len(scan_ret) else None
        out[f"scan_reference_min_{horizon}_pct"] = _round(scan_ret.min()) if len(scan_ret) else None
        out[f"scan_reference_max_{horizon}_pct"] = _round(scan_ret.max()) if len(scan_ret) else None
    for horizon in ("1d", "3d", "5d"):
        target = _operational_path_column(sub, f"target_before_stop_{horizon}")
        stop = _operational_path_column(sub, f"stop_before_target_{horizon}")
        target_valid = target.notna()
        if target_valid.any():
            mfe_horizon = _adjusted_return_series(sub.loc[target_valid], f"max_high_return_{horizon}_pct")
            mae_horizon = _adjusted_return_series(sub.loc[target_valid], f"min_low_return_{horizon}_pct")
            adjusted_target = _bool_series(target.loc[target_valid]) & mfe_horizon.ge(PRIMARY_TARGET_RETURN_PCT).fillna(False)
            adjusted_stop = _bool_series(stop.loc[target_valid]) | mae_horizon.le(-PRIMARY_TARGET_RETURN_PCT).fillna(False)
            out[f"target_before_stop_{horizon}_pct"] = _pct(adjusted_target.mean())
            out[f"stop_before_target_{horizon}_pct"] = _pct(adjusted_stop.mean())
    mfe = _adjusted_return_series(sub, "max_high_return_5d_pct").dropna()
    mae = _adjusted_return_series(sub, "min_low_return_5d_pct").dropna()
    if len(mfe):
        out["hit5_5d_pct"] = _pct(mfe.ge(PRIMARY_TARGET_RETURN_PCT).mean())
        out["hit10_5d_pct"] = _pct(mfe.ge(EXTENDED_TARGET_RETURN_PCT).mean())
        out["win_5d_pct"] = out["hit5_5d_pct"]
    if len(mfe) and len(mae):
        aligned = pd.DataFrame(
            {
                "max_high_return_5d_pct": _adjusted_return_series(sub, "max_high_return_5d_pct"),
                "min_low_return_5d_pct": _adjusted_return_series(sub, "min_low_return_5d_pct"),
            },
            index=sub.index,
        ).dropna()
        if not aligned.empty:
            out["hit5_guard_5d_pct"] = _pct((aligned["max_high_return_5d_pct"].ge(5.0) & aligned["min_low_return_5d_pct"].gt(-5.0)).mean())
            out["hit5_dd10_5d_pct"] = _pct(
                (
                    aligned["max_high_return_5d_pct"].ge(5.0)
                    & aligned["min_low_return_5d_pct"].ge(MIN_PROMOTION_MIN_LOW_5D_PCT)
                ).mean()
            )
            out["hit10_guard_5d_pct"] = _pct((aligned["max_high_return_5d_pct"].ge(10.0) & aligned["min_low_return_5d_pct"].gt(-5.0)).mean())
    out["avg_max_high_5d_pct"] = _round(mfe.mean()) if len(mfe) else None
    out["min_max_high_5d_pct"] = _round(mfe.min()) if len(mfe) else None
    out["max_max_high_5d_pct"] = _round(mfe.max()) if len(mfe) else None
    out["avg_min_low_5d_pct"] = _round(mae.mean()) if len(mae) else None
    out["min_min_low_5d_pct"] = _round(mae.min()) if len(mae) else None
    out["max_min_low_5d_pct"] = _round(mae.max()) if len(mae) else None
    raw_mfe = pd.to_numeric(sub.get("max_high_return_5d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce").dropna()
    raw_mae = pd.to_numeric(sub.get("min_low_return_5d_pct", pd.Series(index=sub.index, dtype=float)), errors="coerce").dropna()
    out["scan_reference_avg_max_high_5d_pct"] = _round(raw_mfe.mean()) if len(raw_mfe) else None
    out["scan_reference_avg_min_low_5d_pct"] = _round(raw_mae.mean()) if len(raw_mae) else None
    return out


def quality_score(result_metrics: Dict[str, Any], *, topn: int, label_name: str = "") -> float:
    n = float(result_metrics.get("n") or 0)
    runs = float(result_metrics.get("active_runs") or 0)
    days = float(result_metrics.get("active_days") or 0)
    avg1 = float(result_metrics.get("avg_1d_pct") or -20.0)
    avg3 = float(result_metrics.get("avg_3d_pct") or -20.0)
    avg5 = float(result_metrics.get("avg_5d_pct") or -20.0)
    close_win1 = float(result_metrics.get("close_win_1d_pct") or 0.0)
    close_win3 = float(result_metrics.get("close_win_3d_pct") or 0.0)
    close_win5 = float(result_metrics.get("close_win_5d_pct") or 0.0)
    win1 = float(result_metrics.get("win_1d_pct") or 0.0)
    win3 = float(result_metrics.get("win_3d_pct") or 0.0)
    win5 = float(result_metrics.get("win_5d_pct") or 0.0)
    min1 = float(result_metrics.get("min_1d_pct") or -50.0)
    min3 = float(result_metrics.get("min_3d_pct") or -50.0)
    min5 = float(result_metrics.get("min_5d_pct") or -50.0)
    bad = float(result_metrics.get("bad_path_pct") if result_metrics.get("bad_path_pct") is not None else 100.0)
    stop = float(result_metrics.get("stop5_pct") if result_metrics.get("stop5_pct") is not None else 100.0)
    target_first = float(result_metrics.get("target_before_stop_5d_pct") or 0.0)
    hit5 = float(result_metrics.get("hit5_5d_pct") or 0.0)
    hit10 = float(result_metrics.get("hit10_5d_pct") or 0.0)
    hit5_guard = float(result_metrics.get("hit5_guard_5d_pct") or 0.0)
    hit5_dd10 = float(result_metrics.get("hit5_dd10_5d_pct") or 0.0)
    hit10_guard = float(result_metrics.get("hit10_guard_5d_pct") or 0.0)
    avg_mfe = float(result_metrics.get("avg_max_high_5d_pct") or -20.0)
    min_mfe = float(result_metrics.get("min_max_high_5d_pct") or -20.0)
    min_low = float(result_metrics.get("min_min_low_5d_pct") or 0.0)
    sample_penalty = 0.0
    if runs < MIN_PROMOTION_RUNS:
        sample_penalty += (MIN_PROMOTION_RUNS - runs) * 18.0
    if days < MIN_PROMOTION_DAYS:
        sample_penalty += (MIN_PROMOTION_DAYS - days) * 24.0
    if n < max(MIN_PROMOTION_ROWS, topn * 8):
        sample_penalty += (max(MIN_PROMOTION_ROWS, topn * 8) - n) * 12.0
    tail_penalty = max(0.0, -5.0 - min1) * 2.5 + max(0.0, -8.0 - min3) * 1.5 + max(0.0, -12.0 - min5)
    if label_name == "touch5_dd10_5d":
        touch_tail_penalty = max(0.0, MIN_PROMOTION_MIN_LOW_5D_PCT - min_low) * 10.0
        return (
            hit5_dd10 * 2.2
            + hit5 * 0.35
            + hit10 * 0.55
            + avg_mfe * 22.0
            + min_mfe * 9.0
            + close_win5 * 0.10
            + avg5 * 1.0
            - touch_tail_penalty
            - sample_penalty
        )
    return (
        win1 * 0.7
        + win3 * 1.0
        + win5 * 1.8
        + close_win1 * 0.15
        + close_win3 * 0.20
        + close_win5 * 0.25
        + avg1 * 3.0
        + avg3 * 5.0
        + avg5 * 7.0
        + target_first * 0.25
        + hit5 * 0.60
        + hit10 * 1.10
        + hit5_guard * 0.85
        + hit10_guard * 1.35
        + avg_mfe * 20.0
        + min_mfe * 8.0
        - bad * 0.8
        - stop * 0.6
        - tail_penalty
        - sample_penalty
    )


def usable_features(frame: pd.DataFrame, numeric: Sequence[str], categorical: Sequence[str]) -> Tuple[List[str], List[str]]:
    usable_numeric = []
    for col in numeric:
        if col not in frame.columns:
            continue
        values = pd.to_numeric(frame[col], errors="coerce")
        if values.notna().any():
            usable_numeric.append(col)
    usable_categorical = []
    for col in categorical:
        if col not in frame.columns:
            continue
        values = frame[col].fillna("UNKNOWN").astype(str)
        if values.nunique(dropna=False) > 1:
            usable_categorical.append(col)
    return usable_numeric, usable_categorical


def run_candidate(
    work: pd.DataFrame,
    *,
    market: str,
    label_spec: LabelSpec,
    feature_name: str,
    numeric: List[str],
    categorical: List[str],
    model_name: str,
    topn: int,
    prob_threshold: float | None,
    min_train_rows: int,
    min_test_rows: int,
    min_train_days: int,
    test_days: int,
    max_folds: int,
    min_kis_rows: int = 0,
    min_kis_days: int = MIN_KIS_TRAIN_DAYS,
) -> Dict[str, Any]:
    label, valid = label_series(work, label_spec)
    scoped = work.loc[valid & work["market"].eq(market)].copy()
    kis_family = kis_feature_family(feature_name)
    kis_scope_summary: Dict[str, Any] = {}
    if kis_family:
        required_rows = max(int(min_kis_rows or 0), int(min_train_rows) + int(min_test_rows))
        kis_mask = kis_presence_mask(scoped, feature_name)
        kis_scope_summary = {
            "kis_feature_family": kis_family,
            "kis_valid_label_rows": int(kis_mask.sum()),
            "kis_valid_label_days": int(scoped.loc[kis_mask, "trade_date"].nunique()) if "trade_date" in scoped.columns else 0,
            "min_kis_rows": required_rows,
            "min_kis_days": int(min_kis_days),
        }
        scoped = scoped.loc[kis_mask].copy()
    y = label.loc[scoped.index].astype(int)
    base = {
        "market": market,
        "label": label_spec.name,
        "label_description": label_spec.description,
        "feature_set": feature_name,
        "model": model_name,
        "topn": topn,
        "prob_threshold": _round(prob_threshold) if prob_threshold is not None else None,
        "selection_rule": f"top{topn}" if prob_threshold is None else f"top{topn}_p{prob_threshold:.2f}",
        "rows": int(len(scoped)),
        "positive_rate_pct": _pct(y.mean()) if len(y) else None,
        "status": "skipped",
        **kis_scope_summary,
    }
    if kis_family:
        if int(base.get("kis_valid_label_rows") or 0) < int(base.get("min_kis_rows") or 0):
            return {**base, "skip_reason": "insufficient_kis_feature_rows"}
        if int(base.get("kis_valid_label_days") or 0) < int(base.get("min_kis_days") or 0):
            return {**base, "skip_reason": "insufficient_kis_feature_days"}
    if len(scoped) < min_train_rows + min_test_rows:
        return {**base, "skip_reason": "insufficient_rows"}
    if y.nunique() < 2:
        return {**base, "skip_reason": "single_class"}
    windows = split_windows(scoped, min_train_days=min_train_days, test_days=test_days, max_folds=max_folds)
    if not windows:
        return {**base, "skip_reason": "insufficient_time_windows"}
    estimator = model_candidate(model_name)
    if estimator is None:
        return {**base, "skip_reason": "model_unavailable"}
    numeric, categorical = usable_features(scoped, numeric, categorical)
    features = [col for col in numeric + categorical if col in scoped.columns]
    if not features:
        return {**base, "skip_reason": "no_features"}
    selected_indices: List[pd.Index] = []
    fold_metrics = []
    aucs = []
    briers = []
    for train_days, test_day_set in windows:
        train_idx = scoped.index[scoped["trade_date"].isin(train_days)]
        test_idx = scoped.index[scoped["trade_date"].isin(test_day_set)]
        if len(train_idx) < min_train_rows or len(test_idx) < min_test_rows:
            continue
        if y.loc[train_idx].nunique() < 2 or y.loc[test_idx].nunique() < 2:
            continue
        scale = model_name == "logistic"
        pipe = Pipeline([("pre", preprocessor(numeric, categorical, scale_numeric=scale)), ("model", estimator)])
        x_train = scoped.loc[train_idx, features].copy()
        x_test = scoped.loc[test_idx, features].copy()
        for col in categorical:
            if col in x_train.columns:
                x_train[col] = x_train[col].fillna("UNKNOWN").astype(str)
                x_test[col] = x_test[col].fillna("UNKNOWN").astype(str)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pipe.fit(x_train, y.loc[train_idx])
                prob = pd.Series(pipe.predict_proba(x_test)[:, 1], index=test_idx)
        except Exception as exc:
            return {**base, "skip_reason": f"{type(exc).__name__}: {exc}"}
        idx = top_indices_by_run(scoped.loc[test_idx], prob, topn, min_score=prob_threshold)
        if len(idx):
            selected_indices.append(idx)
        fold_m = metrics(scoped, idx, label)
        fold_m["test_days"] = sorted(test_day_set)
        fold_metrics.append(fold_m)
        try:
            aucs.append(float(roc_auc_score(y.loc[test_idx], prob)))
            briers.append(float(brier_score_loss(y.loc[test_idx], prob)))
        except Exception:
            pass
    if not selected_indices:
        return {**base, "skip_reason": "no_selected_indices"}
    idx_all = selected_indices[0].append(selected_indices[1:]) if len(selected_indices) > 1 else selected_indices[0]
    merged = metrics(scoped, idx_all, label)
    return {
        **base,
        "status": "ok",
        "folds": int(len(fold_metrics)),
        "auc_mean": _round(np.mean(aucs)) if aucs else None,
        "brier_mean": _round(np.mean(briers)) if briers else None,
        "metrics": merged,
        "fold_metrics": fold_metrics,
        "quality_score": _round(quality_score(merged, topn=topn, label_name=label_spec.name), 6),
        "feature_columns": {"numeric": numeric, "categorical": categorical},
    }


def baseline_results(work: pd.DataFrame, *, market: str, label_spec: LabelSpec, topn: int, holdout_days: set[str]) -> List[Dict[str, Any]]:
    label, valid = label_series(work, label_spec)
    scoped = work.loc[valid & work["market"].eq(market) & work["trade_date"].isin(holdout_days)].copy()
    if scoped.empty:
        return []
    out = []
    for name, idx in [
        (f"current_top{topn}", current_top_indices(scoped, topn, include_exception=False)),
        (f"current_top{topn}_exception", current_top_indices(scoped, topn, include_exception=True)),
        (f"decision_score_top{topn}", top_indices_by_run(scoped, scoped.get("decision_score", pd.Series(index=scoped.index)), topn)),
        (f"ml_prob_top{topn}", top_indices_by_run(scoped, scoped.get("ml_prob", pd.Series(index=scoped.index)), topn)),
    ]:
        out.append({"baseline": name, "market": market, "label": label_spec.name, "topn": topn, "metrics": metrics(scoped, idx, label)})
    return out


def parse_thresholds(raw: str) -> List[float | None]:
    values: List[float | None] = [None]
    for item in str(raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        values.append(float(item))
    return values


def apply_grid_preset(args: argparse.Namespace) -> argparse.Namespace:
    preset = str(getattr(args, "grid_preset", "custom") or "custom")
    if preset == "custom":
        return args
    if preset == "kis_operational_fast":
        args.labels = "touch5_dd10_5d,touch5_5d,touch5_guard_5d,touch10_5d,touch10_guard_5d,target_first_5d,target_first_sustain_5d,target_hit_no_stop_5d"
        args.feature_sets = "kis_sidecar_only,kis_sidecar_augmented,kis_sidecar_failure_risk_numeric,kis_full_augmented,kis_failure_risk_numeric"
        args.models = "random_forest,hist_gb,lightgbm"
        args.topns = "1,3"
        args.prob_thresholds = "0.60,0.65"
        args.max_folds = min(int(args.max_folds), 3)
        args.test_days = max(1, min(int(args.test_days), 2))
        return args
    if preset == "kis_operational_full":
        args.labels = "touch5_dd10_5d,touch5_5d,touch5_guard_5d,touch10_5d,touch10_guard_5d,target_first_5d,target_first_sustain_5d,target_hit_no_stop_5d"
        args.feature_sets = "kis_sidecar_only,kis_sidecar_augmented,kis_sidecar_failure_risk_numeric,kis_sidecar_failure_risk_augmented,kis_full_augmented,kis_failure_risk_numeric,kis_failure_risk_augmented"
        args.models = "random_forest,extra_trees,hist_gb,lightgbm"
        args.topns = "1,3,5"
        args.prob_thresholds = "0.55,0.60,0.65"
        return args
    raise ValueError(f"unknown grid preset: {preset}")


def candidate_jobs(
    *,
    data: pd.DataFrame,
    args: argparse.Namespace,
    feature_map: Mapping[str, Tuple[List[str], List[str]]],
    markets: Sequence[str],
    selected_specs: Sequence[LabelSpec],
    model_names: Sequence[str],
    topns: Sequence[int],
    prob_thresholds: Sequence[float | None],
) -> List[CandidateJob]:
    feature_filters = {
        item.strip()
        for item in str(args.feature_sets).split(",")
        if item.strip()
    }
    jobs: List[CandidateJob] = []
    for market in markets:
        market_df = data[data["market"].eq(market)]
        if market_df.empty:
            continue
        for spec in selected_specs:
            for feature_name, (numeric, categorical) in feature_map.items():
                if args.no_theme and "theme" in feature_name:
                    continue
                if feature_filters and feature_name not in feature_filters:
                    continue
                for model_name in model_names:
                    for topn in topns:
                        for prob_threshold in prob_thresholds:
                            jobs.append(
                                CandidateJob(
                                    market=market,
                                    label_spec=spec,
                                    feature_name=feature_name,
                                    numeric=tuple(numeric),
                                    categorical=tuple(categorical),
                                    model_name=model_name,
                                    topn=int(topn),
                                    prob_threshold=prob_threshold,
                                )
                            )
    return jobs


def _run_candidate_job(work: pd.DataFrame, job: CandidateJob, args: argparse.Namespace) -> Dict[str, Any]:
    return run_candidate(
        work,
        market=job.market,
        label_spec=job.label_spec,
        feature_name=job.feature_name,
        numeric=list(job.numeric),
        categorical=list(job.categorical),
        model_name=job.model_name,
        topn=job.topn,
        prob_threshold=job.prob_threshold,
        min_train_rows=int(args.min_train_rows),
        min_test_rows=int(args.min_test_rows),
        min_train_days=int(args.min_train_days),
        test_days=int(args.test_days),
        max_folds=int(args.max_folds),
        min_kis_rows=int(args.min_kis_rows),
        min_kis_days=int(args.min_kis_days),
    )


def evaluate_candidate_jobs(
    work: pd.DataFrame,
    jobs: Sequence[CandidateJob],
    args: argparse.Namespace,
    *,
    progress: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    workers = max(1, int(getattr(args, "eval_workers", 1) or 1))
    progress_every = max(1, int(getattr(args, "progress_every", 25) or 25))
    started = perf_counter()
    results: List[Dict[str, Any]] = []
    total = len(jobs)
    _log(progress, f"[INFO] evaluating {total} challenger combinations with eval_workers={workers}")
    if workers == 1 or total <= 1:
        for idx, job in enumerate(jobs, start=1):
            results.append(_run_candidate_job(work, job, args))
            if idx % progress_every == 0 or idx == total:
                _log(progress, f"[INFO] evaluated {idx}/{total} challenger combinations")
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {executor.submit(_run_candidate_job, work, job, args): job for job in jobs}
            for idx, future in enumerate(as_completed(future_map), start=1):
                try:
                    results.append(future.result())
                except Exception as exc:
                    job = future_map[future]
                    results.append(
                        {
                            "market": job.market,
                            "label": job.label_spec.name,
                            "feature_set": job.feature_name,
                            "model": job.model_name,
                            "topn": job.topn,
                            "prob_threshold": _round(job.prob_threshold) if job.prob_threshold is not None else None,
                            "selection_rule": f"top{job.topn}" if job.prob_threshold is None else f"top{job.topn}_p{job.prob_threshold:.2f}",
                            "status": "skipped",
                            "skip_reason": f"{type(exc).__name__}: {exc}",
                        }
                    )
                if idx % progress_every == 0 or idx == total:
                    _log(progress, f"[INFO] evaluated {idx}/{total} challenger combinations")
    elapsed = perf_counter() - started
    return results, {
        "planned_combinations": int(total),
        "evaluated_combinations": int(len(results)),
        "eval_workers": int(workers),
        "elapsed_sec": _round(elapsed, 3),
        "combinations_per_sec": _round(len(results) / elapsed, 3) if elapsed > 0 else None,
    }


def candidate_risk_gate(candidate: Dict[str, Any] | None) -> Dict[str, Any]:
    if not candidate:
        return {"pass": False, "risk_score": None, "blocking_reasons": ["no_valid_challenger"]}
    m = candidate.get("metrics") or {}
    folds = [item for item in candidate.get("fold_metrics") or [] if isinstance(item, dict)]
    label_name = str(candidate.get("label") or "")
    is_touch_label = label_name.startswith("touch") or label_name.startswith("target_")
    is_touch10 = label_name.startswith("touch10")
    is_touch5_dd10 = label_name == "touch5_dd10_5d"
    reasons: List[str] = []

    stop5 = _metric_float(m, "stop5_pct", 100.0)
    bad_path = _metric_float(m, "bad_path_pct", stop5 if "stop5_pct" in m else 0.0)
    stop_before_target_5d = _metric_float(m, "stop_before_target_5d_pct", stop5)
    target_before_stop_5d = _metric_float(m, "target_before_stop_5d_pct", 100.0)
    min_1d = _metric_float(m, "min_1d_pct", -999.0)
    min_low_5d = _metric_float(m, "min_min_low_5d_pct", 0.0)
    max_fold_stop5 = max((_metric_float(item, "stop5_pct", stop5) for item in folds), default=stop5)
    max_fold_bad_path = max((_metric_float(item, "bad_path_pct", bad_path) for item in folds), default=bad_path)
    fold_target_values = [
        _metric_float(item, "target_before_stop_5d_pct", target_before_stop_5d)
        for item in folds
        if "target_before_stop_5d_pct" in item
    ]
    min_fold_target_before_stop = min(
        fold_target_values,
        default=target_before_stop_5d,
    )
    min_fold_low_5d = min(
        (_metric_float(item, "min_min_low_5d_pct", min_low_5d) for item in folds if "min_min_low_5d_pct" in item),
        default=min_low_5d,
    )

    if not is_touch5_dd10:
        if stop5 > MAX_PROMOTION_STOP5_PCT:
            _append_unique(reasons, "stop5_above_35")
        if bad_path > MAX_PROMOTION_BAD_PATH_PCT:
            _append_unique(reasons, "bad_path_above_45")
        if stop_before_target_5d > MAX_PROMOTION_STOP_BEFORE_TARGET_5D_PCT:
            _append_unique(reasons, "stop_before_target_5d_above_35")
        if "target_before_stop_5d_pct" in m and target_before_stop_5d < MIN_PROMOTION_TARGET_BEFORE_STOP_5D_PCT:
            _append_unique(reasons, "target_before_stop_5d_lt_50")
        if min_1d < -5.0:
            _append_unique(reasons, "min_1d_below_stop")
    if "min_min_low_5d_pct" in m and min_low_5d < MIN_PROMOTION_MIN_LOW_5D_PCT:
        _append_unique(reasons, "min_low_5d_below_10")
    if is_touch5_dd10:
        if folds and min_fold_low_5d < MIN_PROMOTION_MIN_LOW_5D_PCT:
            _append_unique(reasons, "fold_min_low_5d_below_10")
    else:
        if max_fold_stop5 > MAX_PROMOTION_FOLD_STOP5_PCT:
            _append_unique(reasons, "fold_stop5_above_50")
        if max_fold_bad_path > 60.0:
            _append_unique(reasons, "fold_bad_path_above_60")
        if fold_target_values and min_fold_target_before_stop < MIN_PROMOTION_FOLD_TARGET_BEFORE_STOP_5D_PCT:
            _append_unique(reasons, "fold_target_before_stop_5d_lt_35")

    guard_shortfall = 0.0
    guard_ratio_shortfall = 0.0
    guard_components: Dict[str, Any] = {}
    if is_touch_label:
        raw_key = "hit10_5d_pct" if is_touch10 else "hit5_5d_pct"
        if label_name == "touch5_dd10_5d":
            guard_key = "hit5_dd10_5d_pct"
        else:
            guard_key = "hit10_guard_5d_pct" if is_touch10 else "hit5_guard_5d_pct"
        min_guard = MIN_PROMOTION_TOUCH10_GUARD_PCT if is_touch10 else MIN_PROMOTION_TOUCH5_GUARD_PCT
        raw_value = _metric_float(m, raw_key, 0.0)
        guard_value = _metric_float(m, guard_key, raw_value if guard_key not in m else 0.0)
        guard_components = {"raw_key": raw_key, "raw_pct": _round(raw_value), "guard_key": guard_key, "guard_pct": _round(guard_value)}
        if guard_key in m:
            if guard_value < min_guard:
                _append_unique(reasons, f"{guard_key}_lt_{int(min_guard)}")
                guard_shortfall = max(guard_shortfall, min_guard - guard_value)
            if raw_value > 0:
                ratio = guard_value / raw_value
                guard_components["guard_raw_ratio"] = _round(ratio)
                if ratio < MIN_PROMOTION_GUARD_RAW_RATIO:
                    _append_unique(reasons, f"{guard_key}_raw_ratio_lt_70")
                    guard_ratio_shortfall = max(guard_ratio_shortfall, (MIN_PROMOTION_GUARD_RAW_RATIO - ratio) * 100.0)

    if is_touch5_dd10:
        risk_score = (
            max(0.0, MIN_PROMOTION_MIN_LOW_5D_PCT - min_low_5d) * 8.0
            + max(0.0, MIN_PROMOTION_MIN_LOW_5D_PCT - min_fold_low_5d) * 8.0
            + guard_shortfall * 1.4
            + guard_ratio_shortfall * 1.4
        )
    else:
        risk_score = (
            stop5 * 1.4
            + bad_path * 0.8
            + stop_before_target_5d * 1.2
            + max_fold_stop5 * 1.7
            + max_fold_bad_path * 0.8
            + max(0.0, MIN_PROMOTION_TARGET_BEFORE_STOP_5D_PCT - target_before_stop_5d) * 1.1
            + max(0.0, MIN_PROMOTION_FOLD_TARGET_BEFORE_STOP_5D_PCT - min_fold_target_before_stop) * 1.2
            + max(0.0, -5.0 - min_1d) * 8.0
            + max(0.0, MIN_PROMOTION_MIN_LOW_5D_PCT - min_low_5d) * 4.0
            + guard_shortfall * 1.1
            + guard_ratio_shortfall * 1.4
        )
    return {
        "pass": not reasons,
        "risk_score": _round(risk_score),
        "blocking_reasons": reasons,
        "components": {
            "stop5_pct": _round(stop5),
            "bad_path_pct": _round(bad_path),
            "stop_before_target_5d_pct": _round(stop_before_target_5d),
            "target_before_stop_5d_pct": _round(target_before_stop_5d),
            "min_1d_pct": _round(min_1d),
            "min_min_low_5d_pct": _round(min_low_5d),
            "max_fold_stop5_pct": _round(max_fold_stop5),
            "max_fold_bad_path_pct": _round(max_fold_bad_path),
            "min_fold_min_low_5d_pct": _round(min_fold_low_5d),
            "min_fold_target_before_stop_5d_pct": _round(min_fold_target_before_stop),
            **guard_components,
        },
    }


def candidate_blocking_reasons(candidate: Dict[str, Any] | None) -> List[str]:
    if not candidate:
        return ["no_valid_challenger"]
    m = candidate.get("metrics") or {}
    reasons = []
    topn = int(candidate.get("topn") or 1)
    if int(m.get("active_runs") or 0) < MIN_PROMOTION_RUNS:
        reasons.append("active_runs_lt_12")
    if int(m.get("active_days") or 0) < MIN_PROMOTION_DAYS:
        reasons.append("active_days_lt_6")
    if str(candidate.get("feature_set") or "").startswith("kis_") and int(m.get("active_days") or 0) < MIN_KIS_TRAIN_DAYS:
        reasons.append(f"kis_active_days_lt_{MIN_KIS_TRAIN_DAYS}")
    if int(m.get("n") or 0) < max(MIN_PROMOTION_ROWS, topn * 8):
        reasons.append("sample_too_small")
    label_name = str(candidate.get("label") or "")
    is_touch_label = label_name.startswith("touch") or label_name.startswith("target_")
    is_touch10 = label_name.startswith("touch10")
    is_touch5_dd10 = label_name == "touch5_dd10_5d"
    if is_touch_label:
        min_label_win = 45.0 if is_touch10 else 65.0
        if _metric_float(m, "label_win_pct", 0.0) < min_label_win:
            reasons.append(f"label_win_lt_{int(min_label_win)}")
        if is_touch5_dd10:
            if _metric_float(m, "hit5_dd10_5d_pct", 0.0) < MIN_PROMOTION_TOUCH5_GUARD_PCT:
                reasons.append(f"hit5_dd10_5d_lt_{int(MIN_PROMOTION_TOUCH5_GUARD_PCT)}")
        elif _metric_float(m, "hit5_5d_pct", 0.0) < 65.0:
            reasons.append("hit5_5d_lt_65")
        if is_touch10 and _metric_float(m, "hit10_5d_pct", 0.0) < 35.0:
            reasons.append("hit10_5d_lt_35")
        if _metric_float(m, "avg_max_high_5d_pct", -999.0) < 5.0:
            reasons.append("avg_mfe_5d_lt_5")
        if m.get("min_max_high_5d_pct") is not None and _metric_float(m, "min_max_high_5d_pct", -999.0) < 1.5:
            reasons.append("min_mfe_5d_lt_1p5")
    else:
        if _metric_float(m, "win_3d_pct", 0.0) < 70.0:
            reasons.append("win_3d_lt_70")
        if _metric_float(m, "win_5d_pct", 0.0) < 70.0:
            reasons.append("win_5d_lt_70")
        if _metric_float(m, "avg_3d_pct", -999.0) <= 0.0:
            reasons.append("avg_3d_not_positive")
        if _metric_float(m, "avg_5d_pct", -999.0) <= 0.0:
            reasons.append("avg_5d_not_positive")
        reasons.append("label_not_target_touch_objective")
    if not is_touch5_dd10 and _metric_float(m, "min_1d_pct", -999.0) < -5.0:
        reasons.append("min_1d_below_stop")
    if m.get("min_5d_pct") is not None and _metric_float(m, "min_5d_pct", -999.0) < -12.0:
        reasons.append("min_5d_tail_below_12")
    risk_gate = candidate_risk_gate(candidate)
    for reason in risk_gate.get("blocking_reasons") or []:
        _append_unique(reasons, str(reason))
    if str(candidate.get("feature_set") or "").lower().startswith("kis"):
        kis_gate = evaluate_kis_model_gate(
            identity={
                "market": candidate.get("market"),
                "label": candidate.get("label"),
                "feature_set": candidate.get("feature_set"),
                "model": candidate.get("model"),
                "topn": candidate.get("topn"),
                "selection_rule": candidate.get("selection_rule"),
            },
            metrics=m,
            market=str(candidate.get("market") or ""),
        )
        for reason in kis_gate.get("production_blocking_reasons") or []:
            _append_unique(reasons, str(reason))
    return reasons


def candidate_verdict(candidate: Dict[str, Any] | None) -> Dict[str, Any]:
    reasons = candidate_blocking_reasons(candidate)
    risk_gate = candidate_risk_gate(candidate)
    out = {"promotable": not reasons, "blocking_reasons": reasons, "risk_gate": risk_gate}
    if candidate and str(candidate.get("feature_set") or "").lower().startswith("kis"):
        out["kis_model_gate"] = evaluate_kis_model_gate(
            identity={
                "market": candidate.get("market"),
                "label": candidate.get("label"),
                "feature_set": candidate.get("feature_set"),
                "model": candidate.get("model"),
                "topn": candidate.get("topn"),
                "selection_rule": candidate.get("selection_rule"),
            },
            metrics=candidate.get("metrics") or {},
            market=str(candidate.get("market") or ""),
        )
    return out


def risk_first_sort_key(candidate: Dict[str, Any]) -> Tuple[Any, ...]:
    promotion = candidate.get("promotion_candidate") or candidate_verdict(candidate)
    risk_gate = candidate.get("risk_gate") or promotion.get("risk_gate") or candidate_risk_gate(candidate)
    m = candidate.get("metrics") or {}
    return (
        bool(promotion.get("promotable")),
        bool(risk_gate.get("pass")),
        -float(risk_gate.get("risk_score") if risk_gate.get("risk_score") is not None else 1e9),
        int(m.get("active_days") or 0),
        int(m.get("active_runs") or 0),
        int(m.get("n") or 0),
        float(candidate.get("quality_score") or -1e9),
    )


def rank_candidate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = []
    for row in results:
        row["risk_gate"] = candidate_risk_gate(row)
        row["promotion_candidate"] = candidate_verdict(row)
        if str(row.get("feature_set") or "").lower().startswith("kis"):
            row["kis_model_gate"] = row["promotion_candidate"].get("kis_model_gate")
        ranked.append(row)
    return sorted(ranked, key=risk_first_sort_key, reverse=True)


def promotion_verdict(best: Dict[str, Any] | None, baselines: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not best:
        return {"promotable": False, "reason": "no_valid_challenger"}
    reasons = candidate_blocking_reasons(best)
    baseline_rows = []
    for row in baselines:
        bm = row.get("metrics") or {}
        if int(bm.get("n") or 0) <= 0:
            continue
        baseline_rows.append(
            {
                "baseline": row.get("baseline"),
                "topn": row.get("topn"),
                "win_3d_pct": bm.get("win_3d_pct"),
                "win_5d_pct": bm.get("win_5d_pct"),
                "avg_3d_pct": bm.get("avg_3d_pct"),
                "avg_5d_pct": bm.get("avg_5d_pct"),
                "min_5d_pct": bm.get("min_5d_pct"),
            }
        )
    return {
        **candidate_verdict(best),
        "blocking_reasons": reasons,
        "baseline_rows_considered": baseline_rows,
    }


def _series_present_pct(frame: pd.DataFrame, col: str) -> float:
    if frame.empty or col not in frame.columns:
        return 0.0
    values = frame[col]
    if col in KIS_CATEGORICAL_FEATURES:
        present = values.fillna("").astype(str).str.strip().ne("") & ~values.fillna("").astype(str).str.upper().eq("UNKNOWN")
    else:
        numeric = pd.to_numeric(values, errors="coerce")
        diagnostic_presence = (
            col.endswith("_present")
            or col.endswith("_ready")
            or "_coverage_" in col
            or col.endswith("_ok")
            or col.endswith("_valid")
            or col.endswith("_triggered")
            or col.endswith("_source_count")
            or col.endswith("_warning_count")
            or col.endswith("_rejected")
        )
        present = numeric.gt(0) if diagnostic_presence else numeric.notna()
    return round(float(present.mean() * 100.0), 3) if len(present) else 0.0


def _kis_family_scope(frame: pd.DataFrame, family: str) -> pd.Series:
    if family == "sidecar":
        return kis_presence_mask(frame, "kis_sidecar_only")
    if family == "prefilter":
        return kis_presence_mask(frame, "kis_prefilter_only")
    if family == "any_kis":
        return kis_presence_mask(frame, "kis_full_augmented")
    if family == "theme_news":
        backed = pd.to_numeric(frame.get("kis_theme_news_kis_backed", pd.Series(0, index=frame.index)), errors="coerce").fillna(0).gt(0)
        score = pd.to_numeric(frame.get("kis_theme_news_evidence_score", pd.Series(0, index=frame.index)), errors="coerce").fillna(0).gt(0)
        return backed & score
    return pd.Series(False, index=frame.index)


def kis_feature_readiness(
    data: pd.DataFrame,
    *,
    min_train_rows: int,
    min_test_rows: int,
    min_kis_rows: int,
    min_kis_days: int,
) -> Dict[str, Any]:
    required_rows = max(int(min_kis_rows or 0), int(min_train_rows) + int(min_test_rows))
    required_days = int(min_kis_days)
    if data.empty:
        return {
            "status": "blocked",
            "reason": "no_prepared_rows",
            "required_rows": required_rows,
            "required_days": required_days,
        }
    outcome_mask = (
        data.get("return_5d_pct", pd.Series(index=data.index, dtype=float)).notna()
        | data.get("max_high_return_5d_pct", pd.Series(index=data.index, dtype=float)).notna()
        | data.get("target_before_stop_5d", pd.Series(index=data.index, dtype=object)).notna()
    )

    def _date_coverage(rows: pd.DataFrame, outcomes: pd.Series) -> Dict[str, Any]:
        if rows.empty or "trade_date" not in rows.columns:
            return {}
        scoped_outcomes = outcomes.reindex(rows.index).fillna(False)
        out: Dict[str, Any] = {}
        for day, day_rows in rows.groupby("trade_date", dropna=False):
            day_outcomes = scoped_outcomes.reindex(day_rows.index).fillna(False)
            market_values = day_rows.get("market", pd.Series(dtype=object)).fillna("UNKNOWN").astype(str)
            out[str(day)] = {
                "rows": int(len(day_rows)),
                "outcome_label_rows": int(day_outcomes.sum()),
                "unique_runs": int(day_rows["run_id"].nunique()) if "run_id" in day_rows.columns else 0,
                "rows_by_market": {str(key): int(value) for key, value in market_values.value_counts().to_dict().items()},
            }
        return dict(sorted(out.items()))

    families = {}
    for family in ("sidecar", "prefilter", "theme_news", "any_kis"):
        mask = _kis_family_scope(data, family)
        rows = data.loc[mask]
        outcome_rows = data.loc[mask & outcome_mask]
        families[family] = {
            "rows": int(len(rows)),
            "outcome_label_rows": int(len(outcome_rows)),
            "unique_runs": int(rows["run_id"].nunique()) if "run_id" in rows.columns and not rows.empty else 0,
            "unique_days": int(rows["trade_date"].nunique()) if "trade_date" in rows.columns and not rows.empty else 0,
            "mature_for_training": bool(len(outcome_rows) >= required_rows and (rows["trade_date"].nunique() if "trade_date" in rows.columns and not rows.empty else 0) >= required_days),
            "date_coverage": _date_coverage(rows, outcome_mask),
        }
    by_market = {}
    for market in sorted(str(item) for item in data.get("market", pd.Series(dtype=object)).dropna().unique()):
        scoped = data[data["market"].eq(market)].copy()
        by_market[market] = {}
        for family in ("sidecar", "prefilter", "theme_news", "any_kis"):
            mask = _kis_family_scope(scoped, family)
            rows = scoped.loc[mask]
            outcome_rows = scoped.loc[mask & outcome_mask.reindex(scoped.index).fillna(False)]
            unique_days = int(rows["trade_date"].nunique()) if "trade_date" in rows.columns and not rows.empty else 0
            by_market[market][family] = {
                "rows": int(len(rows)),
                "outcome_label_rows": int(len(outcome_rows)),
                "unique_runs": int(rows["run_id"].nunique()) if "run_id" in rows.columns and not rows.empty else 0,
                "unique_days": unique_days,
                "mature_for_training": bool(len(outcome_rows) >= required_rows and unique_days >= required_days),
                "date_coverage": _date_coverage(rows, outcome_mask.reindex(scoped.index).fillna(False)),
            }
    sidecar_cols = list(KIS_SIDECAR_DIAGNOSTIC_NUMERIC_FEATURES) + list(KIS_SIDECAR_MODEL_NUMERIC_FEATURES) + list(KIS_SIDECAR_CATEGORICAL_FEATURES)
    prefilter_cols = list(KIS_PREFILTER_NUMERIC_FEATURES) + list(KIS_PREFILTER_CATEGORICAL_FEATURES)
    theme_news_cols = list(KIS_THEME_NEWS_NUMERIC_FEATURES) + list(KIS_THEME_NEWS_CATEGORICAL_FEATURES)
    coverage = {
        "sidecar_top_feature_fill_pct": {
            col: _series_present_pct(data, col)
            for col in sidecar_cols
            if col in data.columns and _series_present_pct(data, col) > 0
        },
        "prefilter_top_feature_fill_pct": {
            col: _series_present_pct(data, col)
            for col in prefilter_cols
            if col in data.columns and _series_present_pct(data, col) > 0
        },
        "theme_news_top_feature_fill_pct": {
            col: _series_present_pct(data, col)
            for col in theme_news_cols
            if col in data.columns and _series_present_pct(data, col) > 0
        },
    }
    return {
        "status": "ok" if any(item.get("mature_for_training") for item in families.values()) else "blocked",
        "required_rows": required_rows,
        "required_days": required_days,
        "families": families,
        "by_market": by_market,
        "feature_fill": coverage,
        "promotion_rule": "KIS feature sets only train on rows with real KIS payload; no dummy or missing-only KIS rows are used.",
    }


def train_final_model(work: pd.DataFrame, best: Dict[str, Any], *, output_dir: Path) -> Dict[str, Any]:
    label_spec = next(item for item in LABEL_SPECS if item.name == best["label"])
    label, valid = label_series(work, label_spec)
    scoped = work.loc[valid & work["market"].eq(best["market"])].copy()
    y = label.loc[scoped.index].astype(int)
    cols = best.get("feature_columns") or {}
    numeric, categorical = usable_features(
        scoped,
        [col for col in cols.get("numeric", []) if col in scoped.columns],
        [col for col in cols.get("categorical", []) if col in scoped.columns],
    )
    features = numeric + categorical
    estimator = model_candidate(best["model"])
    if estimator is None or scoped.empty or y.nunique() < 2:
        return {"saved": False, "reason": "not_trainable"}
    pipe = Pipeline(
        [
            ("pre", preprocessor(numeric, categorical, scale_numeric=best["model"] == "logistic")),
            ("model", estimator),
        ]
    )
    x = scoped[features].copy()
    for col in categorical:
        x[col] = x[col].fillna("UNKNOWN").astype(str)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe.fit(x, y)
    output_dir.mkdir(parents=True, exist_ok=True)
    rule = str(best.get("selection_rule") or f"top{best['topn']}").replace(".", "p")
    model_path = output_dir / f"{best['market'].lower()}__{best['label']}__{best['feature_set']}__{best['model']}__{rule}.pkl"
    bundle = {
        "version": REPORT_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "target_table": TARGET_TABLE,
        "label": best["label"],
        "label_description": best.get("label_description"),
        "market": best["market"],
        "topn": best["topn"],
        "prob_threshold": best.get("prob_threshold"),
        "selection_rule": best.get("selection_rule"),
        "feature_set": best["feature_set"],
        "feature_columns": {"numeric": numeric, "categorical": categorical},
        "model_name": best["model"],
        "pipeline": pipe,
        "validation": best,
    }
    joblib.dump(bundle, model_path)
    return {"saved": True, "model_path": str(model_path), "train_rows": int(len(scoped)), "positive_rate_pct": _pct(y.mean())}


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    args = apply_grid_preset(args)
    fetch_filters = {
        "market": args.market,
        "scan_mode": args.scan_mode,
        "page_size": max(1, int(args.page_size)),
        "min_id": int(args.min_id or 0),
        "max_id": int(args.max_id or 0),
        "base_date": _date_text(args.base_date),
        "min_base_date": _date_text(args.min_base_date),
        "max_base_date": _date_text(args.max_base_date),
        "limit": int(args.limit or 0),
        "client_filter": bool(args.client_filter),
    }
    progress_enabled = not bool(getattr(args, "no_progress", False))
    cache_path = Path(args.prepared_cache) if str(getattr(args, "prepared_cache", "") or "").strip() else None
    cache_mode = str(getattr(args, "cache_mode", "off") or "off")
    signature_filters = {**fetch_filters, "max_fetch_chunks": int(args.max_fetch_chunks or 0)}
    signature = _dataset_cache_signature(signature_filters, return_sanity=args.return_sanity)
    cache_info: Dict[str, Any] = {"enabled": bool(cache_path), "mode": "off"}
    fetch_meta: Dict[str, Any] = {}
    raw_rows = 0
    data: pd.DataFrame
    return_sanity: Dict[str, Any]

    cached = None
    if cache_path and cache_mode in {"read", "readwrite"}:
        cached = load_prepared_dataset_cache(cache_path, signature=signature)
        if cached is not None:
            data, cache_info = cached
            raw_rows = int(cache_info.get("raw_rows") or len(data))
            return_sanity = cache_info.get("return_sanity") if isinstance(cache_info.get("return_sanity"), dict) else {}
            fetch_meta = {"mode": "prepared_cache_hit", "rows": raw_rows, "elapsed_sec": 0.0}
            _log(progress_enabled, f"[INFO] loaded prepared dataset cache: {cache_path} rows={len(data)}")
        elif cache_mode == "read":
            raise SystemExit(f"Prepared dataset cache miss or signature mismatch: {cache_path}")

    if cached is None:
        raw, fetch_meta = fetch_rows_chunked(
            **fetch_filters,
            fetch_chunk_days=int(args.fetch_chunk_days or 0),
            fetch_id_chunk_size=int(args.fetch_id_chunk_size or 0),
            fetch_timeout_sec=float(args.fetch_timeout_sec or 0.0),
            max_fetch_chunks=int(args.max_fetch_chunks or 0),
            progress=progress_enabled,
        )
        raw_rows = int(len(raw))
        prepare_started = perf_counter()
        data, return_sanity = prepare_dataset(raw, return_sanity=args.return_sanity)
        prepare_elapsed = _round(perf_counter() - prepare_started, 3)
        if cache_path and cache_mode in {"write", "readwrite"}:
            cache_info = write_prepared_dataset_cache(
                cache_path,
                signature=signature,
                data=data,
                raw_rows=raw_rows,
                return_sanity=return_sanity,
            )
            _log(progress_enabled, f"[INFO] wrote prepared dataset cache: {cache_path} rows={len(data)}")
        elif cache_path:
            cache_info = {"enabled": True, "mode": "miss_no_write", "path": str(cache_path)}
        cache_info["prepare_elapsed_sec"] = prepare_elapsed

    feature_map = feature_sets(data)
    model_names = [name.strip() for name in str(args.models).split(",") if name.strip()]
    markets = ["KOSPI", "KOSDAQ"] if args.market == "ALL" else [args.market]
    labels = {
        item.strip()
        for item in str(args.labels).split(",")
        if item.strip()
    }
    selected_specs = [spec for spec in LABEL_SPECS if not labels or spec.name in labels]
    topns = [int(item.strip()) for item in str(args.topns).split(",") if item.strip()]
    prob_thresholds = parse_thresholds(args.prob_thresholds)
    jobs = candidate_jobs(
        data=data,
        args=args,
        feature_map=feature_map,
        markets=markets,
        selected_specs=selected_specs,
        model_names=model_names,
        topns=topns,
        prob_thresholds=prob_thresholds,
    )
    all_results, eval_meta = evaluate_candidate_jobs(data, jobs, args, progress=progress_enabled)
    ok_results = rank_candidate_results([row for row in all_results if row.get("status") == "ok"])
    best = ok_results[0] if ok_results else None
    kis_ok_results = [row for row in ok_results if str(row.get("feature_set") or "").startswith("kis_")]
    best_kis = kis_ok_results[0] if kis_ok_results else None
    holdout_days = set()
    if best and best.get("fold_metrics"):
        for item in best.get("fold_metrics") or []:
            holdout_days.update(str(day) for day in item.get("test_days") or [])
    baselines: List[Dict[str, Any]] = []
    if best:
        best_label = next(item for item in LABEL_SPECS if item.name == best["label"])
        for topn in topns:
            baselines.extend(baseline_results(data, market=best["market"], label_spec=best_label, topn=topn, holdout_days=holdout_days))
    kis_holdout_days = set()
    if best_kis and best_kis.get("fold_metrics"):
        for item in best_kis.get("fold_metrics") or []:
            kis_holdout_days.update(str(day) for day in item.get("test_days") or [])
    kis_baselines: List[Dict[str, Any]] = []
    if best_kis:
        best_kis_label = next(item for item in LABEL_SPECS if item.name == best_kis["label"])
        for topn in topns:
            kis_baselines.extend(
                baseline_results(data, market=best_kis["market"], label_spec=best_kis_label, topn=topn, holdout_days=kis_holdout_days)
            )
    verdict = promotion_verdict(best, baselines)
    kis_verdict = promotion_verdict(best_kis, kis_baselines)
    readiness = kis_feature_readiness(
        data,
        min_train_rows=int(args.min_train_rows),
        min_test_rows=int(args.min_test_rows),
        min_kis_rows=int(args.min_kis_rows),
        min_kis_days=int(args.min_kis_days),
    )
    final_model = (
        train_final_model(data, best, output_dir=Path(args.model_dir))
        if best and verdict.get("promotable") and not args.no_save_model
        else {"saved": False, "reason": "not_promotable" if best else "no_best"}
    )
    report = {
        "version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": TARGET_TABLE,
        "fetch_filters": fetch_filters,
        "fetch_strategy": fetch_meta,
        "prepared_cache": cache_info,
        "grid_preset": str(getattr(args, "grid_preset", "custom") or "custom"),
        "evaluation": eval_meta,
        "raw_rows": int(raw_rows),
        "prepared_rows": int(len(data)),
        "markets": markets,
        "scan_mode": args.scan_mode,
        "evaluated_combinations": int(len(all_results)),
        "ok_combinations": int(len(ok_results)),
        "best": best,
        "best_kis": best_kis,
        "top_results": ok_results[: int(args.top_results)],
        "top_kis_results": kis_ok_results[: int(args.top_results)],
        "baselines_for_best_holdout": baselines,
        "baselines_for_best_kis_holdout": kis_baselines,
        "promotion_verdict": verdict,
        "kis_promotion_verdict": kis_verdict,
        "final_model": final_model,
        "kis_feature_readiness": readiness,
        "selection_policy": {
            "description": "Candidates are ranked by promotability and path risk before raw quality score.",
            "min_active_runs": MIN_PROMOTION_RUNS,
            "min_active_days": MIN_PROMOTION_DAYS,
            "min_rows": MIN_PROMOTION_ROWS,
            "min_kis_train_days": MIN_KIS_TRAIN_DAYS,
            "max_stop5_pct": MAX_PROMOTION_STOP5_PCT,
            "max_bad_path_pct": MAX_PROMOTION_BAD_PATH_PCT,
            "max_stop_before_target_5d_pct": MAX_PROMOTION_STOP_BEFORE_TARGET_5D_PCT,
            "max_fold_stop5_pct": MAX_PROMOTION_FOLD_STOP5_PCT,
            "min_target_before_stop_5d_pct": MIN_PROMOTION_TARGET_BEFORE_STOP_5D_PCT,
            "min_fold_target_before_stop_5d_pct": MIN_PROMOTION_FOLD_TARGET_BEFORE_STOP_5D_PCT,
            "min_touch10_guard_5d_pct": MIN_PROMOTION_TOUCH10_GUARD_PCT,
            "min_touch5_guard_5d_pct": MIN_PROMOTION_TOUCH5_GUARD_PCT,
            "min_guard_raw_ratio": MIN_PROMOTION_GUARD_RAW_RATIO,
            "min_min_low_5d_pct": MIN_PROMOTION_MIN_LOW_5D_PCT,
            "configured_min_kis_days": int(args.min_kis_days),
            "configured_min_kis_rows": max(int(args.min_kis_rows or 0), int(args.min_train_rows) + int(args.min_test_rows)),
        },
        "data_quality": {
            "return_sanity": return_sanity,
            "rows_by_market": data.get("market", pd.Series(dtype=object)).value_counts().to_dict() if not data.empty else {},
            "rows_by_role": data.get("row_role", pd.Series(dtype=object)).value_counts().to_dict() if "row_role" in data.columns else {},
            "date_min": str(data["trade_date"].min()) if not data.empty else None,
            "date_max": str(data["trade_date"].max()) if not data.empty else None,
            "unique_runs": int(data["run_id"].nunique()) if "run_id" in data.columns else 0,
        },
    }
    return report


def _markdown(report: Dict[str, Any]) -> str:
    best = report.get("best") or {}
    best_kis = report.get("best_kis") or {}
    m = best.get("metrics") or {}
    km = best_kis.get("metrics") or {}
    readiness = report.get("kis_feature_readiness") or {}
    lines = [
        "# Scan Universe Admission Challenger",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source: `{report.get('source')}`",
        f"- grid_preset: `{report.get('grid_preset')}`",
        f"- fetch_strategy: `{report.get('fetch_strategy')}`",
        f"- prepared_cache: `{report.get('prepared_cache')}`",
        f"- evaluation: `{report.get('evaluation')}`",
        f"- prepared_rows: `{report.get('prepared_rows')}`",
        f"- evaluated_combinations: `{report.get('evaluated_combinations')}`",
        f"- ok_combinations: `{report.get('ok_combinations')}`",
        f"- final_model: `{report.get('final_model')}`",
        f"- promotion_verdict: `{report.get('promotion_verdict')}`",
        "",
        "## Best",
        f"- market: `{best.get('market')}`",
        f"- label: `{best.get('label')}`",
        f"- feature_set: `{best.get('feature_set')}`",
        f"- model: `{best.get('model')}`",
        f"- topn: `{best.get('topn')}`",
        f"- selection_rule: `{best.get('selection_rule')}`",
        f"- quality_score: `{best.get('quality_score')}`",
        f"- n / active_runs / active_days: `{m.get('n')}` / `{m.get('active_runs')}` / `{m.get('active_days')}`",
        f"- win_metric_semantics: `{m.get('win_metric_semantics')}`",
        f"- close_win_metric_semantics: `{m.get('close_win_metric_semantics')}`",
        f"- 1d target-touch win / close defense / close avg/min/max: `{m.get('win_1d_pct')}` / `{m.get('close_win_1d_pct')}` / `{m.get('avg_1d_pct')}` / `{m.get('min_1d_pct')}` / `{m.get('max_1d_pct')}`",
        f"- 3d target-touch win / close defense / close avg/min/max: `{m.get('win_3d_pct')}` / `{m.get('close_win_3d_pct')}` / `{m.get('avg_3d_pct')}` / `{m.get('min_3d_pct')}` / `{m.get('max_3d_pct')}`",
        f"- 5d target-touch win / close defense / close avg/min/max: `{m.get('win_5d_pct')}` / `{m.get('close_win_5d_pct')}` / `{m.get('avg_5d_pct')}` / `{m.get('min_5d_pct')}` / `{m.get('max_5d_pct')}`",
        f"- target_before_stop_5d_pct: `{m.get('target_before_stop_5d_pct')}`",
        f"- hit5/hit10 5d pct: `{m.get('hit5_5d_pct')}` / `{m.get('hit10_5d_pct')}`",
        f"- guarded hit5/hit10 5d pct: `{m.get('hit5_guard_5d_pct')}` / `{m.get('hit10_guard_5d_pct')}`",
        f"- 5d max-high avg/min/max: `{m.get('avg_max_high_5d_pct')}` / `{m.get('min_max_high_5d_pct')}` / `{m.get('max_max_high_5d_pct')}`",
        f"- stop5_pct / bad_path_pct: `{m.get('stop5_pct')}` / `{m.get('bad_path_pct')}`",
        "",
        "## Best KIS",
        f"- market: `{best_kis.get('market')}`",
        f"- label: `{best_kis.get('label')}`",
        f"- feature_set: `{best_kis.get('feature_set')}`",
        f"- model: `{best_kis.get('model')}`",
        f"- selection_rule: `{best_kis.get('selection_rule')}`",
        f"- quality_score: `{best_kis.get('quality_score')}`",
        f"- n / active_runs / active_days: `{km.get('n')}` / `{km.get('active_runs')}` / `{km.get('active_days')}`",
        f"- win_metric_semantics: `{km.get('win_metric_semantics')}`",
        f"- 1d target-touch win / close defense / close avg/min/max: `{km.get('win_1d_pct')}` / `{km.get('close_win_1d_pct')}` / `{km.get('avg_1d_pct')}` / `{km.get('min_1d_pct')}` / `{km.get('max_1d_pct')}`",
        f"- 3d target-touch win / close defense / close avg/min/max: `{km.get('win_3d_pct')}` / `{km.get('close_win_3d_pct')}` / `{km.get('avg_3d_pct')}` / `{km.get('min_3d_pct')}` / `{km.get('max_3d_pct')}`",
        f"- 5d target-touch win / close defense / close avg/min/max: `{km.get('win_5d_pct')}` / `{km.get('close_win_5d_pct')}` / `{km.get('avg_5d_pct')}` / `{km.get('min_5d_pct')}` / `{km.get('max_5d_pct')}`",
        f"- hit5/hit10 5d pct: `{km.get('hit5_5d_pct')}` / `{km.get('hit10_5d_pct')}`",
        f"- promotion_verdict: `{report.get('kis_promotion_verdict')}`",
        "",
        "## KIS Feature Readiness",
        f"- status: `{readiness.get('status')}`",
        f"- required_rows / required_days: `{readiness.get('required_rows')}` / `{readiness.get('required_days')}`",
        f"- families: `{readiness.get('families')}`",
        f"- by_market: `{readiness.get('by_market')}`",
        f"- theme_news_feature_fill: `{(readiness.get('feature_fill') or {}).get('theme_news_top_feature_fill_pct')}`",
        "",
        "## Baselines",
    ]
    for row in report.get("baselines_for_best_holdout") or []:
        bm = row.get("metrics") or {}
        lines.append(
            f"- `{row.get('baseline')}` top{row.get('topn')}: "
            f"n={bm.get('n')}, 1d_target={bm.get('win_1d_pct')}% close={bm.get('close_win_1d_pct')}%/{bm.get('avg_1d_pct')}%, "
            f"3d_target={bm.get('win_3d_pct')}% close={bm.get('close_win_3d_pct')}%/{bm.get('avg_3d_pct')}%, "
            f"5d_target={bm.get('win_5d_pct')}% close={bm.get('close_win_5d_pct')}%/{bm.get('avg_5d_pct')}%, "
            f"hit5={bm.get('hit5_5d_pct')}%, hit10={bm.get('hit10_5d_pct')}%, "
            f"mfe5={bm.get('avg_max_high_5d_pct')}%, min5={bm.get('min_5d_pct')}%, max5={bm.get('max_5d_pct')}%"
        )
    lines.extend(["", "## Top Results"])
    for idx, row in enumerate(report.get("top_results") or [], start=1):
        rm = row.get("metrics") or {}
        lines.append(
            f"{idx}. `{row.get('market')}` `{row.get('label')}` `{row.get('feature_set')}` "
            f"`{row.get('model')}` {row.get('selection_rule') or ('top' + str(row.get('topn')))}: "
            f"score={row.get('quality_score')}, n={rm.get('n')}, "
            f"1d_target={rm.get('win_1d_pct')}% close={rm.get('close_win_1d_pct')}%/{rm.get('avg_1d_pct')}%, "
            f"3d_target={rm.get('win_3d_pct')}% close={rm.get('close_win_3d_pct')}%/{rm.get('avg_3d_pct')}%, "
            f"5d_target={rm.get('win_5d_pct')}% close={rm.get('close_win_5d_pct')}%/{rm.get('avg_5d_pct')}%, "
            f"hit5={rm.get('hit5_5d_pct')}%, hit10={rm.get('hit10_5d_pct')}%, "
            f"mfe5={rm.get('avg_max_high_5d_pct')}%, min5={rm.get('min_5d_pct')}%, max5={rm.get('max_5d_pct')}%"
        )
    lines.extend(["", "## Top KIS Results"])
    for idx, row in enumerate(report.get("top_kis_results") or [], start=1):
        rm = row.get("metrics") or {}
        lines.append(
            f"{idx}. `{row.get('market')}` `{row.get('label')}` `{row.get('feature_set')}` "
            f"`{row.get('model')}` {row.get('selection_rule') or ('top' + str(row.get('topn')))}: "
            f"score={row.get('quality_score')}, n={rm.get('n')}, "
            f"5d_target={rm.get('win_5d_pct')}% close={rm.get('close_win_5d_pct')}%/{rm.get('avg_5d_pct')}%, "
            f"hit5={rm.get('hit5_5d_pct')}%, hit10={rm.get('hit10_5d_pct')}%, "
            f"mfe5={rm.get('avg_max_high_5d_pct')}%, min5={rm.get('min_5d_pct')}%, max5={rm.get('max_5d_pct')}%"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Train and validate a full-universe KR admission challenger model.")
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="SWING")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to read after filters; 0 means all matching rows.")
    parser.add_argument("--min-id", type=int, default=0, help="Inclusive lower id bound for chunked Supabase reads.")
    parser.add_argument("--max-id", type=int, default=0, help="Inclusive upper id bound for chunked Supabase reads.")
    parser.add_argument("--base-date", default="", help="Exact base_trade_date filter, YYYY-MM-DD.")
    parser.add_argument("--min-base-date", default="", help="Inclusive base_trade_date lower bound, YYYY-MM-DD.")
    parser.add_argument("--max-base-date", default="", help="Inclusive base_trade_date upper bound, YYYY-MM-DD.")
    parser.add_argument("--client-filter", action="store_true", help="Fetch by id order only, then apply market/mode/date filters locally to avoid slow Supabase filtered queries.")
    parser.add_argument("--fetch-chunk-days", type=int, default=0, help="Split Supabase reads into N-day base_trade_date chunks when min/max base dates are supplied.")
    parser.add_argument("--fetch-id-chunk-size", type=int, default=0, help="Split Supabase reads into id chunks when max-id is supplied.")
    parser.add_argument("--fetch-timeout-sec", type=float, default=0.0, help="Fail a single Supabase query after N seconds and retry with a smaller page; 0 disables the local alarm.")
    parser.add_argument("--max-fetch-chunks", type=int, default=0, help="Optional smoke-test guard that stops after N fetch chunks; 0 means all chunks.")
    parser.add_argument("--prepared-cache", default="", help="Optional pickle path for prepared training data cache.")
    parser.add_argument(
        "--cache-mode",
        choices=["off", "read", "write", "readwrite"],
        default="off",
        help="Prepared dataset cache behavior. read/readwrite require matching fetch filters and return_sanity.",
    )
    parser.add_argument(
        "--grid-preset",
        choices=["custom", "kis_operational_fast", "kis_operational_full"],
        default="custom",
        help="Bounded operational KIS grids for faster promotion iteration.",
    )
    parser.add_argument("--models", default="logistic,hist_gb,extra_trees,random_forest,xgboost,lightgbm")
    parser.add_argument("--labels", default="", help="Comma-separated label names. Empty means all labels.")
    parser.add_argument("--feature-sets", default="", help="Comma-separated feature-set names. Empty means all feature sets.")
    parser.add_argument("--topns", default="1,3,5", help="Comma-separated top-N cutoffs to evaluate.")
    parser.add_argument("--prob-thresholds", default="", help="Comma-separated probability floors. Empty means top-N without a floor.")
    parser.add_argument("--eval-workers", type=int, default=1, help="Parallel candidate-grid evaluation workers. Keep low when tree models use internal n_jobs.")
    parser.add_argument("--progress-every", type=int, default=25, help="Progress log frequency in evaluated candidate combinations.")
    parser.add_argument("--min-train-rows", type=int, default=1000)
    parser.add_argument("--min-test-rows", type=int, default=200)
    parser.add_argument("--min-train-days", type=int, default=3)
    parser.add_argument("--test-days", type=int, default=2)
    parser.add_argument("--max-folds", type=int, default=5)
    parser.add_argument("--min-kis-rows", type=int, default=0, help="Minimum valid-label KIS rows for KIS feature-set training. 0 means min_train_rows + min_test_rows.")
    parser.add_argument("--min-kis-days", type=int, default=MIN_KIS_TRAIN_DAYS, help="Minimum unique trade dates for KIS feature-set training.")
    parser.add_argument("--top-results", type=int, default=20)
    parser.add_argument("--no-theme", action="store_true")
    parser.add_argument("--return-sanity", choices=["kr_price_limit", "off"], default="kr_price_limit")
    parser.add_argument("--no-save-model", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="Write full report files but print only a compact JSON summary.")
    parser.add_argument("--no-progress", action="store_true", help="Suppress progress logs even during chunked fetch/evaluation.")
    parser.add_argument("--output", default=str(REPORT_DIR / "scan_universe_admission_challenger.json"))
    parser.add_argument("--model-dir", default=str(MODEL_DIR))
    args = parser.parse_args()
    report = build_report(args)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
    out.with_suffix(".md").write_text(_markdown(report), encoding="utf-8")
    if args.quiet:
        best = report.get("best") or {}
        best_kis = report.get("best_kis") or {}
        summary = {
            "output": str(out),
            "raw_rows": report.get("raw_rows"),
            "prepared_rows": report.get("prepared_rows"),
            "evaluated_combinations": report.get("evaluated_combinations"),
            "ok_combinations": report.get("ok_combinations"),
            "grid_preset": report.get("grid_preset"),
            "fetch_strategy": report.get("fetch_strategy"),
            "prepared_cache": report.get("prepared_cache"),
            "evaluation": report.get("evaluation"),
            "best": {
                "market": best.get("market"),
                "label": best.get("label"),
                "feature_set": best.get("feature_set"),
                "model": best.get("model"),
                "topn": best.get("topn"),
                "quality_score": best.get("quality_score"),
                "promotable": (best.get("promotion_candidate") or {}).get("promotable"),
            },
            "best_kis": {
                "market": best_kis.get("market"),
                "label": best_kis.get("label"),
                "feature_set": best_kis.get("feature_set"),
                "model": best_kis.get("model"),
                "topn": best_kis.get("topn"),
                "quality_score": best_kis.get("quality_score"),
                "promotable": (best_kis.get("promotion_candidate") or {}).get("promotable"),
            },
            "promotion_verdict": report.get("promotion_verdict"),
            "kis_promotion_verdict": report.get("kis_promotion_verdict"),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
