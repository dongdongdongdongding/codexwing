from modules.realized_expectancy_admission import (
    ADMISSION_POLICY_VERSION,
    build_realized_expectancy_admission,
    compare_original_vs_expectancy_order,
    compare_unadjusted_vs_regime_theme_order,
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
    assert admission["base_expected_value_5d_pct"] == admission["expected_value_5d_pct"]
    assert admission["stress_expected_value_5d_pct"] < admission["base_expected_value_5d_pct"]
    assert admission["expected_value_band"]["stress_5d_pct"] == admission["stress_expected_value_5d_pct"]


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


def test_regime_theme_adjustment_is_applied_with_trace(monkeypatch):
    def fake_adjustment(_row):
        return {
            "version": "test",
            "prob_multiplier": 1.2,
            "return_multiplier": 1.2,
            "stop_risk_multiplier": 0.8,
            "confidence": 0.75,
            "warnings": [],
            "evidence": ["market_gate", "same_scan_theme"],
        }

    monkeypatch.setattr("modules.realized_expectancy_admission.build_regime_theme_adjustment", fake_adjustment)
    base_row = {
        "market": "KOSPI",
        "_analysis_section": "Top5",
        "expected_edge_score": 5.0,
        "prob_clean": 64.0,
        "decision_score": 82.0,
        "loss_risk_score": 34.0,
        "trend": "UP",
        "volume_ratio": 2.1,
        "day_change_pct": 2.0,
    }

    admission = build_realized_expectancy_admission(base_row, market="KOSPI", section="Top5")

    assert admission["3d_prob"] > admission["unadjusted_expectancy"]["3d_prob"]
    assert admission["avg_return_5d_pct"] > admission["unadjusted_expectancy"]["avg_return_5d_pct"]
    assert admission["stop_first_risk_pct"] < admission["unadjusted_expectancy"]["stop_first_risk_pct"]
    assert admission["regime_theme_adjustment"]["evidence"] == ["market_gate", "same_scan_theme"]
    assert admission["trace"]["regime_theme_effective_confidence"] == 0.75


def test_sparse_feature_rows_keep_rank_fallback_despite_regime_adjustment(monkeypatch):
    monkeypatch.setattr(
        "modules.realized_expectancy_admission.build_regime_theme_adjustment",
        lambda _row: {
            "version": "test",
            "prob_multiplier": 1.2,
            "return_multiplier": 1.2,
            "stop_risk_multiplier": 0.8,
            "confidence": 0.75,
            "warnings": [],
            "evidence": ["market_gate"],
        },
    )

    admission = build_realized_expectancy_admission(
        {"ticker": "005930.KS", "market": "KR", "_analysis_section_rank": 3},
        market="KR",
        section="Top5",
    )

    assert admission["ranking_score_5d"] == 97.0
    assert admission["trace"]["feature_evidence_count"] < 2


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


def test_regime_theme_comparison_reports_unadjusted_vs_adjusted(monkeypatch):
    monkeypatch.setattr(
        "modules.realized_expectancy_admission.build_regime_theme_adjustment",
        lambda row: {
            "version": "test",
            "prob_multiplier": 1.2 if row.get("ticker") == "B.KS" else 0.85,
            "return_multiplier": 1.2 if row.get("ticker") == "B.KS" else 0.85,
            "stop_risk_multiplier": 0.8 if row.get("ticker") == "B.KS" else 1.2,
            "confidence": 0.75,
            "warnings": [],
            "evidence": ["market_gate", "same_scan_theme"],
        },
    )
    rows = [
        {
            "ticker": "A.KS",
            "market": "KOSPI",
            "section": "Top5",
            "section_rank": 1,
            "expected_edge_score": 2.0,
            "prob_clean": 64.0,
            "loss_risk_score": 34.0,
            "trend": "UP",
            "return_3d_pct": -1.0,
            "return_5d_pct": -2.0,
            "stop_before_target_5d": True,
        },
        {
            "ticker": "B.KS",
            "market": "KOSPI",
            "section": "Top5",
            "section_rank": 2,
            "expected_edge_score": 2.0,
            "prob_clean": 64.0,
            "loss_risk_score": 34.0,
            "trend": "UP",
            "return_3d_pct": 3.0,
            "return_5d_pct": 7.0,
            "stop_before_target_5d": False,
        },
    ]

    report = compare_unadjusted_vs_regime_theme_order(rows, top_n=1)

    assert report["unadjusted_order"]["tickers"] == ["A.KS"]
    assert report["regime_theme_order"]["tickers"] == ["B.KS"]
    assert report["regime_theme_order"]["regime_theme_applied_rows"] == 1
