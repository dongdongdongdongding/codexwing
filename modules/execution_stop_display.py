from __future__ import annotations

import math
from typing import Any, Dict


STOP_DISPLAY_VERSION = "execution_stop_display_v1"


def _num(value: Any) -> float | None:
    try:
        if value in (None, "", "nan", "None"):
            return None
        numeric = float(str(value).replace(",", "").replace("%", "").strip())
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    except Exception:
        return None


def _first(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _pct_from_price(entry: float | None, stop_price: float | None) -> float | None:
    if entry is None or stop_price is None or entry <= 0:
        return None
    return (stop_price / entry - 1.0) * 100.0


def _price_from_pct(entry: float | None, stop_pct: float | None) -> float | None:
    if entry is None or stop_pct is None or entry <= 0:
        return None
    return entry * (1.0 + stop_pct / 100.0)


def build_execution_stop_display(row: Dict[str, Any], trade_plan: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return the single stop surface the UI/Discord should display.

    For long-only swing entries, the stricter stop is the higher stop price,
    or equivalently the less-negative stop percentage. This is display-only:
    it does not change scanner ranking or candidate selection.
    """
    row = row if isinstance(row, dict) else {}
    trade_plan = trade_plan if isinstance(trade_plan, dict) else {}
    entry = _num(
        _first(
            trade_plan.get("entry_reference_price"),
            row.get("entry_reference_price"),
            row.get("Entry"),
            row.get("매수가(-2%)"),
            row.get("curr_price"),
            row.get("price"),
        )
    )
    raw_pct = _num(_first(row.get("stop_sl_pct"), row.get("SL"), row.get("raw_stop_sl_pct")))
    raw_price = _num(_first(row.get("stop_price"), row.get("raw_stop_price")))
    if raw_pct is None:
        raw_pct = _pct_from_price(entry, raw_price)
    if raw_price is None:
        raw_price = _price_from_pct(entry, raw_pct)

    dynamic_pct = _num(_first(trade_plan.get("stop_sl_pct"), trade_plan.get("dynamic_stop_sl_pct")))
    dynamic_price = _num(_first(trade_plan.get("stop_price"), trade_plan.get("dynamic_stop_price")))
    if dynamic_pct is None:
        dynamic_pct = _pct_from_price(entry, dynamic_price)
    if dynamic_price is None:
        dynamic_price = _price_from_pct(entry, dynamic_pct)

    candidates = []
    if raw_pct is not None:
        candidates.append(("raw_scan", raw_pct, raw_price))
    if dynamic_pct is not None:
        candidates.append(("top_deep_dynamic", dynamic_pct, dynamic_price))
    if not candidates:
        return {
            "version": STOP_DISPLAY_VERSION,
            "entry_reference_price": entry,
            "display_stop_sl_pct": None,
            "display_stop_price": None,
            "display_stop_source": "unavailable",
            "raw_stop_sl_pct": raw_pct,
            "dynamic_stop_sl_pct": dynamic_pct,
            "stop_conflict": False,
            "warnings": ["stop_display_unavailable"],
        }

    source, pct, price = max(candidates, key=lambda item: item[1])
    conflict = raw_pct is not None and dynamic_pct is not None and abs(raw_pct - dynamic_pct) >= 0.5
    warnings = []
    if conflict:
        warnings.append("raw_and_dynamic_stop_diverged_stricter_displayed")
    if source == "raw_scan" and dynamic_pct is not None:
        source = "raw_scan_stricter"
    elif source == "top_deep_dynamic" and raw_pct is not None:
        source = "top_deep_dynamic_stricter"
    return {
        "version": STOP_DISPLAY_VERSION,
        "entry_reference_price": entry,
        "display_stop_sl_pct": round(pct, 6) if pct is not None else None,
        "display_stop_price": round(price, 6) if price is not None else None,
        "display_stop_source": source,
        "raw_stop_sl_pct": round(raw_pct, 6) if raw_pct is not None else None,
        "raw_stop_price": round(raw_price, 6) if raw_price is not None else None,
        "dynamic_stop_sl_pct": round(dynamic_pct, 6) if dynamic_pct is not None else None,
        "dynamic_stop_price": round(dynamic_price, 6) if dynamic_price is not None else None,
        "stop_conflict": conflict,
        "stop_gap_pct_points": round(abs(raw_pct - dynamic_pct), 6) if raw_pct is not None and dynamic_pct is not None else None,
        "warnings": warnings,
    }


__all__ = ["STOP_DISPLAY_VERSION", "build_execution_stop_display"]
