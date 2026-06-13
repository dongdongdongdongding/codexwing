import json

from multi_agent.tools.report_kis_touch5_research_objective_verification import _markdown, build_report


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_keeps_shadow_performance_separate_from_production(tmp_path):
    shadow = tmp_path / "shadow.json"
    dynamic = tmp_path / "dynamic.json"
    fixed = tmp_path / "fixed.json"
    comparison = tmp_path / "comparison.json"
    sidecar_baseline = tmp_path / "sidecar_baseline.json"
    sidecar_score = tmp_path / "sidecar_score.json"
    candidate_leaderboard = tmp_path / "candidate_leaderboard.json"
    drawdown_filter = tmp_path / "drawdown_filter.json"
    coverage_audit = tmp_path / "coverage_audit.json"
    finaltopn_proxy = tmp_path / "finaltopn_proxy.json"
    finaltopn_actual = tmp_path / "finaltopn_actual.json"
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
                        "metrics": {
                            "n": 40,
                            "active_days": 11,
                            "active_runs": 20,
                            "hit5_dd10_5d_pct": 100.0,
                            "hit10_5d_pct": 100.0,
                            "avg_5d_pct": 20.411507,
                            "min_min_low_5d_pct": -9.300619,
                        },
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
                    "analysis_summary": {
                        "status_counts": {"shadow_ready": 2},
                        "production_blocking_reason_counts": {"active_days_lt_15": 2},
                        "sample_only_blocked_count": 2,
                        "sample_only_top": [
                            {
                                "selection_rule": "top1_prob_x_tail_p0p75_tail0p95",
                                "metrics": {"hit5_dd10_5d_pct": 90.0, "min_min_low_5d_pct": -6.0},
                            }
                        ],
                        "sample_sufficient_count": 1,
                        "sample_sufficient_top": [
                            {
                                "selection_rule": "top2_prob_x_tail_p0p75_tail0p95",
                                "metrics": {"hit5_dd10_5d_pct": 60.0, "min_min_low_5d_pct": -12.0},
                            }
                        ],
                        "pareto_top": [
                            {
                                "selection_rule": "top1_prob_x_tail_p0p75_tail0p95",
                                "metrics": {"hit5_dd10_5d_pct": 90.0, "min_min_low_5d_pct": -6.0},
                            }
                        ],
                    },
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
                        {
                            "market": "KOSPI",
                            "selection_rule": "top3_ev_p0p3_tail0p9",
                            "score_mode": "ev",
                            "quality_score": 110.0,
                            "metrics": {
                                "n": 142,
                                "active_days": 11,
                                "active_runs": 50,
                                "hit5_dd10_5d_pct": 83.8028,
                                "avg_5d_pct": 9.912085,
                                "min_min_low_5d_pct": -9.864936,
                            },
                            "kis_model_gate": {
                                "status": "shadow_ready",
                                "shadow_display_allowed": True,
                                "production_ready": False,
                                "production_blocking_reasons": ["active_days_lt_15"],
                            },
                        },
                    ],
                },
                {**sweep_market, "scope": {"market": "KOSDAQ"}},
            ]
        },
    )
    _write(
        candidate_leaderboard,
        {
            "decision": {
                "status": "keep_current_shadow",
                "production_replacement_ready": False,
                "shadow_upgrade_found": False,
                "recommended_action": "continue_forward_tracking_until_sample_gate_clears",
            },
            "markets": {
                "KOSPI": {
                    "status": "shadow_candidates_found_no_upgrade",
                    "candidate_count": 120,
                    "production_ready_count": 0,
                    "shadow_display_allowed_count": 20,
                    "sample_only_shadow_count": 5,
                    "best_sample_only_shadow": {
                        "source_path": "report.json",
                        "identity": {
                            "feature_set": "kis_sidecar_failure_risk_numeric",
                            "model": "lightgbm",
                            "selection_rule": "top1_tail0.95",
                            "score_mode": None,
                        },
                        "metrics": {
                            "n": 55,
                            "active_days": 12,
                            "active_runs": 55,
                            "hit5_dd10_5d_pct": 85.4545,
                            "avg_5d_pct": 7.937496,
                            "min_min_low_5d_pct": -9.816164,
                        },
                        "gate": {
                            "status": "shadow_ready",
                            "production_ready": False,
                            "shadow_display_allowed": True,
                            "production_blocking_reasons": ["active_days_lt_15"],
                            "non_sample_blockers": [],
                        },
                        "sample_progress": {"completion_pct": 93.333333},
                    },
                    "best_high_precision_shadow": {
                        "source_path": "score_report.json",
                        "identity": {
                            "feature_set": "kis_sidecar_failure_risk_augmented",
                            "model": "lightgbm",
                            "selection_rule": "top1_prob_tail_margin_tail0p95",
                            "score_mode": "prob_tail_margin",
                        },
                        "metrics": {
                            "n": 46,
                            "active_days": 10,
                            "active_runs": 46,
                            "hit5_dd10_5d_pct": 93.4783,
                            "avg_5d_pct": 5.385336,
                            "min_min_low_5d_pct": -5.558554,
                        },
                        "gate": {
                            "status": "shadow_ready",
                            "production_ready": False,
                            "shadow_display_allowed": True,
                            "production_blocking_reasons": ["active_days_lt_15"],
                            "non_sample_blockers": [],
                        },
                        "sample_progress": {"completion_pct": 88.888889},
                    },
                }
            },
        },
    )
    _write(
        drawdown_filter,
        {
            "status": "production_gate_pass_research_candidate_found",
            "validation_mode": "research_sweep_only_walk_forward_predictions",
            "deployment_ready": False,
            "market": "KOSPI",
            "filters_tested": 1107,
            "production_ready_count": 6,
            "scope": {"rows": 38361, "unique_days": 27},
            "base_candidate": {
                "identity": {
                    "feature_set": "kis_sidecar_failure_risk_augmented",
                    "model": "lightgbm",
                    "selection_rule": "top1_prob_tail0p85",
                    "validation_mode": "research_sweep_only_walk_forward_predictions",
                    "deployment_ready": False,
                },
                "metrics": {
                    "n": 58,
                    "active_days": 15,
                    "active_runs": 58,
                    "hit5_dd10_5d_pct": 79.3103,
                    "avg_5d_pct": 34.754917,
                    "min_min_low_5d_pct": -10.87344,
                },
                "gate": {
                    "status": "shadow_risk_review",
                    "production_ready": False,
                    "shadow_display_allowed": True,
                    "production_blocking_reasons": ["min_low_5d_lt_neg10"],
                },
            },
            "best_production_candidate": {
                "identity": {
                    "feature_set": "kis_sidecar_failure_risk_augmented",
                    "model": "lightgbm_drawdown_filter",
                    "selection_rule": "top1_prob_tail0p85_close_failure_prior_kis_sector_failure_rate_pct_le_46p6667",
                    "score_mode": "prob",
                    "drawdown_filter": {
                        "type": "single_feature_threshold",
                        "feature": "close_failure_prior_kis_sector_failure_rate_pct",
                        "op": "le",
                        "threshold": 46.666667,
                    },
                    "validation_mode": "research_sweep_only_walk_forward_predictions",
                    "deployment_ready": False,
                },
                "metrics": {
                    "n": 54,
                    "active_days": 15,
                    "active_runs": 54,
                    "hit5_dd10_5d_pct": 98.1481,
                    "avg_5d_pct": 24.676158,
                    "min_min_low_5d_pct": -9.230497,
                },
                "gate": {
                    "status": "production_ready",
                    "production_ready": True,
                    "shadow_display_allowed": True,
                    "production_economics": {"expected_touch_policy_net_5d_pct": 4.331054},
                },
            },
            "holdout_validation": {
                "status": "no_holdout_gate_pass",
                "validation_mode": "selection_fixed_rule_holdout_walk_forward_predictions",
                "deployment_ready": False,
                "selection_folds": [1, 2, 3, 4, 5],
                "holdout_folds": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
                "selection_candidates_tested": 811,
                "holdout_candidates_evaluated": 811,
                "holdout_gate_pass_count": 0,
                "selection_best_holdout_evaluation": {
                    "identity": {
                        "feature_set": "kis_sidecar_failure_risk_augmented",
                        "model": "lightgbm_drawdown_filter_selection_best_holdout",
                        "selection_rule": "top1_prob_tail0p85_close_failure_prior_theme_touch5_n_ge_3824",
                        "validation_mode": "selection_best_fixed_rule_holdout_walk_forward_predictions",
                        "deployment_ready": False,
                    },
                    "metrics": {
                        "n": 23,
                        "active_days": 7,
                        "active_runs": 23,
                        "hit5_dd10_5d_pct": 100.0,
                        "avg_5d_pct": 39.699864,
                        "min_min_low_5d_pct": -5.551964,
                    },
                    "gate": {
                        "status": "shadow_ready",
                        "production_ready": False,
                        "shadow_display_allowed": True,
                        "production_blocking_reasons": ["n_lt_30", "active_days_lt_15"],
                    },
                },
                "best_holdout_gate_pass_candidate": None,
                "decision": {
                    "holdout_gate_pass_observed": False,
                    "selection_best_holdout_gate_pass": False,
                    "deployment_ready": False,
                },
            },
            "rolling_prior_validation": {
                "status": "rolling_prior_shadow_ready",
                "validation_mode": "rolling_prior_oos_next_fold_walk_forward_predictions",
                "deployment_ready": False,
                "min_prior_folds": 5,
                "evaluated_steps": 15,
                "selected_count": 27,
                "aggregate_candidate": {
                    "identity": {
                        "feature_set": "kis_sidecar_failure_risk_augmented",
                        "model": "lightgbm_drawdown_filter_rolling_prior",
                        "selection_rule": "top1_prob_tail0p85_rolling_prior_oos",
                        "validation_mode": "rolling_prior_oos_next_fold_walk_forward_predictions",
                        "deployment_ready": False,
                    },
                    "metrics": {
                        "n": 27,
                        "active_days": 8,
                        "active_runs": 27,
                        "hit5_dd10_5d_pct": 96.2963,
                        "avg_5d_pct": 12.0,
                        "min_min_low_5d_pct": -6.578573,
                    },
                    "gate": {
                        "status": "shadow_ready",
                        "production_ready": False,
                        "shadow_display_allowed": True,
                        "production_blocking_reasons": ["n_lt_30", "active_days_lt_15"],
                    },
                },
                "decision": {
                    "production_gate_pass_observed": False,
                    "shadow_display_allowed": True,
                    "deployment_ready": False,
                },
            },
        },
    )
    _write(
        coverage_audit,
        {
            "decision": {
                "status": "coverage_gap_blocks_production_replacement",
                "actual_kis_full_jan_jun_period_proven": False,
                "actual_kis_oos_months": ["2026-05", "2026-06"],
                "missing_or_sparse_actual_kis_months": ["2026-01", "2026-02", "2026-03", "2026-04"],
                "feature_family_ablation_required": True,
                "rolling_prior_required": True,
            }
        },
    )
    finaltopn_market = {
        "rows": 1000,
        "days": 40,
        "best": {
            "config": {"pool": "prefilter", "pool_k": 20, "final_topn": 2, "score_mode": "ev"},
            "metrics": {
                "n": 40,
                "active_days": 21,
                "hit5_dd10_5d_pct": 57.5,
                "avg_ordered_exit_5d_pct": -0.618404,
                "avg_dynamic_exit_5d_pct": 1.249479,
                "min_min_low_5d_pct": -27.443637,
            },
            "gate": {
                "status": "blocked",
                "production_ready": False,
                "shadow_display_allowed": False,
                "production_blocking_reasons": ["hit5_dd10_5d_lt_73", "min_low_5d_lt_neg10"],
                "shadow_blocking_reasons": ["min_low_5d_lt_neg18"],
            },
        },
    }
    _write(
        finaltopn_proxy,
        {
            "status": "no_improvement",
            "dummy_data_used": False,
            "validation": "walk-forward",
            "markets": [
                {"market": "KOSPI", **finaltopn_market},
                {"market": "KOSDAQ", **finaltopn_market},
            ],
        },
    )
    _write(
        finaltopn_actual,
        {
            "status": "no_improvement",
            "dummy_data_used": False,
            "validation": "actual-sidecar",
            "markets": [
                {"market": "KOSPI", **finaltopn_market},
                {"market": "KOSDAQ", "rows": 200, "days": 27, "best": None},
            ],
        },
    )

    report = build_report(
        shadow_report_path=shadow,
        three_stage_dynamic_path=dynamic,
        three_stage_fixed_path=fixed,
        market_comparison_path=comparison,
        sidecar_baseline_sweep_path=sidecar_baseline,
        sidecar_score_sweep_path=sidecar_score,
        candidate_leaderboard_path=candidate_leaderboard,
        drawdown_filter_report_path=drawdown_filter,
        coverage_audit_path=coverage_audit,
        finaltopn_prefilter_proxy_path=finaltopn_proxy,
        finaltopn_actual_sidecar_path=finaltopn_actual,
    )

    assert report["research_inputs"]["no_dummy_data"] is True
    assert report["decision"]["status"] == "verified_shadow_performance"
    assert report["decision"]["production_replacement_proven"] is False
    assert report["decision"]["shadow_performance_proven"] is True
    assert report["decision"]["drawdown_filter_research_candidate_found"] is True
    assert report["decision"]["drawdown_filter_holdout_gate_pass"] is False
    assert report["decision"]["drawdown_filter_deployment_ready"] is False
    assert report["decision"]["drawdown_filter_action"] == "keep_research_only_until_holdout_or_forward_gate_pass"
    assert report["decision"]["coverage_audit_status"] == "coverage_gap_blocks_production_replacement"
    assert report["decision"]["actual_kis_full_jan_jun_period_proven"] is False
    assert report["decision"]["missing_or_sparse_actual_kis_months"] == [
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
    ]
    assert report["decision"]["feature_family_ablation_required"] is True
    assert report["decision"]["rolling_prior_required"] is True
    assert report["research_inputs"]["candidate_leaderboard"]["status"] == "keep_current_shadow"
    assert report["research_inputs"]["coverage_audit"]["status"] == "coverage_gap_blocks_production_replacement"
    assert report["research_inputs"]["drawdown_filter_production_gate_pass_count"] == 6
    assert report["research_inputs"]["finaltopn_prefilter_proxy_report"].endswith("finaltopn_proxy.json")
    leaderboard = report["markets"]["KOSPI"]["candidate_leaderboard"]
    assert leaderboard["best_sample_only_shadow"]["selection_rule"] == "top1_tail0.95"
    assert leaderboard["best_sample_only_shadow"]["metrics"]["hit5_dd10_5d_pct"] == 85.4545
    assert leaderboard["best_sample_only_shadow"]["sample_progress"]["completion_pct"] == 93.333333
    assert leaderboard["best_high_precision_shadow"]["selection_rule"] == "top1_prob_tail_margin_tail0p95"
    assert leaderboard["best_high_precision_shadow"]["metrics"]["hit5_dd10_5d_pct"] == 93.4783
    assert leaderboard["best_high_precision_shadow"]["sample_progress"]["completion_pct"] == 88.888889
    drawdown = report["markets"]["KOSPI"]["drawdown_filter_research"]
    assert drawdown["decision"]["production_gate_pass_observed"] is True
    assert drawdown["decision"]["holdout_gate_pass_observed"] is False
    assert drawdown["decision"]["promotable_now"] is False
    assert drawdown["best_gate_pass_research_candidate"]["production_gate_pass_observed"] is True
    assert drawdown["best_gate_pass_research_candidate"]["deployment_ready"] is False
    assert drawdown["best_gate_pass_research_candidate"]["metrics"]["hit5_dd10_5d_pct"] == 98.1481
    assert drawdown["holdout_validation"]["status"] == "no_holdout_gate_pass"
    assert drawdown["holdout_validation"]["holdout_candidates_evaluated"] == 811
    assert drawdown["holdout_validation"]["selection_best_holdout_evaluation"]["gate_status"] == "shadow_ready"
    assert drawdown["holdout_validation"]["selection_best_holdout_evaluation"]["metrics"]["hit5_dd10_5d_pct"] == 100.0
    rolling = drawdown["rolling_prior_validation"]
    assert rolling["status"] == "rolling_prior_shadow_ready"
    assert rolling["decision"]["production_gate_pass_observed"] is False
    assert rolling["aggregate_candidate"]["gate_status"] == "shadow_ready"
    assert rolling["aggregate_candidate"]["metrics"]["hit5_dd10_5d_pct"] == 96.2963
    assert report["markets"]["KOSDAQ"]["drawdown_filter_research"] == {}
    assert "+5%" in report["user_goal"]["win_definition"]
    assert report["markets"]["KOSPI"]["kis_sidecar_longfold_shadow"]["gate"]["status"] == "shadow_ready"
    assert report["markets"]["KOSDAQ"]["kis_sidecar_longfold_shadow"]["metrics"]["n"] == 40
    assert report["markets"]["KOSDAQ"]["kis_sidecar_longfold_shadow"]["metrics"]["active_runs"] == 20
    assert report["markets"]["KOSDAQ"]["three_stage_ev_ranker"]["decision"]["production_candidate"] is False
    finaltopn_exp = report["markets"]["KOSPI"]["finaltopn_three_stage_experiments"]["prefilter_proxy"]
    assert finaltopn_exp["best_config"]["final_topn"] == 2
    assert finaltopn_exp["best_gate"]["status"] == "blocked"
    assert finaltopn_exp["decision"]["promotable"] is False
    assert (
        report["markets"]["KOSDAQ"]["finaltopn_three_stage_experiments"]["actual_sidecar"]["best_metrics"] == {}
    )
    score_exp = report["markets"]["KOSPI"]["sidecar_score_mode_experiment"]
    assert score_exp["same_fold_scope_verified"] is True
    assert score_exp["risk_adjusted_alternative"]["found"] is True
    assert score_exp["risk_adjusted_alternative"]["decision"] == "risk_adjusted_shadow_candidate_not_current_replacement"
    assert score_exp["near_production_candidate"]["found"] is True
    assert score_exp["near_production_candidate"]["candidate"]["selection_rule"] == "top3_ev_p0p3_tail0p9"
    assert score_exp["near_production_candidate"]["candidate"]["sample_blockers"] == ["active_days_lt_15"]
    score_summary = score_exp["score_report_analysis_summary"]
    assert score_summary["production_blocking_reason_counts"]["active_days_lt_15"] == 2
    assert score_summary["sample_only_top"][0]["selection_rule"] == "top1_prob_x_tail_p0p75_tail0p95"
    assert score_summary["sample_sufficient_top"][0]["selection_rule"] == "top2_prob_x_tail_p0p75_tail0p95"


def test_build_report_includes_static_master_shadow_validation_without_production_promotion(tmp_path):
    shadow = tmp_path / "shadow.json"
    dynamic = tmp_path / "dynamic.json"
    fixed = tmp_path / "fixed.json"
    comparison = tmp_path / "comparison.json"
    sidecar_baseline = tmp_path / "sidecar_baseline.json"
    sidecar_score = tmp_path / "sidecar_score.json"
    static_aug = tmp_path / "static_aug.json"
    static_suite = tmp_path / "static_suite.json"
    static_three_kospi = tmp_path / "static_three_kospi.json"
    static_three_kosdaq = tmp_path / "static_three_kosdaq.json"

    _write(
        shadow,
        {
            "research_inputs": {"data_rows": 100, "prepared_rows": 100},
            "exploration_result": {"evaluated_results": 2, "production_ready": 0, "shadow_display_allowed": 0},
            "market_results": {},
        },
    )
    _write(
        dynamic,
        {
            "status": "research",
            "dummy_data_used": False,
            "validation": "walk-forward",
            "markets": [
                {"market": "KOSPI", "best": {"metrics": {}}},
                {"market": "KOSDAQ", "best": {"metrics": {}}},
            ],
        },
    )
    _write(fixed, {"status": "research", "dummy_data_used": False, "markets": []})
    _write(
        comparison,
        {
            "markets": {
                "KOSPI": {"current_kis_model": {"identity": {}, "metrics": {}, "kis_model_gate": {"status": "blocked"}}},
                "KOSDAQ": {"current_kis_model": {"identity": {}, "metrics": {}, "kis_model_gate": {"status": "blocked"}}},
            }
        },
    )
    _write(sidecar_baseline, {"market_reports": []})
    _write(sidecar_score, {"market_reports": [], "summary": {"evaluated_results": 0}})
    _write(
        static_aug,
        {
            "decision": {"augmented_cache_ready_for_research": True, "production_replacement_ready": False},
            "markets": [
                {
                    "market": "KOSPI",
                    "master_matched_rows": 10,
                    "master_matched_row_pct": 80.0,
                    "augmented_rows": 10,
                    "augmented_row_pct": 80.0,
                    "no_dummy_data": True,
                    "leakage_policy": "ticker static only",
                    "coverage_delta": {
                        "sidecar_stock_static": {
                            "features_improved": 2,
                            "avg_positive_delta_pct": 80.0,
                            "top_deltas": [{"feature": "kis_stock_type", "delta_pct": 80.0}],
                        }
                    },
                },
                {
                    "market": "KOSDAQ",
                    "master_matched_rows": 20,
                    "master_matched_row_pct": 90.0,
                    "augmented_rows": 20,
                    "augmented_row_pct": 90.0,
                    "no_dummy_data": True,
                    "leakage_policy": "ticker static only",
                    "coverage_delta": {},
                },
            ],
        },
    )

    def suite_market(market, hit5, win5):
        return {
            "market": market,
            "best": {
                "identity": {"market": market, "feature_set": "kis_failure_prior_numeric", "model": "lightgbm_ranker"},
                "metrics": {
                    "n": 48,
                    "active_days": 48,
                    "active_runs": 48,
                    "hit5_dd10_5d_pct": hit5,
                    "win_5d_pct": win5,
                    "hit10_5d_pct": hit5,
                    "avg_5d_pct": 9.0,
                    "min_ordered_exit_5d_pct": -12.0,
                    "buy_premium_pct": 2.0,
                },
                "gate": {
                    "status": "shadow_risk_review",
                    "production_ready": False,
                    "shadow_display_allowed": True,
                    "risk_review_required": True,
                    "production_blocking_reasons": ["hit5_dd10_5d_lt_73"],
                    "production_economics": {"expected_touch_policy_net_5d_pct": -1.0},
                },
                "quality_score": 100.0,
            },
        }

    _write(
        static_suite,
        {
            "decision": {
                "status": "shadow_ready",
                "all_required_markets_shadow_display_allowed": True,
                "all_required_markets_production_ready": False,
            },
            "markets": {
                "KOSPI": suite_market("KOSPI", 52.0833, 62.5),
                "KOSDAQ": suite_market("KOSDAQ", 60.4167, 72.9167),
            },
        },
    )

    def three_stage_report(market, hit5, avg_exit, dynamic_exit):
        return {
            "status": "improved_shadow_research",
            "dummy_data_used": False,
            "validation": "walk-forward; fold fit/calibration/test split",
            "markets": [
                {
                    "market": market,
                    "best": {
                        "config": {"pool": "prefilter", "pool_k": 5, "score_mode": "success_tail"},
                        "metrics": {
                            "n": 22,
                            "active_days": 22,
                            "hit5_dd10_5d_pct": hit5,
                            "avg_ordered_exit_5d_pct": avg_exit,
                            "avg_dynamic_exit_5d_pct": dynamic_exit,
                            "tail_breach_5d_pct": 27.0,
                            "min_min_low_5d_pct": -22.0,
                        },
                        "gate": {
                            "status": "blocked",
                            "production_ready": False,
                            "shadow_display_allowed": False,
                            "production_blocking_reasons": ["hit5_dd10_5d_lt_73", "min_low_5d_lt_neg10"],
                        },
                    },
                    "improvement": {
                        "avg_ordered_exit_delta_pct": 0.8,
                        "hit5_dd10_delta_pct": 10.0,
                    },
                }
            ],
        }

    _write(static_three_kospi, three_stage_report("KOSPI", 68.1818, 0.104695, 1.915976))
    _write(static_three_kosdaq, three_stage_report("KOSDAQ", 65.2174, 0.034024, 2.416252))

    report = build_report(
        shadow_report_path=shadow,
        three_stage_dynamic_path=dynamic,
        three_stage_fixed_path=fixed,
        market_comparison_path=comparison,
        sidecar_baseline_sweep_path=sidecar_baseline,
        sidecar_score_sweep_path=sidecar_score,
        static_master_augmentation_path=static_aug,
        static_master_focused_suite_path=static_suite,
        static_master_three_stage_paths={
            "KOSPI": static_three_kospi,
            "KOSDAQ": static_three_kosdaq,
        },
    )

    experiment = report["historical_proxy_augmentation_experiment"]
    assert experiment["decision"]["static_master_shadow_ready"] is True
    assert experiment["decision"]["static_master_production_ready"] is False
    assert experiment["decision"]["static_master_three_stage_improved"] is True
    assert experiment["decision"]["static_master_three_stage_production_ready"] is False
    assert experiment["decision"]["production_replacement_ready"] is False
    assert "both-market shadow-ready" in experiment["decision"]["positive_shadow_result"]
    assert experiment["markets"]["KOSPI"]["static_master_augmentation"]["augmented_row_pct"] == 80.0
    kospi_three = experiment["markets"]["KOSPI"]["static_master_three_stage"]
    assert kospi_three["best_metrics"]["avg_dynamic_exit_5d_pct"] == 1.915976
    assert kospi_three["best_gate"]["production_ready"] is False
    kosdaq_suite = experiment["markets"]["KOSDAQ"]["static_master_focused_suite"]
    assert kosdaq_suite["status"] == "shadow_ready"
    assert kosdaq_suite["best_metrics"]["win_5d_pct"] == 72.9167
    assert kosdaq_suite["best_gate"]["production_ready"] is False


def test_build_report_routes_optional_kosdaq_drawdown_filter_without_overwriting_kospi(tmp_path):
    shadow = tmp_path / "shadow.json"
    dynamic = tmp_path / "dynamic.json"
    fixed = tmp_path / "fixed.json"
    comparison = tmp_path / "comparison.json"
    sidecar_baseline = tmp_path / "sidecar_baseline.json"
    sidecar_score = tmp_path / "sidecar_score.json"
    kosdaq_drawdown = tmp_path / "kosdaq_drawdown.json"

    _write(
        shadow,
        {
            "research_inputs": {"data_rows": 100, "prepared_rows": 100},
            "exploration_result": {"evaluated_results": 0, "production_ready": 0, "shadow_display_allowed": 0},
            "market_results": {},
        },
    )
    _write(
        dynamic,
        {
            "status": "research",
            "dummy_data_used": False,
            "validation": "walk-forward",
            "markets": [
                {"market": "KOSPI", "best": {"metrics": {}}},
                {"market": "KOSDAQ", "best": {"metrics": {}}},
            ],
        },
    )
    _write(fixed, {"status": "research", "dummy_data_used": False, "markets": []})
    _write(
        comparison,
        {
            "markets": {
                "KOSPI": {"current_kis_model": {"identity": {}, "metrics": {}, "kis_model_gate": {"status": "blocked"}}},
                "KOSDAQ": {"current_kis_model": {"identity": {}, "metrics": {}, "kis_model_gate": {"status": "blocked"}}},
            }
        },
    )
    _write(sidecar_baseline, {"market_reports": []})
    _write(sidecar_score, {})
    _write(
        kosdaq_drawdown,
        {
            "status": "no_production_gate_pass_candidate",
            "validation_mode": "research_sweep_only_walk_forward_predictions",
            "deployment_ready": False,
            "market": "KOSDAQ",
            "filters_tested": 1120,
            "production_ready_count": 0,
            "base_candidate": {
                "identity": {
                    "feature_set": "kis_failure_risk_augmented",
                    "model": "lightgbm",
                    "selection_rule": "top3_prob_tail_margin_p0p5",
                },
                "metrics": {
                    "n": 83,
                    "active_days": 14,
                    "active_runs": 28,
                    "hit5_dd10_5d_pct": 75.9036,
                    "avg_5d_pct": 6.54185,
                    "min_min_low_5d_pct": -21.915669,
                },
                "gate": {
                    "status": "blocked",
                    "production_ready": False,
                    "shadow_display_allowed": False,
                    "production_blocking_reasons": ["active_days_lt_20", "min_low_5d_lt_neg10"],
                },
            },
            "holdout_validation": {
                "status": "no_holdout_gate_pass",
                "validation_mode": "selection_fixed_rule_holdout_walk_forward_predictions",
                "deployment_ready": False,
                "selection_candidates_tested": 947,
                "holdout_candidates_evaluated": 80,
                "holdout_gate_pass_count": 0,
                "selection_best_holdout_evaluation": {
                    "identity": {
                        "feature_set": "kis_failure_risk_augmented",
                        "model": "lightgbm_drawdown_filter_selection_best_holdout",
                        "selection_rule": "top3_prob_tail_margin_p0p5_close_failure_prior_market_touch5_n_le_8765",
                    },
                    "metrics": {
                        "n": 53,
                        "active_days": 8,
                        "active_runs": 17,
                        "hit5_dd10_5d_pct": 62.2642,
                        "avg_5d_pct": 3.885862,
                        "min_min_low_5d_pct": -31.118999,
                    },
                    "gate": {
                        "status": "blocked",
                        "production_ready": False,
                        "shadow_display_allowed": False,
                        "production_blocking_reasons": [
                            "active_days_lt_20",
                            "hit5_dd10_5d_lt_73",
                            "min_low_5d_lt_neg10",
                        ],
                    },
                },
                "decision": {
                    "holdout_gate_pass_observed": False,
                    "selection_best_holdout_gate_pass": False,
                    "deployment_ready": False,
                },
            },
            "rolling_prior_validation": {
                "status": "skipped_by_operator",
                "deployment_ready": False,
                "decision": {"production_gate_pass_observed": False, "deployment_ready": False},
            },
        },
    )

    report = build_report(
        shadow_report_path=shadow,
        three_stage_dynamic_path=dynamic,
        three_stage_fixed_path=fixed,
        market_comparison_path=comparison,
        sidecar_baseline_sweep_path=sidecar_baseline,
        sidecar_score_sweep_path=sidecar_score,
        kosdaq_drawdown_filter_report_path=kosdaq_drawdown,
    )

    assert report["markets"]["KOSPI"]["drawdown_filter_research"] == {}
    drawdown = report["markets"]["KOSDAQ"]["drawdown_filter_research"]
    assert drawdown["status"] == "no_production_gate_pass_candidate"
    assert drawdown["production_gate_pass_count"] == 0
    assert drawdown["base_candidate"]["selection_rule"] == "top3_prob_tail_margin_p0p5"
    assert drawdown["base_candidate"]["metrics"]["min_min_low_5d_pct"] == -21.915669
    assert drawdown["holdout_validation"]["status"] == "no_holdout_gate_pass"
    assert drawdown["holdout_validation"]["selection_best_holdout_evaluation"]["metrics"]["hit5_dd10_5d_pct"] == 62.2642
    assert report["research_inputs"]["kosdaq_drawdown_filter_status"] == "no_production_gate_pass_candidate"
    assert "kosdaq_drawdown_filter_research" in _markdown(report)
