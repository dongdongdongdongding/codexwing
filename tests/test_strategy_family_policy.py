from modules.strategy_family_policy import apply_strategy_family_policy
from modules.scanner_services import resolve_strategy_family


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


def test_kr_intraday_family_is_distinct_from_swing_core():
    assert resolve_strategy_family("KOSPI") == "KR_CORE"
    assert resolve_strategy_family("KOSPI", scan_mode="SWING") == "KR_CORE"
    assert resolve_strategy_family("KOSPI", scan_mode="INTRADAY") == "KR_INTRADAY"
    assert resolve_strategy_family("KOSDAQ", scan_mode="INTRADAY") == "KR_INTRADAY"


def test_kr_intraday_five_day_family_reroutes_horizon_without_promotion():
    decision, horizon, trace = apply_strategy_family_policy(
        decision="WATCHLIST",
        strategy_family="KR_INTRADAY_5D",
        market="KOSPI",
        scan_mode="INTRADAY",
        target_horizon_days=1,
    )

    assert decision == "WATCHLIST"
    assert horizon == 5
    assert trace["rationale"] == ["strategy_family_horizon_reroute=KR_INTRADAY_5D:5d"]
    assert trace["risk_flags"] == []


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
