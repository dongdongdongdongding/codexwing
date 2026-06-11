from modules.kis_shadow_exit_policy import build_kis_shadow_exit_policy


def test_touch5_dd10_exit_policy_uses_minus_ten_five_day_guard():
    policy = build_kis_shadow_exit_policy(
        features={},
        metrics={
            "avg_5d_pct": 16.57,
            "avg_max_high_5d_pct": 29.5,
            "hit10_5d_pct": 92.3,
            "bad_path_pct": 69.2,
            "stop5_pct": 53.8,
            "stop_before_target_5d_pct": 53.8,
            "min_min_low_5d_pct": -5.97,
        },
        identity={"label": "touch5_dd10_5d"},
        market="KOSPI",
    )

    assert policy["target_tp_pct"] == 5.0
    assert policy["stop_sl_pct"] == -10.0
    assert policy["hold_days"] == 5
    assert policy["risk_level"] == "LOW"
    assert "touch5_dd10_target_plus5_drawdown_minus10" in policy["reason_codes"]


def test_default_shadow_exit_policy_keeps_tight_stop_for_high_risk_legacy_label():
    policy = build_kis_shadow_exit_policy(
        features={},
        metrics={
            "avg_5d_pct": 12.0,
            "avg_max_high_5d_pct": 20.0,
            "hit10_5d_pct": 70.0,
            "bad_path_pct": 69.2,
            "stop5_pct": 53.8,
            "stop_before_target_5d_pct": 53.8,
            "min_min_low_5d_pct": -5.97,
        },
        identity={"label": "touch10_guard_5d"},
        market="KOSPI",
    )

    assert policy["target_tp_pct"] == 5.0
    assert policy["stop_sl_pct"] == -3.0
    assert policy["hold_days"] == 3
    assert policy["risk_level"] == "EXTREME"
