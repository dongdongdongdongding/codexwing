#!/usr/bin/env python3
"""Backfill KIS ticker-period sidecar features into historical prepared caches.

This tool fills only real KIS-backed values:
- investor flow is cached by ticker and joined by exact trading date
- financial ratios are cached by ticker and joined only when statement period
  end date is on or before the base trade date
- news titles are cached by exact date and filtered per ticker/name for that date
"""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.kis_openapi import KISConfig, KISOpenAPIClient, normalize_kr_stock_code
from modules.kis_operational_adapter import normalize_kis_flow_for_whale_contract, normalize_kis_news_titles
from multi_agent.tools.augment_kis_historical_proxy_with_sidecar_cache import (
    _present_mask,
    _round,
    _scope,
)


REPORT_VERSION = "kis_ticker_period_sidecar_backfill_v1"
DEFAULT_CACHE_DIR = ROOT / "runtime_state/long_term/kis_ticker_period_sidecar"
DEFAULT_OUTPUT_JSON = ROOT / "runtime_state/reports/learning/kis_ticker_period_sidecar_backfill_20260614.json"
DEFAULT_INPUT_CACHES = (
    "KOSPI="
    + str(
        ROOT
        / "runtime_state/reports/learning/kis_historical_universe_fullrank_actual_augmented_prepared_kospi_20260101_20260610.pkl"
    ),
    "KOSDAQ="
    + str(
        ROOT
        / "runtime_state/reports/learning/kis_historical_universe_fullrank_actual_augmented_prepared_kosdaq_20260101_20260610.pkl"
    ),
)
DEFAULT_OUTPUT_CACHES = (
    "KOSPI="
    + str(
        ROOT
        / "runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kospi_20260101_20260610.pkl"
    ),
    "KOSDAQ="
    + str(
        ROOT
        / "runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kosdaq_20260101_20260610.pkl"
    ),
)

FLOW_FEATURE_COLUMNS = (
    "kis_whale_score",
    "kis_foreigner_1d",
    "kis_institution_1d",
    "kis_retail_1d",
    "kis_whale_flow_3d",
    "kis_whale_flow_10d",
    "flow_source",
    "flow_unit",
    "flow_asof",
    "kis_sidecar_coverage_investor_flow",
)
FINANCIAL_FEATURE_COLUMNS = (
    "kis_financial_statement_period",
    "kis_financial_revenue_growth_rate",
    "kis_financial_operating_profit_margin",
    "kis_financial_net_income_margin",
    "kis_financial_roe",
    "kis_financial_eps",
    "kis_financial_bps",
    "kis_financial_per",
    "kis_financial_pbr",
    "kis_financial_debt_ratio",
    "kis_financial_current_ratio",
    "kis_financial_reserve_ratio",
    "kis_sidecar_coverage_financial_ratio",
    "kis_sidecar_coverage_financial_style",
)
NEWS_FEATURE_COLUMNS = (
    "kis_news_title_count",
    "kis_news_raw_title_count",
    "kis_news_rows_filtered_out_count",
    "kis_news_source_scope_confidence",
    "kis_news_source_scope_ambiguous",
    "kis_news_promotion_blocked",
    "kis_news_source_scope",
    "kis_sidecar_coverage_news_titles",
)
BACKFILL_FEATURE_COLUMNS = FLOW_FEATURE_COLUMNS + FINANCIAL_FEATURE_COLUMNS + NEWS_FEATURE_COLUMNS
FINANCIAL_VALUE_COLUMNS = tuple(col for col in FINANCIAL_FEATURE_COLUMNS if col.startswith("kis_financial_"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return round(number, 6)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def _load_local_env() -> None:
    for env_path in (ROOT / ".env", ROOT / ".env.local"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            key, value = text.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _output_rows(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    for key in ("output2", "output", "Output", "output1"):
        value = payload.get(key)
        if isinstance(value, list):
            return [dict(row) for row in value if isinstance(row, Mapping)]
    value = payload.get("output")
    if isinstance(value, Mapping):
        return [dict(value)]
    return []


def _first_present(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        text = str(value).strip().replace(",", "").replace("%", "")
        if not text:
            return None
        number = float(text)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _date_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return pd.to_datetime(text).strftime("%Y%m%d")
    except Exception:
        return ""


def _date_iso(value: Any) -> str:
    key = _date_key(value)
    if not key:
        return ""
    return f"{key[:4]}-{key[4:6]}-{key[6:8]}"


def _normalize_ticker(value: Any) -> str:
    return normalize_kr_stock_code(str(value or "").strip())


def _parse_market_path(value: str) -> Tuple[str, Path]:
    if "=" not in value:
        raise ValueError(f"expected MARKET=PATH, got {value!r}")
    market, raw_path = value.split("=", 1)
    market = market.strip().upper()
    if not market:
        raise ValueError(f"empty market in {value!r}")
    return market, Path(raw_path)


def _date_column(frame: pd.DataFrame) -> str:
    for col in ("base_trade_date", "trade_date", "date"):
        if col in frame.columns:
            return col
    raise ValueError("frame has no base_trade_date/trade_date/date")


def _ticker_universe(frames: Mapping[str, pd.DataFrame], *, max_tickers: int = 0) -> pd.DataFrame:
    rows: List[pd.DataFrame] = []
    for market, frame in frames.items():
        if "ticker" not in frame.columns:
            raise ValueError(f"{market} frame has no ticker column")
        date_col = _date_column(frame)
        cols = ["ticker", date_col]
        if "stock_name" in frame.columns:
            cols.append("stock_name")
        part = frame.loc[:, cols].copy()
        part["market"] = market.upper()
        part["__ticker"] = part["ticker"].map(_normalize_ticker)
        part["__date"] = part[date_col].map(_date_key)
        part["stock_name"] = part["stock_name"] if "stock_name" in part.columns else ""
        rows.append(part.loc[part["__ticker"].ne("") & part["__date"].ne(""), ["market", "__ticker", "__date", "stock_name"]])
    universe = pd.concat(rows, ignore_index=True).drop_duplicates(["market", "__ticker", "__date"])
    if max_tickers and max_tickers > 0:
        keep = set(sorted(universe["__ticker"].dropna().unique().tolist())[: int(max_tickers)])
        universe = universe[universe["__ticker"].isin(keep)].copy()
    return universe


def _cache_file(cache_dir: Path, family: str, key: str) -> Path:
    safe = str(key).replace("/", "_").replace(":", "_")
    return cache_dir / family / f"{safe}.json"


def _call_with_cache(
    *,
    path: Path,
    refresh: bool,
    fetch_fn,
    label: str,
    call_counts: Counter[str],
    failures: Counter[str],
    sleep_sec: float,
) -> Dict[str, Any]:
    if path.exists() and not refresh:
        cached = _read_json(path)
        if cached:
            return cached
    call_counts[label] += 1
    try:
        payload = fetch_fn()
        out = {
            "source": "kis_openapi",
            "source_status": "ok",
            "fetched_at": _utc_now(),
            "payload": payload,
        }
    except Exception as exc:
        failures[f"{label}:{type(exc).__name__}"] += 1
        out = {
            "source": "kis_openapi",
            "source_status": "error",
            "fetched_at": _utc_now(),
            "error": str(exc),
            "payload": {},
        }
    finally:
        if sleep_sec > 0:
            time.sleep(float(sleep_sec))
    _write_json(path, out)
    return out


def fetch_flow_cache(
    client: KISOpenAPIClient,
    ticker: str,
    *,
    min_date: str,
    max_date: str,
    cache_dir: Path,
    refresh: bool,
    max_chunks: int,
    sleep_sec: float,
    call_counts: Counter[str],
    failures: Counter[str],
) -> Dict[str, Any]:
    path = _cache_file(cache_dir, "flow", ticker)
    if path.exists() and not refresh:
        cached = _read_json(path)
        if cached:
            return cached

    min_required = (pd.to_datetime(min_date) - pd.Timedelta(days=30)).strftime("%Y%m%d")
    cursor = max_date
    chunks: List[Dict[str, Any]] = []
    seen_earliest: set[str] = set()
    for _idx in range(max(1, int(max_chunks or 1))):
        chunk = _call_with_cache(
            path=cache_dir / "flow_chunks" / ticker / f"{cursor}.json",
            refresh=refresh,
            fetch_fn=lambda cursor=cursor: client.investor_trading_daily(ticker, trade_date=cursor, market_div="J"),
            label="stock_investor_daily",
            call_counts=call_counts,
            failures=failures,
            sleep_sec=sleep_sec,
        )
        chunks.append(chunk)
        if chunk.get("source_status") != "ok":
            break
        rows = _output_rows(chunk.get("payload") if isinstance(chunk.get("payload"), Mapping) else {})
        dates = sorted({_date_key(_first_present(row, "stck_bsop_date", "bsop_date", "date")) for row in rows if _date_key(_first_present(row, "stck_bsop_date", "bsop_date", "date"))})
        if not dates:
            break
        earliest = dates[0]
        if earliest in seen_earliest:
            break
        seen_earliest.add(earliest)
        if earliest <= min_required:
            break
        cursor = (pd.to_datetime(earliest) - pd.Timedelta(days=1)).strftime("%Y%m%d")

    out = {
        "source": "kis_openapi",
        "source_status": "ok" if any(chunk.get("source_status") == "ok" for chunk in chunks) else "error",
        "fetched_at": _utc_now(),
        "ticker": ticker,
        "min_required_date": min_required,
        "max_date": max_date,
        "chunks": chunks,
    }
    _write_json(path, out)
    return out


def _row_date(row: Mapping[str, Any]) -> str:
    return _date_key(_first_present(row, "stck_bsop_date", "bsop_date", "date"))


def _row_flow_value(row: Mapping[str, Any], keys: Sequence[str]) -> float | None:
    for key in keys:
        value = _safe_float(row.get(key))
        if value is not None:
            return value
    return None


def build_flow_lookup(cache: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw_rows: List[Dict[str, Any]] = []
    for chunk in cache.get("chunks") or []:
        if not isinstance(chunk, Mapping) or chunk.get("source_status") != "ok":
            continue
        payload = chunk.get("payload") if isinstance(chunk.get("payload"), Mapping) else {}
        raw_rows.extend(_output_rows(payload))

    deduped: Dict[str, Dict[str, Any]] = {}
    for row in raw_rows:
        key = _row_date(row)
        if key and key not in deduped:
            deduped[key] = row
    rows = [deduped[key] for key in sorted(deduped.keys(), reverse=True)]
    amount_keys = {
        "foreigner": ("frgn_ntby_tr_pbmn", "frgn_ntby_pbmn"),
        "institution": ("orgn_ntby_tr_pbmn",),
        "retail": ("prsn_ntby_tr_pbmn",),
    }
    qty_keys = {
        "foreigner": ("frgn_ntby_qty",),
        "institution": ("orgn_ntby_qty",),
        "retail": ("prsn_ntby_qty",),
    }
    use_amount = any(_row_flow_value(row, keys) is not None for row in rows for keys in amount_keys.values())

    def side_value(row: Mapping[str, Any], side: str) -> float | None:
        return _row_flow_value(row, amount_keys[side] if use_amount else qty_keys[side])

    lookup: Dict[str, Dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        date_key = _row_date(row)
        if not date_key:
            continue

        def total(side: str, take: int) -> float | None:
            found = False
            value = 0.0
            for sub in rows[idx : idx + take]:
                part = side_value(sub, side)
                if part is None:
                    continue
                value += float(part)
                found = True
            return value if found else None

        f1, i1, r1 = total("foreigner", 1), total("institution", 1), total("retail", 1)
        f3, i3, r3 = total("foreigner", 3), total("institution", 3), total("retail", 3)
        f10, i10, r10 = total("foreigner", 10), total("institution", 10), total("retail", 10)
        flow = {
            "source": "kis_openapi",
            "source_status": "ok",
            "flow_unit": "KRW" if use_amount else "shares",
            "flow_asof": date_key,
            "foreigner_1d": f1,
            "institution_1d": i1,
            "retail_1d": r1,
            "foreigner_3d": f3,
            "institution_3d": i3,
            "retail_3d": r3,
            "foreigner_10d": f10,
            "institution_10d": i10,
            "retail_10d": r10,
            "whale_flow_1d": (f1 + i1) if f1 is not None and i1 is not None else None,
            "whale_flow_3d": (f3 + i3) if f3 is not None and i3 is not None else None,
            "whale_flow_10d": (f10 + i10) if f10 is not None and i10 is not None else None,
        }
        whale = normalize_kis_flow_for_whale_contract(flow)
        if not whale.get("valid"):
            continue
        lookup[date_key] = {
            "kis_whale_score": whale.get("whale_score"),
            "kis_foreigner_1d": whale.get("foreigner_1d"),
            "kis_institution_1d": whale.get("institution_1d"),
            "kis_retail_1d": whale.get("retail_1d"),
            "kis_whale_flow_3d": whale.get("whale_flow_3d"),
            "kis_whale_flow_10d": whale.get("whale_flow_10d"),
            "flow_source": "kis_openapi_period_cache",
            "flow_unit": whale.get("flow_unit"),
            "flow_asof": date_key,
            "kis_sidecar_coverage_investor_flow": 1.0,
        }
    return lookup


def fetch_financial_cache(
    client: KISOpenAPIClient,
    ticker: str,
    *,
    cache_dir: Path,
    refresh: bool,
    sleep_sec: float,
    call_counts: Counter[str],
    failures: Counter[str],
) -> Dict[str, Any]:
    return _call_with_cache(
        path=_cache_file(cache_dir, "financial", ticker),
        refresh=refresh,
        fetch_fn=lambda: client.financial_ratio(ticker, market_div="J", div_cls_code="0"),
        label="financial_ratio",
        call_counts=call_counts,
        failures=failures,
        sleep_sec=sleep_sec,
    )


def _statement_period_end(value: Any) -> pd.Timestamp | None:
    text = str(value or "").strip()
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 6:
        period = digits[:6]
        try:
            return pd.Period(period, freq="M").end_time.normalize()
        except Exception:
            return None
    return None


def _financial_row_features(ticker: str, row: Mapping[str, Any]) -> Dict[str, Any]:
    period = _first_present(row, "stac_yymm", "stac_month", "statement_period")
    return {
        "ticker": ticker,
        "statement_period": str(period or "").strip(),
        "statement_period_end": _statement_period_end(period),
        "kis_financial_statement_period": str(period or "").strip() or None,
        "kis_financial_revenue_growth_rate": _safe_float(_first_present(row, "grs", "revenue_growth_rate", "sale_inrt")),
        "kis_financial_operating_profit_margin": _safe_float(_first_present(row, "bsop_prfi_inrt", "operating_profit_margin")),
        "kis_financial_net_income_margin": _safe_float(_first_present(row, "ntin_inrt", "net_income_margin")),
        "kis_financial_roe": _safe_float(_first_present(row, "roe_val", "roe", "self_cptl_ntin_inrt")),
        "kis_financial_eps": _safe_float(_first_present(row, "eps", "eps_val")),
        "kis_financial_bps": _safe_float(_first_present(row, "bps", "bps_val")),
        "kis_financial_per": _safe_float(_first_present(row, "per", "per_val")),
        "kis_financial_pbr": _safe_float(_first_present(row, "pbr", "pbr_val")),
        "kis_financial_debt_ratio": _safe_float(_first_present(row, "lblt_rate", "debt_ratio")),
        "kis_financial_current_ratio": _safe_float(_first_present(row, "crnt_rate", "current_ratio")),
        "kis_financial_reserve_ratio": _safe_float(_first_present(row, "rsrv_rate", "reserve_ratio")),
    }


def build_financial_lookup(cache: Mapping[str, Any], ticker: str) -> List[Dict[str, Any]]:
    if cache.get("source_status") != "ok":
        return []
    payload = cache.get("payload") if isinstance(cache.get("payload"), Mapping) else {}
    rows = []
    for raw in _output_rows(payload):
        features = _financial_row_features(ticker, raw)
        if features.get("statement_period_end") is None:
            continue
        if not any(features.get(col) is not None for col in FINANCIAL_VALUE_COLUMNS if col != "kis_financial_statement_period"):
            continue
        features["kis_sidecar_coverage_financial_ratio"] = 1.0
        features["kis_sidecar_coverage_financial_style"] = 1.0
        rows.append(features)
    rows.sort(key=lambda item: item["statement_period_end"])
    return rows


def financial_for_date(rows: Sequence[Mapping[str, Any]], base_date: str) -> Dict[str, Any]:
    base_ts = pd.to_datetime(base_date)
    candidate: Mapping[str, Any] | None = None
    for row in rows:
        period_end = row.get("statement_period_end")
        if period_end is not None and pd.Timestamp(period_end) <= base_ts:
            candidate = row
    if candidate is None:
        return {}
    return {col: candidate.get(col) for col in FINANCIAL_FEATURE_COLUMNS if col in candidate}


def fetch_news_cache(
    client: KISOpenAPIClient,
    date_key: str,
    *,
    cache_dir: Path,
    refresh: bool,
    sleep_sec: float,
    call_counts: Counter[str],
    failures: Counter[str],
) -> Dict[str, Any]:
    return _call_with_cache(
        path=_cache_file(cache_dir, "news_by_date", date_key),
        refresh=refresh,
        fetch_fn=lambda: client.news_titles(symbol="", trade_date=date_key, hour=""),
        label="news_titles_by_date",
        call_counts=call_counts,
        failures=failures,
        sleep_sec=sleep_sec,
    )


def news_features_for_ticker(cache: Mapping[str, Any], *, ticker: str, stock_name: str) -> Dict[str, Any]:
    if cache.get("source_status") != "ok":
        return {}
    payload = cache.get("payload") if isinstance(cache.get("payload"), Mapping) else {}
    normalized = normalize_kis_news_titles(payload, symbol=ticker, stock_name=stock_name)
    if not normalized.get("checked"):
        return {}
    return {
        "kis_news_title_count": normalized.get("news_count"),
        "kis_news_raw_title_count": normalized.get("raw_news_count"),
        "kis_news_rows_filtered_out_count": normalized.get("rows_filtered_out_count"),
        "kis_news_source_scope_confidence": normalized.get("source_scope_confidence"),
        "kis_news_source_scope_ambiguous": 1.0 if normalized.get("promotion_blocked") else 0.0,
        "kis_news_promotion_blocked": 1.0 if normalized.get("promotion_blocked") else 0.0,
        "kis_news_source_scope": normalized.get("source_scope"),
        "kis_sidecar_coverage_news_titles": 1.0,
    }


def _future_financial_mask(frame: pd.DataFrame) -> pd.Series:
    if "kis_financial_statement_period" not in frame.columns:
        return pd.Series(False, index=frame.index)
    date_col = _date_column(frame)
    periods = frame["kis_financial_statement_period"].map(_statement_period_end)
    dates = pd.to_datetime(frame[date_col], errors="coerce")
    mask = []
    for period_end, base in zip(periods.tolist(), dates.tolist()):
        if period_end is None or pd.isna(base):
            mask.append(False)
        else:
            mask.append(pd.Timestamp(period_end) > pd.Timestamp(base))
    return pd.Series(mask, index=frame.index)


def _target_coverage_delta(before: pd.DataFrame, after: pd.DataFrame) -> Dict[str, Any]:
    families = {
        "flow": FLOW_FEATURE_COLUMNS,
        "financial": FINANCIAL_FEATURE_COLUMNS,
        "news": NEWS_FEATURE_COLUMNS,
    }
    out: Dict[str, Any] = {}
    for family, columns in families.items():
        rows: List[Dict[str, Any]] = []
        for col in columns:
            if col not in before.columns and col not in after.columns:
                continue
            before_pct = _round(float(_present_mask(before[col], col).mean() * 100.0), 3) if col in before.columns and not before.empty else 0.0
            after_pct = _round(float(_present_mask(after[col], col).mean() * 100.0), 3) if col in after.columns and not after.empty else 0.0
            rows.append(
                {
                    "feature": col,
                    "before_present_pct": before_pct,
                    "after_present_pct": after_pct,
                    "delta_pct": _round(float(after_pct or 0.0) - float(before_pct or 0.0), 3),
                }
            )
        rows.sort(key=lambda item: float(item.get("delta_pct") or 0.0), reverse=True)
        positive = [row for row in rows if float(row.get("delta_pct") or 0.0) > 0]
        out[family] = {
            "features_improved": int(len(positive)),
            "top_deltas": rows[:15],
        }
    return out


def _fill_features(
    frame: pd.DataFrame,
    *,
    market: str,
    flow_lookup: Mapping[Tuple[str, str], Mapping[str, Any]],
    financial_lookup: Mapping[Tuple[str, str], Mapping[str, Any]],
    news_lookup: Mapping[Tuple[str, str], Mapping[str, Any]],
    generated_at: str,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    out = frame.copy()
    before = out.copy()
    date_col = _date_column(out)
    out["__ticker"] = out["ticker"].map(_normalize_ticker)
    out["__date"] = out[date_col].map(_date_key)

    for col in BACKFILL_FEATURE_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan

    future_financial = _future_financial_mask(out)
    future_financial_cleared = int(future_financial.sum())
    if future_financial_cleared:
        for col in FINANCIAL_FEATURE_COLUMNS:
            if col in out.columns:
                out.loc[future_financial, col] = np.nan

    source_tags: List[List[str]] = [[] for _ in range(len(out))]
    family_augmented = {
        "flow": pd.Series(False, index=out.index),
        "financial": pd.Series(False, index=out.index),
        "news": pd.Series(False, index=out.index),
    }
    fill_counts: MutableMapping[str, int] = Counter()

    families = (
        ("flow", FLOW_FEATURE_COLUMNS, flow_lookup, "kis_flow_period_cache"),
        ("financial", FINANCIAL_FEATURE_COLUMNS, financial_lookup, "kis_financial_period_cache"),
        ("news", NEWS_FEATURE_COLUMNS, news_lookup, "kis_news_date_cache_exact_date"),
    )
    keys = list(zip(out["__ticker"].tolist(), out["__date"].tolist()))
    for family, columns, lookup, source in families:
        for row_pos, (idx, key) in enumerate(zip(out.index, keys)):
            values = lookup.get(key)
            if not values:
                continue
            row_filled = False
            for col in columns:
                if col not in values:
                    continue
                value = values.get(col)
                if value is None:
                    continue
                current = out.at[idx, col] if col in out.columns else np.nan
                before_present = _present_mask(pd.Series([current]), col).iloc[0]
                if before_present:
                    continue
                out.at[idx, col] = value
                fill_counts[col] += 1
                row_filled = True
            if row_filled:
                family_augmented[family].at[idx] = True
                source_tags[row_pos].append(source)

    augmented = pd.Series(False, index=out.index)
    for values in family_augmented.values():
        augmented = augmented | values

    out["kis_period_sidecar_augmented"] = augmented.astype(int)
    out["kis_period_sidecar_source"] = ["|".join(tags) if tags else None for tags in source_tags]
    out["kis_period_sidecar_augmented_at"] = np.where(augmented, generated_at, None)
    out["kis_period_sidecar_no_dummy_data"] = np.where(augmented, True, None)
    out["kis_period_sidecar_leakage_policy"] = np.where(
        augmented,
        "flow exact trading date; financial statement period end <= base date; news exact date only; fill missing cells only",
        None,
    )
    for family, values in family_augmented.items():
        out[f"kis_period_sidecar_{family}_augmented"] = values.astype(int)

    out = out.drop(columns=["__ticker", "__date"])
    before_for_delta = before.drop(columns=[col for col in before.columns if col.startswith("__")], errors="ignore")
    summary = {
        "market": market.upper(),
        "input_scope": _scope(frame),
        "output_scope": _scope(out),
        "augmented_rows": int(augmented.sum()),
        "augmented_row_pct": _round(float(augmented.mean() * 100.0), 3) if len(augmented) else 0.0,
        "flow_augmented_rows": int(family_augmented["flow"].sum()),
        "financial_augmented_rows": int(family_augmented["financial"].sum()),
        "news_augmented_rows": int(family_augmented["news"].sum()),
        "future_financial_rows_cleared": future_financial_cleared,
        "no_dummy_data": True,
        "leakage_policy": "no forward-fill; financial period end must be <= base date; news exact date only",
        "feature_fill_counts_top": sorted(
            [{"feature": key, "filled_missing_values": int(value)} for key, value in fill_counts.items() if value > 0],
            key=lambda item: int(item["filled_missing_values"]),
            reverse=True,
        )[:50],
        "coverage_delta": _target_coverage_delta(before_for_delta, out),
    }
    return out, summary


def build_backfill(
    *,
    input_caches: Mapping[str, Path],
    output_caches: Mapping[str, Path],
    cache_dir: Path,
    live: bool,
    include_flow: bool,
    include_financial: bool,
    include_news: bool,
    refresh_flow: bool,
    refresh_financial: bool,
    refresh_news: bool,
    max_tickers: int,
    flow_max_chunks: int,
    sleep_sec: float,
    timeout: float,
) -> Dict[str, Any]:
    _load_local_env()
    os.environ.setdefault("KIS_MODE", "real")
    if live:
        os.environ["KIS_ENABLE_LIVE_CALLS"] = "1"
    client = KISOpenAPIClient(config=KISConfig.from_env(), timeout=timeout)
    generated_at = _utc_now()
    frames = {market: pd.read_pickle(path) for market, path in input_caches.items()}
    universe = _ticker_universe(frames, max_tickers=max_tickers)
    min_date = str(universe["__date"].min()) if not universe.empty else ""
    max_date = str(universe["__date"].max()) if not universe.empty else ""
    tickers = sorted(universe["__ticker"].dropna().unique().tolist())
    dates = sorted(universe["__date"].dropna().unique().tolist())
    if max_tickers and max_tickers > 0:
        selected = set(tickers)
        frames = {
            market: frame.loc[frame["ticker"].map(_normalize_ticker).isin(selected)].copy()
            for market, frame in frames.items()
        }
    call_counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()

    flow_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    financial_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    news_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

    if include_flow:
        for idx, ticker in enumerate(tickers, start=1):
            cache = fetch_flow_cache(
                client,
                ticker,
                min_date=min_date,
                max_date=max_date,
                cache_dir=cache_dir,
                refresh=refresh_flow,
                max_chunks=flow_max_chunks,
                sleep_sec=sleep_sec,
                call_counts=call_counts,
                failures=failures,
            )
            for date_key, values in build_flow_lookup(cache).items():
                flow_by_key[(ticker, date_key)] = values
            if idx % 100 == 0 or idx == len(tickers):
                print(f"[INFO] flow {idx}/{len(tickers)} tickers lookup_rows={len(flow_by_key)} failures={sum(failures.values())}", flush=True)

    financial_rows_by_ticker: Dict[str, List[Dict[str, Any]]] = {}
    if include_financial:
        for idx, ticker in enumerate(tickers, start=1):
            cache = fetch_financial_cache(
                client,
                ticker,
                cache_dir=cache_dir,
                refresh=refresh_financial,
                sleep_sec=sleep_sec,
                call_counts=call_counts,
                failures=failures,
            )
            financial_rows_by_ticker[ticker] = build_financial_lookup(cache, ticker)
            if idx % 100 == 0 or idx == len(tickers):
                print(f"[INFO] financial {idx}/{len(tickers)} tickers failures={sum(failures.values())}", flush=True)
        for ticker, date_key in universe.loc[:, ["__ticker", "__date"]].itertuples(index=False, name=None):
            values = financial_for_date(financial_rows_by_ticker.get(ticker, []), date_key)
            if values:
                financial_by_key[(ticker, date_key)] = values

    if include_news:
        news_cache_by_date: Dict[str, Dict[str, Any]] = {}
        for idx, date_key in enumerate(dates, start=1):
            news_cache_by_date[date_key] = fetch_news_cache(
                client,
                date_key,
                cache_dir=cache_dir,
                refresh=refresh_news,
                sleep_sec=sleep_sec,
                call_counts=call_counts,
                failures=failures,
            )
            if idx % 25 == 0 or idx == len(dates):
                print(f"[INFO] news {idx}/{len(dates)} dates failures={sum(failures.values())}", flush=True)
        for ticker, date_key, stock_name in universe.loc[:, ["__ticker", "__date", "stock_name"]].itertuples(index=False, name=None):
            values = news_features_for_ticker(
                news_cache_by_date.get(date_key, {}),
                ticker=ticker,
                stock_name=str(stock_name or ""),
            )
            if values:
                news_by_key[(ticker, date_key)] = values

    market_reports = []
    for market, frame in frames.items():
        out, summary = _fill_features(
            frame,
            market=market,
            flow_lookup=flow_by_key,
            financial_lookup=financial_by_key,
            news_lookup=news_by_key,
            generated_at=generated_at,
        )
        output_path = output_caches[market]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_pickle(output_path)
        summary["input_cache"] = str(input_caches[market])
        summary["output_cache"] = str(output_path)
        market_reports.append(summary)

    return {
        "version": REPORT_VERSION,
        "generated_at": generated_at,
        "dummy_data_used": False,
        "live_network_requested": bool(live),
        "kis_mode": client.config.mode,
        "kis_live_network_allowed": bool(client.config.live_network_allowed),
        "cache_dir": str(cache_dir),
        "input_caches": {market: str(path) for market, path in input_caches.items()},
        "output_caches": {market: str(path) for market, path in output_caches.items()},
        "target_scope": {
            "rows": int(sum(len(frame) for frame in frames.values())),
            "tickers": int(len(tickers)),
            "dates": int(len(dates)),
            "min_date": min_date,
            "max_date": max_date,
            "max_tickers": int(max_tickers or 0),
        },
        "include": {
            "flow": bool(include_flow),
            "financial": bool(include_financial),
            "news": bool(include_news),
        },
        "lookup_rows": {
            "flow": int(len(flow_by_key)),
            "financial": int(len(financial_by_key)),
            "news": int(len(news_by_key)),
        },
        "call_counts": dict(call_counts),
        "failure_counts": dict(failures),
        "no_dummy_data": True,
        "leakage_policy": {
            "flow": "exact ticker/trading-date lookup from stock_investor_daily rows; no forward-fill",
            "financial": "latest financial statement whose period end is <= base_trade_date",
            "news": "date-level KIS news payload filtered for ticker/name on the same date; no forward-fill",
        },
        "markets": market_reports,
        "decision": {
            "backfilled_cache_ready_for_research": True,
            "production_replacement_ready": False,
            "reason": "This regenerates research inputs only; promotion still requires walk-forward gates.",
        },
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# KIS Ticker-Period Sidecar Backfill",
        "",
        f"- version: `{report.get('version')}`",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- dummy_data_used: `{report.get('dummy_data_used')}`",
        f"- live_network_requested: `{report.get('live_network_requested')}`",
        f"- kis_live_network_allowed: `{report.get('kis_live_network_allowed')}`",
        f"- cache_dir: `{report.get('cache_dir')}`",
        "",
        "## Target Scope",
    ]
    scope = report.get("target_scope") if isinstance(report.get("target_scope"), Mapping) else {}
    lines.extend(
        [
            f"- rows: `{scope.get('rows')}`",
            f"- tickers: `{scope.get('tickers')}`",
            f"- dates: `{scope.get('dates')}`",
            f"- date_range: `{scope.get('min_date')}`..`{scope.get('max_date')}`",
            "",
            "## Lookup Rows",
        ]
    )
    lookup = report.get("lookup_rows") if isinstance(report.get("lookup_rows"), Mapping) else {}
    lines.append(
        f"- flow: `{lookup.get('flow')}` financial: `{lookup.get('financial')}` news: `{lookup.get('news')}`"
    )
    lines.append(f"- call_counts: `{report.get('call_counts')}`")
    lines.append(f"- failure_counts: `{report.get('failure_counts')}`")
    lines.extend(["", "## Market Outputs"])
    for market_report in report.get("markets") or []:
        if not isinstance(market_report, Mapping):
            continue
        lines.extend(
            [
                f"### {market_report.get('market')}",
                f"- augmented_rows: `{market_report.get('augmented_rows')}` ({market_report.get('augmented_row_pct')}%)",
                f"- flow_augmented_rows: `{market_report.get('flow_augmented_rows')}`",
                f"- financial_augmented_rows: `{market_report.get('financial_augmented_rows')}`",
                f"- news_augmented_rows: `{market_report.get('news_augmented_rows')}`",
                f"- future_financial_rows_cleared: `{market_report.get('future_financial_rows_cleared')}`",
                f"- output_cache: `{market_report.get('output_cache')}`",
                "",
                "| feature | filled_missing_values |",
                "|---|---:|",
            ]
        )
        rows = market_report.get("feature_fill_counts_top") if isinstance(market_report.get("feature_fill_counts_top"), list) else []
        if not rows:
            lines.append("| - | 0 |")
        for row in rows[:20]:
            if isinstance(row, Mapping):
                lines.append(f"| `{row.get('feature')}` | {_fmt(row.get('filled_missing_values'))} |")
        lines.append("")
    decision = report.get("decision") if isinstance(report.get("decision"), Mapping) else {}
    lines.extend(
        [
            "## Decision",
            f"- backfilled_cache_ready_for_research: `{decision.get('backfilled_cache_ready_for_research')}`",
            f"- production_replacement_ready: `{decision.get('production_replacement_ready')}`",
            f"- reason: {decision.get('reason')}",
        ]
    )
    return "\n".join(lines)


def write_report(report: Mapping[str, Any], output_json: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    output_json.with_suffix(".md").write_text(render_markdown(report) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-cache", action="append", default=[], help="MARKET=input pickle path")
    parser.add_argument("--output-cache", action="append", default=[], help="MARKET=output pickle path")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--no-flow", action="store_true")
    parser.add_argument("--no-financial", action="store_true")
    parser.add_argument("--no-news", action="store_true")
    parser.add_argument("--refresh-flow", action="store_true")
    parser.add_argument("--refresh-financial", action="store_true")
    parser.add_argument("--refresh-news", action="store_true")
    parser.add_argument("--max-tickers", type=int, default=0)
    parser.add_argument("--flow-max-chunks", type=int, default=8)
    parser.add_argument("--sleep-sec", type=float, default=0.08)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--retry-count", type=int, default=0)
    parser.add_argument("--max-runtime-sec", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if int(args.max_runtime_sec or 0) > 0:
        def _alarm_handler(_signum: int, _frame: Any) -> None:
            raise TimeoutError(f"max_runtime_sec exceeded: {args.max_runtime_sec}")

        signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(int(args.max_runtime_sec))
    os.environ.setdefault("KIS_LIVE_RETRY_COUNT", str(max(0, int(args.retry_count or 0))))
    raw_input_caches = args.input_cache or list(DEFAULT_INPUT_CACHES)
    raw_output_caches = args.output_cache or list(DEFAULT_OUTPUT_CACHES)
    input_caches = dict(_parse_market_path(value) for value in raw_input_caches)
    output_caches = dict(_parse_market_path(value) for value in raw_output_caches)
    missing = sorted(set(input_caches) - set(output_caches))
    if missing:
        raise SystemExit(f"missing output-cache for markets: {missing}")
    report = build_backfill(
        input_caches=input_caches,
        output_caches=output_caches,
        cache_dir=Path(args.cache_dir),
        live=bool(args.live),
        include_flow=not bool(args.no_flow),
        include_financial=not bool(args.no_financial),
        include_news=not bool(args.no_news),
        refresh_flow=bool(args.refresh_flow),
        refresh_financial=bool(args.refresh_financial),
        refresh_news=bool(args.refresh_news),
        max_tickers=int(args.max_tickers or 0),
        flow_max_chunks=int(args.flow_max_chunks or 1),
        sleep_sec=float(args.sleep_sec or 0.0),
        timeout=float(args.timeout or 0.0),
    )
    write_report(report, Path(args.output_json))
    print(
        json.dumps(
            {
                "output_json": args.output_json,
                "output_caches": report.get("output_caches"),
                "lookup_rows": report.get("lookup_rows"),
                "call_counts": report.get("call_counts"),
                "failure_counts": report.get("failure_counts"),
                "markets": [
                    {
                        "market": row.get("market"),
                        "augmented_rows": row.get("augmented_rows"),
                        "flow_augmented_rows": row.get("flow_augmented_rows"),
                        "financial_augmented_rows": row.get("financial_augmented_rows"),
                        "news_augmented_rows": row.get("news_augmented_rows"),
                    }
                    for row in report.get("markets", [])
                    if isinstance(row, Mapping)
                ],
            },
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
