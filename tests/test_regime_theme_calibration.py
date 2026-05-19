from datetime import datetime, timedelta, timezone

from modules.regime_theme_calibration import (
    REGIME_THEME_CALIBRATION_VERSION,
    build_regime_theme_adjustment,
)


def test_dynamic_theme_cache_can_boost_arbitrary_theme_without_whitelist():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    adjustment = build_regime_theme_adjustment(
        {
            "market_gate": {"gate": "GREEN"},
            "primary_theme": "custom-next-ai-power-theme",
            "theme_day_avg_decision_score": 78,
            "theme_day_symbol_count": 9,
            "regime_breadth_pct": 64,
            "regime_avg_chg": 1.4,
        },
        theme_cache={
            "generated_at": now.isoformat(),
            "theme_states": [
                {
                    "theme_name": "custom-next-ai-power-theme",
                    "avg_change_pct": 3.2,
                }
            ],
        },
        now=now,
    )

    assert adjustment["version"] == REGIME_THEME_CALIBRATION_VERSION
    assert adjustment["prob_multiplier"] > 1.0
    assert adjustment["return_multiplier"] > 1.0
    assert adjustment["stop_risk_multiplier"] < 1.0
    assert "theme_cache" in adjustment["evidence"]
    assert "theme_cache_miss" not in adjustment["warnings"]


def test_weak_market_gate_and_breadth_raise_stop_risk():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    adjustment = build_regime_theme_adjustment(
        {
            "market_gate": "RED",
            "primary_theme": "semiconductor",
            "theme_day_avg_decision_score": 48,
            "theme_day_symbol_count": 6,
            "regime_breadth_pct": 35,
            "regime_avg_chg": -1.8,
        },
        theme_cache={
            "generated_at": now.isoformat(),
            "theme_states": [{"theme_name": "semiconductor", "avg_change_pct": -2.5}],
        },
        now=now,
    )

    assert adjustment["prob_multiplier"] < 1.0
    assert adjustment["return_multiplier"] < 1.0
    assert adjustment["stop_risk_multiplier"] > 1.0


def test_stale_theme_cache_dampens_theme_boost_and_warns():
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    fresh = build_regime_theme_adjustment(
        {
            "market_gate": "GREEN",
            "primary_theme": "shipbuilding",
            "theme_day_avg_decision_score": 80,
            "theme_day_symbol_count": 8,
        },
        theme_cache={
            "generated_at": now.isoformat(),
            "theme_states": [{"theme_name": "shipbuilding", "avg_change_pct": 4.0}],
        },
        now=now,
    )
    stale = build_regime_theme_adjustment(
        {
            "market_gate": "GREEN",
            "primary_theme": "shipbuilding",
            "theme_day_avg_decision_score": 80,
            "theme_day_symbol_count": 8,
        },
        theme_cache={
            "generated_at": (now - timedelta(hours=30)).isoformat(),
            "theme_states": [{"theme_name": "shipbuilding", "avg_change_pct": 4.0}],
        },
        now=now,
    )

    assert "stale_theme_cache" in stale["warnings"]
    assert stale["prob_multiplier"] < fresh["prob_multiplier"]
    assert stale["return_multiplier"] < fresh["return_multiplier"]


def test_small_theme_sample_keeps_adjustment_low_confidence():
    adjustment = build_regime_theme_adjustment(
        {
            "market_gate": "GREEN",
            "primary_theme": "robotics",
            "theme_day_avg_decision_score": 88,
            "theme_day_symbol_count": 1,
        },
        theme_cache={"generated_at": datetime.now(timezone.utc).isoformat(), "theme_states": []},
    )

    assert "small_theme_sample" in adjustment["warnings"]
    assert adjustment["confidence"] < 0.35
