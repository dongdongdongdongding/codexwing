"""Korean-first copy for operational scan readiness.

This module keeps user-facing operational interpretation out of Streamlit-only
code. The input is the machine-readable daily foundation gate report; the
output is a compact view model that explains whether candidates are actionable,
shadow-only, or blocked.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from modules.korean_display_copy import korean_display_text


STATUS_COPY: Dict[str, Dict[str, str]] = {
    "production_ready": {
        "title": "운영 판정: 제한 승격 검토 가능",
        "badge": "운영 검토 가능",
        "body": "일일 검증과 운영 승격 게이트가 모두 통과했습니다. 그래도 실제 매수 전에는 후보별 경로위험과 뉴스 근거를 확인해야 합니다.",
        "caption": "사람 검토 후 제한 승격 가능",
        "tone": "good",
    },
    "shadow_only": {
        "title": "운영 판정: 관찰 전용",
        "badge": "관찰 전용",
        "body": "스캔과 데이터 검증은 정상입니다. 다만 모델 승격 근거가 부족하므로 신규/KIS 후보는 기존 운영 후보와 비교 관찰만 해야 합니다.",
        "caption": "기존 운영 후보 유지, 신규 후보는 관찰 비교",
        "tone": "caution",
    },
    "blocked": {
        "title": "운영 판정: 사용 차단",
        "badge": "사용 차단",
        "body": "데이터 계약, 더미 데이터, 학습 사이클 중 하나 이상이 막혀 있습니다. 이 상태의 후보는 운영 판단에 쓰면 안 됩니다.",
        "caption": "데이터와 검증 리포트 복구 후 재평가",
        "tone": "danger",
    },
    "missing": {
        "title": "운영 판정: 검증 리포트 없음",
        "badge": "확인 필요",
        "body": "일일 운영 검증 리포트를 찾지 못했습니다. 스캔 결과가 있어도 운영 판단에 쓰기 전에 daily foundation gate를 먼저 생성해야 합니다.",
        "caption": "report_daily_model_foundation_gate.py 실행 필요",
        "tone": "risk",
    },
}


ACTION_COPY = {
    "human_review_then_controlled_promotion": "사람 검토 후 제한 승격 가능",
    "keep_existing_production_and_run_daily_shadow_verification": "기존 운영 후보 유지 + 신규/KIS 후보는 관찰 비교",
    "keep_existing_production_and_show_kis_shadow_top_section": "기존 운영 후보 유지 + KIS 후보는 상단 관찰용으로만 표시",
    "fix_daily_data_contract_before_shadow_or_promotion": "데이터 계약 복구 전까지 후보 사용 금지",
    "do_not_show_as_trade_candidate_until_gate_recovers": "게이트 복구 전까지 매매 후보로 표시 금지",
}


CHECK_COPY: Dict[str, Dict[str, str]] = {
    "NIGHTLY_LEARNING_ACTION": {
        "label": "야간 학습 실행",
        "meaning": "최근 결과가 학습 데이터셋에 반영됐는지 봅니다.",
    },
    "NIGHTLY_LEARNING_FRESHNESS": {
        "label": "야간 학습 최신성",
        "meaning": "검증 리포트가 오래되지 않았는지 봅니다.",
    },
    "NIGHTLY_LEARNING_NEW_OUTCOMES": {
        "label": "신규 실현결과 반영",
        "meaning": "새로 확정된 수익률/손실 결과가 충분히 들어왔는지 봅니다.",
    },
    "WEEKLY_LEARNING_ACTION": {
        "label": "주간 재학습 실행",
        "meaning": "주간 모델 갱신 또는 데이터 갱신이 정상 실행됐는지 봅니다.",
    },
    "WEEKLY_LEARNING_FRESHNESS": {
        "label": "주간 재학습 최신성",
        "meaning": "주간 학습 리포트가 너무 오래되지 않았는지 봅니다.",
    },
    "WEEKLY_LEARNING_NEW_OUTCOMES": {
        "label": "주간 신규 표본",
        "meaning": "주간 학습에 들어갈 새 표본이 있는지 봅니다.",
    },
    "RETRAIN_EXECUTION_STATUS": {
        "label": "모델 학습 실행",
        "meaning": "재학습이 실패하지 않았는지 봅니다.",
    },
    "RETRAIN_FRESHNESS": {
        "label": "모델 학습 최신성",
        "meaning": "학습 결과가 운영 판단에 쓸 만큼 최신인지 봅니다.",
    },
    "RETRAIN_THRESHOLD_RETURN_POSITIVE": {
        "label": "학습 모델 기대수익",
        "meaning": "선택 임계값에서 평균 수익이 양수인지 봅니다.",
    },
    "RETRAIN_OOS_RETURN_POSITIVE": {
        "label": "미사용 구간 수익",
        "meaning": "학습에 쓰지 않은 구간에서도 수익이 양수인지 봅니다.",
    },
    "RETRAIN_AUC_FLOOR": {
        "label": "모델 분류력 하한",
        "meaning": "모델이 무작위보다 충분히 나은지 봅니다.",
    },
    "NO_DUMMY_SCAN_ROWS": {
        "label": "더미 데이터 0건",
        "meaning": "가짜/대체 데이터가 섞이지 않았는지 봅니다.",
    },
    "SUPABASE_SCHEMA_COMPATIBLE": {
        "label": "DB 스키마 호환",
        "meaning": "웹/정밀분석/Discord가 같은 컬럼 계약으로 읽을 수 있는지 봅니다.",
    },
    "SUPABASE_QUALITY_FRESHNESS": {
        "label": "DB 품질 리포트 최신성",
        "meaning": "Supabase 품질 검증 리포트가 최신인지 봅니다.",
    },
    "KIS_COMPARISON_NO_DUMMY": {
        "label": "KIS 비교 더미 없음",
        "meaning": "KIS 비교 리포트가 실데이터만 사용했는지 봅니다.",
    },
    "KIS_SHADOW_DISPLAY_ALLOWED": {
        "label": "KIS 관찰 표시 가능",
        "meaning": "KIS 후보를 관찰용으로 보여줘도 되는지 봅니다.",
    },
    "KIS_PROMOTION_READY": {
        "label": "KIS 운영 승격",
        "meaning": "KIS 기반 후보를 기존 운영 후보 대신 쓸 수 있는지 봅니다.",
    },
    "KOSPI_WALKFORWARD_RELEASE": {
        "label": "KOSPI 실전 구간 검증",
        "meaning": "KOSPI 후보가 날짜별 재현 검증에서 수익/방어 기준을 넘었는지 봅니다.",
    },
    "KOSDAQ_WALKFORWARD_RELEASE": {
        "label": "KOSDAQ 실전 구간 검증",
        "meaning": "KOSDAQ 후보가 날짜별 재현 검증에서 수익/방어 기준을 넘었는지 봅니다.",
    },
    "PROMOTION_CHALLENGER_CANDIDATE": {
        "label": "승격 후보 존재",
        "meaning": "기존 운영을 대체할 만한 검증 후보가 1개 이상 있는지 봅니다.",
    },
}


def _bool_text(value: Any) -> str:
    return "통과" if bool(value) else "미통과"


def _card(label: str, value: str, meta: str, tone: str) -> Dict[str, str]:
    return {"label": label, "value": value, "meta": meta, "tone": tone}


def _unknown_check_label(code: str) -> str:
    return code.replace("_", " ").title()


def translate_check_code(code: Any) -> Dict[str, str]:
    text = str(code or "").strip()
    copy = CHECK_COPY.get(text, {})
    return {
        "code": text,
        "label": copy.get("label") or _unknown_check_label(text),
        "meaning": copy.get("meaning") or "내부 운영 검증 항목입니다. 상세 리포트에서 원문 코드를 확인하세요.",
    }


def korean_recommended_action(action: Any) -> str:
    text = str(action or "").strip()
    return ACTION_COPY.get(text, text or "운영 판단 보류")


def build_operational_readiness_view(report: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(report, Mapping) or not report:
        missing = STATUS_COPY["missing"]
        return {
            "available": False,
            "status": "missing",
            "title": missing["title"],
            "badge": missing["badge"],
            "body": missing["body"],
            "caption": missing["caption"],
            "tone": missing["tone"],
            "cards": [
                _card("일일 검증", "없음", "리포트 필요", "danger"),
                _card("운영 승격", "보류", "판정 불가", "danger"),
                _card("더미 데이터", "확인 필요", "판정 불가", "danger"),
            ],
            "blockers": [
                {
                    "code": "DAILY_FOUNDATION_GATE_MISSING",
                    "label": "일일 검증 리포트 없음",
                    "meaning": "운영 판단에 필요한 daily foundation gate 리포트가 없습니다.",
                    "severity": "hard_daily",
                    "next_action": "report_daily_model_foundation_gate.py 실행",
                }
            ],
            "recommended_action_ko": missing["caption"],
            "detail_line": "검증 리포트가 없으므로 후보를 매매 판단에 쓰지 마세요.",
        }

    status = str(report.get("status") or "missing").strip()
    copy = STATUS_COPY.get(status, STATUS_COPY["missing"])
    blockers_by_group = report.get("blocking_reasons") if isinstance(report.get("blocking_reasons"), Mapping) else {}
    blocker_codes: List[str] = []
    for group in ("hard_daily", "hard_production", "soft_daily"):
        values = blockers_by_group.get(group) if isinstance(blockers_by_group.get(group), list) else []
        blocker_codes.extend(str(code) for code in values if str(code).strip())

    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    check_by_code = {
        str(item.get("code")): item for item in checks if isinstance(item, Mapping) and item.get("code")
    }
    blocker_rows = []
    for code in blocker_codes[:12]:
        translated = translate_check_code(code)
        source = check_by_code.get(code, {})
        blocker_rows.append(
            {
                **translated,
                "severity": source.get("severity") or _severity_for_code(code, blockers_by_group),
                "detail": source.get("detail") or "",
                "next_action": korean_display_text(source.get("next_action"), fallback=""),
            }
        )

    daily_ready = bool(report.get("daily_verification_ready"))
    production_ready = bool(report.get("production_promotion_ready"))
    no_dummy = bool(report.get("no_dummy_data"))
    generated_at = str(report.get("generated_at") or "-")
    recommended_action = korean_recommended_action(report.get("recommended_action"))
    hard_daily_count = len(blockers_by_group.get("hard_daily") or [])
    hard_production_count = len(blockers_by_group.get("hard_production") or [])

    return {
        "available": True,
        "status": status,
        "title": copy["title"],
        "badge": copy["badge"],
        "body": copy["body"],
        "caption": recommended_action,
        "tone": copy["tone"],
        "cards": [
            _card(
                "일일 검증",
                _bool_text(daily_ready),
                "스캔/DB/학습 기반",
                "good" if daily_ready else "danger",
            ),
            _card(
                "운영 승격",
                _bool_text(production_ready),
                "실전 게이트 기준",
                "good" if production_ready else "caution",
            ),
            _card(
                "더미 데이터",
                "0건" if no_dummy else "확인 필요",
                "실데이터 원칙",
                "good" if no_dummy else "danger",
            ),
            _card(
                "차단 사유",
                f"{hard_daily_count + hard_production_count}개",
                f"일일 {hard_daily_count} · 승격 {hard_production_count}",
                "good" if hard_daily_count + hard_production_count == 0 else "caution",
            ),
        ],
        "blockers": blocker_rows,
        "recommended_action_ko": recommended_action,
        "detail_line": f"생성시각 {generated_at[:19]} · 내부상태 {copy['badge']}",
    }


def _severity_for_code(code: str, blockers_by_group: Mapping[str, Any]) -> str:
    for group in ("hard_daily", "hard_production", "soft_daily"):
        values = blockers_by_group.get(group) if isinstance(blockers_by_group.get(group), list) else []
        if code in {str(item) for item in values}:
            return group
    return ""


__all__ = [
    "build_operational_readiness_view",
    "korean_recommended_action",
    "translate_check_code",
]
