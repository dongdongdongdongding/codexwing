from multi_agent.agents.planner_runtime import (
    _apply_expected_edge_gate,
    _apply_kosdaq_swing_gate,
    _apply_kr_market_mode_quality_gate,
    _apply_phase25_reliability_gate,
)
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


def test_retired_kosdaq_intraday_phase25_variant_is_avoided():
    rationale = []
    theme_risk = []

    decision = _apply_phase25_reliability_gate(
        decision="PRIORITY_WATCHLIST",
        phase25_variant="phase25_kosdaq_intraday",
        phase25_signal_direction="normal",
        phase25_raw_auc=0.62,
        phase25_oos_auc=0.61,
        phase25_oos_win_rate_pct=80.0,
        phase25_oos_avg_return_pct=8.0,
        rationale=rationale,
        theme_risk=theme_risk,
    )

    assert decision == "AVOID"
    assert "PHASE25_RETIRED_VARIANT" in theme_risk
    assert rationale == ["phase25_retired_variant=phase25_kosdaq_intraday"]


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


def test_kospi_swing_priority_relax_defaults_to_hard_demote(monkeypatch):
    monkeypatch.delenv("AG_KOSPI_SWING_PRIORITY_GUARD_RELAX", raising=False)
    rationale = []
    theme_risk = []

    decision = _apply_kr_market_mode_quality_gate(
        decision="PRIORITY_WATCHLIST",
        run_market="KOSPI",
        scan_mode="SWING",
        score=80.0,
        phase25_variant="phase25_kospi_swing",
        raw_phase25_prob=20.0,
        recommended_threshold=60.0,
        prob_clean=20.0,
        real_trend="UP",
        theme_routing_path="core_only",
        rationale=rationale,
        theme_risk=theme_risk,
    )

    assert decision == "WATCHLIST"
    assert "KOSPI_SWING_PRIORITY_GUARD" in theme_risk
    assert "KOSPI_SWING_PRIORITY_GUARD_SOFT" not in theme_risk


def test_kospi_expected_edge_relax_defaults_to_hard_demote(monkeypatch):
    monkeypatch.delenv("AG_EXPECTED_EDGE_PRIORITY_GUARD_RELAX", raising=False)
    rationale = []
    theme_risk = []

    decision = _apply_expected_edge_gate(
        decision="PRIORITY_WATCHLIST",
        run_market="KOSPI",
        scan_mode="SWING",
        expected_return_1d_pct=0.2,
        expected_return_3d_pct=0.5,
        score=90.0,
        real_trend="UP",
        rationale=rationale,
        theme_risk=theme_risk,
    )

    assert decision == "WATCHLIST"
    assert "EXPECTED_EDGE_PRIORITY_GUARD" in theme_risk
    assert "EXPECTED_EDGE_PRIORITY_GUARD_SOFT" not in theme_risk


def test_kospi_swing_relax_can_be_enabled_explicitly(monkeypatch):
    monkeypatch.setenv("AG_KOSPI_SWING_PRIORITY_GUARD_RELAX", "1")
    rationale = []
    theme_risk = []

    decision = _apply_kr_market_mode_quality_gate(
        decision="PRIORITY_WATCHLIST",
        run_market="KOSPI",
        scan_mode="SWING",
        score=80.0,
        phase25_variant="phase25_kospi_swing",
        raw_phase25_prob=20.0,
        recommended_threshold=60.0,
        prob_clean=20.0,
        real_trend="UP",
        theme_routing_path="core_only",
        rationale=rationale,
        theme_risk=theme_risk,
    )

    assert decision == "PRIORITY_WATCHLIST"
    assert "KOSPI_SWING_PRIORITY_GUARD_SOFT" in theme_risk
