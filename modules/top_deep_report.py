from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf

from modules.entry_readiness import build_entry_readiness_analysis
from modules.entry_readiness_contract import build_entry_readiness_contract
from modules.execution_stop_display import build_execution_stop_display
from modules.practical_entry_gate import evaluate_practical_entry_gate
from modules.candidate_data_quality import build_candidate_data_quality
from modules.candidate_interpretation import build_candidate_interpretation
from modules.scan_universe_admission import (
    build_kis_shadow_admission_records,
    build_scan_universe_admission_input_rows,
    build_scan_universe_admission_records,
    merge_kis_prefilter_evidence_into_rows,
)
from modules.ui_helpers import build_top5_plus_exception_records, enrich_signal_rows_with_planner_trace
from modules.incident_regression import detect_failure_risk_reason_codes
from modules.kr_stock_theme_master import get_stock_theme_record
from modules.kis_theme_news_evidence import build_kis_theme_news_evidence
from modules.model_governance import active_policy_metadata
from modules.operational_candidate_scoring import build_operational_candidate_score
from modules.portfolio_exposure import build_portfolio_exposure_summary
from modules.realized_expectancy_admission import build_realized_expectancy_admission
from modules.tradable_pnl import TradableCostModel, compute_net_return_pct


REPORT_VERSION = "top_deep_report_v1"
SOURCE_TIMING_VERSION = "scan_deep_source_timing_v1"
LOCAL_REPORT_DIR = Path("runtime_state/reports/top_deep")

SCAN_DEEP_REPORT_COLUMNS = {
    "report_id",
    "report_version",
    "run_id",
    "market",
    "scan_mode",
    "rank",
    "ticker",
    "stock_name",
    "generated_at",
    "scan_as_of",
    "deep_analysis_as_of",
    "signal_label",
    "analysis_section",
    "analysis_section_rank",
    "source_order",
    "decision",
    "decision_bucket",
    "buy_score",
    "accuracy",
    "day_change_pct",
    "loss_risk_score",
    "selection_alignment",
    "risk_flags",
    "rationale",
    "prediction",
    "selection_thesis",
    "risk_overrides",
    "display_contract",
    "candidate_data_quality",
    "candidate_interpretation",
    "policy_metadata",
    "scan_universe_admission",
    "scan_result_interpretation",
    "realized_expectancy_admission",
    "entry_action",
    "entry_readiness_contract",
    "portfolio_exposure_summary",
    "structural_exclusion_risk",
    "exclusion_reasons",
    "stock_quality_score",
    "stock_quality_grade",
    "upside_room_score",
    "upside_room_grade",
    "entry_timing_score",
    "entry_timing_grade",
    "chase_risk_level",
    "chase_risk_reasons",
    "exclusion_risk_level",
    "final_action",
    "action_reason_codes",
    "practical_entry_gate",
    "trade_plan",
    "flow",
    "theme",
    "price",
    "news",
    "source_timing",
    "scan_source_snapshot",
    "deep_analysis_source_snapshot",
    "data_warnings",
}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() != "none"
    if isinstance(value, float):
        return not (math.isnan(value) or math.isinf(value))
    return True


def _safe_float(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return round(numeric, 4)


def _float_from_text(value: Any) -> float | None:
    direct = _safe_float(value)
    if direct is not None:
        return direct
    if value is None:
        return None
    try:
        import re

        text = str(value).replace(",", "")
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not match:
            return None
        return _safe_float(match.group(0))
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        numeric = int(float(value))
    except (TypeError, ValueError):
        return None
    return numeric


def _parse_flow_label(value: Any) -> Dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {}
    score = None
    try:
        import re

        match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*점", text)
        if match:
            score = float(match.group(1))
    except Exception:
        score = None
    trend = text
    if score is not None:
        trend = text.split("점", 1)[1].strip()
    return {"whale_score": score, "whale_trend": trend or None}


def _list_warnings(value: Any) -> List[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    return [str(value)]


def _derive_flow_dominance(flow: Dict[str, Any]) -> Dict[str, Any]:
    foreigner = _safe_float(flow.get("foreigner"))
    institution = _safe_float(flow.get("institution"))
    retail = _safe_float(flow.get("retail"))
    pairs = [
        ("외인", foreigner),
        ("기관", institution),
        ("개인", retail),
    ]
    buyers = [(name, value) for name, value in pairs if value is not None and value > 0]
    sellers = [(name, value) for name, value in pairs if value is not None and value < 0]
    buy = max(buyers, key=lambda item: item[1]) if buyers else (None, None)
    sell = min(sellers, key=lambda item: item[1]) if sellers else (None, None)
    dominant = buy if buy[0] else sell
    return {
        "buy_dominant": buy[0],
        "buy_dominant_flow": buy[1],
        "sell_dominant": sell[0],
        "sell_dominant_flow": sell[1],
        "dominant": dominant[0],
        "dominant_side": "buy" if buy[0] else ("sell" if sell[0] else None),
        "dominant_flow": dominant[1],
        "whale_flow": (foreigner + institution) if foreigner is not None and institution is not None else None,
    }


def _ticker(row: Dict[str, Any]) -> str:
    return str(row.get("ticker") or row.get("Ticker") or row.get("티커") or "").strip()


def _market_from_ticker(ticker: str) -> str:
    value = str(ticker or "").upper().strip()
    if value.endswith(".KS"):
        return "KOSPI"
    if value.endswith(".KQ"):
        return "KOSDAQ"
    return ""


def _first_present(row: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if _present(value):
            return value
    return None


def _nested_dict(row: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    current: Any = row
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return dict(current) if isinstance(current, dict) else {}


def _extract_kis_sidecar(row: Dict[str, Any], trace: Dict[str, Any]) -> Dict[str, Any]:
    candidates = [
        row.get("_kis_sidecar"),
        row.get("kis_sidecar"),
        _nested_dict(row, "_leader_metrics", "kis_sidecar"),
        _nested_dict(row, "leader_metrics", "kis_sidecar"),
        _nested_dict(row, "feature_snapshot", "kis_sidecar"),
        _nested_dict(row, "feature_snapshot", "leader_metrics", "kis_sidecar"),
        trace.get("_kis_sidecar"),
        trace.get("kis_sidecar"),
        _nested_dict(trace, "_leader_metrics", "kis_sidecar"),
        _nested_dict(trace, "leader_metrics", "kis_sidecar"),
        _nested_dict(trace, "feature_snapshot", "kis_sidecar"),
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("feature_origin") == "kis_openapi_sidecar":
            return dict(candidate)
        if candidate.get("contract_version") and (
            isinstance(candidate.get("operational_fields"), dict)
            or isinstance(candidate.get("flow_contract"), dict)
            or isinstance(candidate.get("model_candidate_features"), dict)
        ):
            return dict(candidate)
    return {}


def _coerce_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _coerce_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_coerce_jsonable(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    return value


def _planner_trace_by_ticker(planner_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    traces: Dict[str, Dict[str, Any]] = {}
    payload = planner_payload if isinstance(planner_payload, dict) else {}
    for section in ("decisions", "watchlist_meta"):
        for row in payload.get(section, []) or []:
            if not isinstance(row, dict):
                continue
            ticker = _ticker(row)
            if ticker and ticker not in traces:
                traces[ticker] = dict(row)
    return traces


def _select_top_candidates(
    scan_rows: List[Dict[str, Any]],
    planner_payload: Dict[str, Any],
    limit: int,
    diagnostics: Dict[str, Any] | None = None,
    scan_summary: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    ranked_rows = []
    for idx, row in enumerate(scan_rows or [], start=1):
        if not isinstance(row, dict):
            continue
        copy = dict(row)
        copy.setdefault("_raw_scan_rank", idx)
        ranked_rows.append(copy)
    enriched = enrich_signal_rows_with_planner_trace(ranked_rows, planner_payload)
    rows = [row for row in enriched if _ticker(row)]
    market = str(((planner_payload or {}).get("run_context") or {}).get("market") or "").upper()
    if market not in {"KOSPI", "KOSDAQ"}:
        inferred = {_market_from_ticker(_ticker(row)) for row in rows}
        inferred = {item for item in inferred if item in {"KOSPI", "KOSDAQ"}}
        if len(inferred) != 1:
            inferred = {
                _market_from_ticker(ticker)
                for ticker in _planner_trace_by_ticker(planner_payload).keys()
            }
            inferred = {item for item in inferred if item in {"KOSPI", "KOSDAQ"}}
        if len(inferred) == 1:
            market = next(iter(inferred))
    if market in {"KOSPI", "KOSDAQ"}:
        universe_input = build_scan_universe_admission_input_rows(
            rows,
            diagnostics=diagnostics,
            market=market,
        )
        admission_rows = universe_input.get("rows") if isinstance(universe_input.get("rows"), list) else rows
        admission_rows = merge_kis_prefilter_evidence_into_rows(admission_rows, scan_summary)
        groups = build_scan_universe_admission_records(
            admission_rows,
            market=market,
            limit=max(int(limit or 0), 5),
            include_near_miss=True,
            input_summary=universe_input,
        )
        shadow_rows = build_kis_shadow_admission_records(
            admission_rows,
            market=market,
            limit=max(int(limit or 0), 3),
            include_blocked_watch=True,
        )
        shadow_tickers = {_ticker(row) for row in shadow_rows if _ticker(row)}
        primary_rows = [
            row
            for row in list(groups.get("combined", []) or [])
            if _ticker(row) not in shadow_tickers
        ]
        selected = shadow_tickers | {_ticker(row) for row in primary_rows if _ticker(row)}
        exception_limit = max(int(limit or 0), 5)
        exception_groups = build_top5_plus_exception_records(
            ranked_rows,
            planner_payload,
            top_limit=0,
            exception_limit=exception_limit,
        )
        exception_rows = list(exception_groups.get("exception_leaders") or [])
        if exception_rows:
            scored_exceptions = build_scan_universe_admission_records(
                exception_rows,
                market=market,
                limit=exception_limit,
                include_near_miss=True,
            )
            scored_by_ticker = {
                _ticker(row): row
                for row in scored_exceptions.get("all_records", []) or []
                if _ticker(row)
            }
            for idx, row in enumerate(exception_rows, start=1):
                ticker = _ticker(row)
                if not ticker or ticker in selected:
                    continue
                scored = scored_by_ticker.get(ticker)
                copy = {**row, **scored} if isinstance(scored, dict) else dict(row)
                copy["_analysis_section"] = "Exception Leader"
                copy["_analysis_section_order"] = 1
                copy["_analysis_section_rank"] = idx
                copy["_source_order"] = "scan_universe_admission_model_plus_exception"
                primary_rows.append(copy)
                selected.add(ticker)
        return shadow_rows + primary_rows
    return rows[: max(int(limit or 0), 0)]


def _fetch_price_snapshot(ticker: str) -> Dict[str, Any]:
    warnings: List[str] = []
    try:
        hist = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
    except Exception as exc:
        return {"warnings": [f"price_fetch_failed:{exc}"], "ohlcv_tail": []}

    if hist is None or hist.empty:
        return {"warnings": ["price_history_empty"], "ohlcv_tail": []}

    hist = hist.dropna(subset=["Close"]).copy()
    latest = hist.iloc[-1]
    close = _safe_float(latest.get("Close"))
    prev_close = _safe_float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
    open_price = _safe_float(latest.get("Open"))
    high = _safe_float(latest.get("High"))
    low = _safe_float(latest.get("Low"))
    day_change_pct = None
    if close is not None and prev_close not in (None, 0):
        day_change_pct = round((close - prev_close) / prev_close * 100.0, 4)
    gap_up_pct = None
    if open_price is not None and prev_close not in (None, 0):
        gap_up_pct = round((open_price - prev_close) / prev_close * 100.0, 4)
    candle_return_pct = None
    if close is not None and open_price not in (None, 0):
        candle_return_pct = round((close - open_price) / open_price * 100.0, 4)
    close_location_pct = None
    if close is not None and high is not None and low is not None and high > low:
        close_location_pct = round((close - low) / (high - low) * 100.0, 4)
    volume = _safe_int(latest.get("Volume"))
    vol20 = _safe_float(hist["Volume"].tail(20).mean()) if "Volume" in hist else None
    volume_ratio = None
    if volume is not None and vol20 not in (None, 0):
        volume_ratio = round(float(volume) / float(vol20), 4)
    ma5 = _safe_float(hist["Close"].tail(5).mean()) if len(hist) >= 5 else None
    ma20 = _safe_float(hist["Close"].tail(20).mean()) if len(hist) >= 20 else None
    ma60 = _safe_float(hist["Close"].tail(60).mean()) if len(hist) >= 60 else None
    prior_20d_high = _safe_float(hist["High"].iloc[:-1].tail(20).max()) if "High" in hist and len(hist) >= 21 else None
    high_52w = _safe_float(hist["High"].tail(252).max()) if "High" in hist else None
    pct_from_52w_high = None
    if close is not None and high_52w not in (None, 0):
        pct_from_52w_high = round((close - high_52w) / high_52w * 100.0, 4)

    def _lookback_return(days: int) -> float | None:
        if close is None or len(hist) <= days:
            return None
        base = _safe_float(hist["Close"].iloc[-days - 1])
        if base in (None, 0):
            return None
        return round((close - base) / base * 100.0, 4)

    prev_candle_return_pct = None
    if len(hist) >= 2:
        prev = hist.iloc[-2]
        prev_open = _safe_float(prev.get("Open"))
        prev_close_for_candle = _safe_float(prev.get("Close"))
        if prev_open not in (None, 0) and prev_close_for_candle is not None:
            prev_candle_return_pct = round((prev_close_for_candle - prev_open) / prev_open * 100.0, 4)
    gap_up_after_long_bullish = bool(
        prev_candle_return_pct is not None
        and prev_candle_return_pct >= 8.0
        and gap_up_pct is not None
        and gap_up_pct >= 3.0
    )
    trend = "UNKNOWN"
    if close is not None and ma20 is not None and ma60 is not None:
        if close >= ma20 >= ma60:
            trend = "UP"
        elif close <= ma20 <= ma60:
            trend = "DOWN"
        else:
            trend = "MIXED"
    if len(hist) < 60:
        warnings.append("price_history_lt_60d")

    ohlcv_tail = []
    for idx, row in hist.tail(30).iterrows():
        ohlcv_tail.append(
            {
                "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx),
                "open": _safe_float(row.get("Open")),
                "high": _safe_float(row.get("High")),
                "low": _safe_float(row.get("Low")),
                "close": _safe_float(row.get("Close")),
                "volume": _safe_int(row.get("Volume")),
            }
        )

    return {
        "source": "yfinance_daily_history",
        "asof": ohlcv_tail[-1]["date"] if ohlcv_tail else None,
        "warnings": warnings,
        "current_price": close,
        "prev_close": prev_close,
        "day_change_pct": day_change_pct,
        "gap_up_pct": gap_up_pct,
        "candle_return_pct": candle_return_pct,
        "prev_candle_return_pct": prev_candle_return_pct,
        "gap_up_after_long_bullish": gap_up_after_long_bullish,
        "close_location_pct": close_location_pct,
        "volume": volume,
        "volume_ratio_20d": volume_ratio,
        "ma5": ma5,
        "ma20": ma20,
        "ma60": ma60,
        "trend": trend,
        "return_5d_pct": _lookback_return(5),
        "return_20d_pct": _lookback_return(20),
        "return_60d_pct": _lookback_return(60),
        "high_52w": high_52w,
        "pct_from_52w_high": pct_from_52w_high,
        "prior_20d_high": prior_20d_high,
        "range_20d_high": _safe_float(hist["High"].tail(20).max()) if "High" in hist else None,
        "range_20d_low": _safe_float(hist["Low"].tail(20).min()) if "Low" in hist else None,
        "ohlcv_tail": ohlcv_tail,
    }


def _entry_proxy_current_price(row: Dict[str, Any], trace: Dict[str, Any]) -> float | None:
    current = _float_from_text(
        _first_present(trace, "current_price", "Current Price", "현재가", "curr_price", "price")
        or _first_present(row, "current_price", "Current Price", "현재가", "curr_price", "price")
    )
    if current is not None:
        return current

    explicit_entry = _float_from_text(
        _first_present(trace, "entry_reference_price", "entry_price", "Entry Price", "Entry(-2%)")
        or _first_present(row, "entry_reference_price", "entry_price", "Entry Price", "Entry(-2%)")
    )
    if explicit_entry is not None:
        return explicit_entry

    limit_entry = _float_from_text(_first_present(trace, "매수가(-2%)") or _first_present(row, "매수가(-2%)"))
    if limit_entry is not None and limit_entry > 0:
        return _safe_float(limit_entry / 0.98)
    return None


def _price_proxy_from_scan_row(row: Dict[str, Any], trace: Dict[str, Any], *, generated_at: str) -> Dict[str, Any]:
    merged = {**(row if isinstance(row, dict) else {}), **(trace if isinstance(trace, dict) else {})}
    current = _entry_proxy_current_price(row, trace)
    day_change = _float_from_text(_first_present(merged, "day_return_pct", "전일비"))
    volume_ratio = _float_from_text(
        _first_present(merged, "volume_ratio", "volume_ratio_20d", "거래량")
        or ((merged.get("_leader_metrics") or {}).get("kr_volume_ratio") if isinstance(merged.get("_leader_metrics"), dict) else None)
    )
    proxy = {
        "warnings": [],
        "current_price": current,
        "day_change_pct": day_change,
        "volume_ratio_20d": volume_ratio,
        "asof": generated_at,
    }
    if current is None and day_change is None and volume_ratio is None:
        return {"warnings": []}
    proxy["warnings"] = ["price_proxy_from_scan_row"]
    return proxy


def _merge_price_snapshot_with_scan_row(
    fetched: Dict[str, Any],
    row: Dict[str, Any],
    trace: Dict[str, Any],
    *,
    generated_at: str,
) -> Dict[str, Any]:
    price = dict(fetched if isinstance(fetched, dict) else {})
    proxy = _price_proxy_from_scan_row(row, trace, generated_at=generated_at)
    for key, value in proxy.items():
        if key == "warnings":
            continue
        if not _present(price.get(key)) and _present(value):
            price[key] = value
    if _present(proxy.get("current_price")) or _present(proxy.get("day_change_pct")) or _present(proxy.get("volume_ratio_20d")):
        warnings = list(price.get("warnings") or [])
        for warning in proxy.get("warnings") or []:
            if warning not in warnings:
                warnings.append(warning)
        price["warnings"] = warnings
    return price


def _price_snapshot_from_kis_sidecar(kis_sidecar: Dict[str, Any]) -> Dict[str, Any]:
    sidecar = kis_sidecar if isinstance(kis_sidecar, dict) else {}
    fields = sidecar.get("operational_fields") if isinstance(sidecar.get("operational_fields"), dict) else {}
    features = sidecar.get("model_candidate_features") if isinstance(sidecar.get("model_candidate_features"), dict) else {}
    daily = sidecar.get("daily_ohlcv_summary") if isinstance(sidecar.get("daily_ohlcv_summary"), dict) else {}
    if not (fields or features or daily):
        return {}

    snapshot_at = (
        _first_present(fields, "snapshot_at", "updated_at", "asof", "as_of")
        or daily.get("latest_date")
        or sidecar.get("generated_at")
    )
    price = {
        "source": "kis_openapi_sidecar",
        "source_status": fields.get("source_status") or ("ok" if _present(fields.get("current_price") or features.get("kis_current_price")) else "partial"),
        "asof": snapshot_at,
        "snapshot_at": snapshot_at,
        "current_price": _safe_float(fields.get("current_price") or fields.get("last_price") or features.get("kis_current_price") or daily.get("latest_close")),
        "day_change_pct": _safe_float(fields.get("day_change_pct") or fields.get("prev_pct_change") or features.get("kis_day_change_pct")),
        "volume": _safe_int(fields.get("volume")),
        "value_traded": _safe_float(fields.get("value_traded") or features.get("kis_value_traded")),
        "prev_volume_ratio": _safe_float(fields.get("prev_volume_ratio") or fields.get("volume_ratio") or features.get("kis_prev_volume_ratio")),
        "volume_ratio_20d": _safe_float(daily.get("volume_ratio_20d") or features.get("kis_daily_volume_ratio_20d")),
        "market_cap": _safe_float(fields.get("market_cap") or features.get("kis_market_cap")),
        "per": _safe_float(fields.get("per") or features.get("kis_per")),
        "pbr": _safe_float(fields.get("pbr") or features.get("kis_pbr")),
        "ma5": _safe_float(daily.get("ma5") or features.get("kis_daily_ma5")),
        "ma20": _safe_float(daily.get("ma20") or features.get("kis_daily_ma20")),
        "ma60": _safe_float(daily.get("ma60") or features.get("kis_daily_ma60")),
        "return_5d_pct": _safe_float(daily.get("return_5d_pct") or features.get("kis_daily_return_5d_pct")),
        "return_20d_pct": _safe_float(daily.get("return_20d_pct") or features.get("kis_daily_return_20d_pct")),
        "return_60d_pct": _safe_float(daily.get("return_60d_pct") or features.get("kis_daily_return_60d_pct")),
        "high_52w": _safe_float(daily.get("high_52w") or features.get("kis_daily_high_52w")),
        "pct_from_52w_high": _safe_float(daily.get("pct_from_52w_high") or features.get("kis_daily_pct_from_52w_high") or fields.get("high_250d_gap_pct")),
        "prior_20d_high": _safe_float(daily.get("prior_20d_high") or features.get("kis_daily_prior_20d_high")),
        "range_20d_high": _safe_float(daily.get("range_20d_high") or features.get("kis_daily_range_20d_high")),
        "range_20d_low": _safe_float(daily.get("range_20d_low") or features.get("kis_daily_range_20d_low")),
        "close_location_pct": _safe_float(daily.get("close_location_pct") or features.get("kis_daily_close_location_pct")),
        "warnings": list(sidecar.get("warnings") or []),
    }
    if price["current_price"] is None:
        price["warnings"].append("kis_sidecar_current_price_missing")
    if price["volume_ratio_20d"] is None and price["prev_volume_ratio"] is not None:
        price["warnings"].append("kis_prev_volume_ratio_available_but_20d_volume_ratio_missing")
    return {key: value for key, value in price.items() if key == "warnings" or _present(value)}


def _merge_kis_price_snapshot(
    price: Dict[str, Any],
    kis_sidecar: Dict[str, Any],
) -> Dict[str, Any]:
    kis_price = _price_snapshot_from_kis_sidecar(kis_sidecar)
    if not kis_price:
        return price
    merged = dict(price if isinstance(price, dict) else {})
    existing_source = str(merged.get("source") or "").strip()
    fallback_sources = list(merged.get("fallback_sources") or [])
    if not existing_source and (merged.get("ohlcv_tail") or merged.get("warnings")):
        fallback_sources.append("yfinance_daily_history")
    elif existing_source and existing_source != "kis_openapi_sidecar":
        fallback_sources.append(existing_source)

    for key, value in kis_price.items():
        if key == "warnings":
            continue
        if _present(value):
            merged[key] = value
    warnings = list(merged.get("warnings") or [])
    for warning in list(kis_price.get("warnings") or []) + ["price_source:kis_openapi_sidecar"]:
        if warning and warning not in warnings:
            warnings.append(warning)
    merged["warnings"] = warnings
    if fallback_sources:
        merged["fallback_sources"] = sorted(set(str(item) for item in fallback_sources if item))
    return merged


def _flow_snapshot_from_kis_sidecar(kis_sidecar: Dict[str, Any]) -> Dict[str, Any]:
    sidecar = kis_sidecar if isinstance(kis_sidecar, dict) else {}
    flow = sidecar.get("flow_contract") if isinstance(sidecar.get("flow_contract"), dict) else {}
    if not flow:
        return {}
    if not flow.get("valid") and not any(_present(flow.get(key)) for key in ("foreigner_1d", "institution_1d", "retail_1d", "whale_score")):
        return {}
    warnings = list(flow.get("warnings") or [])
    for warning in sidecar.get("warnings") or []:
        if warning not in warnings:
            warnings.append(str(warning))
    return {
        "valid": bool(flow.get("valid")),
        "type": flow.get("type") or "KR",
        "source": f"kis_openapi_sidecar:{flow.get('flow_source') or 'kis_openapi'}",
        "flow_unit": flow.get("flow_unit"),
        "whale_score": _safe_float(flow.get("whale_score")),
        "foreigner": _safe_float(flow.get("foreigner_1d") if _present(flow.get("foreigner_1d")) else flow.get("foreigner")),
        "institution": _safe_float(flow.get("institution_1d") if _present(flow.get("institution_1d")) else flow.get("institution")),
        "retail": _safe_float(flow.get("retail_1d") if _present(flow.get("retail_1d")) else flow.get("retail")),
        "dominant": flow.get("dominant"),
        "dominant_side": flow.get("dominant_side"),
        "dominant_flow": flow.get("dominant_flow"),
        "buy_dominant": flow.get("buy_dominant"),
        "buy_dominant_flow": flow.get("buy_dominant_flow"),
        "sell_dominant": flow.get("sell_dominant"),
        "sell_dominant_flow": flow.get("sell_dominant_flow"),
        "foreigner_1d": flow.get("foreigner_1d"),
        "institution_1d": flow.get("institution_1d"),
        "retail_1d": flow.get("retail_1d"),
        "foreigner_3d": flow.get("foreigner_3d"),
        "institution_3d": flow.get("institution_3d"),
        "retail_3d": flow.get("retail_3d"),
        "foreigner_10d": flow.get("foreigner_10d"),
        "institution_10d": flow.get("institution_10d"),
        "retail_10d": flow.get("retail_10d"),
        "whale_flow": flow.get("whale_flow"),
        "whale_flow_1d": flow.get("whale_flow_1d"),
        "whale_flow_3d": flow.get("whale_flow_3d"),
        "whale_flow_10d": flow.get("whale_flow_10d"),
        "flow_window": flow.get("flow_window") or "1d",
        "flow_asof": flow.get("flow_asof"),
        "whale_trend": flow.get("whale_trend"),
        "warnings": warnings,
    }


def _news_snapshot_from_kis_sidecar(kis_sidecar: Dict[str, Any]) -> Dict[str, Any]:
    sidecar = kis_sidecar if isinstance(kis_sidecar, dict) else {}
    news = sidecar.get("news_contract") if isinstance(sidecar.get("news_contract"), dict) else {}
    if not news.get("checked"):
        return {}
    rows = [row for row in news.get("rows") or [] if isinstance(row, dict)]
    headlines = []
    for row in rows[:5]:
        title = row.get("title") or row.get("hts_pbnt_titl_cntt") or row.get("headline")
        if not title:
            continue
        date_value = row.get("date")
        if not date_value and (row.get("data_dt") or row.get("data_tm")):
            date_value = f"{row.get('data_dt') or ''} {row.get('data_tm') or ''}".strip()
        headlines.append(
            {
                "title": str(title),
                "score": None,
                "source": str(row.get("source") or row.get("dorg") or "KIS"),
                "date": date_value,
                "url": row.get("url"),
            }
        )
    warnings = []
    if news.get("rows_truncated"):
        warnings.append("kis_news_rows_truncated")
    return {
        "status": "OK" if str(news.get("source_status") or "").lower() in {"ok", ""} else news.get("source_status"),
        "source": "kis_openapi_sidecar",
        "sentiment_score": None,
        "headlines": headlines,
        "news_count": news.get("news_count"),
        "warnings": warnings,
    }


def _source_timing_payload(
    *,
    row: Dict[str, Any],
    trace: Dict[str, Any],
    kis_sidecar: Dict[str, Any],
    price: Dict[str, Any],
    flow: Dict[str, Any],
    news: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    scan_as_of = (
        row.get("scan_as_of")
        or trace.get("scan_as_of")
        or row.get("created_at")
        or trace.get("created_at")
        or row.get("generated_at")
        or trace.get("generated_at")
        or kis_sidecar.get("generated_at")
    )
    price_as_of = price.get("asof") or price.get("as_of") or price.get("snapshot_at") or price.get("updated_at")
    flow_as_of = flow.get("flow_asof") or flow.get("asof") or flow.get("as_of") or flow.get("updated_at")
    news_as_of = None
    for headline in news.get("headlines") or []:
        if isinstance(headline, dict) and _present(headline.get("date")):
            news_as_of = headline.get("date")
            break
    coverage = kis_sidecar.get("coverage") if isinstance(kis_sidecar.get("coverage"), dict) else {}
    readiness = kis_sidecar.get("replacement_readiness") if isinstance(kis_sidecar.get("replacement_readiness"), dict) else {}
    scan_source = {
        "feature_origin": row.get("feature_origin") or trace.get("feature_origin") or ("kis_openapi_sidecar" if kis_sidecar else "raw_scan_results"),
        "kis_sidecar_present": bool(kis_sidecar),
        "kis_sidecar_generated_at": kis_sidecar.get("generated_at"),
        "kis_sidecar_contract_version": kis_sidecar.get("contract_version"),
        "kis_sidecar_coverage": coverage,
        "kis_replacement_readiness": readiness,
        "kis_production_replacement_ready": readiness.get("production_replacement_ready"),
    }
    deep_source = {
        "price_source": price.get("source") or ("scan_row_proxy" if "price_proxy_from_scan_row" in (price.get("warnings") or []) else "unknown"),
        "flow_source": flow.get("source") or flow.get("flow_source") or "unknown",
        "news_source": news.get("source") or "news_analyzer",
        "used_kis_sidecar": bool(
            price.get("source") == "kis_openapi_sidecar"
            or str(flow.get("source") or "").startswith("kis_openapi_sidecar")
            or news.get("source") == "kis_openapi_sidecar"
        ),
        "fallback_sources": price.get("fallback_sources") or [],
    }
    return {
        "version": SOURCE_TIMING_VERSION,
        "scan_as_of": scan_as_of,
        "deep_analysis_as_of": generated_at,
        "price_as_of": price_as_of,
        "flow_as_of": flow_as_of,
        "news_as_of": news_as_of,
        "scan_source_snapshot": scan_source,
        "deep_analysis_source_snapshot": deep_source,
    }


def _fetch_news_snapshot(ticker: str, stock_name: str) -> Dict[str, Any]:
    try:
        from modules.news_analysis import NewsAnalyzer

        payload = NewsAnalyzer(ticker, stock_name=stock_name, max_results=5).get_news_sentiment()
        return {
            "status": payload.get("status"),
            "sentiment_score": _safe_float(payload.get("score")),
            "headlines": [
                {
                    "title": str(item.get("title") or ""),
                    "score": _safe_float(item.get("score")),
                    "source": str(item.get("source") or ""),
                    "date": item.get("date"),
                    "url": item.get("url"),
                }
                for item in (payload.get("headlines") or [])
                if isinstance(item, dict)
            ],
            "warnings": [],
        }
    except Exception as exc:
        return {"status": "ERROR", "sentiment_score": None, "headlines": [], "warnings": [f"news_fetch_failed:{exc}"]}


def _fetch_investor_flow_snapshot(ticker: str, row: Dict[str, Any], trace: Dict[str, Any]) -> Dict[str, Any]:
    base = {**(row if isinstance(row, dict) else {}), **(trace if isinstance(trace, dict) else {})}
    flow_label = _parse_flow_label(_first_present(base, "수급", "flow_label"))
    whale_score = _safe_float(_first_present(base, "whale_score", "Whale", "kr_flow_leader_score"))
    if whale_score is None:
        whale_score = flow_label.get("whale_score")
    direct = {
        "whale_score": whale_score,
        "foreigner": _safe_float(
            _first_present(base, "foreigner_1d", "foreigner", "foreign_flow", "foreign_net", "foreign_net_buy", "kr_foreign_flow")
        ),
        "institution": _safe_float(
            _first_present(
                base,
                "institution_1d",
                "institution",
                "institution_flow",
                "institution_net",
                "institution_net_buy",
                "kr_institution_flow",
            )
        ),
        "retail": _safe_float(
            _first_present(base, "retail_1d", "retail", "retail_flow", "individual", "individual_net", "retail_net_buy", "kr_retail_flow")
        ),
    }
    has_flow_breakdown = any(direct.get(key) is not None for key in ("foreigner", "institution", "retail"))
    if has_flow_breakdown:
        whale = direct.get("whale_score")
        direct_source = str(base.get("flow_source") or "").strip()
        flow_window = str(base.get("flow_window") or "").strip()
        dominance = _derive_flow_dominance(direct)
        whale_flow = (
            base.get("whale_flow_1d")
            if _present(base.get("whale_flow_1d"))
            else (base.get("whale_flow") if _present(base.get("whale_flow")) else dominance.get("whale_flow"))
        )
        return {
            "valid": True,
            "type": "KR" if str(ticker).upper().endswith((".KS", ".KQ")) else "UNKNOWN",
            "source": f"scan_row:{direct_source}" if direct_source else "scan_row",
            "flow_unit": base.get("flow_unit") or "shares",
            "whale_score": whale,
            "foreigner": direct.get("foreigner"),
            "institution": direct.get("institution"),
            "retail": direct.get("retail"),
            "dominant": dominance.get("dominant") or base.get("dominant"),
            "dominant_side": dominance.get("dominant_side") or base.get("dominant_side"),
            "dominant_flow": dominance.get("dominant_flow") or base.get("dominant_flow"),
            "buy_dominant": dominance.get("buy_dominant"),
            "buy_dominant_flow": dominance.get("buy_dominant_flow"),
            "sell_dominant": dominance.get("sell_dominant"),
            "sell_dominant_flow": dominance.get("sell_dominant_flow"),
            "foreigner_1d": direct.get("foreigner"),
            "institution_1d": direct.get("institution"),
            "retail_1d": direct.get("retail"),
            "foreigner_3d": base.get("foreigner_3d"),
            "institution_3d": base.get("institution_3d"),
            "retail_3d": base.get("retail_3d"),
            "foreigner_10d": base.get("foreigner_10d"),
            "institution_10d": base.get("institution_10d"),
            "retail_10d": base.get("retail_10d"),
            "whale_flow": whale_flow,
            "whale_flow_1d": whale_flow,
            "whale_flow_3d": base.get("whale_flow_3d"),
            "whale_flow_10d": base.get("whale_flow_10d"),
            "flow_window": flow_window or "legacy_unknown",
            "flow_asof": base.get("flow_asof"),
            "whale_trend": base.get("whale_trend") or flow_label.get("whale_trend"),
            "warnings": _list_warnings(base.get("flow_warnings"))
            + ([] if flow_window else ["legacy_flow_window_unknown"])
            + ([] if whale is not None else ["investor_flow_score_missing_scan_row"]),
        }
    if not str(ticker).upper().endswith((".KS", ".KQ")):
        return {
            "valid": False,
            "type": "UNSUPPORTED",
            "source": "none",
            "whale_score": None,
            "foreigner": None,
            "institution": None,
            "retail": None,
            "warnings": ["investor_flow_supported_for_kr_only"],
        }

    try:
        from modules.quant_analysis import QuantStrategy

        payload = QuantStrategy(ticker).get_investor_flows()
        fetched_whale = _safe_float(payload.get("whale_score"))
        payload_warnings = [str(item) for item in (payload.get("warnings") or []) if item]
        if direct.get("whale_score") is not None:
            payload_warnings.append("live_flow_breakdown_used_for_scan_score_only_row")
        if not payload.get("valid"):
            payload_warnings.append(str(payload.get("reason") or "investor_flow_unavailable"))
        dominance = _derive_flow_dominance(payload)
        whale_flow = (
            payload.get("whale_flow_1d")
            if _present(payload.get("whale_flow_1d"))
            else (payload.get("whale_flow") if _present(payload.get("whale_flow")) else dominance.get("whale_flow"))
        )
        return {
            "valid": bool(payload.get("valid")),
            "type": payload.get("type") or "KR",
            "source": f"live_fetch:{payload.get('flow_source') or 'quant_strategy'}",
            "flow_unit": payload.get("flow_unit"),
            "whale_score": fetched_whale if fetched_whale is not None else direct.get("whale_score"),
            "scan_whale_score": direct.get("whale_score"),
            "foreigner": _safe_float(payload.get("foreigner")),
            "institution": _safe_float(payload.get("institution")),
            "retail": _safe_float(payload.get("retail")),
            "dominant": payload.get("dominant") or dominance.get("dominant"),
            "dominant_side": payload.get("dominant_side") or dominance.get("dominant_side"),
            "dominant_flow": payload.get("dominant_flow") or dominance.get("dominant_flow"),
            "buy_dominant": payload.get("buy_dominant") or dominance.get("buy_dominant"),
            "buy_dominant_flow": payload.get("buy_dominant_flow") or dominance.get("buy_dominant_flow"),
            "sell_dominant": payload.get("sell_dominant") or dominance.get("sell_dominant"),
            "sell_dominant_flow": payload.get("sell_dominant_flow") or dominance.get("sell_dominant_flow"),
            "foreigner_1d": payload.get("foreigner_1d", payload.get("foreigner")),
            "institution_1d": payload.get("institution_1d", payload.get("institution")),
            "retail_1d": payload.get("retail_1d", payload.get("retail")),
            "foreigner_3d": payload.get("foreigner_3d"),
            "institution_3d": payload.get("institution_3d"),
            "retail_3d": payload.get("retail_3d"),
            "foreigner_10d": payload.get("foreigner_10d"),
            "institution_10d": payload.get("institution_10d"),
            "retail_10d": payload.get("retail_10d"),
            "whale_flow": whale_flow,
            "whale_flow_1d": whale_flow,
            "whale_flow_3d": payload.get("whale_flow_3d"),
            "whale_flow_10d": payload.get("whale_flow_10d"),
            "flow_window": payload.get("flow_window") or "1d",
            "flow_asof": payload.get("flow_asof"),
            "whale_trend": payload.get("whale_trend"),
            "warnings": payload_warnings,
        }
    except Exception as exc:
        return {
            "valid": False,
            "type": "KR",
            "source": "quant_strategy",
            "whale_score": direct.get("whale_score"),
            "foreigner": None,
            "institution": None,
            "retail": None,
            "warnings": [f"investor_flow_failed:{exc}"],
        }


def _practical_gate_blocks(gate: Dict[str, Any] | None) -> bool:
    if not isinstance(gate, dict):
        return False
    return gate.get("level") == "fail" and bool(gate.get("evidence"))


def _apply_practical_gate_override(readiness: Dict[str, Any], gate: Dict[str, Any]) -> Dict[str, Any]:
    if not _practical_gate_blocks(gate):
        return readiness
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness.get("final_buy_judgment"), dict) else {}
    if judgment.get("action") not in {"즉시 매수 가능", "조건부 매수 가능"}:
        return readiness
    updated = dict(readiness)
    updated["final_buy_judgment"] = {
        "action": "관망",
        "tone": "neutral",
        "summary": "실전 80% 필터 미달 후보라 매수 액션에서 제외합니다.",
    }
    overrides = list(updated.get("safety_overrides") or [])
    overrides.append("실전 80% 필터 미달")
    updated["safety_overrides"] = overrides[:8]
    return updated


def _signal_label(
    row: Dict[str, Any],
    loss_risk: float | None,
    *,
    readiness: Dict[str, Any] | None = None,
    practical_gate: Dict[str, Any] | None = None,
) -> str:
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness, dict) else {}
    action = str(judgment.get("action") or "")
    if action in {"매수 금지", "스윙 제외"}:
        return "NO_BUY"
    if action in {"눌림 대기", "돌파 확인", "관망"}:
        return "WAIT_CONFIRM"
    if _practical_gate_blocks(practical_gate):
        return "WAIT_CONFIRM"
    decision = str(row.get("decision") or row.get("Decision") or "").upper()
    if decision == "EXCEPTION_LEADER":
        return "SURGE_CAPTURE"
    if loss_risk is not None and loss_risk >= 65:
        return "RISK_REVIEW"
    if decision in {"PRIORITY_WATCHLIST", "PICK", "BUY", "STRONG_BUY"}:
        return "PRIMARY_BUY"
    if decision in {"WATCHLIST", "WATCHLIST_ONLY"}:
        return "WATCH_BUY"
    return decision or "OBSERVE"


def _segment_accuracy(row: Dict[str, Any], trace: Dict[str, Any], ticker: str, market: str, scan_mode: str) -> float | None:
    direct = _safe_float(
        _first_present(row, "phase25_oos_win_rate_pct")
        or trace.get("phase25_oos_win_rate_pct")
        or row.get("prob_clean")
        or trace.get("prob_clean")
    )
    if direct is not None:
        return direct
    try:
        from modules.segment_accuracy import lookup_segment_win_rate

        return _safe_float(
            lookup_segment_win_rate(
                decision=_first_present(row, "decision", "Decision") or trace.get("decision"),
                market=market or trace.get("market") or row.get("market"),
                scan_mode=scan_mode or trace.get("scan_mode") or row.get("scan_mode"),
                ticker=ticker,
                horizon_days=5,
            )
        )
    except Exception:
        return None


def _derive_trade_price_levels(policy: Dict[str, Any], price: Dict[str, Any], ticker: str) -> Dict[str, Any]:
    policy = dict(policy if isinstance(policy, dict) else {})
    price = price if isinstance(price, dict) else {}
    warnings: List[str] = [str(item) for item in policy.get("warnings", []) if str(item).strip()]
    current = _safe_float(price.get("current_price"))
    entry = _safe_float(policy.get("entry_reference_price")) or current
    if entry is None:
        policy.update(
            {
                "entry_zone_low": None,
                "entry_zone_high": None,
                "target_price": None,
                "stop_price": None,
                "risk_reward": None,
                "price_level_source": "unavailable",
                "warnings": ["trade_price_level_unavailable"],
            }
        )
        return policy

    if policy.get("entry_reference_price") is None:
        policy["entry_reference_price"] = entry
        warnings.append("entry_reference_price_fallback_current_price")

    is_kq = str(ticker).upper().endswith(".KQ")
    ma20 = _safe_float(price.get("ma20"))
    ma5 = _safe_float(price.get("ma5"))
    range_low = _safe_float(price.get("range_20d_low"))
    prior_high = _safe_float(price.get("prior_20d_high"))
    tp_pct = _safe_float(policy.get("target_tp_pct")) or 0.0
    sl_pct = _safe_float(policy.get("stop_sl_pct")) or (-7.0 if is_kq else -5.0)

    pullback = 0.025 if is_kq else 0.018
    entry_zone_low = entry * (1.0 - pullback)
    support_candidates = []
    for support in (ma5, ma20, range_low):
        if support is not None and 0 < support < entry and ((entry - support) / entry) <= 0.15:
            support_candidates.append(support)
    if support_candidates:
        entry_zone_low = min(entry_zone_low, max(support_candidates))
    entry_zone_high = entry

    fallback_stop = entry * (1.0 + sl_pct / 100.0)
    stop_candidates = [fallback_stop]
    for support in (ma20, range_low):
        if support is not None and 0 < support < entry:
            stop_candidates.append(support * 0.985)
    stop_price = max([candidate for candidate in stop_candidates if candidate < entry], default=fallback_stop)
    if (entry - stop_price) / entry < 0.015:
        stop_price = entry * 0.985
    if (entry - stop_price) / entry > 0.15:
        stop_price = fallback_stop
        warnings.append("stop_price_default_pct_used_due_far_support")

    target_price = entry * (1.0 + tp_pct / 100.0) if tp_pct else None
    if target_price is not None and prior_high is not None and prior_high > entry:
        target_price = max(target_price, prior_high * 1.01)

    reward = (target_price - entry) if target_price is not None else None
    risk = entry - stop_price if stop_price is not None else None
    risk_reward = round(reward / risk, 4) if reward is not None and risk and risk > 0 else None

    policy.update(
        {
            "entry_zone_low": _safe_float(entry_zone_low),
            "entry_zone_high": _safe_float(entry_zone_high),
            "target_price": _safe_float(target_price),
            "stop_price": _safe_float(stop_price),
            "risk_reward": risk_reward,
            "stop_sl_pct": _safe_float((stop_price / entry - 1.0) * 100.0) if stop_price is not None else policy.get("stop_sl_pct"),
            "target_tp_pct": _safe_float((target_price / entry - 1.0) * 100.0) if target_price is not None else policy.get("target_tp_pct"),
            "price_level_source": "per_stock_price_snapshot",
            "warnings": warnings,
        }
    )
    return policy


def _trade_policy(row: Dict[str, Any], trace: Dict[str, Any], ticker: str, price: Dict[str, Any]) -> Dict[str, Any]:
    tp = _safe_float(trace.get("target_tp_pct") or row.get("target_tp_pct"))
    sl = _safe_float(trace.get("stop_sl_pct") or row.get("stop_sl_pct"))
    hold = _safe_int(trace.get("hold_days") or row.get("hold_days"))
    entry_policy = str(row.get("entry_policy") or trace.get("entry_policy") or "").strip()
    if tp is None or sl is None or hold is None or not entry_policy:
        try:
            from modules.scanner_services import DEFAULT_EXIT_HOLD_DAYS, DEFAULT_EXIT_SL_PCT, DEFAULT_EXIT_TP_PCT

            tp = DEFAULT_EXIT_TP_PCT if tp is None else tp
            sl = DEFAULT_EXIT_SL_PCT if sl is None else sl
            hold = DEFAULT_EXIT_HOLD_DAYS if hold is None else hold
        except Exception:
            tp = 15.0 if tp is None else tp
            sl = -10.0 if sl is None else sl
            hold = 5 if hold is None else hold
        if not entry_policy:
            entry_policy = "-2% limit" if str(ticker).upper().endswith(".KQ") else "open/reference"
    if not _present(_first_present(trace, "target_tp_pct") or row.get("target_tp_pct")):
        # Exit percent defaults are an explicit fallback; concrete price levels below remain per-stock.
        trace = {**trace, "trade_policy_warning": "default_target_pct_used"}
    policy = {
        "entry_policy": entry_policy,
        "entry_reference_price": _safe_float(
            _first_present(
                trace,
                "entry_reference_price",
                "entry_price",
                "Entry Price",
                "Entry(-2%)",
                "매수가(-2%)",
                "Current Price",
                "현재가",
                "curr_price",
                "price",
            )
            or _first_present(
                row,
                "entry_reference_price",
                "entry_price",
                "Entry Price",
                "Entry(-2%)",
                "매수가(-2%)",
                "Current Price",
                "현재가",
                "curr_price",
                "price",
            )
        ),
        "target_tp_pct": tp,
        "stop_sl_pct": sl,
        "hold_days": hold,
    }
    if trace.get("trade_policy_warning"):
        policy["warnings"] = [trace.get("trade_policy_warning")]
    return _derive_trade_price_levels(policy, price, ticker)


def _build_selection_thesis(
    *,
    row: Dict[str, Any],
    trace: Dict[str, Any],
    prediction: Dict[str, Any],
    readiness: Dict[str, Any],
) -> Dict[str, Any]:
    merged = {**(row if isinstance(row, dict) else {}), **(trace if isinstance(trace, dict) else {})}
    decision = str(merged.get("decision") or "").upper()
    raw_score = _safe_float(_first_present(row, "Decision Score", "decision_score", "score"))
    relative_score = _safe_float(merged.get("relative_rank_score"))
    expected_edge = _safe_float(prediction.get("expected_edge_score"))
    loss = _safe_float(merged.get("loss_risk_score"))
    selection_reasons = []
    for item in merged.get("rationale") or []:
        text = str(item).strip()
        if text and text not in selection_reasons:
            selection_reasons.append(text)
        if len(selection_reasons) >= 8:
            break

    if decision in {"PRIORITY_WATCHLIST", "PICK", "BUY", "STRONG_BUY"}:
        status = "planner_priority"
        summary = "플래너가 실행 후보군으로 유지한 종목입니다."
    elif decision in {"WATCHLIST", "WATCHLIST_ONLY"}:
        status = "planner_watchlist"
        summary = "스캔 강도는 있으나 플래너가 감시 후보로 낮춘 종목입니다."
    elif decision in {"OBSERVE", "AVOID"}:
        status = "planner_demoted"
        summary = "스캔에는 포착됐지만 플래너가 관망/회피로 강등한 종목입니다."
    else:
        status = "scanner_candidate"
        summary = "스캔 후보로 포착된 종목입니다."

    if raw_score is not None and raw_score >= 80 and decision in {"OBSERVE", "AVOID"}:
        summary += " 원본 점수는 높지만 손실위험/기대수익/상대순위에서 차단 신호가 있습니다."
    elif expected_edge is not None and expected_edge < 0:
        summary += " 다만 기대 엣지는 음수라 즉시 매수 논리는 약합니다."
    elif loss is not None and loss >= 65:
        summary += " 손실위험 하드캡에 가까워 진입 판단은 보수적으로 봅니다."

    quality = readiness.get("quality") if isinstance(readiness.get("quality"), dict) else {}
    timing = readiness.get("timing") if isinstance(readiness.get("timing"), dict) else {}
    upside = readiness.get("upside") if isinstance(readiness.get("upside"), dict) else {}
    return {
        "status": status,
        "summary": summary,
        "scanner_basis": {
            "raw_decision_score": raw_score,
            "quant_priority_score": _safe_float(merged.get("quant_priority_score")),
            "relative_rank_score": relative_score,
            "relative_rank_pct": _safe_float(merged.get("relative_rank_pct")),
            "expected_edge_score": expected_edge,
            "expected_return_1d_pct": _safe_float(prediction.get("expected_return_1d_pct")),
            "expected_return_3d_pct": _safe_float(prediction.get("expected_return_3d_pct")),
            "loss_risk_score": loss,
        },
        "readiness_snapshot": {
            "quality_score": quality.get("score"),
            "upside_score": upside.get("score"),
            "timing_score": timing.get("score"),
            "chase_risk_level": readiness.get("chase_risk_level"),
        },
        "selection_reasons": selection_reasons,
    }


def _build_risk_overrides(
    *,
    row: Dict[str, Any],
    trace: Dict[str, Any],
    readiness: Dict[str, Any],
    loss_risk_score: float | None,
) -> Dict[str, Any]:
    merged = {**(row if isinstance(row, dict) else {}), **(trace if isinstance(trace, dict) else {})}
    flags = []
    for source in (merged.get("theme_risk"), merged.get("risk_flags"), merged.get("rationale")):
        for item in source or []:
            text = str(item).strip()
            if text and text not in flags:
                flags.append(text)
    upside = readiness.get("upside") if isinstance(readiness.get("upside"), dict) else {}
    filters = upside.get("filters") if isinstance(upside.get("filters"), list) else []
    triggered_filters = [item for item in filters if isinstance(item, dict) and item.get("triggered")]
    warnings = [str(item) for item in readiness.get("warnings") or [] if str(item).strip()]
    severity = "none"
    if loss_risk_score is not None and loss_risk_score >= 65:
        severity = "hard"
    elif any(str(item.get("severity")) == "block" for item in triggered_filters):
        severity = "hard"
    elif loss_risk_score is not None and loss_risk_score >= 45:
        severity = "soft"
    elif triggered_filters:
        severity = "soft"

    return {
        "severity": severity,
        "loss_risk_score": loss_risk_score,
        "triggered_chase_filters": triggered_filters,
        "planner_risk_flags": flags[:10],
        "data_warnings": warnings[:8],
    }


def _build_display_contract(row: Dict[str, Any], trace: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    alignment = report.get("selection_alignment") if isinstance(report.get("selection_alignment"), dict) else {}
    readiness = report.get("trade_plan", {}).get("readiness_analysis", {}) if isinstance(report.get("trade_plan"), dict) else {}
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness.get("final_buy_judgment"), dict) else {}
    risk_flags = report.get("risk_flags") if isinstance(report.get("risk_flags"), list) else []
    data_warnings = report.get("data_warnings") if isinstance(report.get("data_warnings"), list) else []
    action = str(judgment.get("action") or report.get("signal_label") or "").strip()
    high_risk = action in {"매수 금지", "신규 매수 금지", "스윙 제외"} or str(report.get("signal_label") or "").upper() == "NO_BUY"
    return {
        "version": "candidate_display_contract_v1",
        "visible": True,
        "suppression_allowed": False,
        "display_status": "VISIBLE_RISK_ANNOTATED" if high_risk or risk_flags else "VISIBLE",
        "display_reason": "risk_annotation_only" if high_risk or risk_flags else "scanner_emitted_candidate",
        "analysis_section": alignment.get("analysis_section") or "Top5",
        "analysis_section_rank": _safe_int(alignment.get("analysis_section_rank")),
        "original_scan_rank": _safe_int(alignment.get("raw_scan_rank") or row.get("_raw_scan_rank")),
        "planner_priority_rank": _safe_int(alignment.get("planner_priority_rank") or trace.get("priority_rank") or row.get("priority_rank")),
        "display_rank": _safe_int(report.get("rank")),
        "action_label": action or None,
        "risk_flags": risk_flags[:10],
        "failure_risk_reason_codes": detect_failure_risk_reason_codes({**row, **trace, **report}),
        "data_warning_count": len(data_warnings),
    }


def build_top_deep_reports(
    *,
    scan_rows: List[Dict[str, Any]],
    planner_payload: Dict[str, Any],
    run_id: str,
    market: str,
    scan_mode: str,
    top_n: int = 5,
    diagnostics: Dict[str, Any] | None = None,
    scan_summary: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    traces = _planner_trace_by_ticker(planner_payload)
    reports: List[Dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc).isoformat()
    policy_metadata = active_policy_metadata(market=market, scan_mode=scan_mode)
    for rank, row in enumerate(
        _select_top_candidates(
            scan_rows,
            planner_payload,
            top_n,
            diagnostics=diagnostics,
            scan_summary=scan_summary,
        ),
        start=1,
    ):
        ticker = _ticker(row)
        trace = traces.get(ticker, {})
        kis_sidecar = _extract_kis_sidecar(row, trace)
        stock_name = str(_first_present(row, "stock_name", "종목명", "Name", "name") or trace.get("stock_name") or ticker)
        price = _merge_price_snapshot_with_scan_row(
            _fetch_price_snapshot(ticker),
            row,
            trace,
            generated_at=generated_at,
        )
        if kis_sidecar:
            price = _merge_kis_price_snapshot(price, kis_sidecar)
        news = _news_snapshot_from_kis_sidecar(kis_sidecar) or _fetch_news_snapshot(ticker, stock_name)
        loss_risk = _safe_float(_first_present(row, "loss_risk_score") or trace.get("loss_risk_score"))
        day_change = _safe_float(_first_present(row, "day_return_pct", "전일비") or price.get("day_change_pct"))
        buy_score = _safe_float(_first_present(row, "relative_rank_score", "decision_score", "Decision Score", "score"))
        trade_policy = _trade_policy(row, trace, ticker, price)
        flow = _flow_snapshot_from_kis_sidecar(kis_sidecar) or _fetch_investor_flow_snapshot(ticker, row, trace)
        prediction = {
            "phase25_prob": _safe_float(trace.get("phase25_prob") or row.get("phase25_prob")),
            "expected_return_1d_pct": _safe_float(trace.get("expected_return_1d_pct") or row.get("expected_return_1d_pct")),
            "expected_return_3d_pct": _safe_float(trace.get("expected_return_3d_pct") or row.get("expected_return_3d_pct")),
            "expected_edge_score": _safe_float(trace.get("expected_edge_score") or row.get("expected_edge_score")),
            "relative_rank_score": _safe_float(trace.get("relative_rank_score") or row.get("relative_rank_score")),
            "relative_rank_pct": _safe_float(trace.get("relative_rank_pct") or row.get("relative_rank_pct")),
            "relative_rank_model": trace.get("relative_rank_model") or row.get("relative_rank_model"),
        }
        prediction["expected_net_return_3d_pct"] = compute_net_return_pct(
            prediction.get("expected_return_3d_pct"),
            TradableCostModel(),
        )
        prediction["tradable_pnl_model_version"] = TradableCostModel().version
        admission = row.get("realized_expectancy_admission") if isinstance(row.get("realized_expectancy_admission"), dict) else {}
        if not admission:
            admission = build_realized_expectancy_admission(
                {**row, **trace},
                market=market,
                section=row.get("_analysis_section") or "Top5",
            )
        if admission.get("available"):
            prediction["realized_expectancy_3d_prob"] = admission.get("3d_prob")
            prediction["realized_expectancy_5d_prob"] = admission.get("5d_prob")
            prediction["ranking_score_3d"] = admission.get("ranking_score_3d")
            prediction["ranking_score_5d"] = admission.get("ranking_score_5d")
            prediction["admission_policy_version"] = admission.get("policy_version")
        analysis_section = str(row.get("_analysis_section") or "Top5")
        analysis_section_rank = _safe_int(row.get("_analysis_section_rank"))
        source_order = str(row.get("_source_order") or "scan_universe_admission_model")
        decision = str(_first_present(row, "decision", "Decision") or trace.get("decision") or "")
        decision_bucket = str(_first_present(row, "decision_bucket") or trace.get("decision_bucket") or "")
        if analysis_section == "Exception Leader":
            decision = "EXCEPTION_LEADER"
            decision_bucket = "exception_leader"
        elif analysis_section == "Admission Near Miss" and not decision_bucket:
            decision_bucket = "admission_near_miss"
        readiness_analysis = build_entry_readiness_analysis(
            candidate={**row, **trace},
            price=price,
            prediction=prediction,
            trade_plan=trade_policy,
            news=news,
            flow=flow,
            loss_risk_score=loss_risk,
        )
        practical_gate = evaluate_practical_entry_gate({**row, **trace})
        readiness_analysis = _apply_practical_gate_override(readiness_analysis, practical_gate)
        readiness_analysis["contract"] = build_entry_readiness_contract(readiness_analysis, source="top_deep_report")
        readiness_contract = readiness_analysis.get("contract") if isinstance(readiness_analysis.get("contract"), dict) else {}
        selection_thesis = _build_selection_thesis(
            row=row,
            trace=trace,
            prediction=prediction,
            readiness=readiness_analysis,
        )
        risk_overrides = _build_risk_overrides(
            row=row,
            trace=trace,
            readiness=readiness_analysis,
            loss_risk_score=loss_risk,
        )
        entry_action = {
            "judgment": readiness_analysis.get("final_buy_judgment"),
            "entry_strategy": readiness_analysis.get("entry_strategy"),
            "risk_management": readiness_analysis.get("risk_management"),
        }
        trade_policy["readiness_analysis"] = readiness_analysis
        if isinstance(readiness_analysis.get("entry_strategy"), dict):
            trade_policy["entry_strategy"] = readiness_analysis["entry_strategy"]
        if isinstance(readiness_analysis.get("risk_management"), dict):
            trade_policy["risk_management"] = readiness_analysis["risk_management"]
        if isinstance(readiness_analysis.get("data_coverage"), dict):
            trade_policy["data_coverage"] = readiness_analysis["data_coverage"]
        trade_policy["selection_thesis"] = selection_thesis
        trade_policy["risk_overrides"] = risk_overrides
        trade_policy["entry_action"] = entry_action
        trade_policy["practical_entry_gate"] = practical_gate
        execution_stop = build_execution_stop_display({**row, **trace}, trade_policy)
        trade_policy["execution_stop"] = execution_stop
        theme_master = get_stock_theme_record(ticker)
        theme_master_primary = str(theme_master.get("primary_theme") or "").strip()
        if theme_master_primary == "unclassified":
            theme_master_primary = ""
        primary_theme = (
            _first_present(trace, "primary_theme", "테마", "Theme")
            or _first_present(row, "primary_theme", "테마", "Theme")
            or theme_master_primary
        )
        theme_routing_path = (
            _first_present(trace, "theme_routing_path", "theme_routing_path")
            or _first_present(row, "theme_routing_path", "theme_routing_path")
            or ("stock_theme_master" if theme_master_primary and primary_theme == theme_master_primary else None)
        )
        kis_theme_news_evidence = build_kis_theme_news_evidence(
            row,
            trace=trace,
            market=market,
            theme_master=theme_master,
        )
        source_timing = _source_timing_payload(
            row=row,
            trace=trace,
            kis_sidecar=kis_sidecar,
            price=price,
            flow=flow,
            news=news,
            generated_at=generated_at,
        )
        operational_score = build_operational_candidate_score(
            {
                **row,
                "feature_snapshot": trace.get("feature_snapshot") if isinstance(trace.get("feature_snapshot"), dict) else row.get("feature_snapshot"),
                "theme": {
                    "primary_theme": primary_theme,
                    "theme_routing_path": theme_routing_path,
                    "kis_theme_news_evidence": kis_theme_news_evidence,
                },
                "theme_context": {
                    "primary_theme": primary_theme,
                    "theme_routing_path": theme_routing_path,
                    "theme_strength_score": _first_present(trace, "theme_strength_score") or row.get("theme_strength_score"),
                    "theme_direction": _first_present(trace, "theme_direction") or row.get("theme_direction"),
                },
                "price": price,
                "flow": flow,
                "kis_theme_news_evidence": kis_theme_news_evidence,
                "market_gate": _first_present(trace, "market_gate") or row.get("market_gate"),
                "regime_breadth_pct": _first_present(trace, "regime_breadth_pct") or row.get("regime_breadth_pct"),
                "regime_avg_chg": _first_present(trace, "regime_avg_chg") or row.get("regime_avg_chg"),
                "regime_volatility_20d": _first_present(trace, "regime_volatility_20d") or row.get("regime_volatility_20d"),
                "realized_expectancy_admission": admission,
            }
        )
        report = {
            "report_id": f"{run_id}:{ticker}:{REPORT_VERSION}",
            "report_version": REPORT_VERSION,
            "run_id": str(run_id),
            "market": str(market or ""),
            "scan_mode": str(scan_mode or ""),
            "rank": rank,
            "ticker": ticker,
            "stock_name": stock_name,
            "generated_at": generated_at,
            "scan_as_of": source_timing.get("scan_as_of"),
            "deep_analysis_as_of": source_timing.get("deep_analysis_as_of"),
            "analysis_section": analysis_section,
            "analysis_section_rank": analysis_section_rank,
            "source_order": source_order,
            "signal_label": _signal_label(
                {**row, **trace},
                loss_risk,
                readiness=readiness_analysis,
                practical_gate=practical_gate,
            ),
            "decision": decision,
            "decision_bucket": decision_bucket,
            "selection_alignment": {
                "raw_scan_rank": _safe_int(row.get("_raw_scan_rank")),
                "planner_priority_rank": _safe_int(trace.get("priority_rank") or row.get("priority_rank")),
                "raw_decision_score": _safe_float(_first_present(row, "Decision Score", "decision_score", "score")),
                "planner_decision": str(trace.get("decision") or row.get("decision") or ""),
                "relative_rank_score": _safe_float(trace.get("relative_rank_score") or row.get("relative_rank_score")),
                "relative_rank_pct": _safe_float(trace.get("relative_rank_pct") or row.get("relative_rank_pct")),
                "analysis_section": analysis_section,
                "analysis_section_rank": analysis_section_rank,
                "source_order": source_order,
                "validated_winner_profile": row.get("_validated_winner_profile"),
            },
            "buy_score": buy_score,
            "accuracy": _segment_accuracy(row, trace, ticker, market, scan_mode),
            "day_change_pct": day_change,
            "loss_risk_score": loss_risk,
            "practical_entry_gate": practical_gate,
            "risk_flags": trace.get("theme_risk") or row.get("theme_risk") or [],
            "rationale": trace.get("rationale") or row.get("rationale") or [],
            "prediction": prediction,
            "scan_universe_admission": row.get("scan_universe_admission"),
            "scan_result_interpretation": row.get("scan_result_interpretation"),
            "policy_metadata": policy_metadata,
            "realized_expectancy_admission": admission,
            "selection_thesis": selection_thesis,
            "risk_overrides": risk_overrides,
            "entry_action": entry_action,
            "entry_readiness_contract": readiness_contract,
            "structural_exclusion_risk": readiness_analysis.get("structural_exclusion_risk"),
            "stock_quality_score": readiness_contract.get("stock_quality_score"),
            "stock_quality_grade": readiness_contract.get("stock_quality_grade"),
            "upside_room_score": readiness_contract.get("upside_room_score"),
            "upside_room_grade": readiness_contract.get("upside_room_grade"),
            "entry_timing_score": readiness_contract.get("entry_timing_score"),
            "entry_timing_grade": readiness_contract.get("entry_timing_grade"),
            "chase_risk_level": readiness_contract.get("chase_risk_level"),
            "chase_risk_reasons": readiness_contract.get("chase_risk_reasons"),
            "exclusion_risk_level": readiness_contract.get("exclusion_risk_level"),
            "exclusion_reasons": readiness_contract.get("exclusion_reasons"),
            "final_action": readiness_contract.get("final_action"),
            "action_reason_codes": readiness_contract.get("action_reason_codes"),
            "execution_stop": execution_stop,
            "trade_plan": trade_policy,
            "flow": flow,
            "theme": {
                "primary_theme": primary_theme,
                "theme_routing_path": theme_routing_path,
                "theme_inference_status": theme_master.get("theme_inference_status") if theme_master_primary and primary_theme == theme_master_primary else None,
                "theme_source": theme_master.get("source_theme_reference") if theme_master_primary and primary_theme == theme_master_primary else None,
                "theme_score_adjustment": _safe_float(_first_present(trace, "theme_score_adjustment") or row.get("theme_score_adjustment")),
                "theme_day_symbol_count": _safe_float(_first_present(trace, "theme_day_symbol_count", "_theme_day_symbol_count") or _first_present(row, "theme_day_symbol_count", "_theme_day_symbol_count")),
                "theme_day_avg_alpha_score": _safe_float(_first_present(trace, "theme_day_avg_alpha_score", "_theme_day_avg_alpha_score") or _first_present(row, "theme_day_avg_alpha_score", "_theme_day_avg_alpha_score")),
                "theme_day_avg_decision_score": _safe_float(_first_present(trace, "theme_day_avg_decision_score", "_theme_day_avg_decision_score") or _first_present(row, "theme_day_avg_decision_score", "_theme_day_avg_decision_score")),
                "theme_day_avg_volume_ratio": _safe_float(_first_present(trace, "theme_day_avg_volume_ratio", "_theme_day_avg_volume_ratio") or _first_present(row, "theme_day_avg_volume_ratio", "_theme_day_avg_volume_ratio")),
                "theme_day_avg_day_return_pct": _safe_float(_first_present(trace, "theme_day_avg_day_return_pct", "_theme_day_avg_day_return_pct") or _first_present(row, "theme_day_avg_day_return_pct", "_theme_day_avg_day_return_pct")),
                "theme_day_positive_return_pct": _safe_float(_first_present(trace, "theme_day_positive_return_pct", "_theme_day_positive_return_pct") or _first_present(row, "theme_day_positive_return_pct", "_theme_day_positive_return_pct")),
                "theme_day_strength_rank": _safe_float(_first_present(trace, "theme_day_strength_rank", "_theme_day_strength_rank") or _first_present(row, "theme_day_strength_rank", "_theme_day_strength_rank")),
                "theme_day_strength_bucket": _first_present(trace, "theme_day_strength_bucket", "_theme_day_strength_bucket")
                or _first_present(row, "theme_day_strength_bucket", "_theme_day_strength_bucket"),
                "kis_theme_news_evidence": kis_theme_news_evidence,
                "kis_evidence_strength_score": kis_theme_news_evidence.get("evidence_strength_score"),
                "kis_evidence_strength_level": kis_theme_news_evidence.get("evidence_strength_level"),
                "kis_sector_name": (kis_theme_news_evidence.get("theme") or {}).get("kis_sector_name")
                if isinstance(kis_theme_news_evidence.get("theme"), dict)
                else None,
                "kis_standard_industry_code": (kis_theme_news_evidence.get("theme") or {}).get("kis_standard_industry_code")
                if isinstance(kis_theme_news_evidence.get("theme"), dict)
                else None,
            },
            "market_regime": {
                "market_gate": _first_present(trace, "market_gate") or row.get("market_gate"),
                "regime_breadth_pct": _safe_float(_first_present(trace, "regime_breadth_pct") or row.get("regime_breadth_pct")),
                "regime_avg_chg": _safe_float(_first_present(trace, "regime_avg_chg") or row.get("regime_avg_chg")),
                "regime_volatility_20d": _safe_float(_first_present(trace, "regime_volatility_20d") or row.get("regime_volatility_20d")),
                "kospi_chg": _safe_float(_first_present(trace, "kospi_chg") or row.get("kospi_chg")),
                "kosdaq_chg": _safe_float(_first_present(trace, "kosdaq_chg") or row.get("kosdaq_chg")),
            },
            "price": price,
            "news": news,
            "kis_theme_news_evidence": kis_theme_news_evidence,
            "operational_score_axes": operational_score,
            "operational_action_level": operational_score.get("action_level"),
            "operational_action_label": operational_score.get("action_label"),
            "chart_dominance_pct": operational_score.get("chart_dominance_pct"),
            "chart_only_candidate": operational_score.get("chart_only"),
            "source_timing": source_timing,
            "scan_source_snapshot": source_timing.get("scan_source_snapshot"),
            "deep_analysis_source_snapshot": source_timing.get("deep_analysis_source_snapshot"),
            "data_warnings": (
                list(price.get("warnings") or [])
                + list(news.get("warnings") or [])
                + list(flow.get("warnings") or [])
                + list(trade_policy.get("warnings") or [])
            ),
        }
        report["display_contract"] = _build_display_contract(row=row, trace=trace, report=report)
        report["candidate_data_quality"] = build_candidate_data_quality(report)
        report["candidate_interpretation"] = build_candidate_interpretation(report)
        reports.append(_coerce_jsonable(report))
    return reports


def save_reports_local(reports: List[Dict[str, Any]], run_id: str) -> str:
    LOCAL_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = LOCAL_REPORT_DIR / f"{run_id}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)
    return str(path)


def upsert_reports_to_supabase(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not reports:
        return {"rows_seen": 0, "rows_upserted": 0, "warning": ""}
    try:
        from modules.db_manager import DBManager

        db = DBManager()
        if not db.client:
            return {"rows_seen": len(reports), "rows_upserted": 0, "warning": "db_client_unavailable"}
        filtered_reports = []
        for row in reports:
            if not isinstance(row, dict):
                continue
            filtered = db._filter_payload_to_existing_columns("scan_deep_reports", row)
            if set(filtered.keys()) == set(row.keys()):
                filtered = {key: value for key, value in row.items() if key in SCAN_DEEP_REPORT_COLUMNS}
            filtered_reports.append(filtered)
        run_ids = sorted({str(row.get("run_id") or "") for row in reports if row.get("run_id")})
        for run_id in run_ids:
            db.client.table("scan_deep_reports").delete().eq("run_id", run_id).execute()
        dropped_columns: List[str] = []
        for _attempt in range(6):
            try:
                db.client.table("scan_deep_reports").upsert(filtered_reports, on_conflict="report_id").execute()
                break
            except Exception as exc:
                text = str(exc)
                match = re.search(r"Could not find the '([^']+)' column", text)
                if not match:
                    raise
                column = match.group(1)
                dropped_columns.append(column)
                filtered_reports = [
                    {key: value for key, value in row.items() if key != column}
                    for row in filtered_reports
                    if isinstance(row, dict)
                ]
        else:
            return {
                "rows_seen": len(reports),
                "rows_upserted": 0,
                "warning": f"schema_retry_exhausted:dropped={','.join(dropped_columns)}",
            }
        warning = f"schema_columns_dropped:{','.join(dropped_columns)}" if dropped_columns else ""
        return {"rows_seen": len(reports), "rows_upserted": len(filtered_reports), "warning": warning}
    except Exception as exc:
        return {"rows_seen": len(reports), "rows_upserted": 0, "warning": str(exc)}


def generate_and_store_top_deep_reports(
    *,
    scan_rows: List[Dict[str, Any]],
    planner_payload: Dict[str, Any],
    run_id: str,
    market: str,
    scan_mode: str,
    top_n: int = 5,
    write_db: bool = True,
    diagnostics: Dict[str, Any] | None = None,
    scan_summary: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    reports = build_top_deep_reports(
        scan_rows=scan_rows,
        planner_payload=planner_payload,
        run_id=run_id,
        market=market,
        scan_mode=scan_mode,
        top_n=top_n,
        diagnostics=diagnostics,
        scan_summary=scan_summary,
    )
    exposure_summary = build_portfolio_exposure_summary(reports, run_id=run_id)
    for report in reports:
        report["portfolio_exposure_summary"] = exposure_summary
    local_path = save_reports_local(reports, run_id)
    db_result = upsert_reports_to_supabase(reports) if write_db else {"rows_seen": len(reports), "rows_upserted": 0, "warning": "write_db_disabled"}
    runtime_artifact_result = {"enabled": False, "rows_upserted": 0, "reason": "write_db_disabled"}
    if write_db:
        try:
            from modules.runtime_artifact_store import upsert_runtime_artifact_payload

            runtime_artifact_result = upsert_runtime_artifact_payload(
                run_id=run_id,
                artifact_key="top_deep_reports",
                payload=reports,
                market=market,
                scan_mode=scan_mode,
                source="top_deep_report",
                source_path=local_path,
                metadata={"report_count": len(reports), "table": "scan_deep_reports"},
            )
        except Exception as exc:
            runtime_artifact_result = {"ok": False, "enabled": True, "rows_upserted": 0, "error": str(exc)}
    return {
        "count": len(reports),
        "local_path": local_path,
        "db_result": db_result,
        "runtime_artifact_result": runtime_artifact_result,
        "portfolio_exposure_summary": exposure_summary,
    }
