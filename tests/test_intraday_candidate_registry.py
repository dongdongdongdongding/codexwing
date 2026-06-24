from modules.intraday_candidate_registry import (
    REPORT_VERSION,
    build_intraday_candidate_registry,
    build_intraday_candidate_registry_markdown,
)


def test_intraday_candidate_registry_is_intraday_only():
    report = build_intraday_candidate_registry(as_of_date="2026-06-24", generated_at="2026-06-24T00:00:00Z")

    assert report["report_version"] == REPORT_VERSION
    assert report["scope"]["scan_mode"] == "INTRADAY"
    assert report["scope"]["production_enabled"] is True
    assert report["scope"]["swing_contamination_allowed"] is False
    assert {row["scan_mode"] for row in report["candidates"]} == {"INTRADAY"}
    assert {row["strategy_family"] for row in report["candidates"]} == {"KR_INTRADAY_5D", "KR_INTRADAY_3D_T5"}


def test_intraday_candidate_registry_separates_shadow_from_research_only():
    report = build_intraday_candidate_registry(as_of_date="2026-06-24", generated_at="2026-06-24T00:00:00Z")
    by_id = {row["candidate_id"]: row for row in report["candidates"]}

    kospi = by_id["kospi_intraday_0905_5d_t10s5_shadow_v1"]
    assert kospi["market"] == "KOSPI"
    assert kospi["status"] == "shadow_candidate"
    assert kospi["target_horizon_days"] == 5
    assert kospi["validation"]["day_win_pct"] >= 75
    assert kospi["promotion_guard"]["production_enabled"] is False

    touch5 = by_id["kosdaq_intraday_1500_3d_t5_vwap_guard_shadow_v1"]
    assert touch5["market"] == "KOSDAQ"
    assert touch5["status"] == "live_forward_candidate"
    assert touch5["strategy_family"] == "KR_INTRADAY_3D_T5"
    assert touch5["target_horizon_days"] == 3
    assert {lane["floor_eok"] for lane in touch5["liquidity_lanes"]} == {30, 100}
    assert touch5["liquidity_lanes"][0]["hit_ci_low_pct"] >= 70
    assert touch5["liquidity_lanes"][1]["hit_ci_low_pct"] >= 70
    assert touch5["validation"]["hit_pct"] >= 70
    assert touch5["validation"]["hit_ci_pct"][0] >= 70
    assert touch5["selection_policy"]["min_calibrated_probability"] == 0.80
    assert touch5["selection_policy"]["max_picks_per_day"] == 2
    assert touch5["selection_policy"]["entry_quality_guard"]["pre_vwap_dist_pct_min"] == 0.0
    assert touch5["selection_policy"]["return_policy"] == "hold_3d_close"
    assert touch5["validation"]["close3_net033_pct"] > 0
    assert touch5["validation"]["liquidity_decile_excess_ci_pct"][0] > 0
    assert touch5["validation"]["month_hit_min_pct"] >= 70
    assert touch5["promotion_guard"]["micro_production_gate"]["minimum_forward_picks"] == 60
    assert touch5["promotion_guard"]["production_enabled"] is True

    kosdaq = by_id["kosdaq_intraday_tail_guard_research_v1"]
    assert kosdaq["market"] == "KOSDAQ"
    assert kosdaq["status"] == "research_only"
    assert kosdaq["promotion_guard"]["production_enabled"] is False

    markdown = build_intraday_candidate_registry_markdown(report)
    assert "KOSPI" in markdown
    assert "KOSDAQ" in markdown
    assert "INTRADAY" in markdown
