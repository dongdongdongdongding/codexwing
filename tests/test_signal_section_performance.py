from modules.signal_section_performance import (
    build_section_performance_metrics,
    classify_signal_sections,
)


def test_classify_signal_sections_covers_shadow_top5_and_exception():
    kospi_shadow = {
        "ticker": "000001.KS",
        "market": "KOSPI",
        "priority_rank": "2",
        "prob_clean": "30.0",
        "decision_score": "101",
        "explosive_leader_flag": "0",
    }
    top5 = {"ticker": "000002.KS", "market": "KOSPI", "priority_rank": "5"}
    exception = {"ticker": "000003.KQ", "market": "KOSDAQ", "decision": "EXCEPTION_LEADER"}

    assert classify_signal_sections(kospi_shadow) == ["Shadow", "Top5"]
    assert classify_signal_sections(top5) == ["Top5"]
    assert classify_signal_sections(exception) == ["Exception Leader"]


def test_build_section_performance_metrics_records_horizons():
    rows = [
        {
            "ticker": "000001.KS",
            "market": "KOSPI",
            "priority_rank": "2",
            "prob_clean": "30.0",
            "decision_score": "101",
            "explosive_leader_flag": "0",
            "return_1d_pct": "1.0",
            "return_3d_pct": "-2.0",
            "return_5d_pct": "4.0",
            "base_trade_date": "2026-05-10",
        },
        {
            "ticker": "000002.KQ",
            "market": "KOSDAQ",
            "decision": "EXCEPTION_LEADER",
            "return_1d_pct": "-1.0",
            "return_3d_pct": "3.0",
            "return_5d_pct": "5.0",
            "base_trade_date": "2026-05-11",
        },
    ]

    metrics = build_section_performance_metrics(rows, as_of_date="2026-05-15", generated_at="now")
    by_key = {(row["market"], row["section"], row["horizon_days"]): row for row in metrics}

    assert by_key[("KOSPI", "Shadow", 1)]["sample_n"] == 1
    assert by_key[("KOSPI", "Shadow", 1)]["win_rate_pct"] == 100.0
    assert by_key[("KOSPI", "Top5", 3)]["avg_return_pct"] == -2.0
    assert by_key[("KOSDAQ", "Exception Leader", 5)]["win_rate_pct"] == 100.0
