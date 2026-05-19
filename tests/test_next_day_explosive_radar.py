import json

from modules.next_day_explosive_radar import (
    backtest_next_day_radar,
    build_next_day_radar_candidate,
    build_next_day_radar_records,
)
from modules.discord_integration import renderers
from modules.discord_integration.renderers import build_next_day_radar_embed
from modules.ui_helpers import build_signal_display_rows


def test_next_day_radar_scores_reasons_and_missing_features():
    radar = build_next_day_radar_candidate(
        {
            "ticker": "000001.KS",
            "volume_ratio": 3.1,
            "day_change_pct": 4.2,
            "expected_return_1d_pct": 3.5,
            "prob_clean": 52,
            "theme_day_avg_decision_score": 74,
            "market_gate": "GREEN",
        }
    )

    assert radar["market"] == "KOSPI"
    assert radar["production_enabled"] is False
    assert radar["radar_score"] > 80
    assert "volume_acceleration" in radar["feature_reasons"]
    assert "positive_1d_model_edge" in radar["feature_reasons"]
    assert radar["unavailable_features"] == []

    sparse = build_next_day_radar_candidate({"ticker": "000002.KQ"})
    assert sparse["market"] == "KOSDAQ"
    assert "volume_ratio" in sparse["unavailable_features"]
    assert "market_gate" in sparse["unavailable_features"]


def test_next_day_radar_backtest_compares_against_priority_baseline():
    rows = [
        {
            "run_id": "RUN-1",
            "market": "KOSPI",
            "ticker": "A.KS",
            "priority_rank": 1,
            "return_1d_pct": -3,
            "volume_ratio": 0.8,
            "day_change_pct": 13,
        },
        {
            "run_id": "RUN-1",
            "market": "KOSPI",
            "ticker": "B.KS",
            "priority_rank": 2,
            "return_1d_pct": 7,
            "volume_ratio": 3.0,
            "day_change_pct": 3,
            "expected_return_1d_pct": 4,
            "prob_clean": 60,
            "theme_day_avg_decision_score": 80,
            "market_gate": "GREEN",
        },
        {
            "run_id": "RUN-1",
            "market": "KOSPI",
            "ticker": "C.KS",
            "priority_rank": 3,
            "return_1d_pct": 1,
            "volume_ratio": 1.0,
            "day_change_pct": 0.5,
        },
    ]

    report = backtest_next_day_radar(rows, top_n=1)

    assert report["promotion_status"] == "shadow_only"
    assert report["radar"]["plus5_precision_pct"] == 100.0
    assert report["radar"]["avg_return_1d_pct"] == 7.0
    assert report["baseline_priority"]["plus5_precision_pct"] == 0.0
    assert report["baseline_priority"]["avg_return_1d_pct"] == -3.0


def test_radar_records_feed_existing_signal_card_contract():
    rows = build_next_day_radar_records(
        [
            {
                "ticker": "000001.KS",
                "stock_name": "테스트",
                "volume_ratio": 3.1,
                "day_change_pct": 4.2,
                "expected_return_1d_pct": 3.5,
                "prob_clean": 52,
                "theme_day_avg_decision_score": 74,
                "market_gate": "GREEN",
            }
        ]
    )

    display = build_signal_display_rows(rows)

    assert display[0]["analysis_section"] == "별도 급등 레이더"
    assert display[0]["buy_signal"].startswith("NEXT_DAY_RADAR")
    assert display[0]["next_day_radar_score"] > 80
    assert "volume_acceleration" in display[0]["next_day_radar_reasons"]


def test_discord_radar_embed_reads_run_artifact(tmp_path, monkeypatch):
    artifact_dir = tmp_path / "artifacts"
    run_dir = artifact_dir / "RUN-RADAR"
    run_dir.mkdir(parents=True)
    (run_dir / "raw_scan_results.json").write_text(
        json.dumps(
            {
                "results_sorted": [
                    {
                        "ticker": "000001.KS",
                        "stock_name": "테스트",
                        "volume_ratio": 3.1,
                        "day_change_pct": 4.2,
                        "expected_return_1d_pct": 3.5,
                        "prob_clean": 52,
                        "theme_day_avg_decision_score": 74,
                        "market_gate": "GREEN",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(renderers, "ARTIFACT_DIR", artifact_dir)

    embed = build_next_day_radar_embed("RUN-RADAR", limit=5)

    assert embed["title"] == "별도 급등 레이더"
    assert "테스트" in embed["fields"][0]["name"]
    assert "volume_acceleration" in embed["fields"][0]["value"]
