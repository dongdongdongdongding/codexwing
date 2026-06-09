from __future__ import annotations

import pandas as pd

from multi_agent.tools.report_kr_promotion_challenger_gate import (
    CloseCandidateSpec,
    PROMOTION_GATE,
    _combo_effective_metrics,
    evaluate_close_candidates,
    evaluate_ordered_watch_candidates,
)


def _row(day: str, ticker: str, ret5: float, *, ret1: float = 0.5, ret3: float = 2.0, bad: bool = False) -> dict:
    return {
        "trade_date": day,
        "ticker": ticker,
        "market2": "KOSPI",
        "priority_rank": 1,
        "exception_leader": False,
        "ordered_path_exact": True,
        "return_1d_pct": ret1,
        "return_3d_pct": ret3,
        "return_5d_pct": ret5,
        "max_high_return_1d_pct": max(ret1, 0.5),
        "max_high_return_3d_pct": max(ret3, 8.0),
        "max_high_return_5d_pct": max(ret5, 8.0),
        "min_return_observed_pct": -1.0 if not bad else -6.0,
        "stop5_proxy": bad,
        "bad_path": bad or ret1 < -3.0 or ret5 < 0,
        "alpha_score": 60,
        "ml_prob": 20,
        "decision_score": 70,
    }


def test_close_candidate_can_pass_73_gate_with_clean_path(monkeypatch):
    rows = [_row(f"2026-05-{idx:02d}", f"000{idx:03d}.KS", 8.0, ret3=4.0) for idx in range(1, 13)]
    df = pd.DataFrame(rows)
    spec = CloseCandidateSpec(
        "all_clean",
        "KOSPI",
        "test",
        "unit",
        "clean unit candidate",
        lambda frame: pd.Series(True, index=frame.index),
    )
    monkeypatch.setitem(PROMOTION_GATE, "min_train_n", 3)
    monkeypatch.setitem(PROMOTION_GATE, "min_train_days", 3)
    monkeypatch.setitem(PROMOTION_GATE, "min_test_n", 3)
    monkeypatch.setitem(PROMOTION_GATE, "min_test_days", 3)

    result = evaluate_close_candidates(df, specs=[spec])[0]

    assert result["status"] == "promotion_review_candidate"
    assert result["test"]["buy_premium_pct"] == 2.0
    assert result["test"]["scan_reference_avg_5d_pct"] == 8.0
    assert result["test"]["avg_5d_pct"] < result["test"]["scan_reference_avg_5d_pct"]
    assert result["test"]["effective_win_5d_pct"] == 100.0
    assert result["test"]["bad_path_pct"] == 0.0


def test_close_candidate_fails_when_win_is_high_but_early_drop_is_bad(monkeypatch):
    rows = [
        _row(f"2026-05-{idx:02d}", f"000{idx:03d}.KS", 8.0, ret1=-4.0, ret3=1.0, bad=False)
        for idx in range(1, 13)
    ]
    df = pd.DataFrame(rows)
    spec = CloseCandidateSpec(
        "high_return_bad_path",
        "KOSPI",
        "test",
        "unit",
        "high close return but poor path",
        lambda frame: pd.Series(True, index=frame.index),
    )
    monkeypatch.setitem(PROMOTION_GATE, "min_train_n", 3)
    monkeypatch.setitem(PROMOTION_GATE, "min_train_days", 3)
    monkeypatch.setitem(PROMOTION_GATE, "min_test_n", 3)
    monkeypatch.setitem(PROMOTION_GATE, "min_test_days", 3)

    result = evaluate_close_candidates(df, specs=[spec])[0]

    assert result["status"] != "promotion_review_candidate"
    failed = {item["name"] for item in result["gate_checks"] if not item["passed"]}
    assert "test_effective_win_5d" in failed
    assert "test_early_drop_1d" in failed


def test_ordered_watch_candidate_uses_ordered_win_as_effective_5d(tmp_path, monkeypatch):
    cache = tmp_path / "kosdaq_ordered.csv"
    rows = []
    for idx in range(1, 13):
        rows.append(
            {
                "candidate_id": "5D_ordered_5v5",
                "ticker": f"000{idx:03d}.KQ",
                "trade_date": f"2026-05-{idx:02d}",
                "priority_rank": 1,
                "decision": "WATCHLIST",
                "decision_bucket": "watchlist",
                "ordered_label_ready": True,
                "ordered_win": True,
                "ordered_stop": False,
                "ordered_target_before_stop": True,
                "ordered_stop_before_target": False,
                "ordered_terminal_status": "target_before_stop",
                "ordered_mfe_pct": 8.5,
                "ordered_mae_pct": -1.0,
                "return_1d_pct": 0.5,
                "return_3d_pct": 4.0,
                "return_5d_pct": 8.0,
                "theme_day_avg_volume_ratio": 1.0,
                "theme_day_avg_expected_return_1d_pct": 0.2,
                "tech_score": 60,
                "theme_day_avg_alpha_score": 60,
                "primary_theme": "unit_theme",
                "alpha_score": 60,
                "expected_return_1d_pct": 0.2,
                "volume_ratio": 1.0,
            }
        )
    pd.DataFrame(rows).to_csv(cache, index=False)

    monkeypatch.setitem(PROMOTION_GATE, "min_train_n", 3)
    monkeypatch.setitem(PROMOTION_GATE, "min_train_days", 3)
    monkeypatch.setitem(PROMOTION_GATE, "min_test_n", 3)
    monkeypatch.setitem(PROMOTION_GATE, "min_test_days", 3)
    monkeypatch.setattr(
        "multi_agent.tools.report_kr_promotion_challenger_gate._ordered_cache_path",
        lambda market: cache,
    )

    result = evaluate_ordered_watch_candidates(
        markets=("KOSDAQ",),
        rule_ids=("kosdaq_dynamic_theme_tech_watch_5v5",),
    )[0]

    assert result["candidate_id"] == "kosdaq_dynamic_theme_tech_watch_5v5"
    assert result["status"] == "promotion_review_candidate"
    assert result["test"]["buy_premium_pct"] == 2.0
    assert result["test"]["scan_reference_avg_5d_pct"] == 8.0
    assert result["test"]["avg_5d_pct"] < result["test"]["scan_reference_avg_5d_pct"]
    assert result["test"]["effective_win_5d_pct"] == 100.0


def test_combo_candidate_effective_win_uses_5d_not_selected_3d_horizon():
    metrics = _combo_effective_metrics(
        {
            "n_3d": 10,
            "active_days_3d": 5,
            "win_3d_pct": 90.0,
            "n_5d": 8,
            "active_days_5d": 5,
            "win_5d_pct": 50.0,
            "hit5_5d_pct": 50.0,
            "bad_path_5d_pct": 25.0,
            "stop5_5d_pct": 0.0,
        },
        "3d",
    )

    assert metrics["selected_horizon_win_pct"] == 90.0
    assert metrics["effective_win_5d_pct"] == 50.0
    assert metrics["target_touch_metric_source"] == "hit5_5d_pct"
    assert metrics["n"] == 8
