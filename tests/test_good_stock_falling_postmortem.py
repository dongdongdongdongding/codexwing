from modules.good_stock_falling_postmortem import build_good_stock_falling_postmortem, classify_loser_causes


def test_classify_loser_causes_detects_major_failure_modes():
    causes = classify_loser_causes(
        {
            "day_change_pct": 11,
            "foreigner": -1000,
            "institution": -2000,
            "volume_ratio": 0.5,
            "market_gate": "RED",
            "theme_day_avg_day_return_pct": -1.2,
            "stop_before_target_5d": True,
        }
    )

    assert "price_pre_reflection" in causes
    assert "flow_deterioration" in causes
    assert "volume_exhaustion" in causes
    assert "market_regime_drag" in causes
    assert "theme_reversal" in causes
    assert "stop_path_failure" in causes


def test_good_stock_falling_postmortem_reports_loser_causes_and_rule_deltas():
    report = build_good_stock_falling_postmortem(
        [
            {
                "ticker": "A.KS",
                "market": "KOSPI",
                "decision_score": 90,
                "return_5d_pct": -5,
                "day_change_pct": 10,
                "foreigner": -1,
                "institution": -1,
            },
            {
                "ticker": "B.KS",
                "market": "KOSPI",
                "decision_score": 88,
                "return_5d_pct": 7,
                "day_change_pct": 1,
                "foreigner": 1,
                "institution": 1,
            },
        ]
    )

    assert report["high_score_rows"] == 2
    assert report["high_score_losers"] == 1
    assert report["cause_counts"]["price_pre_reflection"] == 1
    assert any(item["cause"] == "price_pre_reflection" for item in report["proposed_rule_deltas"])
    assert report["metrics"]["high_score_all"]["return_5d_win_pct"] == 50.0
