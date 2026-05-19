from pathlib import Path

from modules.incident_regression import (
    IncidentPolicy,
    build_incident_regression_report,
    detect_failure_risk_reason_codes,
    evaluate_incident_case,
    load_incident_fixtures,
)


def test_load_incident_fixtures_and_protected_cases_pass():
    rows = load_incident_fixtures(Path("tests/fixtures/incident_regression_cases.json"))
    report = build_incident_regression_report(rows)

    assert len(rows) == 2
    assert report["current"]["severe_loss_count"] == 2
    assert report["current"]["unprotected_elevation_count"] == 0
    assert report["current"]["status"] == "PASS"


def test_unprotected_high_confidence_severe_loss_fails():
    result = evaluate_incident_case(
        {
            "incident_id": "case-1",
            "ticker": "000000.KS",
            "decision": "PRIORITY_WATCHLIST",
            "decision_bucket": "picked",
            "buy_score": 82.0,
            "return_30m_pct": -9.0,
            "risk_flags": [],
        }
    )

    assert result["severe_loss"] is True
    assert result["elevated"] is True
    assert result["protected_by_reason_code"] is False
    assert result["unprotected_elevation"] is True
    assert result["status"] == "FAIL"


def test_candidate_worsening_requires_tradeoff():
    current = IncidentPolicy(name="current", elevated_score_threshold=90.0)
    candidate = IncidentPolicy(name="candidate", elevated_score_threshold=60.0)
    report = build_incident_regression_report(
        [
            {
                "incident_id": "case-2",
                "ticker": "000001.KS",
                "buy_score": 70.0,
                "return_close_pct": -8.0,
            }
        ],
        current_policy=current,
        candidate_policy=candidate,
    )

    assert report["current"]["unprotected_elevation_count"] == 0
    assert report["candidate"]["unprotected_elevation_count"] == 1
    assert report["candidate"]["worsening_vs_current"] is True
    assert report["candidate"]["status"] == "FAIL"


def test_detect_failure_risk_reason_codes_from_display_contract_and_flags():
    codes = detect_failure_risk_reason_codes(
        {
            "signal_label": "NO_BUY",
            "risk_flags": ["ENTRY_TIMING_RISK_HIGH"],
            "display_contract": {"display_status": "VISIBLE_RISK_ANNOTATED"},
        }
    )

    assert "NO_BUY_ACTION" in codes
    assert "ENTRY_TIMING_RISK_HIGH" in codes
    assert "VISIBLE_RISK_ANNOTATED" in codes
