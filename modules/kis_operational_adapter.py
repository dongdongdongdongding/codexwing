from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pandas as pd

from modules.kis_news_scope import classify_kis_news_source_scope, filter_kis_news_rows_for_symbol
from modules.kis_openapi import normalize_kr_stock_code


KIS_OPERATIONAL_CONTRACT_VERSION = "kis_operational_adapter_v1"


def kis_intraday_input_hour(now: Optional[datetime] = None) -> str:
    """Return the KIS minute-chart input hour for the current KR session."""

    override = str(os.getenv("AG_KIS_INTRADAY_INPUT_HOUR") or "").strip().replace(":", "")
    if override.isdigit() and len(override) >= 4:
        return override.zfill(6)[:6]

    try:
        from zoneinfo import ZoneInfo

        kst = ZoneInfo("Asia/Seoul")
        current = now.astimezone(kst) if now is not None and now.tzinfo is not None else (now or datetime.now(kst))
    except Exception:
        current = now or datetime.now()

    seconds = (int(current.hour) * 3600) + (int(current.minute) * 60) + int(current.second)
    open_seconds = 9 * 3600
    close_seconds = (15 * 3600) + (30 * 60)
    if seconds < open_seconds:
        return "090000"
    if seconds > close_seconds:
        return "153000"
    return f"{int(current.hour):02d}{int(current.minute):02d}{int(current.second):02d}"


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        return float(text)
    except Exception:
        return None


def _to_int(value: Any) -> Optional[int]:
    number = _to_float(value)
    if number is None:
        return None
    return int(number)


def _first_present(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _output_rows(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    for key in ("output2", "output", "Output", "output1"):
        value = payload.get(key)
        if isinstance(value, list):
            return [dict(row) for row in value if isinstance(row, dict)]
    value = payload.get("output")
    if isinstance(value, dict):
        return [dict(value)]
    return []


def _rank_value(row: Mapping[str, Any]) -> Optional[int]:
    value = _first_present(row, "data_rank", "rank", "rn", "순위")
    number = _to_int(value)
    return number if number is not None else None


def _find_symbol_row(symbol: str, rows: Iterable[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    code = normalize_kr_stock_code(symbol)
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        row_code = normalize_kr_stock_code(
            str(_first_present(row, "mksc_shrn_iscd", "stck_shrn_iscd", "isu_cd", "pdno", "ticker") or "")
        )
        if row_code == code:
            return dict(row)
    return None


def normalize_kis_rank_membership(
    symbol: str,
    *,
    volume_rank_payload: Optional[Mapping[str, Any]] = None,
    fluctuation_rank_payload: Optional[Mapping[str, Any]] = None,
    volume_power_rank_payload: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    rank_payloads = {
        "volume_rank": volume_rank_payload,
        "fluctuation_rank": fluctuation_rank_payload,
        "volume_power_rank": volume_power_rank_payload,
    }
    result: Dict[str, Any] = {
        "source": "kis_openapi",
        "source_status": "ok",
        "checked": False,
        "ticker": normalize_kr_stock_code(symbol),
        "present_in_any_rank": False,
    }
    for key, payload in rank_payloads.items():
        if not isinstance(payload, Mapping):
            continue
        rows = _output_rows(payload)
        result["checked"] = True
        result[f"{key}_row_count"] = len(rows)
        row = _find_symbol_row(symbol, rows)
        result[f"{key}_present"] = bool(row)
        result[key] = _rank_value(row or {}) if row else None
        if row:
            result["present_in_any_rank"] = True
            result[f"{key}_name"] = _first_present(row, "hts_kor_isnm", "prdt_name", "name")
            result[f"{key}_raw"] = row
    return result if result["checked"] else {}


def normalize_kis_vi_status(symbol: str, payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    rows = _output_rows(payload)
    row = _find_symbol_row(symbol, rows)
    return {
        "source": "kis_openapi",
        "source_status": "ok",
        "checked": True,
        "ticker": normalize_kr_stock_code(symbol),
        "row_count": len(rows),
        "triggered": bool(row),
        "raw": row or {},
    }


def normalize_kis_news_titles(
    payload: Optional[Mapping[str, Any]],
    *,
    symbol: str = "",
    stock_name: str = "",
) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"source": "kis_openapi", "source_status": "not_requested", "checked": False, "rows": []}
    raw_rows = _output_rows(payload)
    filter_result = filter_kis_news_rows_for_symbol(raw_rows, symbol=symbol, stock_name=stock_name)
    filtered_rows = filter_result.get("rows")
    rows = list(filtered_rows) if isinstance(filtered_rows, list) else raw_rows
    scope = classify_kis_news_source_scope(
        symbol=symbol,
        stock_name=stock_name,
        rows=rows,
        checked=True,
        news_count=len(rows),
    )
    scope = dict(scope)
    scope_warnings = list(scope.get("warnings") or [])
    for warning in filter_result.get("warnings") or []:
        if warning not in scope_warnings:
            scope_warnings.append(str(warning))
    scope["warnings"] = scope_warnings
    evidence = dict(scope.get("evidence") or {})
    evidence.update(
        {
            "raw_news_count": int(filter_result.get("raw_news_count") or len(raw_rows)),
            "rows_filtered_out_count": int(filter_result.get("rows_filtered_out_count") or 0),
            "matched_rows_count": int(filter_result.get("matched_rows_count") or len(rows)),
            "scope_filter_policy": filter_result.get("filter_policy"),
            "scope_filter_applied": bool(filter_result.get("filter_applied")),
        }
    )
    scope["evidence"] = evidence
    return {
        "source": "kis_openapi",
        "source_status": "ok",
        "checked": True,
        "news_count": len(rows),
        "raw_news_count": int(filter_result.get("raw_news_count") or len(raw_rows)),
        "rows_filtered_out_count": int(filter_result.get("rows_filtered_out_count") or 0),
        "matched_rows_count": int(filter_result.get("matched_rows_count") or len(rows)),
        "source_scope_filter_applied": bool(filter_result.get("filter_applied")),
        "source_scope_filter_policy": filter_result.get("filter_policy"),
        "source_scope_filter_warnings": list(filter_result.get("warnings") or []),
        "rows": rows,
        "source_scope": scope.get("source_scope"),
        "source_scope_confidence": scope.get("source_scope_confidence"),
        "source_scope_metadata": scope,
        "promotion_blocked": bool(scope.get("promotion_blocked")),
        "promotion_block_reason": scope.get("promotion_block_reason"),
    }


def _first_row(payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    rows = _output_rows(payload)
    return dict(rows[0]) if rows else {}


def normalize_kis_stock_info(symbol: str, payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"source": "kis_openapi", "source_status": "not_requested", "checked": False}
    row = _first_row(payload)
    row_count = len(_output_rows(payload))
    market_code = _first_present(row, "mket_id_cd", "mrkt_div_cls_code", "market_code")
    market_name = _first_present(row, "mket_id_cd_name", "rprs_mrkt_kor_name", "market_name")
    if not market_name:
        market_name = {"STK": "KOSPI", "KSQ": "KOSDAQ", "KNX": "KONEX"}.get(str(market_code or "").upper())
    return {
        "source": "kis_openapi",
        "source_status": "ok" if row else "empty_output",
        "checked": True,
        "ticker": normalize_kr_stock_code(symbol),
        "row_count": row_count,
        "product_code": _first_present(row, "pdno", "PDNO", "stck_shrn_iscd", "mksc_shrn_iscd"),
        "product_name": _first_present(row, "prdt_name", "prdt_abrv_name", "hts_kor_isnm", "name"),
        "market_code": market_code,
        "market_name": market_name,
        "stock_type": _first_present(row, "scty_dvsn_name", "prdt_clsf_name", "stock_type", "stck_kind_cd", "scty_grp_id_cd"),
        "listed_date": _first_present(
            row,
            "lstg_dt",
            "list_dt",
            "listed_date",
            "scts_mket_lstg_dt",
            "kosdaq_mket_lstg_dt",
            "frbd_mket_lstg_dt",
        ),
        "sector_name": _first_present(
            row,
            "bstp_kor_isnm",
            "sector_name",
            "industry_name",
            "std_idst_clsf_cd_name",
            "idx_bztp_mcls_cd_name",
        ),
        "standard_industry_code": _first_present(row, "std_idst_clsf_cd", "industry_code"),
        "large_sector_name": _first_present(row, "idx_bztp_lcls_cd_name"),
        "mid_sector_name": _first_present(row, "idx_bztp_mcls_cd_name"),
        "small_sector_name": _first_present(row, "idx_bztp_scls_cd_name"),
        "listed_shares": _to_int(_first_present(row, "lstg_stqt", "listed_shares")),
        "capital_amount": _to_float(_first_present(row, "cpta", "capital_amount")),
        "par_value": _to_float(_first_present(row, "papr", "par_value")),
        "kospi200_item": _first_present(row, "kospi200_item_yn"),
        "trade_stop": _first_present(row, "tr_stop_yn", "nxt_tr_stop_yn"),
        "admin_item": _first_present(row, "admn_item_yn"),
        "status_code": _first_present(row, "prdt_sale_stat_cd", "iscd_stat_cls_code", "status_code"),
        "raw": row,
    }


def normalize_kis_financial_ratio(symbol: str, payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"source": "kis_openapi", "source_status": "not_requested", "checked": False}
    row = _first_row(payload)
    row_count = len(_output_rows(payload))
    return {
        "source": "kis_openapi",
        "source_status": "ok" if row else "empty_output",
        "checked": True,
        "ticker": normalize_kr_stock_code(symbol),
        "row_count": row_count,
        "statement_period": _first_present(row, "stac_yymm", "stac_month", "statement_period"),
        "revenue_growth_rate": _to_float(_first_present(row, "grs", "revenue_growth_rate", "sale_inrt")),
        "operating_profit_margin": _to_float(_first_present(row, "bsop_prfi_inrt", "operating_profit_margin")),
        "net_income_margin": _to_float(_first_present(row, "ntin_inrt", "net_income_margin")),
        "roe": _to_float(_first_present(row, "roe_val", "roe", "self_cptl_ntin_inrt")),
        "eps": _to_float(_first_present(row, "eps", "eps_val")),
        "bps": _to_float(_first_present(row, "bps", "bps_val")),
        "per": _to_float(_first_present(row, "per", "per_val")),
        "pbr": _to_float(_first_present(row, "pbr", "pbr_val")),
        "debt_ratio": _to_float(_first_present(row, "lblt_rate", "debt_ratio")),
        "current_ratio": _to_float(_first_present(row, "crnt_rate", "current_ratio")),
        "reserve_ratio": _to_float(_first_present(row, "rsrv_rate", "reserve_ratio")),
        "raw": row,
    }


def _parse_date(value: Any) -> Optional[pd.Timestamp]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return pd.to_datetime(text, format="%Y%m%d")
    except Exception:
        try:
            return pd.to_datetime(text)
        except Exception:
            return None


def _parse_datetime(date_value: Any, time_value: Any) -> Optional[pd.Timestamp]:
    date_text = str(date_value or "").strip()
    time_text = str(time_value or "").strip().zfill(6)
    if not date_text or not time_text:
        return None
    try:
        return pd.to_datetime(date_text + time_text[:6], format="%Y%m%d%H%M%S")
    except Exception:
        return None


def normalize_kis_daily_bars(symbol: str, payload: Mapping[str, Any]) -> pd.DataFrame:
    """Convert KIS daily chart payload into the OHLCV contract used by scanners."""

    rows = []
    for raw in _output_rows(payload):
        date_idx = _parse_date(_first_present(raw, "stck_bsop_date", "bsop_date", "date", "Date"))
        if date_idx is None:
            continue
        row = {
            "Date": date_idx,
            "Open": _to_float(_first_present(raw, "stck_oprc", "oprc", "open", "Open")),
            "High": _to_float(_first_present(raw, "stck_hgpr", "hgpr", "high", "High")),
            "Low": _to_float(_first_present(raw, "stck_lwpr", "lwpr", "low", "Low")),
            "Close": _to_float(_first_present(raw, "stck_clpr", "stck_prpr", "clpr", "close", "Close")),
            "Volume": _to_float(_first_present(raw, "acml_vol", "cntg_vol", "volume", "Volume")),
            "Value": _to_float(_first_present(raw, "acml_tr_pbmn", "tr_pbmn", "value", "Value")),
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).set_index("Date").sort_index()
    keep = ["Open", "High", "Low", "Close", "Volume"]
    frame = frame[[col for col in keep if col in frame.columns]]
    return frame.dropna(subset=[col for col in keep if col in frame.columns], how="any")


def normalize_kis_minute_bars(
    symbol: str,
    payload: Mapping[str, Any],
    *,
    trade_date: str = "",
) -> pd.DataFrame:
    """Convert KIS same-day or historical minute payload into OHLCV bars."""

    rows = []
    fallback_date = str(trade_date or datetime.now().strftime("%Y%m%d")).strip()
    for raw in _output_rows(payload):
        date_value = _first_present(raw, "stck_bsop_date", "bsop_date", "date", "Date") or fallback_date
        time_value = _first_present(raw, "stck_cntg_hour", "cntg_hour", "time", "Time")
        dt_idx = _parse_datetime(date_value, time_value)
        if dt_idx is None:
            continue
        close = _to_float(_first_present(raw, "stck_prpr", "stck_clpr", "clpr", "close", "Close"))
        row = {
            "Date": dt_idx,
            "Open": _to_float(_first_present(raw, "stck_oprc", "oprc", "open", "Open")) or close,
            "High": _to_float(_first_present(raw, "stck_hgpr", "hgpr", "high", "High")) or close,
            "Low": _to_float(_first_present(raw, "stck_lwpr", "lwpr", "low", "Low")) or close,
            "Close": close,
            "Volume": _to_float(_first_present(raw, "cntg_vol", "acml_vol", "volume", "Volume")),
            "Value": _to_float(_first_present(raw, "acml_tr_pbmn", "tr_pbmn", "value", "Value")),
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).set_index("Date").sort_index()
    keep = ["Open", "High", "Low", "Close", "Volume"]
    frame = frame[[col for col in keep if col in frame.columns]]
    return frame.dropna(subset=[col for col in keep if col in frame.columns], how="any")


def normalize_kis_quote_for_operational_fields(quote: Mapping[str, Any]) -> Dict[str, Any]:
    warnings = list(quote.get("warnings") or []) if isinstance(quote.get("warnings"), list) else []
    status_warning = quote.get("status_warning")
    if status_warning and status_warning not in warnings:
        warnings.append(str(status_warning))
    return {
        "source": "kis_openapi",
        "source_status": quote.get("source_status") or "unknown",
        "ticker": normalize_kr_stock_code(str(quote.get("ticker") or "")),
        "snapshot_at": quote.get("snapshot_at"),
        "current_price": _to_float(quote.get("last_price")),
        "last_price": _to_float(quote.get("last_price")),
        "entry_reference_price": _to_float(quote.get("last_price")),
        "day_change_pct": _to_float(quote.get("day_change_pct")),
        "prev_pct_change": _to_float(quote.get("day_change_pct")),
        "session_open": _to_float(quote.get("session_open")),
        "session_high": _to_float(quote.get("session_high")),
        "session_low": _to_float(quote.get("session_low")),
        "volume": _to_int(quote.get("volume")),
        "value_traded": _to_float(quote.get("value_traded")),
        "turnover_amount": _to_float(quote.get("value_traded")),
        "volume_ratio": _to_float(quote.get("prev_volume_ratio")),
        "prev_volume_ratio": _to_float(quote.get("prev_volume_ratio")),
        "weighted_avg_price": _to_float(quote.get("weighted_avg_price")),
        "market_cap": _to_float(quote.get("market_cap")),
        "per": _to_float(quote.get("per")),
        "pbr": _to_float(quote.get("pbr")),
        "eps": _to_float(quote.get("eps")),
        "bps": _to_float(quote.get("bps")),
        "high_250d": _to_float(quote.get("high_250d")),
        "low_250d": _to_float(quote.get("low_250d")),
        "high_250d_gap_pct": _to_float(quote.get("high_250d_gap_pct")),
        "low_250d_gap_pct": _to_float(quote.get("low_250d_gap_pct")),
        "market_name": quote.get("market_name"),
        "sector_name": quote.get("sector_name"),
        "status_code": quote.get("status_code"),
        "status_warning": status_warning,
        "warnings": warnings,
    }


def normalize_kis_flow_for_whale_contract(flow: Mapping[str, Any]) -> Dict[str, Any]:
    f1 = _to_float(flow.get("foreigner_1d")) or 0.0
    i1 = _to_float(flow.get("institution_1d")) or 0.0
    r1 = _to_float(flow.get("retail_1d")) or 0.0
    f3 = _to_float(flow.get("foreigner_3d")) or 0.0
    i3 = _to_float(flow.get("institution_3d")) or 0.0
    r3 = _to_float(flow.get("retail_3d")) or 0.0
    f10 = _to_float(flow.get("foreigner_10d")) or 0.0
    i10 = _to_float(flow.get("institution_10d")) or 0.0
    r10 = _to_float(flow.get("retail_10d")) or 0.0

    whale_1d = f1 + i1
    whale_3d = f3 + i3
    whale_10d = f10 + i10
    total_abs_1d = abs(f1) + abs(i1) + abs(r1)
    total_abs_10d = abs(f10) + abs(i10) + abs(r10)

    score = 50
    if total_abs_10d > 0:
        score += int((whale_10d / total_abs_10d) * 25)
    if total_abs_1d > 0:
        score += int((whale_1d / total_abs_1d) * 35)
    if i1 > 0 and f1 > 0:
        score += 10
    if i1 < 0 and f1 < 0:
        score -= 15
    if whale_1d < 0:
        score -= 15
    if whale_1d > 0 and whale_10d > 0:
        score += 8
    if whale_1d < 0 and whale_10d > 0:
        score -= 10
    if r1 > 0 and r1 > max(abs(whale_1d) * 1.5, 1.0):
        score = min(score, 40)

    buyers = [("foreign", f1), ("institution", i1), ("retail", r1)]
    positive = [item for item in buyers if item[1] > 0]
    negative = [item for item in buyers if item[1] < 0]
    buy_dominant = max(positive, key=lambda item: item[1]) if positive else (None, 0.0)
    sell_dominant = min(negative, key=lambda item: item[1]) if negative else (None, 0.0)
    valid = str(flow.get("source_status") or "").lower() == "ok" and total_abs_1d > 0

    return {
        "whale_score": max(0, min(100, int(score))),
        "foreigner": int(f1),
        "institution": int(i1),
        "retail": int(r1),
        "foreign_flow": int(f1),
        "institution_flow": int(i1),
        "retail_flow": int(r1),
        "foreigner_1d": int(f1),
        "institution_1d": int(i1),
        "retail_1d": int(r1),
        "foreigner_3d": int(f3),
        "institution_3d": int(i3),
        "retail_3d": int(r3),
        "foreigner_10d": int(f10),
        "institution_10d": int(i10),
        "retail_10d": int(r10),
        "whale_flow": int(whale_1d),
        "whale_flow_1d": int(whale_1d),
        "whale_flow_3d": int(whale_3d),
        "whale_flow_10d": int(whale_10d),
        "flow_window": "1d",
        "flow_asof": flow.get("flow_asof"),
        "flow_unit": flow.get("flow_unit") or "source_units",
        "valid": bool(valid),
        "type": "KR",
        "flow_source": "kis_openapi",
        "warnings": list(flow.get("warnings") or []),
        "buy_dominant": buy_dominant[0],
        "buy_dominant_flow": int(buy_dominant[1]) if buy_dominant[0] else 0,
        "sell_dominant": sell_dominant[0],
        "sell_dominant_flow": int(sell_dominant[1]) if sell_dominant[0] else 0,
        "total_abs_flow": int(total_abs_1d),
        "total_abs_flow_10d": int(total_abs_10d),
    }


def _return_pct(frame: pd.DataFrame, lookback: int) -> Optional[float]:
    if frame is None or frame.empty or "Close" not in frame.columns or len(frame) <= lookback:
        return None
    latest = _to_float(frame["Close"].iloc[-1])
    base = _to_float(frame["Close"].iloc[-1 - lookback])
    if latest is None or base in (None, 0):
        return None
    return round(((latest - float(base)) / float(base)) * 100.0, 4)


def _volume_ratio(frame: pd.DataFrame, lookback: int = 20) -> Optional[float]:
    if frame is None or frame.empty or "Volume" not in frame.columns or len(frame) <= lookback:
        return None
    latest = _to_float(frame["Volume"].iloc[-1])
    base = pd.to_numeric(frame["Volume"].iloc[-1 - lookback : -1], errors="coerce").dropna()
    if latest is None or base.empty:
        return None
    avg = float(base.mean())
    if avg <= 0:
        return None
    return round(float(latest) / avg, 4)


def _daily_ohlcv_summary(frame: pd.DataFrame) -> Dict[str, Any]:
    if frame is None or frame.empty or "Close" not in frame.columns:
        return {"source": "kis_openapi", "bar_count": 0}

    close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
    high = pd.to_numeric(frame["High"], errors="coerce").dropna() if "High" in frame.columns else pd.Series(dtype=float)
    low = pd.to_numeric(frame["Low"], errors="coerce").dropna() if "Low" in frame.columns else pd.Series(dtype=float)
    if close.empty:
        return {"source": "kis_openapi", "bar_count": int(len(frame))}

    latest_close = _to_float(close.iloc[-1])
    latest_high = _to_float(high.iloc[-1]) if not high.empty else None
    latest_low = _to_float(low.iloc[-1]) if not low.empty else None

    close_location_pct = None
    if latest_close is not None and latest_high is not None and latest_low is not None and latest_high > latest_low:
        close_location_pct = round((latest_close - latest_low) / (latest_high - latest_low) * 100.0, 4)

    high_52w = _to_float(high.tail(252).max()) if not high.empty else None
    pct_from_52w_high = None
    if latest_close is not None and high_52w not in (None, 0):
        pct_from_52w_high = round((latest_close - float(high_52w)) / float(high_52w) * 100.0, 4)

    latest_index = frame.index[-1] if len(frame.index) else None
    if hasattr(latest_index, "isoformat"):
        latest_date = latest_index.isoformat()
    else:
        latest_date = str(latest_index) if latest_index is not None else None

    return {
        "source": "kis_openapi",
        "bar_count": int(len(frame)),
        "latest_date": latest_date,
        "latest_close": latest_close,
        "ma5": _to_float(close.tail(5).mean()) if len(close) >= 5 else None,
        "ma20": _to_float(close.tail(20).mean()) if len(close) >= 20 else None,
        "ma60": _to_float(close.tail(60).mean()) if len(close) >= 60 else None,
        "return_5d_pct": _return_pct(frame, 5),
        "return_20d_pct": _return_pct(frame, 20),
        "return_60d_pct": _return_pct(frame, 60),
        "volume_ratio_20d": _volume_ratio(frame, 20),
        "prior_20d_high": _to_float(high.iloc[:-1].tail(20).max()) if not high.empty and len(high) >= 21 else None,
        "range_20d_high": _to_float(high.tail(20).max()) if not high.empty else None,
        "range_20d_low": _to_float(low.tail(20).min()) if not low.empty else None,
        "close_location_pct": close_location_pct,
        "high_52w": high_52w,
        "pct_from_52w_high": pct_from_52w_high,
    }


def build_kis_sidecar_snapshot(
    symbol: str,
    *,
    market: str = "",
    quote_snapshot: Optional[Mapping[str, Any]] = None,
    daily_bars: Optional[pd.DataFrame] = None,
    minute_bars: Optional[pd.DataFrame] = None,
    investor_flow: Optional[Mapping[str, Any]] = None,
    rank_membership: Optional[Mapping[str, Any]] = None,
    vi_status: Optional[Mapping[str, Any]] = None,
    news_titles: Optional[Iterable[Mapping[str, Any]]] = None,
    news_titles_checked: bool = False,
    news_title_count: Optional[int] = None,
    news_raw_count: Optional[int] = None,
    news_rows_filtered_out_count: Optional[int] = None,
    news_scope_filter_applied: Optional[bool] = None,
    news_scope_filter_policy: str = "",
    news_scope_filter_warnings: Optional[Iterable[str]] = None,
    stock_info: Optional[Mapping[str, Any]] = None,
    financial_ratio: Optional[Mapping[str, Any]] = None,
    generated_at: str = "",
) -> Dict[str, Any]:
    quote_fields = normalize_kis_quote_for_operational_fields(quote_snapshot or {}) if quote_snapshot else {}
    flow_fields = normalize_kis_flow_for_whale_contract(investor_flow or {}) if investor_flow else {}
    daily = daily_bars if isinstance(daily_bars, pd.DataFrame) else pd.DataFrame()
    minute = minute_bars if isinstance(minute_bars, pd.DataFrame) else pd.DataFrame()
    rank = dict(rank_membership or {})
    vi = dict(vi_status or {})
    news_list = [dict(item) for item in (news_titles or []) if isinstance(item, Mapping)]
    news_checked = bool(news_titles_checked or news_list)
    news_count = int(news_title_count) if news_title_count is not None else len(news_list)
    raw_news_count = int(news_raw_count) if news_raw_count is not None else news_count
    rows_filtered_out_count = int(news_rows_filtered_out_count or 0)
    scope_filter_applied = bool(news_scope_filter_applied) if news_scope_filter_applied is not None else False
    scope_filter_warnings = [str(item) for item in (news_scope_filter_warnings or []) if str(item).strip()]
    stock = dict(stock_info or {})
    financial = dict(financial_ratio or {})
    news_scope = classify_kis_news_source_scope(
        symbol=symbol,
        stock_name=str(stock.get("product_name") or ""),
        rows=news_list,
        checked=news_checked,
        news_count=news_count,
    )
    news_scope = dict(news_scope)
    news_scope_warnings = list(news_scope.get("warnings") or [])
    for warning in scope_filter_warnings:
        if warning not in news_scope_warnings:
            news_scope_warnings.append(warning)
    news_scope["warnings"] = news_scope_warnings
    news_scope_evidence = dict(news_scope.get("evidence") or {})
    news_scope_evidence.update(
        {
            "raw_news_count": raw_news_count,
            "rows_filtered_out_count": rows_filtered_out_count,
            "matched_rows_count": news_count,
            "scope_filter_applied": scope_filter_applied,
            "scope_filter_policy": news_scope_filter_policy or None,
        }
    )
    news_scope["evidence"] = news_scope_evidence
    daily_summary = _daily_ohlcv_summary(daily)
    has_financial_ratio = any(
        financial.get(key) is not None
        for key in (
            "revenue_growth_rate",
            "operating_profit_margin",
            "net_income_margin",
            "roe",
            "eps",
            "bps",
            "per",
            "pbr",
            "debt_ratio",
            "current_ratio",
            "reserve_ratio",
        )
    )

    coverage = {
        "quote_snapshot": bool(quote_fields and quote_fields.get("current_price") is not None),
        "daily_ohlcv": bool(not daily.empty and all(col in daily.columns for col in ["Open", "High", "Low", "Close", "Volume"])),
        "daily_ohlcv_50d": bool(not daily.empty and len(daily) >= 50),
        "minute_ohlcv": bool(not minute.empty),
        "investor_flow": bool(flow_fields.get("valid")),
        "rank_membership": bool(rank.get("checked") or rank),
        "vi_status": bool(vi.get("checked") or vi),
        "news_titles": bool(news_checked),
        "stock_info": bool(stock.get("checked") or stock),
        "financial_ratio": bool(financial.get("checked") or financial),
        "financial_style": any(quote_fields.get(key) is not None for key in ("per", "pbr", "eps", "bps")) or has_financial_ratio,
    }

    model_features = {
        "kis_current_price": quote_fields.get("current_price"),
        "kis_day_change_pct": quote_fields.get("day_change_pct"),
        "kis_value_traded": quote_fields.get("value_traded"),
        "kis_prev_volume_ratio": quote_fields.get("prev_volume_ratio"),
        "kis_market_cap": quote_fields.get("market_cap"),
        "kis_per": quote_fields.get("per"),
        "kis_pbr": quote_fields.get("pbr"),
        "kis_high_250d_gap_pct": quote_fields.get("high_250d_gap_pct"),
        "kis_low_250d_gap_pct": quote_fields.get("low_250d_gap_pct"),
        "kis_whale_score": flow_fields.get("whale_score"),
        "kis_foreigner_1d": flow_fields.get("foreigner_1d"),
        "kis_institution_1d": flow_fields.get("institution_1d"),
        "kis_retail_1d": flow_fields.get("retail_1d"),
        "kis_whale_flow_3d": flow_fields.get("whale_flow_3d"),
        "kis_whale_flow_10d": flow_fields.get("whale_flow_10d"),
        "kis_daily_bar_count": int(len(daily)) if not daily.empty else 0,
        "kis_daily_return_5d_pct": _return_pct(daily, 5),
        "kis_daily_return_20d_pct": _return_pct(daily, 20),
        "kis_daily_return_60d_pct": daily_summary.get("return_60d_pct"),
        "kis_daily_volume_ratio_20d": _volume_ratio(daily, 20),
        "kis_daily_ma5": daily_summary.get("ma5"),
        "kis_daily_ma20": daily_summary.get("ma20"),
        "kis_daily_ma60": daily_summary.get("ma60"),
        "kis_daily_prior_20d_high": daily_summary.get("prior_20d_high"),
        "kis_daily_range_20d_high": daily_summary.get("range_20d_high"),
        "kis_daily_range_20d_low": daily_summary.get("range_20d_low"),
        "kis_daily_close_location_pct": daily_summary.get("close_location_pct"),
        "kis_daily_high_52w": daily_summary.get("high_52w"),
        "kis_daily_pct_from_52w_high": daily_summary.get("pct_from_52w_high"),
        "kis_minute_bar_count": int(len(minute)) if not minute.empty else 0,
        "kis_rank_volume": rank.get("volume_rank"),
        "kis_rank_fluctuation": rank.get("fluctuation_rank"),
        "kis_rank_volume_power": rank.get("volume_power_rank"),
        "kis_vi_triggered": vi.get("triggered"),
        "kis_news_title_count": news_count,
        "kis_news_raw_title_count": raw_news_count,
        "kis_news_rows_filtered_out_count": rows_filtered_out_count,
        "kis_news_source_scope_confidence": news_scope.get("source_scope_confidence"),
        "kis_news_source_scope_ambiguous": bool(news_scope.get("promotion_blocked")),
        "kis_news_promotion_blocked": bool(news_scope.get("promotion_blocked")),
        "kis_news_source_scope": news_scope.get("source_scope"),
        "kis_stock_market_code": stock.get("market_code"),
        "kis_stock_market_name": stock.get("market_name"),
        "kis_stock_type": stock.get("stock_type"),
        "kis_stock_listed_date": stock.get("listed_date"),
        "kis_stock_status_code": stock.get("status_code"),
        "kis_stock_sector_name": stock.get("sector_name"),
        "kis_stock_standard_industry_code": stock.get("standard_industry_code"),
        "kis_stock_listed_shares": stock.get("listed_shares"),
        "kis_stock_capital_amount": stock.get("capital_amount"),
        "kis_stock_par_value": stock.get("par_value"),
        "kis_stock_kospi200_item": stock.get("kospi200_item"),
        "kis_stock_trade_stop": stock.get("trade_stop"),
        "kis_stock_admin_item": stock.get("admin_item"),
        "kis_financial_statement_period": financial.get("statement_period"),
        "kis_financial_revenue_growth_rate": financial.get("revenue_growth_rate"),
        "kis_financial_operating_profit_margin": financial.get("operating_profit_margin"),
        "kis_financial_net_income_margin": financial.get("net_income_margin"),
        "kis_financial_roe": financial.get("roe"),
        "kis_financial_eps": financial.get("eps"),
        "kis_financial_bps": financial.get("bps"),
        "kis_financial_per": financial.get("per"),
        "kis_financial_pbr": financial.get("pbr"),
        "kis_financial_debt_ratio": financial.get("debt_ratio"),
        "kis_financial_current_ratio": financial.get("current_ratio"),
        "kis_financial_reserve_ratio": financial.get("reserve_ratio"),
    }

    ready = {
        "price_snapshot_ready": coverage["quote_snapshot"],
        "scanner_daily_ready": coverage["daily_ohlcv_50d"],
        "intraday_ready": coverage["minute_ohlcv"],
        "flow_ready": coverage["investor_flow"],
        "model_sidecar_ready": coverage["quote_snapshot"] and coverage["daily_ohlcv"],
        "production_replacement_ready": bool(
            coverage["quote_snapshot"]
            and coverage["daily_ohlcv_50d"]
            and coverage["minute_ohlcv"]
            and coverage["investor_flow"]
            and coverage["rank_membership"]
            and coverage["vi_status"]
            and coverage["news_titles"]
            and not bool(news_scope.get("promotion_blocked"))
            and coverage["stock_info"]
            and coverage["financial_ratio"]
        ),
    }
    warnings = list(quote_fields.get("warnings") or []) + list(flow_fields.get("warnings") or [])
    for key, ok in ready.items():
        if not ok:
            warnings.append(f"{key}=false")
    warnings.extend(news_scope.get("warnings") or [])
    warnings.extend(scope_filter_warnings)
    if rows_filtered_out_count > 0:
        warnings.append("kis_news_scope_rows_filtered_out")
    if news_scope.get("promotion_blocked"):
        warnings.append(str(news_scope.get("promotion_block_reason") or "KIS_NEWS_SCOPE_AMBIGUOUS"))

    return {
        "contract_version": KIS_OPERATIONAL_CONTRACT_VERSION,
        "feature_origin": "kis_openapi_sidecar",
        "ticker": normalize_kr_stock_code(symbol),
        "market": market,
        "generated_at": generated_at or datetime.now().isoformat(),
        "operational_fields": quote_fields,
        "daily_ohlcv_summary": daily_summary,
        "flow_contract": flow_fields,
        "rank_contract": rank,
        "vi_contract": vi,
        "news_contract": {
            "source": "kis_openapi",
            "source_status": "ok" if news_checked else "not_requested",
            "checked": news_checked,
            "news_count": news_count,
            "raw_news_count": raw_news_count,
            "rows_filtered_out_count": rows_filtered_out_count,
            "matched_rows_count": news_count,
            "rows_stored_count": len(news_list),
            "rows_truncated": bool(news_count > len(news_list)),
            "rows": news_list,
            "source_scope_filter_applied": scope_filter_applied,
            "source_scope_filter_policy": news_scope_filter_policy or None,
            "source_scope_filter_warnings": scope_filter_warnings,
            "source_scope": news_scope.get("source_scope"),
            "source_scope_confidence": news_scope.get("source_scope_confidence"),
            "source_scope_metadata": news_scope,
            "promotion_blocked": bool(news_scope.get("promotion_blocked")),
            "promotion_block_reason": news_scope.get("promotion_block_reason"),
            "promotion_blocking_reasons": news_scope.get("promotion_blocking_reasons") or [],
        },
        "stock_info_contract": stock,
        "financial_ratio_contract": financial,
        "model_candidate_features": model_features,
        "coverage": coverage,
        "replacement_readiness": ready,
        "warnings": sorted(set(str(item) for item in warnings if item)),
    }


def kis_replacement_roadmap() -> Dict[str, Any]:
    return {
        "target": "KIS-backed KR operation with existing scanner/planner contracts preserved",
        "principle": "Change source adapters first, then promote only after dual-run gates pass.",
        "phases": [
            {
                "phase": 1,
                "name": "contract_adapter",
                "status": "implemented_in_this_issue",
                "exit_gate": "KIS quote, daily, minute, and flow payloads normalize to existing OHLCV/flow contracts in tests.",
            },
            {
                "phase": 2,
                "name": "sidecar_archive",
                "status": "implemented",
                "exit_gate": "Every KR scanner candidate persists KIS sidecar features without changing recommendation order.",
            },
            {
                "phase": 3,
                "name": "deep_analysis_source_contract",
                "status": "implemented",
                "exit_gate": "Top Deep consumes KIS sidecar evidence first and stores scan/deep as-of source timing.",
            },
            {
                "phase": 4,
                "name": "dual_run_parity",
                "status": "planned",
                "exit_gate": "KIS primary vs legacy fallback produces >=99% price/OHLCV parity on eligible KR candidates for 10 trading days.",
            },
            {
                "phase": 5,
                "name": "production_source_promotion",
                "status": "planned",
                "exit_gate": "KIS primary with legacy fallback passes scanner, Discord, archive, top-deep, and learning replay checks.",
            },
            {
                "phase": 6,
                "name": "model_lift_promotion",
                "status": "planned",
                "exit_gate": "KIS-augmented challenger beats current gate by segment without worsening tail-loss metrics.",
            },
        ],
        "high_value_kis_features": [
            "trade value and previous-volume ratio from official quote snapshots",
            "foreign/institution/retail daily flow when the time-gated endpoint is available",
            "volume, fluctuation, execution-strength, and VI rank membership",
            "stock information such as market, listing date, and sale/status flags",
            "financial ratios and 250-day high/low distance",
            "KIS daily MA/range/return features for Top Deep readiness and chase-risk checks",
            "same-day minute bars for intraday volume curve and VWAP features",
            "KIS news-title count as a low-cost event-intensity feature",
        ],
    }


__all__ = [
    "KIS_OPERATIONAL_CONTRACT_VERSION",
    "build_kis_sidecar_snapshot",
    "kis_intraday_input_hour",
    "kis_replacement_roadmap",
    "normalize_kis_daily_bars",
    "normalize_kis_financial_ratio",
    "normalize_kis_flow_for_whale_contract",
    "normalize_kis_minute_bars",
    "normalize_kis_news_titles",
    "normalize_kis_quote_for_operational_fields",
    "normalize_kis_rank_membership",
    "normalize_kis_stock_info",
    "normalize_kis_vi_status",
]
