"""Korean-first display copy for scanner UI contracts.

The scanner, archive, DB, and Discord payloads still keep their machine codes.
This module is display-only: it translates codes and short trace fragments so
operators can read the web UI without needing to know internal enum names.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, List


CODE_COPY = {
    "ADMISSION_PASS": "운영 통과",
    "ADMISSION_NEAR_MISS": "기준 미달",
    "ADMISSION_THRESHOLD_NOT_MET": "운영 기준 미달",
    "SCAN_UNIVERSE_ADMISSION_MODEL": "운영 모델 판단",
    "KR_BASELINE_FILTER_FAIL": "기존 운영 필터 탈락",
    "ML_INFERENCE_FAILED": "모델 추론 실패",
    "ML_PROB_MISSING": "모델 확률 없음",
    "LOSS_RISK_SOFT_CAP": "손실위험 주의",
    "LOSS_RISK_HARD_CAP": "손실위험 한도 초과",
    "ENTRY_TIMING_RISK_HIGH": "진입 타이밍 위험",
    "EXPECTED_EDGE_PRIORITY_GUARD": "기대수익 우선순위 가드",
    "EXPECTED_EDGE_PRIORITY_GUARD_SOFT": "기대수익 주의",
    "EXPECTED_EDGE_WATCH_GUARD": "관찰 후보 기대수익 가드",
    "EXPECTED_EDGE_WATCH_GUARD_SOFT": "관찰 후보 기대수익 주의",
    "KOSDAQ_SWING_TREND_GUARD": "KOSDAQ 스윙 추세 가드",
    "SWING_ENSEMBLE_BUY": "스윙 앙상블 매수",
    "KOSPI_INTRADAY_BUY": "코스피 인트라데이 매수",
    "unavailable": "미제공",
    "UNAVAILABLE": "미제공",
}


SECTION_COPY = {
    "Scan Universe Admission": "운영 모델 통과",
    "Admission Near Miss": "기준 미달 관찰",
    "KIS Shadow Admission": "KIS 관찰 후보",
    "KIS Shadow": "KIS 관찰",
    "Exception Leader": "예외 리더",
    "Top5": "기존 상위5",
}


STRATEGY_COPY = {
    "Momentum": "모멘텀",
    "MOMENTUM": "모멘텀",
    "Mean Reversion": "평균회귀",
    "MEAN_REVERSION": "평균회귀",
}


TEXT_REPLACEMENTS = (
    ("Admission 모델", "운영 모델"),
    ("admission 모델", "운영 모델"),
    ("Admission 직접 채점 universe", "운영 모델 직접 채점 후보군"),
    ("Admission 입력", "운영 모델 입력"),
    ("Admission", "운영 모델"),
    ("selection rule", "선발규칙"),
    ("selection", "선발"),
    ("Top5", "기존 상위5"),
    ("Exception Leader", "예외 리더"),
    ("Exception", "예외"),
    ("feature", "피처"),
    ("production_blocking_reasons", "운영승격 차단 사유"),
    ("promotion_review_candidate", "승격 검토 후보"),
    ("exit policy", "청산 정책"),
    ("bad-path", "나쁜 경로"),
    ("avoid_down", "하락회피"),
    ("positive", "양수수익"),
    ("shadow", "관찰"),
    ("Shadow", "관찰"),
    ("segment", "구간"),
    ("lane", "전략 레인"),
    ("OOS", "미사용 검증구간"),
    ("CI", "신뢰구간"),
    ("objective", "목표"),
    ("threshold", "기준"),
    ("model=", "모델 "),
    ("objective=", "목표 "),
    ("selection=", "선발규칙 "),
    ("unavailable", "미제공"),
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def korean_code_label(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if text in CODE_COPY:
        return CODE_COPY[text]
    if text in SECTION_COPY:
        return SECTION_COPY[text]
    if text in STRATEGY_COPY:
        return STRATEGY_COPY[text]
    if text.startswith("model="):
        model = text.split("=", 1)[1].strip()
        return f"모델 {korean_model_name(model)}" if model else "모델 미확인"
    if text.startswith("objective=5d_touch_"):
        target = text.rsplit("_", 1)[-1]
        return f"목표 5거래일 +{target}% 터치"
    if text.startswith("threshold="):
        return "운영 기준 " + text.split("=", 1)[1].strip()
    if text.startswith("selection="):
        return "선발규칙 " + korean_selection_rule(text.split("=", 1)[1])
    return korean_display_text(text)


def korean_display_text(value: Any, *, fallback: str = "-") -> str:
    text = _text(value)
    if not text or text.lower() in {"none", "null", "nan"}:
        return fallback
    if text in CODE_COPY:
        return CODE_COPY[text]
    if text in SECTION_COPY:
        return SECTION_COPY[text]
    if text in STRATEGY_COPY:
        return STRATEGY_COPY[text]
    for raw, replacement in TEXT_REPLACEMENTS:
        text = text.replace(raw, replacement)
    text = re.sub(r"\blightgbm\b", "LightGBM", text, flags=re.IGNORECASE)
    text = re.sub(r"\btop\s*([0-9]+)\b", r"\1순위", text, flags=re.IGNORECASE)
    text = re.sub(r"\b5d_touch_([0-9]+)\b", r"5거래일 +\1% 터치", text, flags=re.IGNORECASE)
    text = text.replace("구간는", "구간은")
    text = text.replace("정책를", "정책을")
    return text or fallback


def korean_section_label(value: Any) -> str:
    return korean_display_text(value, fallback="")


def korean_decision_label(value: Any) -> str:
    return korean_code_label(value) or korean_display_text(value)


def korean_strategy_label(value: Any) -> str:
    return korean_display_text(value, fallback="")


def korean_model_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    if text.lower() == "lightgbm":
        return "LightGBM"
    return korean_display_text(text, fallback=text)


def korean_selection_rule(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    lower = text.lower().replace("_", " ")
    match = re.search(r"top\s*([0-9]+)", lower)
    if match:
        return f"{match.group(1)}순위 선발"
    return korean_display_text(text, fallback=text)


def korean_source_role(value: Any) -> str:
    text = _text(value).lower()
    if text == "emitted":
        return "기존 통과 후보"
    if text:
        return "기존 필터 탈락 종목"
    return ""


def korean_trace_list(values: Iterable[Any] | None, *, limit: int = 4) -> List[str]:
    translated: List[str] = []
    for value in values or []:
        label = korean_code_label(value)
        if label and label not in translated:
            translated.append(label)
        if len(translated) >= max(int(limit or 0), 0):
            break
    return translated
