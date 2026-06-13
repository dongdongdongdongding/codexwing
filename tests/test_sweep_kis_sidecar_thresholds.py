import pandas as pd

from multi_agent.tools.sweep_kis_sidecar_thresholds import (
    _compact_report,
    _fit_predict_folds,
    _score_predictions,
    _selection_rule,
)


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


def test_fit_predict_folds_keeps_single_class_test_day_for_realistic_validation():
    scoped = pd.DataFrame(
        {
            "trade_date": [
                "2026-05-01",
                "2026-05-01",
                "2026-05-02",
                "2026-05-02",
                "2026-05-03",
                "2026-05-03",
                "2026-05-04",
                "2026-05-04",
            ],
            "feature": [0.0, 1.0, 0.1, 1.1, 0.2, 0.3, 0.4, 1.2],
        }
    )
    y = pd.Series([0, 1, 0, 1, 0, 0, 0, 1], index=scoped.index)
    y_tail = pd.Series([1, 1, 1, 1, 1, 1, 1, 1], index=scoped.index)

    payload = _fit_predict_folds(
        scoped,
        y=y,
        y_tail=y_tail,
        numeric=["feature"],
        categorical=[],
        model_name="logistic",
        min_train_rows=4,
        min_test_rows=2,
        min_train_days=2,
        test_days=1,
        max_folds=2,
        need_tail=False,
        progress=False,
    )

    predicted_days = set(payload["predictions"]["test_days"])
    assert "2026-05-03" in predicted_days
    assert len(payload["folds"]) == 2


def test_compact_report_removes_repeated_heavy_payloads():
    report = {
        "top_results": [
            {
                "selection_rule": "top1",
                "feature_columns": {"numeric": ["a"]},
                "fold_meta": {"folds": []},
                "metrics": {"hit5_dd10_5d_pct": 80.0, "avg_5d_pct": 3.0, "min_min_low_5d_pct": -8.0, "n": 10, "active_days": 5},
                "kis_model_gate": {
                    "status": "shadow_ready",
                    "shadow_display_allowed": True,
                    "production_blocking_reasons": ["active_days_lt_15"],
                },
            },
        ],
        "market_reports": [
            {
                "scope": {"market": "KOSPI"},
                "status": "ok",
                "fold_meta": {"folds": [{"test_days": ["2026-05-13"]}]},
                "results": [
                    {
                        "selection_rule": "top1",
                        "score_mode": "prob",
                        "quality_score": 50.0,
                        "feature_columns": {"numeric": ["a"]},
                        "fold_meta": {"folds": []},
                        "metrics": {
                            "hit5_dd10_5d_pct": 80.0,
                            "avg_5d_pct": 3.0,
                            "min_min_low_5d_pct": -8.0,
                            "n": 10,
                            "active_days": 5,
                        },
                        "kis_model_gate": {
                            "status": "shadow_ready",
                            "shadow_display_allowed": True,
                            "production_blocking_reasons": ["active_days_lt_15"],
                        },
                    },
                    {
                        "selection_rule": "top2",
                        "score_mode": "ev",
                        "quality_score": 100.0,
                        "feature_columns": {"numeric": ["a"]},
                        "fold_meta": {"folds": []},
                        "metrics": {
                            "hit5_dd10_5d_pct": 75.0,
                            "avg_5d_pct": 5.0,
                            "min_min_low_5d_pct": -6.0,
                            "n": 20,
                            "active_days": 5,
                        },
                        "kis_model_gate": {
                            "status": "shadow_ready",
                            "shadow_display_allowed": True,
                            "production_blocking_reasons": ["active_days_lt_15"],
                        },
                    },
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
    summary = compact["market_reports"][0]["analysis_summary"]
    assert summary["status_counts"]["shadow_ready"] == 2
    assert summary["production_blocking_reason_counts"]["active_days_lt_15"] == 2
    assert summary["sample_only_blocked_count"] == 2
    assert summary["sample_only_top"][0]["selection_rule"] == "top2"
    assert summary["sample_sufficient_count"] == 0
    assert summary["sample_sufficient_top"] == []
    assert summary["active_day_frontier"]["max_active_days"] == 5
    assert summary["active_day_frontier"]["top"][0]["selection_rule"] == "top1"
    assert len(summary["pareto_top"]) == 1
    assert summary["pareto_top"][0]["selection_rule"] == "top1"
