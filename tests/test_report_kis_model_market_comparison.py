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
    assert report["markets"]["KOSPI"]["current_kis_model"]["metrics"]["win_3d_pct"] == 50.0
    assert report["markets"]["KOSDAQ"]["existing_production_baselines"][0]["name"] == "current_top5"
