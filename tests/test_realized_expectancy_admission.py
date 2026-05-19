from modules.realized_expectancy_admission import (
    ADMISSION_POLICY_VERSION,
    build_realized_expectancy_admission,
    compare_original_vs_expectancy_order,
    sort_by_realized_expectancy,
)


def test_negative_expected_edge_can_pass_when_momentum_and_section_are_strong():
    admission = build_realized_expectancy_admission(
        {
            "market": "KOSPI",
            "_analysis_section": "Exception Leader",
            "expected_edge_score": -1.0,
            "prob_clean": 62.0,
            "decision_score": 86.0,
            "loss_risk_score": 30.0,
            "trend": "UP",
            "volume_ratio": 2.4,
            "day_change_pct": 3.5,
            "position": "Rising",
        },
        market="KOSPI",
        section="Exception Leader",
    )

    assert admission["available"] is True
    assert admission["policy_version"] == ADMISSION_POLICY_VERSION
    assert admission["ranking_score_5d"] >= 58.0
    assert admission["stop_first_risk_pct"] < 28.0


def test_high_score_with_weak_edge_and_stop_risk_is_penalized():
    admission = build_realized_expectancy_admission(
        {
            "market": "KOSDAQ",
            "_analysis_section": "Top5",
            "expected_edge_score": -5.0,
            "prob_clean": 38.0,
            "decision_score": 92.0,
            "loss_risk_score": 78.0,
            "trend": "DOWN",
            "volume_ratio": 0.5,
            "day_change_pct": -5.0,
            "position": "Peak",
        },
        market="KOSDAQ",
        section="Top5",
    )

    assert admission["available"] is True
    assert admission["ranking_score_5d"] < 45.0
    assert admission["action_label_input"] == "realized_expectancy_risk"


def test_missing_calibration_returns_explicit_unavailable_reason():
    admission = build_realized_expectancy_admission({"market": "NASDAQ"}, market="NASDAQ", section="Top5")

    assert admission["available"] is False
    assert admission["unavailable_reason"] == "missing_calibration:NASDAQ:Top5"


def test_kr_market_rows_are_normalized_from_ticker_suffix():
    admission = build_realized_expectancy_admission({"ticker": "005930.KS", "market": "KR"}, market="KR", section="Top5")

    assert admission["available"] is True
    assert admission["market"] == "KOSPI"


def test_sort_by_realized_expectancy_keeps_original_rows_but_changes_order():
    rows = [
        {
            "ticker": "A.KS",
            "market": "KOSPI",
            "_analysis_section": "Top5",
            "_analysis_section_rank": 1,
            "expected_edge_score": -5.0,
            "prob_clean": 35.0,
            "loss_risk_score": 80.0,
            "trend": "DOWN",
        },
        {
            "ticker": "B.KS",
            "market": "KOSPI",
            "_analysis_section": "Top5",
            "_analysis_section_rank": 2,
            "expected_edge_score": 7.0,
            "prob_clean": 68.0,
            "loss_risk_score": 25.0,
            "trend": "UP",
            "volume_ratio": 2.0,
        },
    ]
    enriched = [dict(row, realized_expectancy_admission=build_realized_expectancy_admission(row, market="KOSPI", section="Top5")) for row in rows]

    sorted_rows = sort_by_realized_expectancy(enriched, horizon=5)

    assert [row["ticker"] for row in sorted_rows] == ["B.KS", "A.KS"]
    assert [row["ticker"] for row in enriched] == ["A.KS", "B.KS"]


def test_validation_comparison_reports_old_vs_expectancy_metrics():
    report = compare_original_vs_expectancy_order(
        [
            {
                "ticker": "A.KS",
                "market": "KOSPI",
                "section": "Top5",
                "section_rank": 1,
                "expected_edge_score": -5.0,
                "prob_clean": 35.0,
                "loss_risk_score": 80.0,
                "trend": "DOWN",
                "return_3d_pct": -2.0,
                "return_5d_pct": -4.0,
                "stop_before_target_5d": True,
            },
            {
                "ticker": "B.KS",
                "market": "KOSPI",
                "section": "Top5",
                "section_rank": 2,
                "expected_edge_score": 8.0,
                "prob_clean": 70.0,
                "loss_risk_score": 20.0,
                "trend": "UP",
                "volume_ratio": 2.0,
                "return_3d_pct": 4.0,
                "return_5d_pct": 9.0,
                "stop_before_target_5d": False,
            },
        ],
        top_n=1,
    )

    assert report["original_order"]["tickers"] == ["A.KS"]
    assert report["expectancy_order"]["tickers"] == ["B.KS"]
    assert report["comparison_groups"] == 1
    assert report["original_order"]["return_5d"]["avg_pct"] == -4.0
    assert report["expectancy_order"]["return_5d"]["avg_pct"] == 9.0
