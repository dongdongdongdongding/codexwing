from modules.operational_candidate_scoring import (
    adjust_return_for_buy_premium,
    attach_operational_candidate_score,
    build_operational_candidate_score,
)


def test_adjust_return_for_buy_premium_uses_entry_price_ratio():
    assert adjust_return_for_buy_premium(10.0, 2.0) == 7.843137
    assert adjust_return_for_buy_premium(-5.0, 2.0) == -6.862745


def test_chart_only_candidate_is_observation_not_operable():
    row = {
        "ticker": "123456.KQ",
        "market": "KOSDAQ",
        "trend": "UP",
        "position": "Rising",
        "tech_score": 90,
        "alpha_score": 88,
        "volume_ratio": 3.0,
        "market_gate": "GREEN",
        "primary_theme": "unclassified",
    }

    score = build_operational_candidate_score(row)

    assert score["axes"]["chart"] >= 80
    assert score["chart_only"] is True
    assert score["action_level"] == "OBSERVE_CHART_ONLY"


def test_multi_axis_candidate_is_operable_with_non_chart_support():
    row = {
        "ticker": "005930.KS",
        "market": "KOSPI",
        "trend": "UP",
        "position": "Rising",
        "tech_score": 82,
        "alpha_score": 80,
        "volume_ratio": 1.8,
        "whale_score": 74,
        "foreigner_1d": 10_000_000,
        "institution_1d": 15_000_000,
        "market_gate": "GREEN",
        "regime_breadth_pct": 64,
        "primary_theme": "반도체",
        "theme_context": {"primary_theme": "반도체", "theme_strength_score": 76, "theme_direction": "BENEFICIARY"},
        "kis_theme_news_evidence": {
            "available": True,
            "kis_backed": True,
            "evidence_strength_score": 78,
            "news": {"checked": True, "news_count": 2, "positive_tags": ["contract_order"]},
        },
        "kis_sidecar": {
            "model_candidate_features": {
                "kis_per": 18,
                "kis_pbr": 1.8,
                "kis_market_cap": 500000000000000,
            }
        },
    }

    row = attach_operational_candidate_score(row)

    assert row["chart_only_candidate"] is False
    assert row["operational_action_level"] == "OPERABLE"
    assert row["operational_score_axes"]["axes"]["flow"] > 60
    assert row["operational_score_axes"]["axes"]["theme_valuechain"] > 60
