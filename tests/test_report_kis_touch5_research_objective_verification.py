import json

from multi_agent.tools.report_kis_touch5_research_objective_verification import build_report


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_keeps_shadow_performance_separate_from_production(tmp_path):
    shadow = tmp_path / "shadow.json"
    dynamic = tmp_path / "dynamic.json"
    fixed = tmp_path / "fixed.json"
    comparison = tmp_path / "comparison.json"
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

    report = build_report(
        shadow_report_path=shadow,
        three_stage_dynamic_path=dynamic,
        three_stage_fixed_path=fixed,
        market_comparison_path=comparison,
    )

    assert report["research_inputs"]["no_dummy_data"] is True
    assert report["decision"]["status"] == "verified_shadow_performance"
    assert report["decision"]["production_replacement_proven"] is False
    assert report["decision"]["shadow_performance_proven"] is True
    assert "+5%" in report["user_goal"]["win_definition"]
    assert report["markets"]["KOSPI"]["kis_sidecar_longfold_shadow"]["gate"]["status"] == "shadow_ready"
    assert report["markets"]["KOSDAQ"]["three_stage_ev_ranker"]["decision"]["production_candidate"] is False
