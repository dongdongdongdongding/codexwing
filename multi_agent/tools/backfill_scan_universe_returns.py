#!/usr/bin/env python3
"""Backfill forward learning labels for scan_universe_snapshots.

The scan_universe_snapshots table contains every emitted and rejected symbol.
This tool attaches 1/3/5 trading-day close returns plus 1/3/5 day max-high
returns and path labels without using market_scan_results as the source of
truth.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TARGET_TABLE = "scan_universe_snapshots"
BACKFILL_VERSION = "scan_universe_forward_returns_v2"
PATH_LABEL_VERSION = "scan_universe_daily_path_target_stop_v1"
FEATURE_QUALITY_VERSION = "scan_universe_feature_quality_v4"
DEFAULT_OUT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "scan_universe_return_backfill.json"
DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "runtime_state" / "artifacts"
RETURN_COLUMNS = (
    "return_1d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "max_high_return_1d_pct",
    "max_high_return_3d_pct",
    "max_high_return_5d_pct",
    "min_low_return_1d_pct",
    "min_low_return_3d_pct",
    "min_low_return_5d_pct",
)
PATH_LABEL_COLUMNS = (
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
    "target_hit_at_1d",
    "target_hit_at_3d",
    "target_hit_at_5d",
    "stop_hit_at_1d",
    "stop_hit_at_3d",
    "stop_hit_at_5d",
    "days_to_target_1d",
    "days_to_target_3d",
    "days_to_target_5d",
    "days_to_stop_1d",
    "days_to_stop_3d",
    "days_to_stop_5d",
    "first_touch_1d",
    "first_touch_3d",
    "first_touch_5d",
)
FEATURE_QUALITY_COLUMNS = (
    "feature_coverage_score",
    "feature_missing_keys",
    "has_actual_flow",
    "normalized_feature_version",
    "whale_flow_1d",
    "whale_flow_3d",
    "whale_flow_10d",
    "flow_consensus_buying",
    "retail_dominant",
    "dominant",
    "whale_trend",
    "flow_source",
    "flow_unit",
    "flow_asof",
    "flow_warnings",
)
META_WRITE_COLUMNS = (
    "base_trade_date",
    "entry_reference_price",
    "label_target_pct",
    "label_stop_pct",
    "path_label_version",
    "path_label_source",
    "path_label_updated_at",
    "outcome_available",
    "outcome_source",
    "backfill_version",
    "updated_at",
)
WRITE_COLUMNS = RETURN_COLUMNS + PATH_LABEL_COLUMNS + FEATURE_QUALITY_COLUMNS + META_WRITE_COLUMNS
HORIZONS = (1, 3, 5)
FEATURE_KEYS = (
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
    "primary_theme",
)
MIN_RETRY_PAGE_SIZE = 25
MIN_WRITE_BATCH_SIZE = 25


def _load_local_env() -> None:
    for candidate in (PROJECT_ROOT / ".env.local", PROJECT_ROOT / ".env"):
        if not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "NaN", "None"):
            return None
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    except Exception:
        return None


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return _safe_float(value) is not None if isinstance(value, (int, float)) else True


def _date_text(value: Any) -> str | None:
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    return text[:10]


def _parse_date(value: Any) -> date | None:
    text = _date_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except Exception:
        return None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_run_date_index(artifact_dir: Path) -> Dict[str, str]:
    index: Dict[str, str] = {}
    if not artifact_dir.exists():
        return index
    for run_dir in artifact_dir.glob("RUN-*"):
        if not run_dir.is_dir():
            continue
        summary = _load_json(run_dir / "scan_pipeline_summary.json")
        raw = _load_json(run_dir / "raw_scan_results.json")
        summary = summary if isinstance(summary, dict) else {}
        raw = raw if isinstance(raw, dict) else {}
        run_context = raw.get("run_context") if isinstance(raw.get("run_context"), dict) else {}
        run_id = str(summary.get("run_id") or run_context.get("run_id") or run_dir.name).strip()
        base = _date_text(
            summary.get("created_at")
            or run_context.get("as_of_date")
            or run_context.get("created_at")
            or raw.get("created_at")
        )
        if run_id and base:
            index[run_id] = base
    return index


def _resolved_base_date(row: Dict[str, Any], run_date_index: Dict[str, str] | None = None) -> date | None:
    return (
        _parse_date(row.get("base_trade_date"))
        or _parse_date(row.get("scanned_at"))
        or _parse_date((run_date_index or {}).get(str(row.get("run_id") or "").strip()))
    )


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _ticker_code(ticker: str) -> str:
    return str(ticker or "").strip().split(".")[0]


class _FetchTimeout(RuntimeError):
    pass


def _run_with_timeout(seconds: float, fn):
    if seconds <= 0:
        return fn()
    previous = signal.getsignal(signal.SIGALRM)

    def _handler(_signum, _frame):
        raise _FetchTimeout("price_fetch_timeout")

    signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, float(seconds))
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class PriceHistoryProvider:
    def __init__(self, *, provider: str = "fdr", sleep_sec: float = 0.0, fetch_timeout: float = 12.0) -> None:
        self.provider = str(provider or "fdr").lower()
        self.sleep_sec = max(0.0, float(sleep_sec or 0.0))
        self.fetch_timeout = max(0.0, float(fetch_timeout or 0.0))
        self.cache: Dict[tuple[str, str, str], List[Dict[str, Any]]] = {}
        self.fetch_counts: Counter[str] = Counter()
        self.fetch_failures: Counter[str] = Counter()
        try:
            import FinanceDataReader as fdr  # type: ignore
        except Exception:
            fdr = None
        try:
            import yfinance as yf  # type: ignore
        except Exception:
            yf = None
        self.fdr = fdr
        self.yf = yf

    def fetch(self, ticker: str, start: str, end: str) -> List[Dict[str, Any]]:
        key = (str(ticker), str(start), str(end))
        if key in self.cache:
            return self.cache[key]
        rows: List[Dict[str, Any]] = []
        if self.provider in {"fdr", "auto"}:
            rows = self._fetch_fdr(ticker, start, end)
        if not rows and self.provider in {"yf", "yfinance", "auto", "fdr"}:
            rows = self._fetch_yfinance(ticker, start, end)
        self.cache[key] = rows
        if self.sleep_sec > 0:
            import time

            time.sleep(self.sleep_sec)
        return rows

    def _fetch_fdr(self, ticker: str, start: str, end: str) -> List[Dict[str, Any]]:
        if self.fdr is None:
            self.fetch_failures["fdr_unavailable"] += 1
            return []
        try:
            hist = _run_with_timeout(
                self.fetch_timeout,
                lambda: self.fdr.DataReader(_ticker_code(ticker), start, end),
            )
        except _FetchTimeout:
            self.fetch_failures["fdr_timeout"] += 1
            return []
        except Exception:
            self.fetch_failures["fdr_exception"] += 1
            return []
        if hist is None or hist.empty:
            self.fetch_failures["fdr_empty"] += 1
            return []
        self.fetch_counts["fdr"] += 1
        return _history_frame_to_bars(hist)

    def _fetch_yfinance(self, ticker: str, start: str, end: str) -> List[Dict[str, Any]]:
        if self.yf is None:
            self.fetch_failures["yf_unavailable"] += 1
            return []
        try:
            hist = _run_with_timeout(
                self.fetch_timeout,
                lambda: self.yf.Ticker(str(ticker)).history(start=start, end=end, auto_adjust=False, timeout=10),
            )
        except _FetchTimeout:
            self.fetch_failures["yf_timeout"] += 1
            return []
        except Exception:
            self.fetch_failures["yf_exception"] += 1
            return []
        if hist is None or hist.empty:
            self.fetch_failures["yf_empty"] += 1
            return []
        self.fetch_counts["yfinance"] += 1
        return _history_frame_to_bars(hist)


def _history_frame_to_bars(hist: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if hist is None or getattr(hist, "empty", True):
        return rows
    for idx, item in hist.iterrows():
        try:
            trade_date = idx.date().isoformat()
        except Exception:
            trade_date = str(idx)[:10]
        close = _safe_float(item.get("Close"))
        high = _safe_float(item.get("High"))
        low = _safe_float(item.get("Low"))
        if not trade_date or close is None:
            continue
        rows.append(
            {
                "date": trade_date,
                "close": close,
                "high": high if high is not None else close,
                "low": low if low is not None else close,
            }
        )
    rows.sort(key=lambda row: str(row.get("date") or ""))
    return rows


def _row_needs_backfill(row: Dict[str, Any], *, overwrite: bool) -> bool:
    if overwrite:
        return True
    if str(row.get("normalized_feature_version") or "") != FEATURE_QUALITY_VERSION:
        return True
    return any(row.get(col) is None for col in RETURN_COLUMNS + PATH_LABEL_COLUMNS + FEATURE_QUALITY_COLUMNS)


def _first_touch_payload(
    future: Sequence[Dict[str, Any]],
    *,
    entry: float,
    horizon: int,
    target_pct: float,
    stop_pct: float,
) -> Dict[str, Any]:
    target_price = entry * (1.0 + target_pct / 100.0)
    stop_price = entry * (1.0 - abs(stop_pct) / 100.0)
    target_hit = False
    stop_hit = False
    target_at = None
    stop_at = None
    days_to_target = None
    days_to_stop = None
    target_before_stop = False
    stop_before_target = False
    first_touch = "no_touch"

    for offset, bar in enumerate(future[:horizon], start=1):
        high = _safe_float(bar.get("high"))
        low = _safe_float(bar.get("low"))
        bar_date = _date_text(bar.get("date"))
        touched_target = high is not None and high >= target_price
        touched_stop = low is not None and low <= stop_price
        if touched_target and target_at is None:
            target_hit = True
            target_at = bar_date
            days_to_target = offset
        if touched_stop and stop_at is None:
            stop_hit = True
            stop_at = bar_date
            days_to_stop = offset
        if touched_target and touched_stop:
            first_touch = "same_bar_stop_first"
            stop_before_target = True
            break
        if touched_stop:
            first_touch = "stop"
            stop_before_target = True
            break
        if touched_target:
            first_touch = "target"
            target_before_stop = True
            break

    if first_touch == "no_touch":
        target_before_stop = False
        stop_before_target = False

    return {
        f"target_hit_{horizon}d": target_hit,
        f"stop_hit_{horizon}d": stop_hit,
        f"target_before_stop_{horizon}d": target_before_stop,
        f"stop_before_target_{horizon}d": stop_before_target,
        f"target_hit_at_{horizon}d": target_at,
        f"stop_hit_at_{horizon}d": stop_at,
        f"days_to_target_{horizon}d": days_to_target,
        f"days_to_stop_{horizon}d": days_to_stop,
        f"first_touch_{horizon}d": first_touch,
    }


def _feature_quality_payload(row: Dict[str, Any], *, overwrite: bool) -> Dict[str, Any]:
    missing = [key for key in FEATURE_KEYS if not _is_present(row.get(key))]
    present = len(FEATURE_KEYS) - len(missing)
    foreigner_1d = _safe_float(row.get("foreigner_1d"))
    institution_1d = _safe_float(row.get("institution_1d"))
    retail_1d = _safe_float(row.get("retail_1d"))
    foreigner_3d = _safe_float(row.get("foreigner_3d"))
    institution_3d = _safe_float(row.get("institution_3d"))
    retail_3d = _safe_float(row.get("retail_3d"))
    foreigner_10d = _safe_float(row.get("foreigner_10d"))
    institution_10d = _safe_float(row.get("institution_10d"))
    retail_10d = _safe_float(row.get("retail_10d"))
    whale_1d = (foreigner_1d or 0.0) + (institution_1d or 0.0) if foreigner_1d is not None or institution_1d is not None else None
    whale_3d = (foreigner_3d or 0.0) + (institution_3d or 0.0) if foreigner_3d is not None or institution_3d is not None else None
    whale_10d = (foreigner_10d or 0.0) + (institution_10d or 0.0) if foreigner_10d is not None or institution_10d is not None else None
    has_flow = any(value is not None for value in (foreigner_1d, institution_1d, retail_1d, foreigner_3d, institution_3d, retail_3d))
    flow_consensus = None
    if whale_1d is not None and whale_3d is not None:
        flow_consensus = whale_1d > 0 and whale_3d > 0
    retail_dominant = None
    if retail_1d is not None and whale_1d is not None:
        retail_dominant = retail_1d > 0 and whale_1d < 0
    dominant = None
    contenders = {
        "foreigner": foreigner_1d,
        "institution": institution_1d,
        "retail": retail_1d,
    }
    contenders = {key: value for key, value in contenders.items() if value is not None}
    if contenders:
        dominant = max(contenders, key=lambda key: abs(float(contenders[key] or 0.0)))
    whale_trend = None
    if whale_1d is not None and whale_3d is not None:
        if whale_1d > 0 and whale_3d > 0:
            whale_trend = "accumulation"
        elif whale_1d < 0 and whale_3d < 0:
            whale_trend = "distribution"
        else:
            whale_trend = "mixed"
    payload = {
        "feature_coverage_score": round(present / len(FEATURE_KEYS), 6),
        "feature_missing_keys": missing,
        "has_actual_flow": has_flow,
        "normalized_feature_version": FEATURE_QUALITY_VERSION,
        "whale_flow_1d": whale_1d,
        "whale_flow_3d": whale_3d,
        "whale_flow_10d": whale_10d,
        "flow_consensus_buying": flow_consensus,
        "retail_dominant": retail_dominant,
        "dominant": dominant,
        "whale_trend": whale_trend,
        "flow_source": "scan_universe_snapshot" if has_flow else None,
        "flow_unit": "source_units" if has_flow else None,
        "flow_asof": None,
        "flow_warnings": [] if has_flow else ["investor_flow_missing_in_scan_archive"],
    }
    if overwrite or str(row.get("normalized_feature_version") or "") != FEATURE_QUALITY_VERSION:
        return payload
    return {key: value for key, value in payload.items() if row.get(key) is None}


def _compute_return_payload(
    row: Dict[str, Any],
    bars: Sequence[Dict[str, Any]],
    *,
    overwrite: bool,
    run_date_index: Dict[str, str] | None = None,
    target_pct: float = 5.0,
    stop_pct: float = 5.0,
) -> Dict[str, Any]:
    base = _resolved_base_date(row, run_date_index)
    if base is None:
        return {}
    eligible = [bar for bar in bars if _parse_date(bar.get("date")) and _parse_date(bar.get("date")) >= base]
    if not eligible:
        return {}
    entry_bar = eligible[0]
    entry = _safe_float(row.get("entry_reference_price"))
    if entry is None or entry <= 0:
        entry = _safe_float(entry_bar.get("close"))
    if entry is None or entry <= 0:
        return {}
    future = eligible[1:]
    payload: Dict[str, Any] = _feature_quality_payload(row, overwrite=overwrite)
    if payload.get("has_actual_flow") is True:
        payload["flow_asof"] = base.isoformat()
    for horizon in HORIZONS:
        ret_col = f"return_{horizon}d_pct"
        high_col = f"max_high_return_{horizon}d_pct"
        low_col = f"min_low_return_{horizon}d_pct"
        if len(future) >= horizon:
            close = _safe_float(future[horizon - 1].get("close"))
            if close is not None and (overwrite or row.get(ret_col) is None):
                payload[ret_col] = round((close - entry) / entry * 100.0, 6)
            highs = [_safe_float(bar.get("high")) for bar in future[:horizon]]
            highs = [value for value in highs if value is not None]
            if highs and (overwrite or row.get(high_col) is None):
                payload[high_col] = round((max(highs) - entry) / entry * 100.0, 6)
            lows = [_safe_float(bar.get("low")) for bar in future[:horizon]]
            lows = [value for value in lows if value is not None]
            if lows and (overwrite or row.get(low_col) is None):
                payload[low_col] = round((min(lows) - entry) / entry * 100.0, 6)
            touch_payload = _first_touch_payload(
                future,
                entry=float(entry),
                horizon=horizon,
                target_pct=float(target_pct),
                stop_pct=float(stop_pct),
            )
            for key, value in touch_payload.items():
                if overwrite or row.get(key) is None:
                    payload[key] = value
    outcome_payload = any(
        key.startswith("return_")
        or key.startswith("max_high_return_")
        or key.startswith("min_low_return_")
        or key.startswith("target_hit_")
        or key.startswith("stop_hit_")
        or key.startswith("target_before_stop_")
        or key.startswith("stop_before_target_")
        or key.startswith("first_touch_")
        for key in payload
    )
    if payload:
        payload["base_trade_date"] = base.isoformat()
        payload["entry_reference_price"] = entry
        payload["label_target_pct"] = float(target_pct)
        payload["label_stop_pct"] = abs(float(stop_pct))
        payload["path_label_version"] = PATH_LABEL_VERSION
        payload["path_label_source"] = "daily_ohlc_stop_first"
        payload["path_label_updated_at"] = datetime.now(timezone.utc).isoformat()
        if outcome_payload:
            payload["outcome_available"] = True
            payload["outcome_source"] = "scan_universe_price_history"
        payload["backfill_version"] = BACKFILL_VERSION
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    return payload


def fetch_snapshot_rows(
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
) -> List[Dict[str, Any]]:
    _load_local_env()
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")
    cols = ",".join(
        [
            "id",
            "snapshot_key",
            "run_id",
            "ticker",
            "market",
            "scan_mode",
            "row_role",
            "base_trade_date",
            "scanned_at",
            "entry_reference_price",
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
            "primary_theme",
            "outcome_available",
            "outcome_source",
            "backfill_version",
            *RETURN_COLUMNS,
            *PATH_LABEL_COLUMNS,
            *FEATURE_QUALITY_COLUMNS,
        ]
    )
    rows: List[Dict[str, Any]] = []
    last_id = max(0, int(min_id or 0) - 1)
    safe_page_size = max(1, int(page_size))
    while True:
        take = safe_page_size
        query = db.client.table(TARGET_TABLE).select(cols).order("id").gt("id", last_id).limit(take)
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
            batch = query.execute().data or []
        except Exception as exc:
            message = str(exc)
            if safe_page_size > MIN_RETRY_PAGE_SIZE and ("statement timeout" in message or "57014" in message):
                next_page_size = max(MIN_RETRY_PAGE_SIZE, safe_page_size // 2)
                print(
                    f"[WARN] Supabase fetch timed out at page_size={safe_page_size}; retrying with page_size={next_page_size}",
                    flush=True,
                )
                safe_page_size = next_page_size
                continue
            raise
        eligible_batch = batch
        if client_filter:
            eligible_batch = []
            for row in batch:
                row_market = str(row.get("market") or "")
                row_scan_mode = str(row.get("scan_mode") or "")
                row_base = _date_text(row.get("base_trade_date") or row.get("scanned_at")) or ""
                if market != "ALL" and row_market != market:
                    continue
                if scan_mode != "ALL" and row_scan_mode != scan_mode:
                    continue
                if base_date and row_base != base_date:
                    continue
                if min_base_date and row_base < min_base_date:
                    continue
                if max_base_date and row_base > max_base_date:
                    continue
                eligible_batch.append(row)
        rows.extend(eligible_batch)
        if limit and len(rows) >= int(limit):
            return rows[: int(limit)]
        if batch:
            last_id = max(int(row.get("id") or last_id) for row in batch)
        if len(batch) < take:
            break
        if max_id and last_id >= int(max_id):
            break
    return rows


def build_updates(
    rows: Iterable[Dict[str, Any]],
    *,
    provider: PriceHistoryProvider,
    overwrite: bool,
    max_tickers: int,
    run_date_index: Dict[str, str] | None = None,
    target_pct: float = 5.0,
    stop_pct: float = 5.0,
) -> Dict[str, Any]:
    run_date_index = run_date_index or {}
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    repaired_base_date_candidates = 0
    for row in rows:
        ticker = str(row.get("ticker") or "").strip()
        if not ticker or not _row_needs_backfill(row, overwrite=overwrite):
            continue
        base_date = _resolved_base_date(row, run_date_index)
        if base_date is None:
            continue
        if not row.get("base_trade_date"):
            repaired_base_date_candidates += 1
        grouped[ticker].append(row)

    tickers = sorted(grouped)
    if max_tickers and max_tickers > 0:
        tickers = tickers[:max_tickers]

    updates: List[Dict[str, Any]] = []
    no_history = 0
    no_payload = 0
    by_market: Counter[str] = Counter()
    by_role: Counter[str] = Counter()
    for idx, ticker in enumerate(tickers, start=1):
        ticker_rows = grouped[ticker]
        dates = [_resolved_base_date(row, run_date_index) for row in ticker_rows]
        dates = [item for item in dates if item is not None]
        if not dates:
            no_payload += len(ticker_rows)
            continue
        start = (min(dates) - timedelta(days=3)).isoformat()
        end = (max(dates) + timedelta(days=14)).isoformat()
        bars = provider.fetch(ticker, start, end)
        if not bars:
            no_history += len(ticker_rows)
            continue
        for row in ticker_rows:
            payload = _compute_return_payload(
                row,
                bars,
                overwrite=overwrite,
                run_date_index=run_date_index,
                target_pct=target_pct,
                stop_pct=stop_pct,
            )
            if not payload:
                no_payload += 1
                continue
            for key in WRITE_COLUMNS:
                if key not in payload and key in row:
                    payload[key] = row.get(key)
            payload["id"] = row.get("id")
            payload["snapshot_key"] = row.get("snapshot_key")
            payload["run_id"] = row.get("run_id")
            payload["ticker"] = row.get("ticker")
            payload["row_role"] = row.get("row_role")
            updates.append(_json_safe(payload))
            by_market[str(row.get("market") or "")] += 1
            by_role[str(row.get("row_role") or "")] += 1
        if idx % 100 == 0:
            print(f"[INFO] priced {idx}/{len(tickers)} tickers, updates={len(updates)}", flush=True)

    return {
        "updates": updates,
        "ticker_count": len(tickers),
        "candidate_rows": sum(len(grouped[ticker]) for ticker in tickers),
        "no_history_rows": no_history,
        "no_payload_rows": no_payload,
        "updates_by_market": dict(by_market),
        "updates_by_role": dict(by_role),
        "repaired_base_date_candidates": repaired_base_date_candidates,
        "price_fetch_counts": dict(provider.fetch_counts),
        "price_fetch_failures": dict(provider.fetch_failures),
    }


def write_updates(updates: List[Dict[str, Any]], *, batch_size: int, write_method: str = "upsert") -> int:
    if not updates:
        return 0
    _load_local_env()
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")
    writable = set(WRITE_COLUMNS)
    written = 0
    method = str(write_method or "upsert").lower()
    if method == "upsert":
        payload_keys = ("id", "snapshot_key", "run_id", "ticker", "row_role", *WRITE_COLUMNS)
        start = 0
        adaptive_batch_size = max(1, int(batch_size))
        while start < len(updates):
            batch = updates[start : start + adaptive_batch_size]
            normalized = []
            for item in batch:
                if item.get("id") is None:
                    continue
                normalized_item = {key: item.get(key) for key in payload_keys}
                normalized_item["outcome_available"] = bool(item.get("outcome_available"))
                if normalized_item.get("feature_missing_keys") is None:
                    normalized_item["feature_missing_keys"] = []
                if normalized_item.get("flow_warnings") is None:
                    normalized_item["flow_warnings"] = []
                normalized.append(normalized_item)
            if not normalized:
                start += adaptive_batch_size
                continue
            last_exc = None
            for attempt in range(1, 4):
                try:
                    db.client.table(TARGET_TABLE).upsert(normalized, on_conflict="id").execute()
                    last_exc = None
                    break
                except Exception as exc:
                    message = str(exc)
                    if adaptive_batch_size > MIN_WRITE_BATCH_SIZE and (
                        "statement timeout" in message or "57014" in message
                    ):
                        next_batch_size = max(MIN_WRITE_BATCH_SIZE, adaptive_batch_size // 2)
                        print(
                            f"[WARN] Supabase upsert timed out at batch_size={adaptive_batch_size}; "
                            f"retrying with batch_size={next_batch_size}",
                            flush=True,
                        )
                        adaptive_batch_size = next_batch_size
                        last_exc = None
                        break
                    last_exc = exc
                    import time

                    time.sleep(min(2 * attempt, 5))
            if last_exc is not None:
                raise last_exc
            if len(normalized) != len(batch) and not normalized:
                start += adaptive_batch_size
                continue
            if len(normalized) != len(batch):
                start += len(batch)
                continue
            if adaptive_batch_size < len(batch):
                continue
            if last_exc is None and len(batch) == adaptive_batch_size:
                written += len(normalized)
                start += adaptive_batch_size
                print(f"[INFO] upserted learning labels {written}/{len(updates)}", flush=True)
                continue
            if last_exc is None and len(batch) < adaptive_batch_size:
                written += len(normalized)
                start += len(batch)
                print(f"[INFO] upserted learning labels {written}/{len(updates)}", flush=True)
                continue
            written += len(normalized)
            start += len(batch)
            print(f"[INFO] upserted learning labels {written}/{len(updates)}", flush=True)
        return written

    for item in updates:
        row_id = item.get("id")
        if row_id is None:
            continue
        payload = {key: value for key, value in item.items() if key in writable}
        if not payload:
            continue
        db.client.table(TARGET_TABLE).update(payload).eq("id", row_id).execute()
        written += 1
        if written % max(1, int(batch_size)) == 0 or written == len(updates):
            print(f"[INFO] updated returns {written}/{len(updates)}", flush=True)
    return written


def _write_report(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Scan Universe Return Backfill",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- source_rows: `{report.get('source_rows')}`",
        f"- candidate_rows: `{report.get('candidate_rows')}`",
        f"- ticker_count: `{report.get('ticker_count')}`",
        f"- updates_built: `{report.get('updates_built')}`",
        f"- rows_written: `{report.get('rows_written')}`",
        f"- dry_run: `{report.get('dry_run')}`",
        f"- overwrite: `{report.get('overwrite')}`",
        f"- no_history_rows: `{report.get('no_history_rows')}`",
        f"- no_payload_rows: `{report.get('no_payload_rows')}`",
        f"- repaired_base_date_candidates: `{report.get('repaired_base_date_candidates')}`",
        f"- run_date_index_size: `{report.get('run_date_index_size')}`",
        "",
        "## Distribution",
        f"- updates_by_market: `{report.get('updates_by_market')}`",
        f"- updates_by_role: `{report.get('updates_by_role')}`",
        f"- price_fetch_counts: `{report.get('price_fetch_counts')}`",
        f"- price_fetch_failures: `{report.get('price_fetch_failures')}`",
    ]
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="ALL")
    parser.add_argument("--provider", choices=["fdr", "yfinance", "auto"], default="fdr")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--write-method", choices=["upsert", "update"], default="upsert")
    parser.add_argument("--limit", type=int, default=0, help="Maximum source rows to process after filters; 0 means all.")
    parser.add_argument(
        "--client-filter",
        action="store_true",
        help="Read by indexed id pages and apply market/date filters client-side to avoid filtered-query timeouts.",
    )
    parser.add_argument("--min-id", type=int, default=0, help="Inclusive lower id bound for chunked Supabase reads.")
    parser.add_argument("--max-id", type=int, default=0, help="Inclusive upper id bound for chunked Supabase reads.")
    parser.add_argument("--base-date", default="", help="Exact base_trade_date filter, YYYY-MM-DD.")
    parser.add_argument("--min-base-date", default="", help="Inclusive base_trade_date lower bound, YYYY-MM-DD.")
    parser.add_argument("--max-base-date", default="", help="Inclusive base_trade_date upper bound, YYYY-MM-DD.")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--fetch-timeout", type=float, default=12.0)
    parser.add_argument("--target-pct", type=float, default=5.0)
    parser.add_argument("--stop-pct", type=float, default=5.0)
    parser.add_argument("--max-tickers", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    args = parser.parse_args()

    rows = fetch_snapshot_rows(
        market=args.market,
        scan_mode=args.scan_mode,
        page_size=max(1, int(args.page_size)),
        min_id=int(args.min_id or 0),
        max_id=int(args.max_id or 0),
        base_date=_date_text(args.base_date) or "",
        min_base_date=_date_text(args.min_base_date) or "",
        max_base_date=_date_text(args.max_base_date) or "",
        limit=int(args.limit or 0),
        client_filter=bool(args.client_filter),
    )
    run_date_index = _load_run_date_index(Path(args.artifact_dir))
    provider = PriceHistoryProvider(
        provider=args.provider,
        sleep_sec=float(args.sleep or 0.0),
        fetch_timeout=float(args.fetch_timeout or 0.0),
    )
    result = build_updates(
        rows,
        provider=provider,
        overwrite=bool(args.overwrite),
        max_tickers=int(args.max_tickers or 0),
        run_date_index=run_date_index,
        target_pct=float(args.target_pct or 5.0),
        stop_pct=float(args.stop_pct or 5.0),
    )
    updates = result.pop("updates")
    rows_written = (
        0
        if args.dry_run
        else write_updates(updates, batch_size=max(1, int(args.batch_size)), write_method=args.write_method)
    )
    report = {
        "version": BACKFILL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": len(rows),
        "updates_built": len(updates),
        "rows_written": rows_written,
        "dry_run": bool(args.dry_run),
        "overwrite": bool(args.overwrite),
        "market": args.market,
        "scan_mode": args.scan_mode,
        "limit": int(args.limit or 0),
        "min_id": int(args.min_id or 0),
        "max_id": int(args.max_id or 0),
        "base_date": _date_text(args.base_date) or "",
        "min_base_date": _date_text(args.min_base_date) or "",
        "max_base_date": _date_text(args.max_base_date) or "",
        "client_filter": bool(args.client_filter),
        "target_pct": float(args.target_pct or 5.0),
        "stop_pct": abs(float(args.stop_pct or 5.0)),
        "run_date_index_size": len(run_date_index),
        "write_method": args.write_method,
        **result,
        "sample_updates": updates[:10],
    }
    _write_report(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BACKFILL_VERSION",
    "PriceHistoryProvider",
    "_compute_return_payload",
    "build_updates",
    "fetch_snapshot_rows",
    "write_updates",
]
