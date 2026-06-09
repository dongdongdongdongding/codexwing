from __future__ import annotations

from modules.operational_readiness_ui import (
    build_operational_readiness_view,
    korean_recommended_action,
    translate_check_code,
)


def test_operational_readiness_view_explains_shadow_only_in_korean():
    view = build_operational_readiness_view(
        {
            "status": "shadow_only",
            "daily_verification_ready": True,
            "production_promotion_ready": False,
            "no_dummy_data": True,
            "recommended_action": "keep_existing_production_and_run_daily_shadow_verification",
            "generated_at": "2026-06-09T01:00:00+00:00",
            "blocking_reasons": {
                "hard_daily": [],
                "hard_production": ["KIS_PROMOTION_READY", "PROMOTION_CHALLENGER_CANDIDATE"],
                "soft_daily": [],
            },
            "checks": [
                {
                    "code": "KIS_PROMOTION_READY",
                    "severity": "hard_production",
                    "detail": "status=shadow_only",
                    "next_action": "기존 운영 모델 유지",
                },
                {
                    "code": "PROMOTION_CHALLENGER_CANDIDATE",
                    "severity": "hard_production",
                    "detail": "promotion_review_candidate_count=0",
                    "next_action": "후보 검증 지속",
                },
            ],
        }
    )

    assert view["badge"] == "관찰 전용"
    assert view["tone"] == "caution"
    assert "기존 운영 후보 유지" in view["recommended_action_ko"]
    assert "Shadow" not in view["recommended_action_ko"]
    assert view["cards"][0]["label"] == "일일 검증"
    assert view["cards"][1]["value"] == "미통과"
    assert [row["label"] for row in view["blockers"]] == ["KIS 운영 승격", "승격 후보 존재"]
    assert "쉽게 말하면" not in view["blockers"][0]
    assert "기존 운영 모델 유지" in view["blockers"][0]["next_action"]


def test_operational_readiness_view_blocks_when_report_missing():
    view = build_operational_readiness_view({})

    assert view["available"] is False
    assert view["badge"] == "확인 필요"
    assert view["blockers"][0]["label"] == "일일 검증 리포트 없음"
    assert "후보를 매매 판단에 쓰지 마세요" in view["detail_line"]


def test_operational_readiness_code_translation_is_korean_first():
    translated = translate_check_code("KOSDAQ_WALKFORWARD_RELEASE")

    assert translated["label"] == "KOSDAQ 실전 구간 검증"
    assert "날짜별 재현 검증" in translated["meaning"]
    assert korean_recommended_action("fix_daily_data_contract_before_shadow_or_promotion") == "데이터 계약 복구 전까지 후보 사용 금지"
