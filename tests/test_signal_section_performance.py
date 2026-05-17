from modules.signal_section_performance import (
    build_section_performance_metrics,
    classify_signal_sections,
)


def test_classify_signal_sections_covers_shadow_top5_and_exception():
    kospi_shadow = {
        "ticker": "000001.KS",
        "market": "KOSPI",
        "priority_rank": "2",
        "prob_clean": "36.0",
        "alpha_score": "70.0",
        "theme_day_avg_alpha_score": "75.0",
        "kr_universe_role": "CORE_TREND",
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
            "prob_clean": "36.0",
            "alpha_score": "70.0",
            "theme_day_avg_alpha_score": "75.0",
            "kr_universe_role": "CORE_TREND",
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


def test_section_performance_computes_same_day_theme_metrics_for_shadow():
    rows = []
    for idx in range(7):
        rows.append(
            {
                "ticker": f"9000{idx}.KQ",
                "market": "KOSDAQ",
                "primary_theme": "로봇/자동화",
                "tech_score": "75",
                "decision_score": "60",
                "trend": "UP",
                "return_1d_pct": "1.0",
                "return_3d_pct": "2.0",
                "return_5d_pct": "3.0",
                "base_trade_date": "2026-05-10",
            }
        )

    metrics = build_section_performance_metrics(rows, as_of_date="2026-05-15", generated_at="now")
    by_key = {(row["market"], row["section"], row["horizon_days"]): row for row in metrics}

    assert by_key[("KOSDAQ", "Shadow", 1)]["sample_n"] == 7
    assert by_key[("KOSDAQ", "Shadow", 5)]["win_rate_pct"] == 100.0
