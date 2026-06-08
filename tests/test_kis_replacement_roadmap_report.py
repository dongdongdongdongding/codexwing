from __future__ import annotations

import json

from multi_agent.tools.report_kis_replacement_roadmap import build_report, render_markdown


def test_replacement_roadmap_report_uses_prior_readiness_and_contract(tmp_path):
    learning_dir = tmp_path / "learning"
    learning_dir.mkdir()
    (learning_dir / "kis_augmented_challenger_readiness.json").write_text(
        json.dumps(
            {
                "kis_feature_readiness": {
                    "status": "blocked",
                    "required_rows": 60,
                    "required_days": 10,
                    "families": {
                        "sidecar": {"rows": 2, "outcome_label_rows": 0},
                        "prefilter": {"rows": 0, "outcome_label_rows": 0},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (learning_dir / "kis_theme_news_emitted_news_backfill.json").write_text(
        json.dumps(
            {
                "summary": {
                    "candidate_rows": 3029,
                    "rows_written": 3029,
                    "unique_keys": 1425,
                    "kis_call_counts": {"news_titles": 1425},
                    "kis_failures": {},
                    "key_failures": {},
                    "rows_by_market": {"KOSPI": 1766, "KOSDAQ": 1263},
                    "no_dummy_data": True,
                }
            }
        ),
        encoding="utf-8",
    )
    (learning_dir / "kis_theme_news_emitted_news_backfill_verify.json").write_text(
        json.dumps(
            {
                "summary": {
                    "checked_rows": 3029,
                    "kis_theme_news_evidence_rows": 3029,
                    "kis_theme_news_kis_backed_rows": 3029,
                    "kis_theme_news_news_checked_rows": 3029,
                    "kis_theme_news_levels": {"medium": 2611, "strong": 418},
                    "no_dummy_data": True,
                }
            }
        ),
        encoding="utf-8",
    )
    (learning_dir / "kis_model_market_comparison.json").write_text(
        json.dumps(
            {
                "metric_contract": "2d is intentionally excluded",
                "markets": {
                    "KOSPI": {
                        "current_kis_model": {
                            "identity": {
                                "label": "pos_5d",
                                "feature_set": "kis_sidecar_only",
                                "model": "random_forest",
                                "selection_rule": "top1",
                                "topn": 1,
                            },
                            "metrics": {
                                "n": 29,
                                "active_days": 9,
                                "active_runs": 26,
                                "win_5d_pct": 96.5517,
                                "avg_5d_pct": 23.2462,
                                "min_min_low_5d_pct": -18.0251,
                                "bad_path_pct": 0.0,
                            },
                            "kis_model_gate": {
                                "status": "shadow_risk_review",
                                "production_ready": False,
                                "shadow_display_allowed": True,
                                "risk_review_required": True,
                                "production_blocking_reasons": ["active_days_lt_20"],
                                "risk_review_reasons": ["min_low_5d_lt_neg18"],
                            },
                        },
                        "source_kis_feature_readiness": {
                            "status": "ok",
                            "required_rows": 1200,
                            "required_days": 10,
                            "families": {
                                "sidecar": {
                                    "rows": 3029,
                                    "outcome_label_rows": 3029,
                                    "unique_days": 16,
                                    "unique_runs": 24,
                                    "mature_for_training": True,
                                },
                                "prefilter": {
                                    "rows": 36,
                                    "outcome_label_rows": 0,
                                    "unique_days": 1,
                                    "unique_runs": 1,
                                    "mature_for_training": False,
                                },
                            },
                        },
                        "operational_reflection": {
                            "action": "shadow_top_section_only_until_gate_passes",
                            "ui_recommendations": ["show KIS shadow gate"],
                        },
                        "performance_comparison_vs_existing": [
                            {
                                "baseline": "current_top5",
                                "topn": 5,
                                "sample_delta_n": -81.0,
                                "win_5d_delta_pct": 42.0062,
                                "avg_5d_delta_pct": 17.5593,
                            }
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    (tmp_path / "kis_operational_readiness.json").write_text(
        json.dumps(
            {
                "summary": {
                    "operational_replacement_verdict": "prior verdict",
                },
                "quote_coverage": {
                    "total_effective_quote_success_rate_pct": 100.0,
                },
                "endpoint_rollup": {
                    "ok_count": 17,
                    "failed_count": 2,
                },
            }
        ),
        encoding="utf-8",
    )

    report = build_report(tmp_path, learning_dir=learning_dir)

    assert report["summary"]["prior_readiness_verdict"] == "prior verdict"
    assert report["summary"]["endpoint_ok_count"] == 17
    assert report["summary"]["kis_model_readiness_status"] == "ok"
    assert report["summary"]["emitted_theme_news_backfill_rows"] == 3029
    assert report["summary"]["emitted_theme_news_no_dummy_data"] is True
    assert report["implemented_now"]["production_default_changed"] is True
    assert report["implemented_now"]["daily_scan_engine_default"] == "AG_KR_DAILY_SCAN_ENGINE=kis_operational"
    assert report["implemented_now"]["legacy_fallback_preserved"] is True
    assert report["implemented_now"]["top_deep_kis_source_timing"].startswith("scan_as_of")
    assert "feature_snapshot" in report["implemented_now"]["kis_challenger_feature_pipeline"]
    assert "real KIS payload rows" in report["implemented_now"]["kis_challenger_maturity_gate"]
    assert report["replacement_gates"][0]["current_status"] == "implemented_and_unit_tested"
    assert {gate["gate"] for gate in report["replacement_gates"]} >= {
        "candidate_only_deep_analysis",
        "deep_analysis_source_timing",
        "nightly_full_universe_validation",
        "model_lift",
    }
    rank_gate = next(gate for gate in report["replacement_gates"] if gate["gate"] == "rank_vi_news_financial")
    assert rank_gate["current_status"]["emitted_theme_news_rows"] == 3029
    assert rank_gate["current_status"]["kis_news_api_calls"] == 1425
    model_lift_gate = next(gate for gate in report["replacement_gates"] if gate["gate"] == "model_lift")
    assert model_lift_gate["current_status"]["sidecar_rows"] == 3029
    assert model_lift_gate["current_status"]["challenger_report"].endswith("kis_model_market_comparison.json")
    assert report["roadmap"]["phases"][0]["name"] == "contract_adapter"
    assert report["scan_logic_maximization_plan"][-1]["layer"] == "operations"
    reflection = report["final_operational_reflection_plan"]
    assert reflection["theme_news_backfill"]["no_dummy_data"] is True
    assert reflection["performance_report"]["current_market_reflections"]["KOSPI"]["gate"]["production_ready"] is False
    assert reflection["ui_report"]["web"][0].startswith("Place KIS Shadow")


def test_replacement_roadmap_markdown_contains_gate_table(tmp_path):
    report = build_report(tmp_path)
    markdown = render_markdown(report)

    assert "# KIS Replacement Roadmap" in markdown
    assert "100 Percent Replacement Gates" in markdown
    assert "source_contract" in markdown
    assert "Scan Logic Maximization Plan" in markdown
    assert "Final Operational Reflection Plan" in markdown
    assert "UI Required Changes" in markdown
