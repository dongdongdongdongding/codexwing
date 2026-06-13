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


def test_tail_first_scores_prioritize_drawdown_safety():
    predictions = pd.DataFrame(
        {
            "prob": [0.95, 0.55],
            "tail_prob": [0.35, 0.90],
        },
        index=["high_prob_unsafe", "lower_prob_safe"],
    )

    for mode in ("tail", "tail_plus_prob", "tail_prob_margin", "ev_strict"):
        scores = _score_predictions(predictions, mode)
        assert scores.loc["lower_prob_safe"] > scores.loc["high_prob_unsafe"]


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


def _touch5_gate(*, status, production_ready=False, shadow_display_allowed=True, reasons=None):
    return {
        "status": status,
        "production_ready": production_ready,
        "shadow_display_allowed": shadow_display_allowed,
        "production_blocking_reasons": list(reasons or []),
        "checks": [
            {"gate": "production", "name": "n", "expected": ">=30"},
            {"gate": "production", "name": "active_days", "expected": ">=15"},
            {"gate": "production", "name": "active_runs", "expected": ">=20"},
            {"gate": "production", "name": "hit5_dd10_5d_pct", "expected": ">=73"},
            {"gate": "production", "name": "min_min_low_5d_pct", "expected": ">=-10"},
        ],
    }


def _touch5_row(selection_rule, *, n, active_days, active_runs, hit5, avg5, min_low, gate):
    return {
        "market": "KOSPI",
        "label": "touch5_dd10_5d",
        "feature_set": "kis_sidecar_failure_risk_augmented",
        "model": "lightgbm",
        "score_mode": "tail_plus_prob",
        "selection_rule": selection_rule,
        "quality_score": hit5 + avg5,
        "metrics": {
            "n": n,
            "active_days": active_days,
            "active_runs": active_runs,
            "hit5_dd10_5d_pct": hit5,
            "avg_5d_pct": avg5,
            "min_min_low_5d_pct": min_low,
        },
        "kis_model_gate": gate,
    }


def test_constraint_frontier_separates_one_day_short_from_drawdown_failures():
    report = {
        "top_results": [],
        "market_reports": [
            {
                "scope": {"market": "KOSPI"},
                "status": "ok",
                "fold_meta": {},
                "results": [
                    _touch5_row(
                        "one_day_short_low_safe",
                        n=93,
                        active_days=14,
                        active_runs=54,
                        hit5=87.0968,
                        avg5=15.093948,
                        min_low=-8.919727,
                        gate=_touch5_gate(status="shadow_ready", reasons=["active_days_lt_15"]),
                    ),
                    _touch5_row(
                        "full_days_touch_low_fail",
                        n=58,
                        active_days=15,
                        active_runs=58,
                        hit5=79.3103,
                        avg5=11.322432,
                        min_low=-10.87344,
                        gate=_touch5_gate(status="shadow_risk_review", reasons=["min_low_5d_lt_neg10"]),
                    ),
                    _touch5_row(
                        "full_days_low_safe_touch_fail",
                        n=50,
                        active_days=15,
                        active_runs=50,
                        hit5=70.0,
                        avg5=5.0,
                        min_low=-8.0,
                        gate=_touch5_gate(status="shadow_ready", reasons=["hit5_dd10_5d_lt_73"]),
                    ),
                ],
            }
        ],
    }

    compact = _compact_report(report, per_market_results=5)
    frontiers = compact["market_reports"][0]["analysis_summary"]["constraint_frontiers"]

    assert frontiers["production_ready_count"] == 0
    assert frontiers["days_low_safe_touch_count"] == 0
    assert frontiers["one_day_short_low_safe_touch_count"] == 1
    one_day_short = frontiers["one_day_short_low_safe_touch_top"][0]
    assert one_day_short["selection_rule"] == "one_day_short_low_safe"
    assert one_day_short["production_frontier"]["deficits"]["active_days"] == 1.0
    assert one_day_short["production_frontier"]["deficits"]["min_low_5d_pct"] == 0.0

    assert frontiers["sample_sufficient_touch_but_low_fail_count"] == 1
    low_fail = frontiers["sample_sufficient_touch_but_low_fail_top"][0]
    assert low_fail["selection_rule"] == "full_days_touch_low_fail"
    assert low_fail["production_frontier"]["deficits"]["min_low_5d_pct"] == 0.87344

    assert frontiers["sample_sufficient_low_safe_but_touch_fail_count"] == 1
    assert (
        frontiers["sample_sufficient_low_safe_but_touch_fail_top"][0]["selection_rule"]
        == "full_days_low_safe_touch_fail"
    )
