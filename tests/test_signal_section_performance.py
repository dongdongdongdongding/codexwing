from modules.signal_section_performance import (
    build_latest_performance_markdown,
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
    kosdaq_theme_shadow = {
        "ticker": "000004.KQ",
        "market": "KOSDAQ",
        "prob_clean": "30.0",
        "theme_day_avg_decision_score": "75.0",
        "theme_day_strength_rank": "1",
        "theme_day_strength_score": "2.1",
    }
    top5 = {"ticker": "000002.KS", "market": "KOSPI", "priority_rank": "5"}
    exception = {"ticker": "000003.KQ", "market": "KOSDAQ", "decision": "EXCEPTION_LEADER"}

    assert classify_signal_sections(kospi_shadow) == ["Shadow", "Top5"]
    assert classify_signal_sections(kosdaq_theme_shadow) == ["Shadow"]
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
            "return_7d_pct": "6.0",
            "return_14d_pct": "8.0",
            "return_30d_pct": "12.0",
            "base_trade_date": "2026-05-10",
        },
        {
            "ticker": "000002.KQ",
            "market": "KOSDAQ",
            "decision": "EXCEPTION_LEADER",
            "return_1d_pct": "-1.0",
            "return_3d_pct": "3.0",
            "return_5d_pct": "5.0",
            "return_7d_pct": "7.0",
            "return_14d_pct": "9.0",
            "return_30d_pct": "11.0",
            "base_trade_date": "2026-05-11",
        },
    ]

    metrics = build_section_performance_metrics(rows, as_of_date="2026-05-15", generated_at="now")
    by_key = {(row["market"], row["section"], row["horizon_days"]): row for row in metrics}

    assert by_key[("KOSPI", "Shadow", 1)]["scan_mode"] == "SWING"
    assert by_key[("KOSPI", "Shadow", 1)]["sample_n"] == 1
    assert by_key[("KOSPI", "Shadow", 1)]["win_rate_pct"] == 100.0
    assert by_key[("KOSPI", "Top5", 3)]["avg_return_pct"] == -2.0
    assert by_key[("KOSPI", "Shadow", 14)]["avg_return_pct"] == 8.0
    assert by_key[("KOSPI", "Shadow", 14)]["active_day_n"] == 1
    assert by_key[("KOSDAQ", "Exception Leader", 5)]["win_rate_pct"] == 100.0
    assert by_key[("KOSDAQ", "Exception Leader", 30)]["sample_n"] == 1
    markdown = build_latest_performance_markdown(metrics)
    assert "worst -2.00% / best -2.00%" in markdown
    assert "14D win 100.0% / avg +8.00% / worst +8.00% / best +8.00% / n=1 / days=1" in markdown


def test_section_performance_keeps_swing_and_intraday_separate():
    rows = [
        {
            "ticker": "000001.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "priority_rank": "1",
            "return_1d_pct": "1.0",
            "return_3d_pct": "2.0",
            "return_5d_pct": "3.0",
            "base_trade_date": "2026-05-10",
        },
        {
            "ticker": "000002.KS",
            "market": "KOSPI",
            "scan_mode": "INTRADAY",
            "priority_rank": "1",
            "return_1d_pct": "-4.0",
            "return_3d_pct": "-5.0",
            "return_5d_pct": "-6.0",
            "base_trade_date": "2026-05-10",
        },
    ]

    metrics = build_section_performance_metrics(rows, as_of_date="2026-05-15", generated_at="now")
    by_key = {
        (row["market"], row["scan_mode"], row["section"], row["horizon_days"]): row
        for row in metrics
    }

    assert by_key[("KOSPI", "SWING", "Top5", 1)]["win_rate_pct"] == 100.0
    assert by_key[("KOSPI", "INTRADAY", "Top5", 1)]["win_rate_pct"] == 0.0
    assert by_key[("KOSPI", "SWING", "Top5", 5)]["avg_return_pct"] == 3.0
    assert by_key[("KOSPI", "INTRADAY", "Top5", 5)]["avg_return_pct"] == -6.0


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
