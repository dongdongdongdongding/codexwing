import json

from modules import operational_admission_monitor as monitor


def _report(market: str, score: float):
    return {
        "generated_at": "2026-05-27T00:00:00Z",
        "evaluated_policies": 1,
        "promotable_count": 0,
        "top_policies": [
            {
                "market": market,
                "cohort": "ranked_top20",
                "policy_type": "score_baseline",
                "model": "prob_clean",
                "feature_set": "score_column",
                "topn": 3,
                "quality_score": score,
                "label_profile": {"name": "ordered_5d_5v3_lowmae"},
                "metrics": {
                    "n": 41,
                    "active_days": 14,
                    "label_win_pct": 73.171,
                    "avg_5d_pct": 0.1308,
                    "min_5d_pct": -33.2955,
                    "stop_before_target_5d_pct": 4.878,
                    "target_before_stop_5d_pct": 95.122,
                },
                "promotion": {"promotable": False, "folds": 3, "min_fold_label_win_pct": 46.667},
            }
        ],
    }


def test_kosdaq_optimizer_monitor_prefers_theme_report(tmp_path, monkeypatch):
    default_path = tmp_path / "operational_admission_optimizer_latest.json"
    kosdaq_path = tmp_path / "operational_admission_optimizer_kosdaq_theme_latest.json"
    default_path.write_text(json.dumps(_report("KOSPI", 10.0)), encoding="utf-8")
    kosdaq_path.write_text(json.dumps(_report("KOSDAQ", 86.3)), encoding="utf-8")
    monkeypatch.setattr(monitor, "DEFAULT_REPORT_PATH", default_path)
    monkeypatch.setattr(monitor, "KOSDAQ_THEME_REPORT_PATH", kosdaq_path)
    monkeypatch.setattr(monitor, "FALLBACK_REPORT_PATH", tmp_path / "missing.json")

    kosdaq_report = monitor.load_admission_optimizer_report(market="KOSDAQ")
    kospi_report = monitor.load_admission_optimizer_report(market="KOSPI")
    summary = monitor.admission_optimizer_discord_summary("KOSDAQ")

    assert kosdaq_report["top_policies"][0]["market"] == "KOSDAQ"
    assert kospi_report["top_policies"][0]["market"] == "KOSPI"
    assert "KOSDAQ/ranked_top20" in summary
    assert "win +73.17%" in summary
