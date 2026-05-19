from modules.entry_readiness_contract import build_entry_readiness_contract, build_unavailable_entry_readiness_contract


def test_entry_readiness_contract_flattens_three_scores_and_reason_codes():
    contract = build_entry_readiness_contract(
        {
            "quality": {"score": 88.2, "grade": "A", "label": "종목 품질", "evidence": ["스캐너 강도 점수 90"]},
            "upside": {
                "score": 42.0,
                "grade": "D",
                "chase_risk_level": "신규 진입 금지",
                "filters": [{"code": "RET_60D_GT_150", "triggered": True}],
                "evidence": ["60D +166.0%"],
            },
            "timing": {"score": 77.5, "grade": "B+", "label": "진입 타이밍", "evidence": ["20일선 지지"]},
            "final_buy_judgment": {"action": "매수 금지", "tone": "danger", "summary": "과열"},
            "data_coverage": {"required_fields": ["ma20", "return_60d_pct"], "available_fields": ["return_60d_pct"]},
            "warnings": ["60D 상승률 계산 가능"],
        }
    )

    assert contract["stock_quality_grade"] == "A"
    assert contract["upside_room_grade"] == "D"
    assert contract["entry_timing_grade"] == "B+"
    assert contract["chase_risk_level"] == "신규 진입 금지"
    assert contract["exclusion_risk_level"] == "높음"
    assert contract["final_action"] == "매수 금지"
    assert "RET_60D_GT_150" in contract["action_reason_codes"]
    assert "READINESS_MISSING_FIELDS" in contract["action_reason_codes"]
    assert contract["missing_fields"] == ["ma20"]


def test_unavailable_entry_readiness_contract_is_explicit_not_faked():
    contract = build_unavailable_entry_readiness_contract(reason="PRICE_SNAPSHOT_UNAVAILABLE_IN_PLANNER_RUNTIME")

    assert contract["source"] == "unavailable"
    assert contract["stock_quality_score"] is None
    assert contract["final_action"] == "관망"
    assert contract["action_reason_codes"] == ["PRICE_SNAPSHOT_UNAVAILABLE_IN_PLANNER_RUNTIME"]
