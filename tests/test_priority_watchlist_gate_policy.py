from multi_agent.agents.planner_runtime import _apply_kosdaq_swing_gate
from multi_agent.tools.emit_daily_backtest import _resolved_return_for_row


def test_kosdaq_swing_gate_rationale_identifies_actual_clean_prob_guard():
    rationale = []
    theme_risk = []

    decision = _apply_kosdaq_swing_gate(
        decision="PRIORITY_WATCHLIST",
        run_market="KOSDAQ",
        scan_mode="SWING",
        phase25_variant="phase25_kosdaq_swing",
        raw_phase25_prob=75.3,
        recommended_threshold=60.0,
        prob_clean=16.3,
        real_trend="UP",
        rationale=rationale,
        theme_risk=theme_risk,
    )

    assert decision == "WATCHLIST"
    assert "KOSDAQ_SWING_CLEAN_PROB_GUARD" in theme_risk
    assert rationale == ["kosdaq_swing_gate:clean_prob=16.3<28.0"]


def test_daily_backtest_uses_kosdaq_swing_5d_horizon():
    value, col = _resolved_return_for_row(
        {
            "scan_mode": "SWING",
            "phase25_variant": "phase25_kosdaq_swing",
            "return_3d_pct": -2.0,
            "return_5d_pct": 7.5,
        }
    )

    assert value == 7.5
    assert col == "return_5d_pct"


def test_daily_backtest_uses_kospi_swing_3d_horizon():
    value, col = _resolved_return_for_row(
        {
            "scan_mode": "SWING",
            "phase25_variant": "phase25_kospi_swing",
            "return_3d_pct": 3.2,
            "return_5d_pct": -1.0,
        }
    )

    assert value == 3.2
    assert col == "return_3d_pct"

