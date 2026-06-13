import json

import pandas as pd

from multi_agent.tools.report_kis_touch5_slice_ablation import build_report, parse_args, render_markdown


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _sample_rows():
    rows = []
    for market in ("KOSPI", "KOSDAQ"):
        for day in range(1, 6):
            for slot in range(4):
                good = slot % 2 == 0
                rows.append(
                    {
                        "trade_date": f"2026-05-{day:02d}",
                        "run_id": f"{market}-RUN-{day:02d}",
                        "market": market,
                        "ticker": f"{market}-{day:02d}-{slot}",
                        "alpha_score": 70.0 + slot,
                        "tech_score": 65.0 + day,
                        "volume_ratio": 1.5 + slot,
                        "turnover": 100000000 + (day * 1000) + slot,
                        "kis_sidecar_present": 1,
                        "kis_current_price": 10000 + day + slot,
                        "kis_day_change_pct": 2.0 if good else -1.0,
                        "kis_foreigner_1d": 3.0 if good else -4.0,
                        "kis_stock_listed_shares": 1000000,
                        "kis_financial_roe": 8.5,
                        "kis_news_title_count": 2 if good else 0,
                        "close_failure_prior_kis_sector_failure_rate_pct": 30.0 if good else 65.0,
                        "return_1d_pct": 2.0 if good else -2.0,
                        "return_3d_pct": 4.0 if good else -4.0,
                        "return_5d_pct": 7.0 if good else -6.0,
                        "max_high_return_1d_pct": 4.0 if good else 1.0,
                        "max_high_return_3d_pct": 6.0 if good else 2.0,
                        "max_high_return_5d_pct": 9.0 if good else 2.5,
                        "min_low_return_1d_pct": -1.0 if good else -4.0,
                        "min_low_return_3d_pct": -2.0 if good else -8.0,
                        "min_low_return_5d_pct": -4.0 if good else -12.0,
                    }
                )
    return rows


def _leaderboard(path):
    payload = {"markets": {}}
    for market in ("KOSPI", "KOSDAQ"):
        payload["markets"][market] = {
            "best_candidate": {
                "identity": {
                    "market": market,
                    "model": "logistic",
                    "topn": 1,
                    "prob_threshold": None,
                    "tail_risk_prob_threshold": None,
                    "score_mode": "prob",
                    "selection_rule": "top1",
                }
            }
        }
    _write_json(path, payload)


def test_slice_ablation_builds_period_and_feature_report(tmp_path):
    cache = tmp_path / "prepared.pkl"
    pd.DataFrame(_sample_rows()).to_pickle(cache)
    leaderboard = tmp_path / "leaderboard.json"
    _leaderboard(leaderboard)

    args = parse_args(
        [
            "--prepared-cache",
            str(cache),
            "--candidate-leaderboard",
            str(leaderboard),
            "--months",
            "2026-05",
            "--feature-configs",
            "all_features,all_minus_close_failure_prior,close_failure_prior_only",
            "--min-train-rows",
            "8",
            "--min-test-rows",
            "1",
            "--min-train-days",
            "2",
            "--test-days",
            "1",
            "--max-folds",
            "2",
            "--min-slice-rows",
            "8",
            "--min-slice-days",
            "3",
        ]
    )
    report = build_report(args)

    assert report["dummy_data_used"] is False
    assert report["data_profile"]["missing_actual_months"] == []
    for market in ("KOSPI", "KOSDAQ"):
        summary = report["markets"][market]
        assert summary["ok_results"] >= 1
        assert summary["all_feature_period_result_count"] >= 1
        assert summary["available_full_ablation_result_count"] >= 1
    markdown = render_markdown(report)
    assert "KIS Touch5 Slice Ablation" in markdown
    assert "Market Summary" in markdown


def test_slice_ablation_surfaces_missing_actual_months(tmp_path):
    cache = tmp_path / "prepared.pkl"
    pd.DataFrame(_sample_rows()).to_pickle(cache)
    leaderboard = tmp_path / "leaderboard.json"
    _leaderboard(leaderboard)

    args = parse_args(
        [
            "--prepared-cache",
            str(cache),
            "--candidate-leaderboard",
            str(leaderboard),
            "--months",
            "2026-01,2026-05",
            "--feature-configs",
            "all_features",
            "--min-train-rows",
            "8",
            "--min-test-rows",
            "1",
            "--min-train-days",
            "2",
            "--test-days",
            "1",
            "--max-folds",
            "1",
            "--min-slice-rows",
            "8",
            "--min-slice-days",
            "3",
        ]
    )
    report = build_report(args)

    assert "2026-01" in report["data_profile"]["missing_actual_months"]
    assert report["decision"]["production_replacement_ready"] is False
