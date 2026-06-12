import json

from multi_agent.tools.report_kis_touch5_research_objective_verification import build_report


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_keeps_shadow_performance_separate_from_production(tmp_path):
    shadow = tmp_path / "shadow.json"
    dynamic = tmp_path / "dynamic.json"
    fixed = tmp_path / "fixed.json"
    comparison = tmp_path / "comparison.json"
    sidecar_baseline = tmp_path / "sidecar_baseline.json"
    sidecar_score = tmp_path / "sidecar_score.json"
    _write(
        shadow,
        {
            "research_inputs": {
                "data_rows": 157551,
                "prepared_rows": 157551,
            },
            "exploration_result": {
                "evaluated_results": 990,
                "production_ready": 0,
                "shadow_display_allowed": 521,
            },
            "market_results": {
                "KOSPI": {
                    "feature_set": "kis_sidecar_failure_risk_augmented",
                    "model": "lightgbm",
                    "selection_rule": "top1_p0p3_tail0p9",
                    "n": 50,
                    "active_days": 11,
                    "active_runs": 50,
                    "hit5_dd10_5d_pct": 82.0,
                    "hit10_5d_pct": 76.0,
                    "avg_5d_pct": 26.115197,
                    "min_min_low_5d_pct": -8.919727,
                    "expected_touch_policy_net_5d_pct": 1.973196,
                    "production_ready": False,
                    "shadow_display_allowed": True,
                    "production_blocking_reasons": ["active_days_lt_15"],
                },
                "KOSDAQ": {
                    "feature_set": "kis_sidecar_failure_risk_augmented",
                    "model": "lightgbm",
                    "selection_rule": "top1_p0p75_tail0p85",
                    "n": 19,
                    "active_days": 9,
                    "active_runs": 19,
                    "hit5_dd10_5d_pct": 100.0,
                    "hit10_5d_pct": 100.0,
                    "avg_5d_pct": 15.458772,
                    "min_min_low_5d_pct": -7.006077,
                    "expected_touch_policy_net_5d_pct": 4.601458,
                    "production_ready": False,
                    "shadow_display_allowed": True,
                    "production_blocking_reasons": ["n_lt_45", "active_days_lt_20", "active_runs_lt_20"],
                },
            },
        },
    )
    three_stage_market = {
        "rows": 100,
        "days": 20,
        "best": {
            "config": {"pool": "defensive", "pool_k": 100, "score_mode": "ev_hit10"},
            "metrics": {
                "n": 37,
                "active_days": 37,
                "hit5_dd10_5d_pct": 59.4595,
                "avg_dynamic_exit_5d_pct": 2.712248,
                "tail_breach_5d_pct": 13.5135,
                "min_min_low_5d_pct": -24.403496,
            },
        },
        "improvement": {
            "avg_ordered_exit_delta_pct": 0.970752,
            "hit5_dd10_delta_pct": 11.4595,
        },
    }
    _write(
        dynamic,
        {
            "status": "improved_shadow_research",
            "dummy_data_used": False,
            "validation": "walk-forward",
            "markets": [
                {"market": "KOSPI", **three_stage_market},
                {"market": "KOSDAQ", **three_stage_market},
            ],
        },
    )
    _write(
        fixed,
        {
            "status": "improved_shadow_research",
            "dummy_data_used": False,
            "markets": [
                {
                    "market": "KOSPI",
                    "best": {"metrics": {"n": 20, "hit5_dd10_5d_pct": 60.0, "avg_ordered_exit_5d_pct": 0.858965}},
                },
                {
                    "market": "KOSDAQ",
                    "best": {"metrics": {"n": 37, "hit5_dd10_5d_pct": 59.4595, "avg_ordered_exit_5d_pct": 0.692915}},
                },
            ],
        },
    )
    _write(
        comparison,
        {
            "markets": {
                "KOSPI": {
                    "current_kis_model": {
                        "identity": {"feature_set": "kis_sidecar_failure_risk_augmented"},
                        "kis_model_gate": {
                            "status": "shadow_ready",
                            "production_ready": False,
                            "shadow_display_allowed": True,
                            "production_blocking_reasons": ["active_days_lt_15"],
                            "production_economics": {"expected_touch_policy_net_5d_pct": 1.973196},
                        },
                    },
                    "operational_reflection": {"action": "shadow_top_section_only_until_gate_passes"},
                },
                "KOSDAQ": {
                    "current_kis_model": {
                        "identity": {"feature_set": "kis_sidecar_failure_risk_augmented"},
                        "kis_model_gate": {
                            "status": "shadow_ready",
                            "production_ready": False,
                            "shadow_display_allowed": True,
                            "production_blocking_reasons": ["n_lt_45"],
                            "production_economics": {"expected_touch_policy_net_5d_pct": 4.601458},
                        },
                    }
                },
            }
        },
    )
    sweep_market = {
        "scope": {"market": "KOSPI"},
        "fold_meta": {"folds": [{"test_days": ["2026-05-13"]}]},
        "results": [
            {
                "market": "KOSPI",
                "selection_rule": "top1_p0p3_tail0p9",
                "score_mode": "prob",
                "quality_score": 100.0,
                "metrics": {"n": 10, "active_days": 5, "hit5_dd10_5d_pct": 80.0, "avg_5d_pct": 3.0, "min_min_low_5d_pct": -8.0},
                "kis_model_gate": {"status": "shadow_ready", "shadow_display_allowed": True, "production_ready": False},
            }
        ],
    }
    _write(
        sidecar_baseline,
        {
            "market_reports": [
                sweep_market,
                {**sweep_market, "scope": {"market": "KOSDAQ"}},
            ]
        },
    )
    _write(
        sidecar_score,
        {
            "market_reports": [
                {
                    **sweep_market,
                    "results": [
                        *sweep_market["results"],
                        {
                            "market": "KOSPI",
                            "selection_rule": "top1_prob_x_tail_p0p75_tail0p95",
                            "score_mode": "prob_x_tail",
                            "quality_score": 90.0,
                            "metrics": {
                                "n": 8,
                                "active_days": 4,
                                "hit5_dd10_5d_pct": 90.0,
                                "avg_5d_pct": 2.0,
                                "min_min_low_5d_pct": -6.0,
                            },
                            "kis_model_gate": {"status": "shadow_ready", "shadow_display_allowed": True, "production_ready": False},
                        },
                    ],
                },
                {**sweep_market, "scope": {"market": "KOSDAQ"}},
            ]
        },
    )

    report = build_report(
        shadow_report_path=shadow,
        three_stage_dynamic_path=dynamic,
        three_stage_fixed_path=fixed,
        market_comparison_path=comparison,
        sidecar_baseline_sweep_path=sidecar_baseline,
        sidecar_score_sweep_path=sidecar_score,
    )

    assert report["research_inputs"]["no_dummy_data"] is True
    assert report["decision"]["status"] == "verified_shadow_performance"
    assert report["decision"]["production_replacement_proven"] is False
    assert report["decision"]["shadow_performance_proven"] is True
    assert "+5%" in report["user_goal"]["win_definition"]
    assert report["markets"]["KOSPI"]["kis_sidecar_longfold_shadow"]["gate"]["status"] == "shadow_ready"
    assert report["markets"]["KOSDAQ"]["three_stage_ev_ranker"]["decision"]["production_candidate"] is False
    score_exp = report["markets"]["KOSPI"]["sidecar_score_mode_experiment"]
    assert score_exp["same_fold_scope_verified"] is True
    assert score_exp["risk_adjusted_alternative"]["found"] is True
    assert score_exp["risk_adjusted_alternative"]["decision"] == "risk_adjusted_shadow_candidate_not_current_replacement"
