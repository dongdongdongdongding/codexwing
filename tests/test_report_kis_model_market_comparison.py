import json

from multi_agent.tools.report_kis_model_market_comparison import build_report


def _source(path, market):
    payload = {
        "generated_at": "2026-06-08T00:00:00+00:00",
        "raw_rows": 10,
        "prepared_rows": 8,
        "evaluated_combinations": 2,
        "ok_combinations": 1,
        "best_kis": {
            "market": market,
            "label": "pos_5d",
            "feature_set": "kis_sidecar_only",
            "model": "random_forest",
            "selection_rule": "top1",
            "metrics": {
                "n": 2,
                "active_days": 2,
                "active_runs": 2,
                "win_1d_pct": 100.0,
                "avg_1d_pct": 1.0,
                "min_1d_pct": 0.5,
                "max_1d_pct": 1.5,
                "win_3d_pct": 50.0,
                "avg_3d_pct": 2.0,
                "min_3d_pct": -1.0,
                "max_3d_pct": 5.0,
                "win_5d_pct": 50.0,
                "avg_5d_pct": 3.0,
                "min_5d_pct": -2.0,
                "max_5d_pct": 8.0,
                "avg_max_high_5d_pct": 6.0,
                "min_min_low_5d_pct": -4.0,
            },
        },
        "kis_feature_readiness": {
            "by_market": {
                market: {
                    "theme_news": {
                        "rows": 4,
                        "outcome_label_rows": 4,
                        "unique_runs": 2,
                        "unique_days": 2,
                        "mature_for_training": False,
                    }
                }
            },
            "feature_fill": {
                "theme_news_top_feature_fill_pct": {
                    "kis_theme_news_kis_backed": 50.0,
                    "kis_theme_news_news_checked": 25.0,
                    "kis_theme_news_evidence_score": 50.0,
                }
            },
        },
        "baselines_for_best_kis_holdout": [
            {
                "market": market,
                "baseline": "current_top5",
                "label": "pos_5d",
                "topn": 5,
                "metrics": {
                    "n": 3,
                    "active_days": 2,
                    "win_1d_pct": 66.6667,
                    "avg_1d_pct": 0.5,
                    "min_1d_pct": -1.0,
                    "max_1d_pct": 2.0,
                    "win_3d_pct": 33.3333,
                    "avg_3d_pct": -0.5,
                    "min_3d_pct": -3.0,
                    "max_3d_pct": 2.0,
                    "win_5d_pct": 33.3333,
                    "avg_5d_pct": -1.5,
                    "min_5d_pct": -5.0,
                    "max_5d_pct": 3.0,
                },
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_excludes_2d_and_keeps_market_sections(tmp_path):
    kospi = tmp_path / "kospi.json"
    kosdaq = tmp_path / "kosdaq.json"
    _source(kospi, "KOSPI")
    _source(kosdaq, "KOSDAQ")

    report = build_report({"KOSPI": kospi, "KOSDAQ": kosdaq})

    assert report["horizons"] == ["1d", "3d", "5d"]
    assert "2d" in report["metric_contract"]
    assert report["promotion_decision"]["status"] == "blocked"
    assert report["promotion_decision"]["all_required_markets_production_ready"] is False
    assert report["markets"]["KOSPI"]["current_kis_model"]["metrics"]["win_3d_pct"] == 50.0
    assert report["markets"]["KOSPI"]["current_kis_model"]["kis_model_gate"]["status"] == "blocked"
    assert "production_economics" in report["markets"]["KOSPI"]["current_kis_model"]["kis_model_gate"]
    assert report["markets"]["KOSDAQ"]["existing_production_baselines"][0]["name"] == "current_top5"
    comparison = report["markets"]["KOSPI"]["performance_comparison_vs_existing"][0]
    assert comparison["win_5d_delta_pct"] == 16.6667
    assert comparison["avg_5d_delta_pct"] == 4.5
    reflection = report["markets"]["KOSPI"]["operational_reflection"]
    assert reflection["action"] == "blocked_do_not_display_as_candidate"
    assert any("theme_news" in item for item in reflection["ui_recommendations"])
    assert report["markets"]["KOSPI"]["theme_news_readiness"]["news_checked_fill_pct"] == 25.0
