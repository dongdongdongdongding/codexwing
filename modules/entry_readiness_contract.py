from __future__ import annotations

from typing import Any, Dict, List

READINESS_CONTRACT_VERSION = "entry_readiness_contract_v1"


def build_entry_readiness_contract(
    readiness: Dict[str, Any] | None,
    *,
    source: str = "entry_readiness_analysis",
) -> Dict[str, Any]:
    """Flatten entry-readiness analysis into a stable machine contract.

    The contract separates stock quality from buyability. It is not a ranking
    score and does not alter scanner/planner selection.
    """
    readiness = readiness if isinstance(readiness, dict) else {}
    quality = readiness.get("quality") if isinstance(readiness.get("quality"), dict) else {}
    upside = readiness.get("upside") if isinstance(readiness.get("upside"), dict) else {}
    timing = readiness.get("timing") if isinstance(readiness.get("timing"), dict) else {}
    judgment = readiness.get("final_buy_judgment") if isinstance(readiness.get("final_buy_judgment"), dict) else {}
    coverage = readiness.get("data_coverage") if isinstance(readiness.get("data_coverage"), dict) else {}
    structural_risk = readiness.get("structural_exclusion_risk") if isinstance(readiness.get("structural_exclusion_risk"), dict) else {}

    required = [str(item) for item in coverage.get("required_fields") or [] if str(item).strip()]
    available = {str(item) for item in coverage.get("available_fields") or [] if str(item).strip()}
    missing = [item for item in required if item not in available]
    warnings = _unique_texts(readiness.get("warnings"), limit=10)
    safety_overrides = _unique_texts(readiness.get("safety_overrides"), limit=10)
    reason_codes = _reason_codes(upside, safety_overrides, missing)
    exclusion_level = _exclusion_risk_level(judgment, safety_overrides, warnings, structural_risk)
    exclusion_reasons = _exclusion_reasons(structural_risk, safety_overrides)

    return {
        "version": READINESS_CONTRACT_VERSION,
        "source": source,
        "stock_quality_score": _num(quality.get("score")),
        "stock_quality_grade": _text(quality.get("grade")) or "N/A",
        "upside_room_score": _num(upside.get("score")),
        "upside_room_grade": _text(upside.get("grade")) or "N/A",
        "entry_timing_score": _num(timing.get("score")),
        "entry_timing_grade": _text(timing.get("grade")) or "N/A",
        "chase_risk_level": _text(readiness.get("chase_risk_level") or upside.get("chase_risk_level")) or "불명",
        "exclusion_risk_level": exclusion_level,
        "exclusion_reasons": exclusion_reasons,
        "final_action": _text(judgment.get("action")) or "관망",
        "final_action_tone": _text(judgment.get("tone")) or "neutral",
        "action_summary": _text(judgment.get("summary")),
        "action_reason_codes": reason_codes,
        "input_signals": _input_signal_trace(quality, upside, timing),
        "missing_fields": missing,
        "warnings": warnings,
        "policy_version": READINESS_CONTRACT_VERSION,
    }


def build_unavailable_entry_readiness_contract(*, reason: str, final_action: str | None = None) -> Dict[str, Any]:
    reason_code = _code(reason or "READINESS_UNAVAILABLE")
    return {
        "version": READINESS_CONTRACT_VERSION,
        "source": "unavailable",
        "stock_quality_score": None,
        "stock_quality_grade": "N/A",
        "upside_room_score": None,
        "upside_room_grade": "N/A",
        "entry_timing_score": None,
        "entry_timing_grade": "N/A",
        "chase_risk_level": "불명",
        "exclusion_risk_level": "불명",
        "exclusion_reasons": [],
        "final_action": final_action or "관망",
        "final_action_tone": "neutral",
        "action_summary": "정밀 가격/수급 스냅샷 전 단계라 진입 가능 여부 계약을 확정할 수 없습니다.",
        "action_reason_codes": [reason_code],
        "input_signals": [],
        "missing_fields": [],
        "warnings": [reason],
        "policy_version": READINESS_CONTRACT_VERSION,
    }


def _reason_codes(upside: Dict[str, Any], safety_overrides: List[str], missing_fields: List[str]) -> List[str]:
    codes: List[str] = []
    filters = upside.get("filters") if isinstance(upside.get("filters"), list) else []
    for item in filters:
        if isinstance(item, dict) and item.get("triggered"):
            code = _text(item.get("code"))
            if code:
                codes.append(code)
    codes.extend(f"SAFETY_OVERRIDE_{_code(item)}" for item in safety_overrides)
    if missing_fields:
        codes.append("READINESS_MISSING_FIELDS")
    return _unique_texts(codes, limit=20)


def _input_signal_trace(*blocks: Dict[str, Any]) -> List[Dict[str, Any]]:
    trace: List[Dict[str, Any]] = []
    for block in blocks:
        label = _text(block.get("label"))
        for item in block.get("evidence") or []:
            text = _text(item)
            if text:
                trace.append({"group": label, "evidence": text})
    return trace[:20]


def _exclusion_reasons(structural_risk: Dict[str, Any], safety_overrides: List[str]) -> List[Dict[str, Any]]:
    reasons = structural_risk.get("reasons") if isinstance(structural_risk.get("reasons"), list) else []
    out: List[Dict[str, Any]] = []
    for item in reasons:
        if isinstance(item, dict):
            out.append(
                {
                    "code": _text(item.get("code")),
                    "level": _text(item.get("level")),
                    "source_type": _text(item.get("source_type")),
                    "source_field": _text(item.get("source_field")),
                    "evidence": _text(item.get("evidence")),
                }
            )
    if not out:
        for item in safety_overrides:
            text = _text(item)
            if text:
                out.append({"code": _code(text), "level": "legacy", "source_type": "safety_override", "source_field": "safety_overrides", "evidence": text})
    return out[:10]


def _exclusion_risk_level(judgment: Dict[str, Any], safety_overrides: List[str], warnings: List[str], structural_risk: Dict[str, Any] | None = None) -> str:
    action = _text(judgment.get("action"))
    structural_risk = structural_risk if isinstance(structural_risk, dict) else {}
    structural_level = _text(structural_risk.get("risk_level"))
    if structural_level == "exclude":
        return "제외"
    if structural_level == "high":
        return "높음"
    text_blob = " ".join(safety_overrides + warnings)
    if action in {"매수 금지", "스윙 제외"}:
        return "높음"
    if any(token in text_blob for token in ("유상증자", "관리종목", "환기종목", "자본잠식", "감사의견")):
        return "높음"
    if safety_overrides:
        return "보통"
    if warnings:
        return "불확실"
    return "낮음"


def _unique_texts(value: Any, *, limit: int) -> List[str]:
    if value is None:
        source = []
    elif isinstance(value, (list, tuple, set)):
        source = list(value)
    else:
        source = [value]
    out: List[str] = []
    for item in source:
        text = _text(item)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _code(value: Any) -> str:
    text = _text(value).upper()
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in text)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "UNKNOWN"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _num(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return round(float(value), 4)
    except Exception:
        return None


__all__ = [
    "READINESS_CONTRACT_VERSION",
    "build_entry_readiness_contract",
    "build_unavailable_entry_readiness_contract",
]
