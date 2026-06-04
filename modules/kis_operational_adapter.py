from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pandas as pd

from modules.kis_openapi import normalize_kr_stock_code


KIS_OPERATIONAL_CONTRACT_VERSION = "kis_operational_adapter_v1"


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
    generated_at: str = "",
) -> Dict[str, Any]:
    quote_fields = normalize_kis_quote_for_operational_fields(quote_snapshot or {}) if quote_snapshot else {}
    flow_fields = normalize_kis_flow_for_whale_contract(investor_flow or {}) if investor_flow else {}
    daily = daily_bars if isinstance(daily_bars, pd.DataFrame) else pd.DataFrame()
    minute = minute_bars if isinstance(minute_bars, pd.DataFrame) else pd.DataFrame()
    rank = dict(rank_membership or {})
    vi = dict(vi_status or {})
    news_list = [dict(item) for item in (news_titles or []) if isinstance(item, Mapping)]

    coverage = {
        "quote_snapshot": bool(quote_fields and quote_fields.get("current_price") is not None),
        "daily_ohlcv": bool(not daily.empty and all(col in daily.columns for col in ["Open", "High", "Low", "Close", "Volume"])),
        "daily_ohlcv_50d": bool(not daily.empty and len(daily) >= 50),
        "minute_ohlcv": bool(not minute.empty),
        "investor_flow": bool(flow_fields.get("valid")),
        "rank_membership": bool(rank),
        "vi_status": bool(vi),
        "news_titles": bool(news_list),
        "financial_style": any(quote_fields.get(key) is not None for key in ("per", "pbr", "eps", "bps")),
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
        "kis_daily_volume_ratio_20d": _volume_ratio(daily, 20),
        "kis_minute_bar_count": int(len(minute)) if not minute.empty else 0,
        "kis_rank_volume": rank.get("volume_rank"),
        "kis_rank_fluctuation": rank.get("fluctuation_rank"),
        "kis_rank_volume_power": rank.get("volume_power_rank"),
        "kis_vi_triggered": vi.get("triggered"),
        "kis_news_title_count": len(news_list),
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
        ),
    }
    warnings = list(quote_fields.get("warnings") or []) + list(flow_fields.get("warnings") or [])
    for key, ok in ready.items():
        if not ok:
            warnings.append(f"{key}=false")

    return {
        "contract_version": KIS_OPERATIONAL_CONTRACT_VERSION,
        "feature_origin": "kis_openapi_sidecar",
        "ticker": normalize_kr_stock_code(symbol),
        "market": market,
        "generated_at": generated_at or datetime.now().isoformat(),
        "operational_fields": quote_fields,
        "flow_contract": flow_fields,
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
                "status": "next",
                "exit_gate": "Every KR scanner candidate persists KIS sidecar features without changing recommendation order.",
            },
            {
                "phase": 3,
                "name": "dual_run_parity",
                "status": "planned",
                "exit_gate": "KIS primary vs legacy fallback produces >=99% price/OHLCV parity on eligible KR candidates for 10 trading days.",
            },
            {
                "phase": 4,
                "name": "production_source_promotion",
                "status": "planned",
                "exit_gate": "KIS primary with legacy fallback passes scanner, Discord, archive, top-deep, and learning replay checks.",
            },
            {
                "phase": 5,
                "name": "model_lift_promotion",
                "status": "planned",
                "exit_gate": "KIS-augmented challenger beats current gate by segment without worsening tail-loss metrics.",
            },
        ],
        "high_value_kis_features": [
            "trade value and previous-volume ratio from official quote snapshots",
            "foreign/institution/retail daily flow when the time-gated endpoint is available",
            "volume, fluctuation, execution-strength, and VI rank membership",
            "financial ratios and 250-day high/low distance",
            "same-day minute bars for intraday volume curve and VWAP features",
            "KIS news-title count as a low-cost event-intensity feature",
        ],
    }


__all__ = [
    "KIS_OPERATIONAL_CONTRACT_VERSION",
    "build_kis_sidecar_snapshot",
    "kis_replacement_roadmap",
    "normalize_kis_daily_bars",
    "normalize_kis_flow_for_whale_contract",
    "normalize_kis_minute_bars",
    "normalize_kis_quote_for_operational_fields",
]
