import json

from multi_agent.tools.report_kis_touch5_kosdaq_bottleneck_matrix import (
    build_report,
    render_markdown,
)


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _stability_payload(feature_set, model, hit5, avg5, min_low, stable_count=0, blockers=None):
    return {
        "evaluation_contract": {
            "feature_set": feature_set,
            "model": model,
        },
        "markets": {
            "KOSDAQ": {
                "evaluated_count": 100,
                "production_ready_count": 0,
                "period_stable_count": stable_count,
                "shadow_period_stable_count": stable_count,
                "top_candidates": [
                    {
                        "selection_rule": f"{feature_set}_{model}_best",
                        "stability_status": "unstable_candidate",
                        "gate_status": "blocked",
                        "metrics": {
                            "n": 83,
                            "active_days": 14,
                            "active_runs": 28,
                            "hit5_dd10_5d_pct": hit5,
                            "avg_5d_pct": avg5,
                            "min_min_low_5d_pct": min_low,
                        },
                        "kis_model_gate": {
                            "status": "blocked",
                            "production_ready": False,
                            "production_blocking_reasons": blockers
                            or ["active_days_lt_20", "min_low_5d_lt_neg10"],
                        },
                    }
                ],
                "period_stable_top": [],
            }
        },
    }


def test_kosdaq_bottleneck_matrix_keeps_high_hit_candidate_blocked_by_tail_and_holdout(tmp_path):
    lightgbm = tmp_path / "lightgbm.json"
    logistic = tmp_path / "logistic.json"
    drawdown = tmp_path / "drawdown.json"
    _write(lightgbm, _stability_payload("kis_failure_risk_augmented", "lightgbm", 75.9036, 6.54185, -21.915669))
    _write(logistic, _stability_payload("kis_failure_risk_augmented", "logistic", 66.6667, 18.984628, -46.675277))
    _write(
        drawdown,
        {
            "status": "no_production_gate_pass_candidate",
            "validation_mode": "research_sweep_only_walk_forward_predictions",
            "filters_tested": 1120,
            "production_ready_count": 0,
            "deployment_ready": False,
            "base_candidate": {
                "identity": {"selection_rule": "top3_prob_tail_margin_p0p5_tail0"},
                "metrics": {
                    "n": 83,
                    "active_days": 14,
                    "hit5_dd10_5d_pct": 75.9036,
                    "avg_5d_pct": 6.54185,
                    "min_min_low_5d_pct": -21.915669,
                },
                "gate": {
                    "status": "blocked",
                    "production_ready": False,
                    "production_blocking_reasons": ["active_days_lt_20", "min_low_5d_lt_neg10"],
                },
            },
            "holdout_validation": {
                "status": "no_holdout_gate_pass",
                "selection_candidates_tested": 947,
                "holdout_candidates_evaluated": 80,
                "holdout_gate_pass_count": 0,
                "selection_best_holdout_evaluation": {
                    "identity": {
                        "selection_rule": "top3_prob_tail_margin_p0p5_close_failure_prior_market_touch5_n_le_8765"
                    },
                    "metrics": {
                        "n": 53,
                        "active_days": 8,
                        "hit5_dd10_5d_pct": 62.2642,
                        "min_min_low_5d_pct": -31.118999,
                    },
                    "gate": {
                        "status": "blocked",
                        "production_ready": False,
                        "production_blocking_reasons": ["hit5_dd10_5d_lt_73", "min_low_5d_lt_neg10"],
                    },
                },
                "decision": {"holdout_gate_pass_observed": False},
            },
        },
    )

    report = build_report(stability_report_paths=[logistic, lightgbm], drawdown_report_path=drawdown)

    decision = report["decision"]
    assert decision["status"] == "kosdaq_tail_risk_blocks_production_replacement"
    assert decision["production_replacement_ready"] is False
    assert decision["best_research_candidate"]["selection_rule"] == "kis_failure_risk_augmented_lightgbm_best"
    assert decision["best_research_candidate"]["metrics"]["hit5_dd10_5d_pct"] == 75.9036
    assert decision["best_research_candidate"]["metrics"]["min_min_low_5d_pct"] == -21.915669
    assert decision["holdout_gate_pass_count"] == 0
    assert decision["model_change_helped"] is False
    assert report["best_safe_tail"] == {}
    assert "drawdown_filter_holdout_gate_pass_count_zero" in decision["primary_blockers"]
    assert "KIS Touch5 KOSDAQ Bottleneck Matrix" in render_markdown(report)
