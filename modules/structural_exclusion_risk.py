from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List


STRUCTURAL_EXCLUSION_VERSION = "structural_exclusion_risk_v1"


@dataclass(frozen=True)
class ExclusionReason:
    code: str
    level: str
    label: str
    source_type: str
    source_field: str
    evidence: str


HARD_FIELD_MAP = {
    "managed_issue": ("MANAGED_ISSUE", "관리/투자주의/환기 상태"),
    "administrative_issue": ("ADMINISTRATIVE_ISSUE", "관리/행정 리스크"),
    "trading_halt": ("TRADING_HALT", "거래정지/매매정지"),
    "auditor_opinion_risk": ("AUDITOR_OPINION_RISK", "감사의견 리스크"),
    "capital_impairment": ("CAPITAL_IMPAIRMENT", "자본잠식/재무구조 리스크"),
    "paid_in_capital_increase": ("RIGHTS_OFFERING", "유상증자/신주 리스크"),
    "rights_offering": ("RIGHTS_OFFERING", "유상증자/신주 리스크"),
}


TEXT_RULES = (
    ("RIGHTS_OFFERING", "exclude", "유상증자/신주 리스크", ("유상증자", "신주배정", "신주 상장", "신주상장")),
    ("CONVERTIBLE_BOND", "high", "CB/BW 희석 리스크", ("전환사채", "주식관련사채", " CB", " BW")),
    ("MANAGED_ISSUE", "exclude", "관리/환기종목 리스크", ("관리종목", "환기종목", "투자주의환기")),
    ("TRADING_HALT", "exclude", "거래정지/매매정지 리스크", ("거래정지", "매매정지", "상장폐지")),
    ("AUDITOR_OPINION_RISK", "exclude", "감사의견 리스크", ("감사의견", "의견거절", "한정의견")),
    ("CAPITAL_IMPAIRMENT", "exclude", "자본잠식 리스크", ("자본잠식", "완전자본잠식")),
    ("EMBEZZLEMENT_BREACH", "exclude", "횡령/배임 리스크", ("횡령", "배임")),
    ("CLINICAL_BIO_EVENT", "high", "임상/바이오 이벤트 의존", ("임상", "FDA", "품목허가", "신약", "바이오")),
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _num(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        return float(value)
    except Exception:
        return None


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "관리", "환기", "halt", "stopped"}
    return bool(value)


def _add_reason(reasons: List[ExclusionReason], reason: ExclusionReason) -> None:
    if reason.code not in {item.code for item in reasons}:
        reasons.append(reason)


def _headline_text(news: Dict[str, Any]) -> List[tuple[str, str]]:
    out: List[tuple[str, str]] = []
    for idx, item in enumerate(news.get("headlines") or []):
        if isinstance(item, dict):
            text = " ".join(_text(item.get(key)) for key in ("title", "summary") if _text(item.get(key)))
        else:
            text = _text(item)
        if text:
            out.append((f"news.headlines[{idx}]", text))
    return out


def _field_texts(candidate: Dict[str, Any], news: Dict[str, Any]) -> List[tuple[str, str, str]]:
    fields = []
    for key in ("reason", "reject_reason", "rationale", "theme_risk", "risk_flags", "news_title", "headline"):
        value = candidate.get(key)
        if isinstance(value, list):
            for idx, item in enumerate(value):
                if _text(item):
                    fields.append(("candidate", f"{key}[{idx}]", _text(item)))
        elif isinstance(value, dict):
            for subkey, item in value.items():
                if _text(item):
                    fields.append(("candidate", f"{key}.{subkey}", _text(item)))
        elif _text(value):
            fields.append(("candidate", key, _text(value)))
    for field, text in _headline_text(news):
        fields.append(("news", field, text))
    return fields


def evaluate_structural_exclusion_risk(
    candidate: Dict[str, Any] | None,
    *,
    price: Dict[str, Any] | None = None,
    news: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    candidate = candidate if isinstance(candidate, dict) else {}
    price = price if isinstance(price, dict) else {}
    news = news if isinstance(news, dict) else {}
    reasons: List[ExclusionReason] = []
    warnings: List[str] = []

    for field, (code, label) in HARD_FIELD_MAP.items():
        if _truthy(candidate.get(field)):
            _add_reason(
                reasons,
                ExclusionReason(code=code, level="exclude", label=label, source_type="candidate_field", source_field=field, evidence=str(candidate.get(field))),
            )

    for source_type, source_field, text in _field_texts(candidate, news):
        upper = text.upper()
        for code, level, label, terms in TEXT_RULES:
            if any(term.upper() in upper for term in terms):
                _add_reason(
                    reasons,
                    ExclusionReason(code=code, level=level, label=label, source_type=source_type, source_field=source_field, evidence=text[:180]),
                )

    turnover = _num(candidate.get("value_traded") or candidate.get("turnover") or price.get("value_traded") or price.get("turnover"))
    if turnover is not None and turnover < 500_000_000:
        _add_reason(
            reasons,
            ExclusionReason(
                code="SEVERE_LIQUIDITY_INSUFFICIENCY",
                level="high",
                label="거래대금 부족",
                source_type="price_snapshot",
                source_field="value_traded",
                evidence=f"turnover={turnover:.0f}",
            ),
        )

    operating_profit = _num(candidate.get("operating_profit") or candidate.get("operating_income"))
    net_income = _num(candidate.get("net_income"))
    chronic_losses = candidate.get("chronic_losses")
    if _truthy(chronic_losses) or (operating_profit is not None and operating_profit < 0 and net_income is not None and net_income < 0):
        _add_reason(
            reasons,
            ExclusionReason(
                code="CHRONIC_LOSSES",
                level="high",
                label="적자 지속/수익성 리스크",
                source_type="financial_snapshot",
                source_field="operating_profit/net_income",
                evidence=f"operating_profit={operating_profit}, net_income={net_income}, chronic_losses={chronic_losses}",
            ),
        )

    if not any(reason.source_type in {"candidate_field", "financial_snapshot"} for reason in reasons):
        warnings.append("UNKNOWN_SOURCE_ADMIN_AUDIT_CORPORATE_ACTION")

    levels = {reason.level for reason in reasons}
    if "exclude" in levels:
        risk_level = "exclude"
        final_action_override = "스윙 제외"
    elif "high" in levels:
        risk_level = "high"
        final_action_override = "매수 금지"
    elif reasons:
        risk_level = "medium"
        final_action_override = ""
    else:
        risk_level = "low"
        final_action_override = ""

    return {
        "version": STRUCTURAL_EXCLUSION_VERSION,
        "risk_level": risk_level,
        "final_action_override": final_action_override,
        "reasons": [asdict(reason) for reason in reasons],
        "reason_codes": [reason.code for reason in reasons],
        "warnings": warnings,
        "source_freshness": {
            "price_asof": price.get("asof") or price.get("snapshot_at") or price.get("date"),
            "news_status": news.get("status"),
        },
    }


def summarize_structural_exclusion_risks(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [row for row in rows or [] if isinstance(row, dict)]
    reason_counts: Dict[str, int] = {}
    level_counts: Dict[str, int] = {}
    for row in rows:
        risk = row.get("structural_exclusion_risk") if isinstance(row.get("structural_exclusion_risk"), dict) else row
        level = _text(risk.get("risk_level") or "unknown")
        level_counts[level] = level_counts.get(level, 0) + 1
        for code in risk.get("reason_codes") or []:
            code_text = _text(code)
            if code_text:
                reason_counts[code_text] = reason_counts.get(code_text, 0) + 1
    return {
        "version": STRUCTURAL_EXCLUSION_VERSION,
        "rows": len(rows),
        "level_counts": level_counts,
        "reason_counts": reason_counts,
    }


__all__ = [
    "STRUCTURAL_EXCLUSION_VERSION",
    "evaluate_structural_exclusion_risk",
    "summarize_structural_exclusion_risks",
]
