import pandas as pd

from multi_agent.tools.report_kis_touch5_stability_search import build_report, parse_args, render_markdown


def _rows():
    rows = []
    for market in ("KOSPI", "KOSDAQ"):
        for day in range(1, 6):
            for slot in range(4):
                good = slot % 2 == 0
                rows.append(
                    {
                        "trade_date": f"2026-05-{day:02d}",
                        "run_id": f"{market}-RUN-{day:02d}",
                        "market": market,
                        "ticker": f"{market}-{day:02d}-{slot}",
                        "alpha_score": 80.0 if good else 30.0,
                        "tech_score": 75.0 if good else 25.0,
                        "volume_ratio": 3.0 if good else 0.8,
                        "kis_sidecar_present": 1,
                        "kis_current_price": 10000 + day + slot,
                        "kis_day_change_pct": 3.0 if good else -2.0,
                        "kis_foreigner_1d": 5.0 if good else -5.0,
                        "kis_news_title_count": 3 if good else 0,
                        "close_failure_prior_kis_sector_failure_rate_pct": 25.0 if good else 75.0,
                        "return_1d_pct": 4.0 if good else -2.0,
                        "return_3d_pct": 7.0 if good else -4.0,
                        "return_5d_pct": 9.0 if good else -6.0,
                        "max_high_return_1d_pct": 7.0 if good else 1.0,
                        "max_high_return_3d_pct": 9.0 if good else 2.0,
                        "max_high_return_5d_pct": 11.0 if good else 3.0,
                        "min_low_return_1d_pct": -1.0 if good else -4.0,
                        "min_low_return_3d_pct": -2.0 if good else -8.0,
                        "min_low_return_5d_pct": -4.0 if good else -12.0,
                    }
                )
    return rows


def test_stability_search_finds_period_stable_candidates(tmp_path):
    cache = tmp_path / "prepared.pkl"
    pd.DataFrame(_rows()).to_pickle(cache)
    args = parse_args(
        [
            "--prepared-cache",
            str(cache),
            "--months",
            "2026-05",
            "--model",
            "logistic",
            "--topns",
            "1",
            "--score-modes",
            "prob",
            "--prob-thresholds",
            "none",
            "--tail-thresholds",
            "none",
            "--min-train-rows",
            "8",
            "--min-test-rows",
            "1",
            "--min-train-days",
            "2",
            "--test-days",
            "1",
            "--max-folds",
            "2",
            "--min-scope-rows",
            "8",
            "--min-scope-days",
            "3",
            "--min-period-selected",
            "1",
            "--min-period-active-days",
            "1",
        ]
    )
    report = build_report(args)

    assert report["dummy_data_used"] is False
    assert report["decision"]["period_stable_both_market_candidate"] is True
    for market in ("KOSPI", "KOSDAQ"):
        assert report["markets"][market]["period_stable_count"] >= 1
        assert report["markets"][market]["top_candidates"][0]["selection_rule"] == "top1"
    markdown = render_markdown(report)
    assert "KIS Touch5 Stability Search" in markdown
    assert "Period Stable Top" in markdown


def test_stability_search_marks_missing_months(tmp_path):
    cache = tmp_path / "prepared.pkl"
    pd.DataFrame(_rows()).to_pickle(cache)
    args = parse_args(
        [
            "--prepared-cache",
            str(cache),
            "--months",
            "2026-01,2026-05",
            "--model",
            "logistic",
            "--topns",
            "1",
            "--score-modes",
            "prob",
            "--prob-thresholds",
            "none",
            "--tail-thresholds",
            "none",
            "--min-train-rows",
            "8",
            "--min-test-rows",
            "1",
            "--min-train-days",
            "2",
            "--test-days",
            "1",
            "--max-folds",
            "1",
            "--min-scope-rows",
            "8",
            "--min-scope-days",
            "3",
        ]
    )
    report = build_report(args)

    assert "2026-01" in report["data_profile"]["missing_actual_months"]
    assert report["decision"]["production_replacement_ready"] is False
