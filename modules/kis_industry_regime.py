from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional


KIS_INDUSTRY_REGIME_VERSION = "kis_industry_regime_v1"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        numeric = float(value)
    except Exception:
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return round(numeric, 6)


def _first_present(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _output_rows(payload: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    raw = payload.get("output2") or payload.get("output") or []
    if isinstance(raw, Mapping):
        raw = [raw]
    return [dict(row) for row in raw if isinstance(row, Mapping)] if isinstance(raw, list) else []


def _parse_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except Exception:
            continue
    return text


def normalize_kis_industry_price(
    payload: Optional[Mapping[str, Any]],
    *,
    index_code: str = "",
    industry_name: str = "",
    market: str = "",
) -> Dict[str, Any]:
    rows = _output_rows(payload)
    row = rows[0] if rows else {}
    return {
        "version": KIS_INDUSTRY_REGIME_VERSION,
        "source": "kis_openapi",
        "source_status": "ok" if row else "empty_output",
        "checked": isinstance(payload, Mapping),
        "index_code": str(index_code or _first_present(row, "bstp_code", "idx_code", "FID_INPUT_ISCD") or ""),
        "industry_name": str(industry_name or _first_present(row, "bstp_kor_isnm", "idx_bztp_name", "industry_name") or ""),
        "market": str(market or ""),
        "current_price": _safe_float(_first_present(row, "bstp_nmix_prpr", "stck_prpr", "current_price")),
        "change": _safe_float(_first_present(row, "bstp_nmix_prdy_vrss", "prdy_vrss", "change")),
        "change_pct": _safe_float(_first_present(row, "bstp_nmix_prdy_ctrt", "prdy_ctrt", "change_pct")),
        "open": _safe_float(_first_present(row, "bstp_nmix_oprc", "stck_oprc", "open")),
        "high": _safe_float(_first_present(row, "bstp_nmix_hgpr", "stck_hgpr", "high")),
        "low": _safe_float(_first_present(row, "bstp_nmix_lwpr", "stck_lwpr", "low")),
        "volume": _safe_float(_first_present(row, "acml_vol", "volume")),
        "raw": row,
    }


def normalize_kis_industry_daily_bars(payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    bars: List[Dict[str, Any]] = []
    for row in _output_rows(payload):
        date_value = _parse_date(_first_present(row, "stck_bsop_date", "date"))
        close = _safe_float(_first_present(row, "bstp_nmix_prpr", "stck_clpr", "close"))
        if not date_value or close is None:
            continue
        bars.append(
            {
                "date": date_value,
                "open": _safe_float(_first_present(row, "bstp_nmix_oprc", "stck_oprc", "open")),
                "high": _safe_float(_first_present(row, "bstp_nmix_hgpr", "stck_hgpr", "high")),
                "low": _safe_float(_first_present(row, "bstp_nmix_lwpr", "stck_lwpr", "low")),
                "close": close,
                "volume": _safe_float(_first_present(row, "acml_vol", "volume")),
            }
        )
    bars = sorted(bars, key=lambda item: str(item.get("date") or ""))
    return {
        "version": KIS_INDUSTRY_REGIME_VERSION,
        "source": "kis_openapi",
        "source_status": "ok" if bars else "empty_output",
        "checked": isinstance(payload, Mapping),
        "bar_count": len(bars),
        "bars": bars,
    }


def _return_pct(bars: List[Mapping[str, Any]], periods: int) -> float | None:
    if len(bars) <= periods:
        return None
    latest = _safe_float(bars[-1].get("close"))
    prior = _safe_float(bars[-1 - periods].get("close"))
    if latest is None or prior in (None, 0):
        return None
    return round((latest / float(prior) - 1.0) * 100.0, 6)


def _mean(values: Iterable[float]) -> float | None:
    source = [float(value) for value in values if value is not None]
    if not source:
        return None
    return round(sum(source) / len(source), 6)


def build_kis_industry_regime_overlay(
    *,
    index_code: str,
    price_payload: Optional[Mapping[str, Any]] = None,
    daily_bars_payload: Optional[Mapping[str, Any]] = None,
    industry_name: str = "",
    market: str = "",
) -> Dict[str, Any]:
    price = normalize_kis_industry_price(
        price_payload,
        index_code=index_code,
        industry_name=industry_name,
        market=market,
    )
    daily = normalize_kis_industry_daily_bars(daily_bars_payload)
    bars = daily.get("bars") if isinstance(daily.get("bars"), list) else []
    closes = [_safe_float(row.get("close")) for row in bars]
    latest_close = closes[-1] if closes else price.get("current_price")
    ma5 = _mean([value for value in closes[-5:] if value is not None]) if len(closes) >= 5 else None
    ma20 = _mean([value for value in closes[-20:] if value is not None]) if len(closes) >= 20 else None
    return_5d = _return_pct(bars, 5)
    return_20d = _return_pct(bars, 20)
    change_pct = _safe_float(price.get("change_pct"))

    score = 0.0
    for value, weight in ((change_pct, 2.0), (return_5d, 1.4), (return_20d, 1.0)):
        if value is not None:
            score += max(-10.0, min(10.0, float(value))) * weight
    if latest_close is not None and ma20 not in (None, 0):
        score += max(-8.0, min(8.0, (float(latest_close) / float(ma20) - 1.0) * 100.0))
    score = round(score, 4)
    if score >= 18:
        trend = "strong_positive"
    elif score >= 6:
        trend = "positive"
    elif score <= -18:
        trend = "strong_negative"
    elif score <= -6:
        trend = "negative"
    else:
        trend = "neutral"

    warnings: List[str] = []
    if price.get("source_status") != "ok":
        warnings.append("kis_industry_price_missing")
    if daily.get("source_status") != "ok":
        warnings.append("kis_industry_daily_bars_missing")
    if len(bars) < 21:
        warnings.append("kis_industry_daily_bars_short_history")

    confidence = 0.0
    if price.get("source_status") == "ok":
        confidence += 0.35
    if len(bars) >= 6:
        confidence += 0.25
    if len(bars) >= 21:
        confidence += 0.25
    if change_pct is not None or return_5d is not None or return_20d is not None:
        confidence += 0.15
    confidence = round(min(1.0, confidence), 4)

    return {
        "version": KIS_INDUSTRY_REGIME_VERSION,
        "source": "kis_openapi",
        "checked": bool(price.get("checked") or daily.get("checked")),
        "index_code": str(index_code or ""),
        "industry_name": price.get("industry_name") or industry_name or None,
        "market": price.get("market") or market or None,
        "source_ok": not warnings or set(warnings) == {"kis_industry_daily_bars_short_history"},
        "confidence": confidence,
        "trend": trend,
        "regime_score": score,
        "current_price": latest_close,
        "change_pct": change_pct,
        "return_5d_pct": return_5d,
        "return_20d_pct": return_20d,
        "ma5": ma5,
        "ma20": ma20,
        "bar_count": len(bars),
        "latest_date": bars[-1].get("date") if bars else None,
        "warnings": warnings,
        "price": price,
        "daily_bars": daily,
        "no_dummy_data": True,
    }


__all__ = [
    "KIS_INDUSTRY_REGIME_VERSION",
    "build_kis_industry_regime_overlay",
    "normalize_kis_industry_daily_bars",
    "normalize_kis_industry_price",
]
