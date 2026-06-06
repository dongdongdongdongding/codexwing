#!/usr/bin/env python3
"""Backfill KIS sidecar features into scan_universe_snapshots.

This tool fills ``feature_snapshot.kis_sidecar`` from real KIS OpenAPI data so
the scan-universe challenger can train on KIS-backed features without changing
the existing Supabase table contract.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.kis_openapi import KISOpenAPIClient, normalize_kr_stock_code
from modules.kis_operational_adapter import (
    build_kis_sidecar_snapshot,
    normalize_kis_daily_bars,
    normalize_kis_financial_ratio,
    normalize_kis_minute_bars,
    normalize_kis_news_titles,
    normalize_kis_rank_membership,
    normalize_kis_stock_info,
    normalize_kis_vi_status,
)


TARGET_TABLE = "scan_universe_snapshots"
BACKFILL_VERSION = "kis_scan_universe_sidecar_backfill_v1"
DEFAULT_REPORT = PROJECT_ROOT / "runtime_state" / "reports" / "validation" / "kis_sidecar_scan_universe_backfill.json"
SNAPSHOT_SELECT_COLUMNS = (
    "id",
    "snapshot_key",
    "run_id",
    "ticker",
    "stock_name",
    "market",
    "scan_mode",
    "row_role",
    "base_trade_date",
    "scanned_at",
    "outcome_available",
    "return_5d_pct",
    "max_high_return_5d_pct",
    "target_before_stop_5d",
    "feature_snapshot",
)
OUTCOME_LABEL_COLUMNS = ("return_5d_pct", "max_high_return_5d_pct", "target_before_stop_5d")


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


def _json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            loaded = json.loads(text)
        except Exception:
            return {}
        return dict(loaded) if isinstance(loaded, Mapping) else {}
    return {}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _date_text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    if len(text) >= 8 and text[:8].isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    try:
        return pd.to_datetime(text).date().isoformat()
    except Exception:
        return None


def _parse_date(value: Any) -> Optional[date]:
    text = _date_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except Exception:
        return None


def _base_trade_date(row: Mapping[str, Any]) -> Optional[date]:
    return _parse_date(row.get("base_trade_date")) or _parse_date(row.get("scanned_at"))


def _yyyymmdd(value: date) -> str:
    return value.strftime("%Y%m%d")


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            text = value.replace(",", "").replace("%", "").strip()
            if not text:
                return None
            value = text
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _safe_int(value: Any) -> Optional[int]:
    number = _safe_float(value)
    return int(number) if number is not None else None


def _payload_rows(payload: Any) -> List[Dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    for key in ("output2", "output", "Output", "output1"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [dict(row) for row in rows if isinstance(row, Mapping)]
    value = payload.get("output")
    return [dict(value)] if isinstance(value, Mapping) else []


def _first_present(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _extract_daily_value_traded(payload: Mapping[str, Any], base_date: date) -> Optional[float]:
    target = _yyyymmdd(base_date)
    fallback: Optional[float] = None
    for row in _payload_rows(payload):
        row_date = str(_first_present(row, "stck_bsop_date", "bsop_date", "date", "Date") or "").strip()
        value = _safe_float(_first_present(row, "acml_tr_pbmn", "tr_pbmn", "value", "Value"))
        if row_date == target:
            return value
        if value is not None:
            fallback = value
    return fallback


def _filter_daily_frame(frame: pd.DataFrame, base_date: date) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    filtered = frame.copy()
    filtered.index = pd.to_datetime(filtered.index)
    cutoff = pd.Timestamp(base_date)
    filtered = filtered[filtered.index <= cutoff].sort_index()
    return filtered


def _volume_ratio(frame: pd.DataFrame, lookback: int = 20) -> Optional[float]:
    if frame is None or frame.empty or "Volume" not in frame.columns or len(frame) <= 1:
        return None
    latest = _safe_float(frame["Volume"].iloc[-1])
    if latest is None:
        return None
    base = pd.to_numeric(frame["Volume"].iloc[max(0, len(frame) - lookback - 1) : -1], errors="coerce").dropna()
    if base.empty:
        return None
    avg = float(base.mean())
    if avg <= 0:
        return None
    return round(float(latest) / avg, 4)


def build_daily_quote_proxy(
    *,
    symbol: str,
    base_date: date,
    daily_bars: pd.DataFrame,
    value_traded: Optional[float] = None,
) -> Dict[str, Any]:
    """Build an as-of quote-like snapshot from KIS historical daily bars."""

    frame = _filter_daily_frame(daily_bars, base_date)
    if frame.empty or "Close" not in frame.columns:
        return {}
    latest = frame.iloc[-1]
    previous = frame.iloc[-2] if len(frame) >= 2 else None
    close = _safe_float(latest.get("Close"))
    previous_close = _safe_float(previous.get("Close")) if previous is not None else None
    day_change_pct = None
    if close is not None and previous_close not in (None, 0):
        day_change_pct = round(((close - float(previous_close)) / float(previous_close)) * 100.0, 4)
    index_value = frame.index[-1]
    latest_date = index_value.date() if hasattr(index_value, "date") else base_date
    warnings = ["quote_snapshot_reconstructed_from_kis_daily_bars"]
    if latest_date != base_date:
        warnings.append(f"latest_daily_bar_before_base_date:{latest_date.isoformat()}")
    return {
        "ticker": normalize_kr_stock_code(symbol),
        "source": "kis_openapi_daily_backfill",
        "source_status": "ok" if close is not None else "empty_output",
        "snapshot_at": f"{latest_date.isoformat()}T15:30:00+09:00",
        "last_price": close,
        "day_change_pct": day_change_pct,
        "session_open": _safe_float(latest.get("Open")),
        "session_high": _safe_float(latest.get("High")),
        "session_low": _safe_float(latest.get("Low")),
        "volume": _safe_int(latest.get("Volume")),
        "value_traded": value_traded,
        "prev_volume_ratio": _volume_ratio(frame, 20),
        "warnings": warnings,
    }


def _has_kis_sidecar(row: Mapping[str, Any]) -> bool:
    snapshot = _json_dict(row.get("feature_snapshot"))
    return bool(_json_dict(snapshot.get("kis_sidecar")) or _json_dict(snapshot.get("_kis_sidecar")))


def _has_outcome_label(row: Mapping[str, Any]) -> bool:
    for key in OUTCOME_LABEL_COLUMNS:
        value = row.get(key)
        if value is not None and str(value).strip() not in {"", "nan", "NaN", "None", "null"}:
            return True
    return False


def _merge_kis_sidecar(
    row: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    *,
    generated_at: str,
) -> Dict[str, Any]:
    snapshot = _json_dict(row.get("feature_snapshot"))
    merged = dict(snapshot)
    sidecar_payload = dict(sidecar)
    sidecar_payload["feature_origin"] = "kis_openapi_backfill"
    sidecar_payload["backfill_contract_version"] = BACKFILL_VERSION
    sidecar_payload["backfilled_at"] = generated_at
    sidecar_payload["backfill_base_trade_date"] = _date_text(row.get("base_trade_date") or row.get("scanned_at"))
    merged["kis_sidecar"] = sidecar_payload
    merged["kis_model_candidate_features"] = dict(sidecar_payload.get("model_candidate_features") or {})
    merged["kis_sidecar_backfill"] = {
        "contract_version": BACKFILL_VERSION,
        "feature_origin": "kis_openapi_backfill",
        "backfilled_at": generated_at,
        "source_table": TARGET_TABLE,
        "source_row_id": row.get("id"),
        "source_snapshot_key": row.get("snapshot_key"),
        "no_dummy_data": True,
    }
    return merged


@dataclass
class BackfillOptions:
    daily_lookback_days: int = 140
    include_flow: bool = True
    include_minute: bool = False
    include_vi: bool = True
    include_news: bool = False
    include_stock_info: bool = True
    include_financial: bool = True
    include_current_rank: bool = False
    input_hour: str = "153000"
    sleep_sec: float = 0.0
    overwrite: bool = False
    require_outcome_label: bool = False


class KISSidecarBackfillBuilder:
    def __init__(self, client: Any, options: BackfillOptions) -> None:
        self.client = client
        self.options = options
        self.call_counts: Counter[str] = Counter()
        self.failures: Counter[str] = Counter()
        self._stock_info_cache: Dict[str, Dict[str, Any]] = {}
        self._financial_cache: Dict[str, Dict[str, Any]] = {}
        self._vi_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._rank_cache: Dict[str, Dict[str, Any]] = {}

    def _call(self, label: str, fn) -> Any:
        self.call_counts[label] += 1
        try:
            result = fn()
        except Exception as exc:
            self.failures[f"{label}:{type(exc).__name__}"] += 1
            return {"_kis_backfill_error": str(exc)}
        finally:
            if self.options.sleep_sec > 0:
                time.sleep(float(self.options.sleep_sec))
        return result

    def _daily_bars(self, symbol: str, base_date: date) -> Tuple[Dict[str, Any], pd.DataFrame]:
        start = base_date - timedelta(days=max(80, int(self.options.daily_lookback_days)))
        payload = self._call(
            "daily_bars",
            lambda: self.client.daily_bars(
                symbol,
                start_date=_yyyymmdd(start),
                end_date=_yyyymmdd(base_date),
                period="D",
                adjusted=True,
                market_div="J",
            ),
        )
        if isinstance(payload, Mapping) and payload.get("_kis_backfill_error"):
            return dict(payload), pd.DataFrame()
        frame = normalize_kis_daily_bars(symbol, payload if isinstance(payload, Mapping) else {})
        return dict(payload or {}), _filter_daily_frame(frame, base_date)

    def _minute_bars(self, symbol: str, base_date: date) -> pd.DataFrame:
        if not self.options.include_minute:
            return pd.DataFrame()
        payload = self._call(
            "daily_minute_bars",
            lambda: self.client.daily_minute_bars(
                symbol,
                trade_date=_yyyymmdd(base_date),
                input_hour=self.options.input_hour,
                include_past=True,
                market_div="J",
            ),
        )
        if isinstance(payload, Mapping) and payload.get("_kis_backfill_error"):
            return pd.DataFrame()
        return normalize_kis_minute_bars(symbol, payload if isinstance(payload, Mapping) else {}, trade_date=_yyyymmdd(base_date))

    def _flow(self, symbol: str, base_date: date) -> Dict[str, Any]:
        if not self.options.include_flow:
            return {}
        payload = self._call(
            "investor_flow_snapshot",
            lambda: self.client.investor_flow_snapshot(symbol, trade_date=_yyyymmdd(base_date), market_div="J"),
        )
        return dict(payload) if isinstance(payload, Mapping) and not payload.get("_kis_backfill_error") else {}

    def _vi(self, symbol: str, market: str, base_date: date) -> Dict[str, Any]:
        if not self.options.include_vi:
            return {}
        key = (str(market or "ALL").upper(), _yyyymmdd(base_date))
        if key not in self._vi_cache:
            payload = self._call("vi_status", lambda: self.client.vi_status(market=key[0], trade_date=key[1]))
            self._vi_cache[key] = dict(payload) if isinstance(payload, Mapping) and not payload.get("_kis_backfill_error") else {}
        return normalize_kis_vi_status(symbol, self._vi_cache.get(key) or {})

    def _news(self, symbol: str, base_date: date) -> Dict[str, Any]:
        if not self.options.include_news:
            return normalize_kis_news_titles(None)
        payload = self._call(
            "news_titles",
            lambda: self.client.news_titles(symbol=symbol, trade_date=_yyyymmdd(base_date), hour=""),
        )
        if isinstance(payload, Mapping) and payload.get("_kis_backfill_error"):
            return normalize_kis_news_titles(None)
        return normalize_kis_news_titles(payload if isinstance(payload, Mapping) else {})

    def _stock_info(self, symbol: str) -> Dict[str, Any]:
        if not self.options.include_stock_info:
            return {}
        code = normalize_kr_stock_code(symbol)
        if code not in self._stock_info_cache:
            payload = self._call("stock_info", lambda: self.client.stock_info(symbol))
            self._stock_info_cache[code] = (
                normalize_kis_stock_info(symbol, payload) if isinstance(payload, Mapping) and not payload.get("_kis_backfill_error") else {}
            )
        return dict(self._stock_info_cache.get(code) or {})

    def _financial(self, symbol: str) -> Dict[str, Any]:
        if not self.options.include_financial:
            return {}
        code = normalize_kr_stock_code(symbol)
        if code not in self._financial_cache:
            payload = self._call("financial_ratio", lambda: self.client.financial_ratio(symbol, market_div="J", div_cls_code="0"))
            self._financial_cache[code] = (
                normalize_kis_financial_ratio(symbol, payload)
                if isinstance(payload, Mapping) and not payload.get("_kis_backfill_error")
                else {}
            )
        return dict(self._financial_cache.get(code) or {})

    def _rank(self, symbol: str, market: str) -> Dict[str, Any]:
        if not self.options.include_current_rank:
            return {}
        market_key = str(market or "ALL").upper()
        if market_key not in self._rank_cache:
            volume = self._call("volume_rank_current", lambda: self.client.volume_rank(market=market_key, rank_by="trade_value"))
            fluctuation = self._call("fluctuation_rank_current", lambda: self.client.fluctuation_rank(market=market_key, sort="up"))
            power = self._call("volume_power_rank_current", lambda: self.client.volume_power_rank(market=market_key))
            self._rank_cache[market_key] = {
                "volume": dict(volume) if isinstance(volume, Mapping) and not volume.get("_kis_backfill_error") else {},
                "fluctuation": dict(fluctuation) if isinstance(fluctuation, Mapping) and not fluctuation.get("_kis_backfill_error") else {},
                "power": dict(power) if isinstance(power, Mapping) and not power.get("_kis_backfill_error") else {},
            }
        cached = self._rank_cache.get(market_key) or {}
        rank = normalize_kis_rank_membership(
            symbol,
            volume_rank_payload=cached.get("volume"),
            fluctuation_rank_payload=cached.get("fluctuation"),
            volume_power_rank_payload=cached.get("power"),
        )
        if rank:
            warnings = list(rank.get("warnings") or [])
            warnings.append("rank_membership_uses_current_kis_rank_not_historical")
            rank["warnings"] = sorted(set(warnings))
        return rank

    def build_sidecar_for_key(self, symbol: str, market: str, base_date: date, *, generated_at: str) -> Dict[str, Any]:
        daily_payload, daily_bars = self._daily_bars(symbol, base_date)
        if daily_bars.empty:
            return {
                "_skip_reason": "daily_bars_unavailable",
                "_warning": daily_payload.get("_kis_backfill_error") if isinstance(daily_payload, Mapping) else "",
            }
        value_traded = _extract_daily_value_traded(daily_payload, base_date) if isinstance(daily_payload, Mapping) else None
        quote_proxy = build_daily_quote_proxy(
            symbol=symbol,
            base_date=base_date,
            daily_bars=daily_bars,
            value_traded=value_traded,
        )
        if not quote_proxy:
            return {"_skip_reason": "quote_proxy_unavailable"}

        minute_bars = self._minute_bars(symbol, base_date)
        flow = self._flow(symbol, base_date)
        vi = self._vi(symbol, market, base_date)
        news = self._news(symbol, base_date)
        stock = self._stock_info(symbol)
        financial = self._financial(symbol)
        rank = self._rank(symbol, market)
        sidecar = build_kis_sidecar_snapshot(
            symbol,
            market=market,
            quote_snapshot=quote_proxy,
            daily_bars=daily_bars,
            minute_bars=minute_bars,
            investor_flow=flow,
            rank_membership=rank,
            vi_status=vi,
            news_titles=news.get("rows") if isinstance(news, Mapping) else [],
            news_titles_checked=bool(news.get("checked")) if isinstance(news, Mapping) else False,
            news_title_count=news.get("news_count") if isinstance(news, Mapping) else None,
            stock_info=stock,
            financial_ratio=financial,
            generated_at=generated_at,
        )
        warnings = list(sidecar.get("warnings") or [])
        warnings.extend(quote_proxy.get("warnings") or [])
        if not flow and self.options.include_flow:
            warnings.append("investor_flow_unavailable_no_dummy_written")
        if not stock and self.options.include_stock_info:
            warnings.append("stock_info_unavailable_no_dummy_written")
        if not financial and self.options.include_financial:
            warnings.append("financial_ratio_unavailable_no_dummy_written")
        if not self.options.include_current_rank:
            warnings.append("historical_rank_membership_not_backfilled_current_rank_disabled")
        if not self.options.include_minute:
            warnings.append("minute_ohlcv_not_backfilled_by_default")
        if not self.options.include_news:
            warnings.append("news_titles_not_backfilled_by_default")
        sidecar["warnings"] = sorted(set(str(item) for item in warnings if item))
        sidecar["feature_origin"] = "kis_openapi_backfill"
        sidecar["asof_policy"] = {
            "base_trade_date": base_date.isoformat(),
            "daily_ohlcv": "historical_kis_daily_bars_on_or_before_base_trade_date",
            "quote_snapshot": "reconstructed_from_historical_kis_daily_bar_close",
            "investor_flow": "kis_stock_investor_daily_for_base_trade_date_when_available",
            "rank_membership": "not_historical_unless_include_current_rank_is_used",
            "no_dummy_data": True,
        }
        return sidecar


def fetch_snapshot_rows(
    *,
    market: str,
    scan_mode: str,
    page_size: int,
    limit: int,
    min_id: int,
    max_id: int,
    base_date: str,
    min_base_date: str,
    max_base_date: str,
    overwrite: bool,
    only_outcome_available: bool,
    require_outcome_label: bool,
    skip_existing: bool = True,
) -> List[Dict[str, Any]]:
    _load_local_env()
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")

    rows: List[Dict[str, Any]] = []
    last_id = max(0, int(min_id or 0) - 1)
    columns = ",".join(SNAPSHOT_SELECT_COLUMNS)
    while True:
        take = max(1, int(page_size))
        query = db.client.table(TARGET_TABLE).select(columns).order("id").gt("id", last_id).limit(take)
        if max_id and int(max_id) > 0:
            query = query.lte("id", int(max_id))
        if market != "ALL":
            query = query.eq("market", market)
        if scan_mode != "ALL":
            query = query.eq("scan_mode", scan_mode)
        if base_date:
            query = query.eq("base_trade_date", base_date)
        if min_base_date:
            query = query.gte("base_trade_date", min_base_date)
        if max_base_date:
            query = query.lte("base_trade_date", max_base_date)
        if only_outcome_available:
            query = query.eq("outcome_available", True)
        batch = query.execute().data or []
        if not batch:
            break
        for row in batch:
            if skip_existing and not overwrite and _has_kis_sidecar(row):
                continue
            if require_outcome_label and not _has_outcome_label(row):
                continue
            if not str(row.get("ticker") or "").strip():
                continue
            if _base_trade_date(row) is None:
                continue
            rows.append(dict(row))
            if limit and len(rows) >= int(limit):
                return rows
        last_id = max(int(row.get("id") or last_id) for row in batch)
        if len(batch) < take:
            break
        if max_id and last_id >= int(max_id):
            break
    return rows


def summarize_candidate_rows(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows_list = [dict(row) for row in rows]
    by_date: Counter[str] = Counter()
    by_market: Counter[str] = Counter()
    by_role: Counter[str] = Counter()
    ids: List[int] = []
    for row in rows_list:
        base = _date_text(row.get("base_trade_date") or row.get("scanned_at")) or ""
        if base:
            by_date[base] += 1
        by_market[str(row.get("market") or "")] += 1
        by_role[str(row.get("row_role") or "")] += 1
        try:
            ids.append(int(row.get("id")))
        except Exception:
            pass
    return {
        "candidate_rows": len(rows_list),
        "unique_base_dates": len(by_date),
        "candidate_rows_by_base_date": dict(sorted(by_date.items())),
        "candidate_rows_by_market": dict(by_market),
        "candidate_rows_by_role": dict(by_role),
        "id_min": min(ids) if ids else None,
        "id_max": max(ids) if ids else None,
        "sample_candidate_rows": [
            {
                "id": row.get("id"),
                "snapshot_key": row.get("snapshot_key"),
                "ticker": row.get("ticker"),
                "market": row.get("market"),
                "row_role": row.get("row_role"),
                "base_trade_date": _date_text(row.get("base_trade_date") or row.get("scanned_at")),
                "has_outcome_label": _has_outcome_label(row),
                "has_kis_sidecar": _has_kis_sidecar(row),
            }
            for row in rows_list[:10]
        ],
    }


def verify_existing_sidecars(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows_list = [dict(row) for row in rows]
    sidecar_rows = [row for row in rows_list if _has_kis_sidecar(row)]
    sidecar_label_rows = [row for row in sidecar_rows if _has_outcome_label(row)]
    origins: Counter[str] = Counter()
    by_market: Counter[str] = Counter()
    by_role: Counter[str] = Counter()
    for row in sidecar_rows:
        sidecar = _json_dict(_json_dict(row.get("feature_snapshot")).get("kis_sidecar"))
        origins[str(sidecar.get("feature_origin") or "unknown")] += 1
        by_market[str(row.get("market") or "")] += 1
        by_role[str(row.get("row_role") or "")] += 1
    return {
        "checked_rows": len(rows_list),
        "kis_sidecar_rows": len(sidecar_rows),
        "kis_sidecar_outcome_label_rows": len(sidecar_label_rows),
        "kis_sidecar_origins": dict(origins),
        "kis_sidecar_by_market": dict(by_market),
        "kis_sidecar_by_role": dict(by_role),
        "sample_sidecar_rows": [
            {
                "id": row.get("id"),
                "snapshot_key": row.get("snapshot_key"),
                "ticker": row.get("ticker"),
                "market": row.get("market"),
                "row_role": row.get("row_role"),
                "base_trade_date": _date_text(row.get("base_trade_date") or row.get("scanned_at")),
                "has_outcome_label": _has_outcome_label(row),
            }
            for row in sidecar_rows[:5]
        ],
    }


def build_updates(
    rows: Iterable[Dict[str, Any]],
    *,
    client: Any,
    options: BackfillOptions,
) -> Dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    builder = KISSidecarBackfillBuilder(client, options)
    grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    skipped_existing = 0
    skipped_missing_date = 0
    skipped_missing_ticker = 0
    skipped_missing_label = 0
    for row in rows:
        if not options.overwrite and _has_kis_sidecar(row):
            skipped_existing += 1
            continue
        if options.require_outcome_label and all(key in row for key in OUTCOME_LABEL_COLUMNS) and not _has_outcome_label(row):
            skipped_missing_label += 1
            continue
        ticker = str(row.get("ticker") or "").strip()
        base = _base_trade_date(row)
        if not ticker:
            skipped_missing_ticker += 1
            continue
        if base is None:
            skipped_missing_date += 1
            continue
        market = str(row.get("market") or "ALL").upper()
        grouped[(normalize_kr_stock_code(ticker), market, base.isoformat())].append(row)

    updates: List[Dict[str, Any]] = []
    key_failures: Counter[str] = Counter()
    rows_by_market: Counter[str] = Counter()
    rows_by_role: Counter[str] = Counter()
    built_keys = 0
    for idx, ((symbol, market, base_text), key_rows) in enumerate(sorted(grouped.items()), start=1):
        base = date.fromisoformat(base_text)
        sidecar = builder.build_sidecar_for_key(symbol, market, base, generated_at=generated_at)
        skip_reason = str(sidecar.get("_skip_reason") or "").strip()
        if skip_reason:
            key_failures[skip_reason] += len(key_rows)
            warning = str(sidecar.get("_warning") or "").strip()
            if warning:
                key_failures[f"{skip_reason}:{warning[:80]}"] += len(key_rows)
            continue
        built_keys += 1
        for row in key_rows:
            feature_snapshot = _merge_kis_sidecar(row, sidecar, generated_at=generated_at)
            updates.append(
                _json_safe(
                    {
                        "id": row.get("id"),
                        "snapshot_key": row.get("snapshot_key"),
                        "run_id": row.get("run_id"),
                        "ticker": row.get("ticker"),
                        "market": row.get("market"),
                        "row_role": row.get("row_role"),
                        "base_trade_date": _date_text(row.get("base_trade_date") or row.get("scanned_at")),
                        "feature_snapshot": feature_snapshot,
                        "updated_at": generated_at,
                    }
                )
            )
            rows_by_market[str(row.get("market") or "")] += 1
            rows_by_role[str(row.get("row_role") or "")] += 1
        if idx % 25 == 0:
            print(f"[INFO] built KIS sidecars {idx}/{len(grouped)} keys, updates={len(updates)}", flush=True)

    return {
        "updates": updates,
        "candidate_rows": sum(len(items) for items in grouped.values()),
        "unique_keys": len(grouped),
        "sidecar_keys_built": built_keys,
        "skipped_existing_rows": skipped_existing,
        "skipped_missing_date_rows": skipped_missing_date,
        "skipped_missing_ticker_rows": skipped_missing_ticker,
        "skipped_missing_outcome_label_rows": skipped_missing_label,
        "rows_by_market": dict(rows_by_market),
        "rows_by_role": dict(rows_by_role),
        "key_failures": dict(key_failures),
        "kis_call_counts": dict(builder.call_counts),
        "kis_failures": dict(builder.failures),
        "generated_at": generated_at,
    }


def write_updates(updates: List[Dict[str, Any]], *, batch_size: int) -> int:
    if not updates:
        return 0
    _load_local_env()
    from modules.db_manager import DBManager

    db = DBManager()
    if not getattr(db, "client", None):
        raise SystemExit("Supabase client unavailable.")

    written = 0
    for item in updates:
        row_id = item.get("id")
        if row_id is None:
            continue
        payload = {
            "feature_snapshot": item.get("feature_snapshot"),
            "updated_at": item.get("updated_at") or datetime.now(timezone.utc).isoformat(),
        }
        try:
            db.client.table(TARGET_TABLE).update(payload).eq("id", row_id).execute()
        except Exception:
            db.client.table(TARGET_TABLE).update({"feature_snapshot": payload["feature_snapshot"]}).eq("id", row_id).execute()
        written += 1
        if written % max(1, int(batch_size)) == 0 or written == len(updates):
            print(f"[INFO] updated KIS sidecars {written}/{len(updates)}", flush=True)
    return written


def _write_report(report: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(report), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    md_path = path.with_suffix(".md")
    summary = report.get("summary") if isinstance(report.get("summary"), Mapping) else {}
    lines = [
        "# KIS sidecar scan_universe backfill",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dry_run: `{report.get('dry_run')}`",
        f"- fetched_rows: `{summary.get('fetched_rows')}`",
        f"- candidate_rows: `{summary.get('candidate_rows')}`",
        f"- unique_keys: `{summary.get('unique_keys')}`",
        f"- sidecar_keys_built: `{summary.get('sidecar_keys_built')}`",
        f"- updates_built: `{summary.get('updates_built')}`",
        f"- rows_written: `{summary.get('rows_written')}`",
        f"- no_dummy_data: `{summary.get('no_dummy_data')}`",
        "",
        "## Limitations",
        "",
        "- Historical quote fields are reconstructed from KIS historical daily bars, not from a live quote endpoint.",
        "- Historical rank membership is not backfilled unless `--include-current-rank` is explicitly used.",
        "- Rows with unavailable KIS daily bars are skipped instead of receiving placeholder values.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=["ALL", "KOSPI", "KOSDAQ"], default="ALL")
    parser.add_argument("--scan-mode", choices=["ALL", "SWING", "INTRADAY"], default="ALL")
    parser.add_argument("--limit", type=int, default=0, help="Maximum eligible rows to process; 0 means all.")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--min-id", type=int, default=0, help="Inclusive lower id bound for chunked Supabase reads.")
    parser.add_argument("--max-id", type=int, default=0, help="Inclusive upper id bound for chunked Supabase reads.")
    parser.add_argument("--base-date", default="", help="Exact base_trade_date filter, YYYY-MM-DD.")
    parser.add_argument("--min-base-date", default="", help="Inclusive base_trade_date lower bound, YYYY-MM-DD.")
    parser.add_argument("--max-base-date", default="", help="Inclusive base_trade_date upper bound, YYYY-MM-DD.")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--daily-lookback-days", type=int, default=140)
    parser.add_argument("--only-outcome-available", action="store_true")
    parser.add_argument(
        "--require-outcome-label",
        action="store_true",
        help="Only process rows with readiness-compatible 5D outcome labels.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--plan-only", action="store_true", help="Only summarize eligible candidate rows; no KIS calls or writes.")
    parser.add_argument("--verify-only", action="store_true", help="Only count existing KIS sidecars in the selected rows.")
    parser.add_argument("--live", action="store_true", help="Set KIS_ENABLE_LIVE_CALLS=1 for this run.")
    parser.add_argument("--kis-timeout-sec", type=float, default=8.0)
    parser.add_argument("--sleep-sec", type=float, default=0.0)
    parser.add_argument("--input-hour", default="153000")
    parser.add_argument("--include-minute", action="store_true")
    parser.add_argument("--include-news", action="store_true")
    parser.add_argument("--include-current-rank", action="store_true")
    parser.add_argument("--no-flow", action="store_true")
    parser.add_argument("--no-vi", action="store_true")
    parser.add_argument("--no-stock-info", action="store_true")
    parser.add_argument("--no-financial", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_local_env()
    if args.live:
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"

    rows = fetch_snapshot_rows(
        market=args.market,
        scan_mode=args.scan_mode,
        page_size=args.page_size,
        limit=args.limit,
        min_id=args.min_id,
        max_id=args.max_id,
        base_date=_date_text(args.base_date) or "",
        min_base_date=_date_text(args.min_base_date) or "",
        max_base_date=_date_text(args.max_base_date) or "",
        overwrite=args.overwrite,
        only_outcome_available=args.only_outcome_available,
        require_outcome_label=args.require_outcome_label,
        skip_existing=not args.verify_only,
    )
    if args.plan_only:
        planning = summarize_candidate_rows(rows)
        report = {
            "contract_version": BACKFILL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": True,
            "plan_only": True,
            "args": {
                "market": args.market,
                "scan_mode": args.scan_mode,
                "limit": args.limit,
                "min_id": args.min_id,
                "max_id": args.max_id,
                "base_date": _date_text(args.base_date) or "",
                "min_base_date": _date_text(args.min_base_date) or "",
                "max_base_date": _date_text(args.max_base_date) or "",
                "only_outcome_available": bool(args.only_outcome_available),
                "require_outcome_label": bool(args.require_outcome_label),
            },
            "summary": {
                **planning,
                "fetched_rows": len(rows),
                "rows_written": 0,
                "no_dummy_data": True,
            },
        }
        _write_report(report, args.output)
        print(json.dumps(_json_safe(report["summary"]), ensure_ascii=False, indent=2, sort_keys=True))
        print(f"[INFO] wrote report {args.output}")
        return 0

    if args.verify_only:
        verification = verify_existing_sidecars(rows)
        report = {
            "contract_version": BACKFILL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": True,
            "verify_only": True,
            "args": {
                "market": args.market,
                "scan_mode": args.scan_mode,
                "limit": args.limit,
                "min_id": args.min_id,
                "max_id": args.max_id,
                "base_date": _date_text(args.base_date) or "",
                "min_base_date": _date_text(args.min_base_date) or "",
                "max_base_date": _date_text(args.max_base_date) or "",
                "only_outcome_available": bool(args.only_outcome_available),
                "require_outcome_label": bool(args.require_outcome_label),
            },
            "summary": {
                **verification,
                "fetched_rows": len(rows),
                "rows_written": 0,
                "no_dummy_data": True,
            },
        }
        _write_report(report, args.output)
        print(json.dumps(_json_safe(report["summary"]), ensure_ascii=False, indent=2, sort_keys=True))
        print(f"[INFO] wrote report {args.output}")
        return 0

    options = BackfillOptions(
        daily_lookback_days=args.daily_lookback_days,
        include_flow=not args.no_flow,
        include_minute=bool(args.include_minute),
        include_vi=not args.no_vi,
        include_news=bool(args.include_news),
        include_stock_info=not args.no_stock_info,
        include_financial=not args.no_financial,
        include_current_rank=bool(args.include_current_rank),
        input_hour=str(args.input_hour or "153000"),
        sleep_sec=max(0.0, float(args.sleep_sec or 0.0)),
        overwrite=bool(args.overwrite),
        require_outcome_label=bool(args.require_outcome_label),
    )
    client = KISOpenAPIClient(timeout=float(args.kis_timeout_sec or 8.0))
    built = build_updates(rows, client=client, options=options)
    updates = built.pop("updates")
    rows_written = 0 if args.dry_run else write_updates(updates, batch_size=args.batch_size)
    report = {
        "contract_version": BACKFILL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": bool(args.dry_run),
        "args": {
            "market": args.market,
            "scan_mode": args.scan_mode,
            "limit": args.limit,
            "min_id": args.min_id,
            "max_id": args.max_id,
            "base_date": _date_text(args.base_date) or "",
            "min_base_date": _date_text(args.min_base_date) or "",
            "max_base_date": _date_text(args.max_base_date) or "",
            "only_outcome_available": bool(args.only_outcome_available),
            "require_outcome_label": bool(args.require_outcome_label),
            "overwrite": bool(args.overwrite),
            "include_flow": options.include_flow,
            "include_minute": options.include_minute,
            "include_vi": options.include_vi,
            "include_news": options.include_news,
            "include_stock_info": options.include_stock_info,
            "include_financial": options.include_financial,
            "include_current_rank": options.include_current_rank,
        },
        "summary": {
            **built,
            "fetched_rows": len(rows),
            "updates_built": len(updates),
            "rows_written": rows_written,
            "no_dummy_data": True,
        },
    }
    _write_report(report, args.output)
    print(json.dumps(_json_safe(report["summary"]), ensure_ascii=False, indent=2, sort_keys=True))
    print(f"[INFO] wrote report {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
