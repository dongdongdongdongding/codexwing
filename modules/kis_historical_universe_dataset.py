from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import pandas as pd

from modules.operational_candidate_scoring import DEFAULT_BUY_PREMIUM_PCT


KIS_HISTORICAL_UNIVERSE_VERSION = "kis_historical_universe_dataset_v1"
KIS_HISTORICAL_SIDECAR_VERSION = "kis_historical_universe_sidecar_v1"
DEFAULT_TARGET_PCT = 5.0
DEFAULT_STOP_PCT = 10.0


@dataclass(frozen=True)
class InstrumentRecord:
    symbol: str
    local_symbol: str
    name: str
    market: str
    listing_date: str
    official_sector: str
    official_industry: str
    industry_code: str
    region: str
    source: str


def _text(value: Any) -> str:
    return str(value or "").strip()


def _date_text(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    try:
        return pd.to_datetime(text).date().isoformat()
    except Exception:
        return ""


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _pct(numerator: Any, denominator: Any) -> float | None:
    num = _safe_float(numerator)
    den = _safe_float(denominator)
    if num is None or den is None or den == 0:
        return None
    return round(((num / den) - 1.0) * 100.0, 6)


def _market_from_symbol(symbol: str, fallback: str = "") -> str:
    upper = _text(symbol).upper()
    if upper.endswith(".KS"):
        return "KOSPI"
    if upper.endswith(".KQ"):
        return "KOSDAQ"
    return _text(fallback).upper()


def _normalize_symbol(record: Mapping[str, Any]) -> str:
    symbol = _text(record.get("symbol") or record.get("local_symbol")).upper()
    market = _text(record.get("market_scope")).upper()
    if symbol.endswith(".KS") or symbol.endswith(".KQ"):
        return symbol
    if market == "KOSPI":
        return f"{symbol}.KS"
    if market in {"KOSDAQ", "KOSDAQ GLOBAL"}:
        return f"{symbol}.KQ"
    return symbol


def load_instrument_records(path: Path, *, markets: Sequence[str] = ("KOSPI", "KOSDAQ")) -> List[InstrumentRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    wanted = {str(item).upper() for item in markets}
    records: List[InstrumentRecord] = []
    for raw in data.get("records") or []:
        if not isinstance(raw, Mapping):
            continue
        market_scope = _text(raw.get("market_scope")).upper()
        if market_scope == "KOSDAQ GLOBAL":
            market_scope = "KOSDAQ"
        if market_scope not in wanted:
            continue
        symbol = _normalize_symbol(raw)
        if not symbol.endswith((".KS", ".KQ")):
            continue
        records.append(
            InstrumentRecord(
                symbol=symbol,
                local_symbol=_text(raw.get("local_symbol") or raw.get("symbol")),
                name=_text(raw.get("name")),
                market=market_scope,
                listing_date=_date_text(raw.get("listing_date")),
                official_sector=_text(raw.get("official_sector")),
                official_industry=_text(raw.get("official_industry")),
                industry_code=_text(raw.get("industry_code")),
                region=_text(raw.get("region")),
                source=_text(raw.get("classification_source") or "instrument_master"),
            )
        )
    return sorted(records, key=lambda item: (item.market, item.symbol))


def normalize_history_frame(history: pd.DataFrame) -> pd.DataFrame:
    if history is None or history.empty:
        return pd.DataFrame()
    out = history.copy()
    rename = {}
    for col in out.columns:
        low = str(col).strip().lower()
        if low == "open":
            rename[col] = "Open"
        elif low == "high":
            rename[col] = "High"
        elif low == "low":
            rename[col] = "Low"
        elif low == "close":
            rename[col] = "Close"
        elif low == "volume":
            rename[col] = "Volume"
    out = out.rename(columns=rename)
    if not isinstance(out.index, pd.DatetimeIndex):
        if "Date" in out.columns:
            out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
            out = out.set_index("Date")
        else:
            out.index = pd.to_datetime(out.index, errors="coerce")
    if out.index.tz is not None:
        out.index = out.index.tz_localize(None)
    keep = [col for col in ["Open", "High", "Low", "Close", "Volume"] if col in out.columns]
    out = out[keep].copy()
    for col in keep:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["Open", "High", "Low", "Close"], how="any")
    return out.sort_index()


def _rolling_value(series: pd.Series, window: int, idx: int, kind: str) -> float | None:
    if idx < 0:
        return None
    values = series.iloc[max(0, idx - window + 1) : idx + 1]
    if values.empty:
        return None
    if kind == "mean":
        return _safe_float(values.mean())
    if kind == "max":
        return _safe_float(values.max())
    if kind == "min":
        return _safe_float(values.min())
    raise ValueError(kind)


def _return_over(close: pd.Series, idx: int, days: int) -> float | None:
    if idx - days < 0:
        return None
    return _pct(close.iloc[idx], close.iloc[idx - days])


def _future_window(history: pd.DataFrame, idx: int, horizon: int) -> pd.DataFrame:
    return history.iloc[idx + 1 : idx + 1 + horizon].copy()


def _path_label(
    history: pd.DataFrame,
    idx: int,
    *,
    horizon: int,
    entry_price: float,
    target_pct: float,
    stop_pct: float,
) -> Dict[str, Any]:
    future = _future_window(history, idx, horizon)
    prefix = f"{horizon}d"
    if len(future) < horizon or entry_price <= 0:
        return {
            f"return_{prefix}_pct": None,
            f"max_high_return_{prefix}_pct": None,
            f"min_low_return_{prefix}_pct": None,
            f"target_hit_{prefix}": None,
            f"stop_hit_{prefix}": None,
            f"target_before_stop_{prefix}": None,
            f"stop_before_target_{prefix}": None,
            f"target_hit_at_{prefix}": None,
            f"stop_hit_at_{prefix}": None,
            f"days_to_target_{prefix}": None,
            f"days_to_stop_{prefix}": None,
            f"first_touch_{prefix}": None,
        }

    close_return = _pct(future["Close"].iloc[-1], entry_price)
    max_high = _pct(future["High"].max(), entry_price)
    min_low = _pct(future["Low"].min(), entry_price)
    target_price = entry_price * (1.0 + float(target_pct) / 100.0)
    stop_price = entry_price * (1.0 - float(stop_pct) / 100.0)
    target_idx = None
    stop_idx = None
    for offset, (_dt, row) in enumerate(future.iterrows(), start=1):
        if target_idx is None and _safe_float(row.get("High")) is not None and float(row["High"]) >= target_price:
            target_idx = offset
        if stop_idx is None and _safe_float(row.get("Low")) is not None and float(row["Low"]) <= stop_price:
            stop_idx = offset
        if target_idx is not None and stop_idx is not None:
            break
    target_hit = target_idx is not None
    stop_hit = stop_idx is not None
    target_at = future.index[target_idx - 1].date().isoformat() if target_hit else None
    stop_at = future.index[stop_idx - 1].date().isoformat() if stop_hit else None
    if target_hit and stop_hit:
        if target_idx < stop_idx:
            first_touch = "target"
            target_before_stop = True
            stop_before_target = False
        elif stop_idx < target_idx:
            first_touch = "stop"
            target_before_stop = False
            stop_before_target = True
        else:
            first_touch = "ambiguous_stop_first"
            target_before_stop = False
            stop_before_target = True
    elif target_hit:
        first_touch = "target"
        target_before_stop = True
        stop_before_target = False
    elif stop_hit:
        first_touch = "stop"
        target_before_stop = False
        stop_before_target = True
    else:
        first_touch = "no_touch"
        target_before_stop = False
        stop_before_target = False

    return {
        f"return_{prefix}_pct": close_return,
        f"max_high_return_{prefix}_pct": max_high,
        f"min_low_return_{prefix}_pct": min_low,
        f"target_hit_{prefix}": target_hit,
        f"stop_hit_{prefix}": stop_hit,
        f"target_before_stop_{prefix}": target_before_stop,
        f"stop_before_target_{prefix}": stop_before_target,
        f"target_hit_at_{prefix}": target_at,
        f"stop_hit_at_{prefix}": stop_at,
        f"days_to_target_{prefix}": target_idx,
        f"days_to_stop_{prefix}": stop_idx,
        f"first_touch_{prefix}": first_touch,
    }


def _prefixed_path_label(label: Mapping[str, Any], prefix: str) -> Dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in label.items()}


def _daily_summary(history: pd.DataFrame, idx: int) -> Dict[str, Any]:
    current = history.iloc[idx]
    close = float(current["Close"])
    high_20 = _rolling_value(history["High"], 20, idx, "max")
    low_20 = _rolling_value(history["Low"], 20, idx, "min")
    close_location = None
    if high_20 is not None and low_20 is not None and high_20 > low_20:
        close_location = round(((close - low_20) / (high_20 - low_20)) * 100.0, 6)
    avg_vol_20 = _rolling_value(history["Volume"], 20, idx - 1, "mean") if idx > 0 and "Volume" in history.columns else None
    volume = _safe_float(current.get("Volume"))
    volume_ratio = round(volume / avg_vol_20, 6) if volume is not None and avg_vol_20 and avg_vol_20 > 0 else None
    high_52w = _rolling_value(history["High"], 252, idx, "max")
    return {
        "source": "kis_openapi",
        "bar_count": int(idx + 1),
        "latest_date": history.index[idx].date().isoformat(),
        "latest_close": close,
        "ma5": _rolling_value(history["Close"], 5, idx, "mean"),
        "ma20": _rolling_value(history["Close"], 20, idx, "mean"),
        "ma60": _rolling_value(history["Close"], 60, idx, "mean"),
        "return_5d_pct": _return_over(history["Close"], idx, 5),
        "return_20d_pct": _return_over(history["Close"], idx, 20),
        "return_60d_pct": _return_over(history["Close"], idx, 60),
        "volume_ratio_20d": volume_ratio,
        "prior_20d_high": high_20,
        "range_20d_high": high_20,
        "range_20d_low": low_20,
        "close_location_pct": close_location,
        "high_52w": high_52w,
        "pct_from_52w_high": _pct(close, high_52w) if high_52w else None,
    }


def _sidecar_payload(record: InstrumentRecord, history: pd.DataFrame, idx: int, day_return_pct: float | None) -> Dict[str, Any]:
    current = history.iloc[idx]
    summary = _daily_summary(history, idx)
    volume = _safe_float(current.get("Volume"))
    close = _safe_float(current.get("Close")) or 0.0
    turnover = close * volume if volume is not None else None
    model_features = {
        "kis_current_price": close,
        "kis_day_change_pct": day_return_pct,
        "kis_value_traded": turnover,
        "kis_prev_volume_ratio": (
            round(float(summary["volume_ratio_20d"]) * 100.0, 6) if summary.get("volume_ratio_20d") is not None else None
        ),
        "kis_daily_bar_count": summary.get("bar_count"),
        "kis_daily_return_5d_pct": summary.get("return_5d_pct"),
        "kis_daily_return_20d_pct": summary.get("return_20d_pct"),
        "kis_daily_return_60d_pct": summary.get("return_60d_pct"),
        "kis_daily_volume_ratio_20d": summary.get("volume_ratio_20d"),
        "kis_daily_ma5": summary.get("ma5"),
        "kis_daily_ma20": summary.get("ma20"),
        "kis_daily_ma60": summary.get("ma60"),
        "kis_daily_prior_20d_high": summary.get("prior_20d_high"),
        "kis_daily_range_20d_high": summary.get("range_20d_high"),
        "kis_daily_range_20d_low": summary.get("range_20d_low"),
        "kis_daily_close_location_pct": summary.get("close_location_pct"),
        "kis_daily_high_52w": summary.get("high_52w"),
        "kis_daily_pct_from_52w_high": summary.get("pct_from_52w_high"),
        "kis_stock_market_name": record.market,
        "kis_stock_market_code": "STK" if record.market == "KOSPI" else "KSQ",
        "kis_stock_sector_name": record.official_industry or record.official_sector,
        "kis_stock_standard_industry_code": record.industry_code or None,
        "kis_stock_listed_date": record.listing_date.replace("-", "") if record.listing_date else None,
        "kis_stock_trade_stop": "N",
        "kis_stock_admin_item": "N",
    }
    coverage = {
        "quote_snapshot": False,
        "daily_ohlcv": True,
        "daily_ohlcv_50d": int(idx + 1) >= 50,
        "minute_ohlcv": False,
        "investor_flow": False,
        "rank_membership": False,
        "vi_status": False,
        "news_titles": False,
        "stock_info": True,
        "financial_ratio": False,
        "financial_style": False,
    }
    readiness = {
        "scanner_daily_ready": coverage["daily_ohlcv_50d"],
        "intraday_ready": False,
        "price_snapshot_ready": True,
        "flow_ready": False,
        "model_sidecar_ready": True,
        "production_replacement_ready": False,
    }
    return {
        "contract_version": KIS_HISTORICAL_SIDECAR_VERSION,
        "feature_origin": "kis_historical_universe",
        "coverage": coverage,
        "daily_ohlcv_summary": summary,
        "model_candidate_features": model_features,
        "stock_info_contract": {
            "checked": True,
            "source": record.source,
            "source_status": "instrument_master",
            "market_name": record.market,
            "sector_name": record.official_industry or record.official_sector,
            "listed_date": record.listing_date.replace("-", "") if record.listing_date else None,
        },
        "replacement_readiness": readiness,
        "warnings": ["historical_universe_no_intraday_quote_flow_news"],
    }


def build_historical_rows_for_symbol(
    record: InstrumentRecord,
    history: pd.DataFrame,
    *,
    min_base_date: str,
    max_base_date: str,
    target_pct: float = DEFAULT_TARGET_PCT,
    stop_pct: float = DEFAULT_STOP_PCT,
    buy_premium_pct: float = DEFAULT_BUY_PREMIUM_PCT,
    min_prior_bars: int = 20,
) -> List[Dict[str, Any]]:
    hist = normalize_history_frame(history)
    if hist.empty:
        return []
    min_dt = pd.Timestamp(min_base_date)
    max_dt = pd.Timestamp(max_base_date)
    listing = pd.Timestamp(record.listing_date) if record.listing_date else None
    rows: List[Dict[str, Any]] = []
    for idx, trade_ts in enumerate(hist.index):
        if trade_ts < min_dt or trade_ts > max_dt:
            continue
        if listing is not None and trade_ts.date() < listing.date():
            continue
        if idx + 1 < int(min_prior_bars):
            continue
        current = hist.iloc[idx]
        close = _safe_float(current.get("Close"))
        if close is None or close <= 0:
            continue
        base_date = trade_ts.date().isoformat()
        prev_close = _safe_float(hist["Close"].iloc[idx - 1]) if idx > 0 else None
        day_return_pct = _pct(close, prev_close) if prev_close else None
        volume = _safe_float(current.get("Volume"))
        turnover = close * volume if volume is not None else None
        summary = _daily_summary(hist, idx)
        sidecar = _sidecar_payload(record, hist, idx, day_return_pct)
        feature_snapshot = {
            "_feature_quality": {
                "feature_origin": "kis_historical_universe",
                "feature_quality": "actual_kis_daily_ohlcv",
                "is_dummy_data": False,
                "validation_excluded": False,
            },
            "_kis_sidecar": sidecar,
        }
        row: Dict[str, Any] = {
            "snapshot_key": f"KIS-HIST:{base_date}:{record.symbol}",
            "run_id": f"KIS-HIST-{base_date}",
            "ticker": record.symbol,
            "stock_name": record.name,
            "market": record.market,
            "scan_mode": "SWING",
            "base_trade_date": base_date,
            "scanned_at": f"{base_date}T15:30:00+09:00",
            "row_role": "historical_universe",
            "passed_current_model": False,
            "priority_rank": None,
            "decision": "HISTORICAL_UNIVERSE",
            "decision_bucket": "actual_kis_daily",
            "reject_stage": "historical_universe",
            "reject_reason": "not_a_live_scan_row",
            "feature_snapshot": feature_snapshot,
            "feature_origin": KIS_HISTORICAL_UNIVERSE_VERSION,
            "source_ref": f"kis_openapi_daily_bars:{record.symbol}:{base_date}",
            "total_scans": None,
            "filtered_count": None,
            "day_return_pct": day_return_pct,
            "volume_ratio": summary.get("volume_ratio_20d"),
            "turnover": turnover,
            "primary_theme": record.official_industry or record.official_sector or "UNKNOWN",
            "theme_source": "instrument_master",
            "theme_inference_status": "official_industry",
            "kr_universe_role": "HISTORICAL_UNIVERSE",
            "scanner_timeframe_profile": "DAILY_KIS_HISTORICAL",
            "entry_reference_price": close,
            "feature_coverage_score": 1.0,
            "feature_missing_keys": [],
            "has_actual_flow": False,
            "flow_source": None,
            "flow_unit": None,
            "flow_asof": None,
            "flow_warnings": ["historical_universe_flow_not_requested"],
            "normalized_feature_version": KIS_HISTORICAL_UNIVERSE_VERSION,
            "outcome_available": False,
            "outcome_source": "kis_openapi_daily_bars",
            "backfill_version": KIS_HISTORICAL_UNIVERSE_VERSION,
            "label_target_pct": float(target_pct),
            "label_stop_pct": float(stop_pct),
            "path_label_version": "kis_historical_daily_path_target5_stop10_v1",
            "path_label_source": "kis_openapi_daily_ohlc_stop_first",
            "path_label_updated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "+00:00",
            "operational_buy_premium_pct": float(buy_premium_pct),
            "buy_premium_entry_price": round(close * (1.0 + float(buy_premium_pct) / 100.0), 6),
            "buy_premium_label_target_pct": float(target_pct),
            "buy_premium_label_stop_pct": float(stop_pct),
            "buy_premium_path_label_version": "kis_historical_plus2pct_entry_target5_stop10_v1",
            "buy_premium_path_label_source": "kis_openapi_daily_ohlc_stop_first_plus2pct_entry",
            "buy_premium_path_label_updated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "+00:00",
        }
        for horizon in (1, 3, 5):
            label = _path_label(hist, idx, horizon=horizon, entry_price=close, target_pct=target_pct, stop_pct=stop_pct)
            row.update(label)
            premium = _path_label(
                hist,
                idx,
                horizon=horizon,
                entry_price=float(row["buy_premium_entry_price"]),
                target_pct=target_pct,
                stop_pct=stop_pct,
            )
            row.update(_prefixed_path_label(premium, "buy_premium"))
        row["outcome_available"] = row.get("return_5d_pct") is not None and row.get("max_high_return_5d_pct") is not None
        rows.append(row)
    return rows


def market_counts(rows: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        market = _market_from_symbol(_text(row.get("ticker")), _text(row.get("market"))) or "UNKNOWN"
        counts[market] = counts.get(market, 0) + 1
    return dict(sorted(counts.items()))


def date_range(rows: Sequence[Mapping[str, Any]]) -> Dict[str, str | None]:
    dates = sorted(_date_text(row.get("base_trade_date")) for row in rows if _date_text(row.get("base_trade_date")))
    return {"date_min": dates[0] if dates else None, "date_max": dates[-1] if dates else None}


def required_fetch_start(min_base_date: str, *, lookback_days: int = 180) -> str:
    start = date.fromisoformat(min_base_date)
    return (start - timedelta(days=max(0, int(lookback_days)))).isoformat()
