import json

import pandas as pd

from multi_agent.tools.report_kis_touch5_research_coverage_audit import build_report, parse_args, render_markdown


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_coverage_audit_uses_actual_cache_dates_and_feature_families(tmp_path):
    rows = []
    for market in ("KOSPI", "KOSDAQ"):
        for idx in range(1001):
            rows.append(
                {
                    "trade_date": "2026-05-13",
                    "market": market,
                    "ticker": f"{market}{idx}",
                    "kis_daily_return_5d_pct": 1.2,
                    "kis_foreigner_1d": 3.4,
                    "kis_stock_listed_shares": 1000000,
                    "kis_financial_operating_profit_margin": 5.5,
                    "kis_news_title_count": 2,
                    "close_failure_prior_kis_sector_failure_rate_pct": 41.0,
                    "tech_score": 71.0,
                }
            )
    cache = tmp_path / "prepared.pkl"
    pd.DataFrame(rows).to_pickle(cache)

    leaderboard = tmp_path / "leaderboard.json"
    _write_json(
        leaderboard,
        {
            "decision": {"production_replacement_ready": False},
            "markets": {
                "KOSPI": {
                    "best_candidate": {
                        "identity": {"selection_rule": "top2_prob_plus_tail_p0p8_tail0p85"},
                        "metrics": {
                            "n": 93,
                            "active_days": 14,
                            "active_runs": 54,
                            "hit5_dd10_5d_pct": 87.0968,
                            "avg_5d_pct": 15.093948,
                            "min_min_low_5d_pct": -8.919727,
                        },
                        "gate": {"production_ready": False, "production_blocking_reasons": ["active_days_lt_15"]},
                        "validation_mode": "tailfirst_realistic_coverage",
                    }
                },
                "KOSDAQ": {
                    "best_candidate": {
                        "identity": {"selection_rule": "top3_ev_tail0p9"},
                        "metrics": {
                            "n": 58,
                            "active_days": 10,
                            "active_runs": 20,
                            "hit5_dd10_5d_pct": 94.8276,
                            "avg_5d_pct": 8.515405,
                            "min_min_low_5d_pct": -7.8413,
                        },
                        "gate": {"production_ready": False, "production_blocking_reasons": ["active_days_lt_20"]},
                        "validation_mode": "dayfold_realistic_coverage",
                    }
                },
            },
        },
    )
    objective = tmp_path / "objective.json"
    _write_json(objective, {"decision": {"production_replacement_proven": False}})
    drawdown = tmp_path / "drawdown.json"
    _write_json(
        drawdown,
        {
            "best_production_candidate": {
                "identity": {"selection_rule": "research_rule", "validation_mode": "research_sweep_only_walk_forward_predictions"},
                "metrics": {
                    "n": 54,
                    "active_days": 15,
                    "active_runs": 54,
                    "hit5_dd10_5d_pct": 98.1481,
                    "avg_5d_pct": 24.676158,
                    "min_min_low_5d_pct": -9.230497,
                },
            },
            "holdout_validation": {"holdout_gate_pass_count": 0},
        },
    )
    drawdown_variant = tmp_path / "drawdown_variant.json"
    _write_json(
        drawdown_variant,
        {
            "status": "production_gate_pass_research_candidate_found",
            "score_mode": "prob",
            "topn": 1,
            "tail_threshold": 0.85,
            "production_ready_count": 1,
            "best_production_candidate": {
                "identity": {"selection_rule": "variant_best", "validation_mode": "research_sweep_only_walk_forward_predictions"},
                "metrics": {
                    "n": 54,
                    "active_days": 15,
                    "active_runs": 54,
                    "hit5_dd10_5d_pct": 98.1481,
                    "avg_5d_pct": 24.676158,
                    "min_min_low_5d_pct": -9.230497,
                },
                "gate": {"status": "production_ready", "production_blocking_reasons": []},
            },
            "top_results": [
                {
                    "identity": {"selection_rule": "one_day_short_rule", "validation_mode": "research_sweep_only_walk_forward_predictions"},
                    "metrics": {
                        "n": 57,
                        "active_days": 14,
                        "active_runs": 57,
                        "hit5_dd10_5d_pct": 98.2456,
                        "avg_5d_pct": 38.060278,
                        "min_min_low_5d_pct": -8.188031,
                    },
                    "gate": {"status": "shadow_ready", "production_blocking_reasons": ["active_days_lt_15"]},
                }
            ],
            "holdout_validation": {
                "holdout_gate_pass_count": 0,
                "selection_best_holdout_evaluation": {
                    "identity": {"selection_rule": "fixed_holdout_rule", "validation_mode": "selection_best_fixed_rule_holdout_walk_forward_predictions"},
                    "metrics": {
                        "n": 40,
                        "active_days": 12,
                        "active_runs": 40,
                        "hit5_dd10_5d_pct": 87.5,
                        "avg_5d_pct": 32.224954,
                        "min_min_low_5d_pct": -10.87344,
                    },
                    "gate": {"status": "shadow_risk_review", "production_blocking_reasons": ["active_days_lt_15"]},
                },
            },
            "rolling_prior_validation": {
                "status": "rolling_prior_shadow_ready",
                "validation_mode": "rolling_prior_oos_next_fold_walk_forward_predictions",
                "min_prior_folds": 3,
                "max_filter_features": 30,
                "evaluated_steps": 17,
                "selected_count": 22,
                "aggregate_candidate": {
                    "identity": {"selection_rule": "rolling_prior_oos", "validation_mode": "rolling_prior_oos_next_fold_walk_forward_predictions"},
                    "metrics": {
                        "n": 22,
                        "active_days": 7,
                        "active_runs": 22,
                        "hit5_dd10_5d_pct": 86.3636,
                        "avg_5d_pct": 33.261526,
                        "min_min_low_5d_pct": -9.469258,
                    },
                    "gate": {"status": "shadow_ready", "production_blocking_reasons": ["n_lt_30", "active_days_lt_15"]},
                },
            },
        },
    )
    actual_report = tmp_path / "actual.json"
    _write_json(actual_report, {"fold_meta": {"folds": [{"test_days": ["2026-05-13", "2026-06-01"]}]}})
    proxy_report = tmp_path / "proxy.json"
    _write_json(proxy_report, {"markets": [{"folds": [{"test_start": "2026-01-02", "test_end": "2026-06-05"}]}]})

    args = parse_args(
        [
            "--prepared-cache",
            str(cache),
            "--candidate-leaderboard",
            str(leaderboard),
            "--objective-report",
            str(objective),
            "--drawdown-report",
            str(drawdown),
            "--additional-drawdown-reports",
            str(drawdown_variant),
            "--actual-reports",
            str(actual_report),
            "--proxy-reports",
            str(proxy_report),
        ]
    )
    report = build_report(args)

    assert report["prepared_cache"]["date_min"] == "2026-05-13"
    assert report["prepared_cache"]["date_max"] == "2026-05-13"
    assert report["decision"]["actual_kis_full_jan_jun_period_proven"] is False
    assert "2026-01" in report["decision"]["missing_or_sparse_actual_kis_months"]
    may = [row for row in report["period_coverage"]["month_market_matrix"] if row["month"] == "2026-05"][0]
    assert may["status"] == "usable"
    assert report["feature_family_coverage"]["ablation_status"]["kis_flow"]["present"] is True
    assert report["feature_family_coverage"]["ablation_status"]["close_failure_prior"]["column_count"] == 1
    assert report["current_best_performance"]["markets"]["KOSPI"]["hit5_dd10_5d_pct"] == 87.0968
    assert report["current_best_performance"]["research_only_best"]["holdout_gate_pass_count"] == 0
    assert report["current_best_performance"]["research_variants"][1]["research_best"]["selection_rule"] == "variant_best"
    assert (
        report["current_best_performance"]["research_variants"][1]["rolling_prior"]["aggregate_candidate"][
            "hit5_dd10_5d_pct"
        ]
        == 86.3636
    )
    assert (
        report["current_best_performance"]["best_near_miss_by_active_days"]["selection_rule"]
        == "one_day_short_rule"
    )


def test_coverage_audit_markdown_surfaces_current_best_and_month_matrix(tmp_path):
    cache = tmp_path / "prepared.pkl"
    pd.DataFrame(
        [
            {
                "trade_date": "2026-06-01",
                "market": "KOSPI",
                "ticker": "000001",
                "kis_daily_return_5d_pct": 1.0,
            }
        ]
    ).to_pickle(cache)
    empty = tmp_path / "empty.json"
    _write_json(empty, {})
    args = parse_args(
        [
            "--prepared-cache",
            str(cache),
            "--candidate-leaderboard",
            str(empty),
            "--objective-report",
            str(empty),
            "--drawdown-report",
            str(empty),
            "--additional-drawdown-reports",
            "--actual-reports",
            str(empty),
            "--proxy-reports",
            str(empty),
        ]
    )
    markdown = render_markdown(build_report(args))

    assert "KIS Touch5 Research Coverage Audit" in markdown
    assert "Month Matrix" in markdown
    assert "Feature Families" in markdown
