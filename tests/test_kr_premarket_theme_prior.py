from datetime import datetime, timezone

from modules.kr_premarket_theme_prior import build_premarket_theme_prior
from multi_agent.tools.run_kr_daily_auto_scans import _before_confirm_window


def test_premarket_theme_prior_projects_us_semis_to_kr_theme():
    artifact = {
        "version": "test-transfer",
        "edges": [
            {
                "source_theme_id": "semiconductor",
                "target_theme_id": "semiconductor",
                "relationship": "CO_MOVE",
                "confidence": 0.9,
            },
            {
                "source_theme_id": "high_yield_risk_off",
                "target_theme_id": "secondary_battery",
                "relationship": "INVERSE",
                "confidence": 0.7,
            },
        ],
    }
    payload = build_premarket_theme_prior(
        {
            "macro_state": "NORMAL",
            "macro_risk_score": 10,
            "us_lead_score": 8,
            "us_lead_state": "RISK_ON",
            "soxx_change_1d": 3.0,
            "qqq_change_1d": 1.0,
            "ixic_change_1d": 1.2,
            "nq_futures_change_1d": 0.8,
        },
        transfer_artifact=artifact,
    )

    assert payload["actionability"] == "PREMARKET_PRIOR_ONLY"
    assert payload["confirm_after_kst"] == "09:30"
    themes = {row["theme_id"]: row for row in payload["kr_theme_priors"]}
    assert themes["semiconductor"]["direction"] == "BENEFICIARY"
    assert themes["semiconductor"]["strength_score"] > 0


def test_premarket_theme_prior_marks_risk_off_as_headwind_via_inverse_edge():
    artifact = {
        "version": "test-transfer",
        "edges": [
            {
                "source_theme_id": "high_yield_risk_off",
                "target_theme_id": "semiconductor",
                "relationship": "INVERSE",
                "confidence": 0.8,
            }
        ],
    }
    payload = build_premarket_theme_prior(
        {
            "macro_state": "RISK_OFF",
            "macro_risk_score": 70,
            "us_lead_score": -30,
            "us_lead_state": "RISK_OFF",
            "spy_change_1d": -2.0,
            "vix_change_1d": 12.0,
            "kr_derivative_lead_score": -6,
        },
        transfer_artifact=artifact,
    )

    themes = {row["theme_id"]: row for row in payload["kr_theme_priors"]}
    assert themes["semiconductor"]["direction"] == "HEADWIND"


def test_confirmed_scan_window_is_after_930_kst():
    before = datetime(2026, 5, 18, 0, 20, tzinfo=timezone.utc)  # 09:20 KST
    after = datetime(2026, 5, 18, 0, 35, tzinfo=timezone.utc)   # 09:35 KST

    assert _before_confirm_window(before) is True
    assert _before_confirm_window(after) is False
