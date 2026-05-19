from modules.strategy_family_policy import apply_strategy_family_policy


def test_amex_moonshot_swing_reroutes_to_five_day_horizon():
    decision, horizon, trace = apply_strategy_family_policy(
        decision="PRIORITY_WATCHLIST",
        strategy_family="AMEX_MOONSHOT",
        market="AMEX",
        scan_mode="SWING",
        target_horizon_days=3,
    )

    assert decision == "PRIORITY_WATCHLIST"
    assert horizon == 5
    assert trace["rationale"] == ["strategy_family_horizon_reroute=AMEX_MOONSHOT:5d"]


def test_unknown_kr_intraday_caps_priority_without_blanket_avoid():
    decision, horizon, trace = apply_strategy_family_policy(
        decision="PRIORITY_WATCHLIST",
        strategy_family="",
        market="KOSDAQ",
        scan_mode="INTRADAY",
        target_horizon_days=1,
    )

    assert decision == "WATCHLIST"
    assert horizon == 1
    assert "STRATEGY_FAMILY_UNKNOWN_KR_INTRADAY" in trace["risk_flags"]


def test_kr_core_swing_is_not_penalized_for_short_horizon_matrix_noise():
    decision, horizon, trace = apply_strategy_family_policy(
        decision="PRIORITY_WATCHLIST",
        strategy_family="KR_CORE",
        market="KOSPI",
        scan_mode="SWING",
        target_horizon_days=5,
    )

    assert decision == "PRIORITY_WATCHLIST"
    assert horizon == 5
    assert trace["risk_flags"] == []
