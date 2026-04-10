from __future__ import annotations

from typing import Any, Dict, List


def detect_market_gate_quality(scanner_payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = scanner_payload.get("summary", {}) if isinstance(scanner_payload, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    input_meta = summary.get("input_meta", {}) if isinstance(summary.get("input_meta"), dict) else {}
    market_gate = input_meta.get("market_gate", {}) or summary.get("market_gate", {}) or {}
    if not isinstance(market_gate, dict):
        market_gate = {}

    market = str((scanner_payload.get("run_context") or {}).get("market") or "").upper()
    msg = str(market_gate.get("msg") or "")
    selected_market = str(market_gate.get("selected_market") or "").upper()
    region = str(market_gate.get("region") or "").upper()
    quality_flags: List[str] = []

    is_us = market in {"NASDAQ", "S&P500", "AMEX", "US"}
    is_kr = market in {"KOSPI", "KOSDAQ", "KR"}
    mentions_kr = any(token in msg for token in ["KOSPI", "KOSDAQ"])
    mentions_us = any(token in msg for token in ["NASDAQ", "S&P500", "AMEX"])

    if is_us:
        if mentions_kr:
            quality_flags.append("MARKET_GATE_KR_MESSAGE_ON_US_RUN")
        if region and region != "US":
            quality_flags.append("MARKET_GATE_REGION_MISMATCH_US")
    if is_kr:
        if mentions_us:
            quality_flags.append("MARKET_GATE_US_MESSAGE_ON_KR_RUN")
        if region and region != "KR":
            quality_flags.append("MARKET_GATE_REGION_MISMATCH_KR")

    if selected_market and market and selected_market != market:
        quality_flags.append("MARKET_GATE_SELECTED_MARKET_MISMATCH")

    contaminated = any(
        code in quality_flags
        for code in {
            "MARKET_GATE_KR_MESSAGE_ON_US_RUN",
            "MARKET_GATE_US_MESSAGE_ON_KR_RUN",
            "MARKET_GATE_REGION_MISMATCH_US",
            "MARKET_GATE_REGION_MISMATCH_KR",
            "MARKET_GATE_SELECTED_MARKET_MISMATCH",
        }
    )
    return {
        "market": market,
        "market_gate": market_gate,
        "quality_flags": quality_flags,
        "validation_excluded": bool(contaminated),
    }

