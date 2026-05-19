from modules.structural_exclusion_risk import evaluate_structural_exclusion_risk, summarize_structural_exclusion_risks


def test_rights_offering_news_routes_to_swing_exclusion():
    risk = evaluate_structural_exclusion_risk(
        {"ticker": "009830.KS"},
        news={"status": "OK", "headlines": [{"title": "한화솔루션, 유상증자 일정 재확정...신주 상장 7월"}]},
    )
    assert risk["risk_level"] == "exclude"
    assert risk["final_action_override"] == "스윙 제외"
    assert "RIGHTS_OFFERING" in risk["reason_codes"]
    reason = risk["reasons"][0]
    assert reason["source_type"] == "news"
    assert reason["source_field"] == "news.headlines[0]"


def test_low_turnover_and_losses_are_high_risk_not_hard_exclusion():
    risk = evaluate_structural_exclusion_risk(
        {
            "ticker": "000001.KQ",
            "value_traded": 100_000_000,
            "operating_profit": -10,
            "net_income": -20,
        }
    )
    assert risk["risk_level"] == "high"
    assert risk["final_action_override"] == "매수 금지"
    assert set(risk["reason_codes"]) == {"SEVERE_LIQUIDITY_INSUFFICIENCY", "CHRONIC_LOSSES"}


def test_unknown_source_warning_does_not_create_false_safe_status():
    risk = evaluate_structural_exclusion_risk({"ticker": "005930.KS"})
    assert risk["risk_level"] == "low"
    assert "UNKNOWN_SOURCE_ADMIN_AUDIT_CORPORATE_ACTION" in risk["warnings"]


def test_structural_summary_counts_reasons():
    summary = summarize_structural_exclusion_risks(
        [
            {"structural_exclusion_risk": {"risk_level": "exclude", "reason_codes": ["RIGHTS_OFFERING"]}},
            {"structural_exclusion_risk": {"risk_level": "high", "reason_codes": ["CHRONIC_LOSSES"]}},
        ]
    )
    assert summary["level_counts"]["exclude"] == 1
    assert summary["reason_counts"]["RIGHTS_OFFERING"] == 1
