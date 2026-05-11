from modules.loss_risk_features import (
    compute_entry_timing_risk_features,
    compute_loss_risk_features,
    get_loss_risk_gate_thresholds,
    get_loss_risk_soft_cap_decision,
)


def test_loss_risk_features_flag_high_alpha_low_prob_weak_volume():
    row = compute_loss_risk_features(
        market_subtype="KOSDAQ",
        alpha_score=100,
        tech_score=100,
        whale_score=80,
        ml_prob=42.8,
        prob_clean=23.4,
        volume_ratio=0.3,
        volume_confirmed=False,
        position="🚀 상승 (Rising)",
        tier="🏆T1",
        trend="UP",
    )

    assert row["alpha_prob_gap"] == 57.2
    assert row["model_prob_disagreement"] == 19.4
    assert row["low_prob_high_alpha_risk"] == 0.0
    assert row["clean_prob_high_alpha_risk"] == 1.0
    assert row["model_prob_disagreement_risk"] == 1.0
    assert row["weak_volume_high_alpha_risk"] == 1.0
    assert row["chase_low_prob_risk"] == 0.0
    assert row["kosdaq_tier_chase_risk"] == 1.0
    assert row["kosdaq_clean_chase_risk"] == 1.0
    assert row["loss_risk_score"] > get_loss_risk_gate_thresholds("KOSDAQ")["hard"]


def test_loss_risk_features_keep_supported_setup_low_risk():
    row = compute_loss_risk_features(
        market_subtype="KOSPI",
        alpha_score=86,
        tech_score=80,
        whale_score=78,
        ml_prob=55,
        prob_clean=58,
        volume_ratio=2.0,
        volume_confirmed=True,
        position="",
        tier="⭐T2",
        trend="UP",
    )

    assert row["weak_volume_high_alpha_risk"] == 0.0
    assert row["clean_prob_high_alpha_risk"] == 0.0
    assert row["model_prob_disagreement_risk"] == 0.0
    assert row["chase_low_prob_risk"] == 0.0
    assert row["kosdaq_tier_chase_risk"] == 0.0
    assert row["loss_risk_score"] < 20


def test_loss_risk_gate_thresholds_are_market_specific():
    assert get_loss_risk_gate_thresholds("KOSPI") == {"soft": 50.0, "hard": 65.0}
    assert get_loss_risk_gate_thresholds("KOSDAQ") == {"soft": 45.0, "hard": 65.0}
    assert get_loss_risk_gate_thresholds("005930.KS") == {"soft": 50.0, "hard": 65.0}
    assert get_loss_risk_gate_thresholds("037230.KQ") == {"soft": 45.0, "hard": 65.0}
    assert get_loss_risk_soft_cap_decision("KOSPI") == "WATCHLIST"
    assert get_loss_risk_soft_cap_decision("KOSDAQ") == "OBSERVE"


def test_loss_risk_features_coerce_nan_to_safe_defaults():
    row = compute_loss_risk_features(
        market_subtype="KOSDAQ",
        alpha_score=float("nan"),
        tech_score=float("nan"),
        whale_score=float("nan"),
        ml_prob=float("nan"),
        prob_clean=float("nan"),
        volume_ratio=float("nan"),
        volume_confirmed=float("nan"),
        position=float("nan"),
        tier=float("nan"),
        trend=float("nan"),
    )

    assert row["loss_risk_score"] == 10.0
    assert row["missing_core_trace_risk"] == 1.0


def test_entry_timing_risk_flags_delayed_kosdaq_chase_setup():
    risky = compute_entry_timing_risk_features(
        market_subtype="KOSDAQ",
        expected_return_1d_pct=-0.8,
        expected_return_3d_pct=6.5,
        expected_edge_score=-1.2,
        prev_pct_change_1d=8.0,
        prev_pct_change_5d=18.0,
        volume_ratio=0.7,
        prob_clean=32.0,
        loss_risk_score=48.0,
        position="🚀 상승 (Rising)",
        tier="🏆T1",
        trend="UP",
    )
    supported = compute_entry_timing_risk_features(
        market_subtype="KOSDAQ",
        expected_return_1d_pct=2.4,
        expected_return_3d_pct=5.4,
        expected_edge_score=4.0,
        prev_pct_change_1d=1.0,
        prev_pct_change_5d=4.0,
        volume_ratio=2.2,
        prob_clean=46.0,
        loss_risk_score=12.0,
        position="Rising",
        tier="T1",
        trend="UP",
    )

    assert risky["entry_timing_risk_score"] > supported["entry_timing_risk_score"] + 40.0
    assert risky["negative_1d_edge_risk"] > 0
    assert risky["delayed_swing_gap_risk"] > 0
