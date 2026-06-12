import pandas as pd

from multi_agent.tools.sweep_kis_sidecar_thresholds import _compact_report, _score_predictions, _selection_rule


def test_selection_rule_preserves_existing_prob_default():
    assert _selection_rule(1, 0.3, 0.9) == "top1_p0p3_tail0p9"


def test_selection_rule_includes_non_default_score_mode():
    assert _selection_rule(1, 0.3, 0.9, "ev") == "top1_ev_p0p3_tail0p9"


def test_ev_score_penalizes_unsafe_candidate_even_with_high_success_prob():
    predictions = pd.DataFrame(
        {
            "prob": [0.90, 0.70],
            "tail_prob": [0.20, 0.95],
        },
        index=["unsafe", "safe"],
    )

    scores = _score_predictions(predictions, "ev")

    assert scores.loc["safe"] > scores.loc["unsafe"]


def test_prob_score_keeps_success_probability_order():
    predictions = pd.DataFrame(
        {
            "prob": [0.90, 0.70],
            "tail_prob": [0.20, 0.95],
        },
        index=["unsafe", "safe"],
    )

    scores = _score_predictions(predictions, "prob")

    assert scores.loc["unsafe"] > scores.loc["safe"]


def test_compact_report_removes_repeated_heavy_payloads():
    report = {
        "top_results": [
            {"selection_rule": "top1", "feature_columns": {"numeric": ["a"]}, "fold_meta": {"folds": []}},
        ],
        "market_reports": [
            {
                "scope": {"market": "KOSPI"},
                "status": "ok",
                "fold_meta": {"folds": [{"test_days": ["2026-05-13"]}]},
                "results": [
                    {"selection_rule": "top1", "feature_columns": {"numeric": ["a"]}, "fold_meta": {"folds": []}},
                    {"selection_rule": "top2", "feature_columns": {"numeric": ["a"]}, "fold_meta": {"folds": []}},
                ],
            }
        ],
    }

    compact = _compact_report(report, per_market_results=1)

    assert "feature_columns" not in compact["top_results"][0]
    assert compact["market_reports"][0]["result_count"] == 2
    assert len(compact["market_reports"][0]["results"]) == 1
    assert "fold_meta" not in compact["market_reports"][0]["results"][0]
    assert compact["market_reports"][0]["fold_meta"]["folds"][0]["test_days"] == ["2026-05-13"]
