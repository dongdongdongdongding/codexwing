from modules.inverted_signal_features import compute_low_prob_high_score_features
from modules.kr_lane_champion_ranker import _engineered_row


def test_low_prob_high_score_uses_real_probabilities_only():
    features = compute_low_prob_high_score_features(
        alpha_score=82,
        tech_score=88,
        ml_prob=35,
        prob_clean=34,
        phase25_prob=10,
        expected_edge_score=-3.6,
    )

    assert features["model_prob_available_count"] == 3.0
    assert features["model_prob_mean"] == 26.333333
    assert features["low_model_prob_score"] == 23.666667
    assert features["low_prob_high_score"] == 58.666667
    assert features["expected_edge_inversion_score"] == 3.6


def test_low_prob_high_score_missing_probs_do_not_create_fake_signal():
    features = compute_low_prob_high_score_features(alpha_score=90, tech_score=90)

    assert features["model_prob_available_count"] == 0.0
    assert features["model_prob_mean"] == 0.0
    assert features["low_model_prob_score"] == 0.0
    assert features["low_prob_high_score"] == 0.0


def test_kr_lane_engineered_row_exposes_inverted_signal_features():
    row = _engineered_row(
        {
            "alpha_score": 82,
            "tech_score": 88,
            "prob_5": 35,
            "prob_clean": 34,
            "phase25_prob": 10,
            "expected_edge_score": -3.6,
            "whale_score": 50,
            "decision_score": 80,
            "volume_ratio": "x1.20",
            "position": "📈 Rising",
            "real_trend": "UP",
            "scan_mode": "SWING",
            "strategy_family": "KR_CORE",
            "kr_universe_role": "CORE_TREND",
            "entry_reference_price": 12000,
            "tier": "T1",
        },
        "KOSPI",
    )

    assert row["model_prob_available_count"] == 3.0
    assert row["low_prob_high_score"] == 58.666667
    assert row["expected_edge_inversion_score"] == 3.6

