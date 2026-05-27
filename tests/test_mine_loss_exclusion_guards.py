from __future__ import annotations

import pandas as pd

from multi_agent.tools.mine_loss_exclusion_guards import _load_guard_dataset, build_report


def test_loss_exclusion_guard_reports_shadow_candidate():
    rows = []
    for idx in range(120):
        day = (idx % 24) + 1
        bad_signal = idx % 4 == 0
        holdout = day >= 17
        rows.append(
            {
                "market2": "KOSPI",
                "trade_date": f"2026-05-{day:02d}",
                "priority_rank": (idx % 5) + 1,
                "alpha_score": 88 if not bad_signal else 45,
                "tech_score": 84 if not bad_signal else 50,
                "whale_score": 78 if not bad_signal else 30,
                "prob_clean": 35 if not bad_signal else 65,
                "volume_ratio": 1.4 if not bad_signal else 0.7,
                "trend": "UP" if not bad_signal else "DOWN",
                "market_gate": "GREEN",
                "decision_bucket": "top5",
                "return_1d_pct": 1.0 if not bad_signal else -4.0,
                "return_3d_pct": 2.0 if not bad_signal else -5.0,
                "return_5d_pct": 5.0 if not bad_signal else (-7.0 if not holdout else -9.0),
                "min_return_observed_pct": -1.0 if not bad_signal else -7.0,
                "stop5_proxy": bool(bad_signal),
                "bad_path": bool(bad_signal),
                "exception_leader": False,
                "core_trend_flag_bool": not bad_signal,
                "explosive_leader_flag_bool": False,
            }
        )

    report = build_report(
        pd.DataFrame(rows),
        scan_mode="SWING",
        markets=["KOSPI"],
        scopes=["top5"],
        horizons=["5d"],
        train_ratio=0.7,
        min_train=20,
        min_test=8,
        min_days=4,
        min_excluded=6,
        min_retention=0.5,
        beam_width=8,
        max_terms=2,
        include_primary_theme=False,
        production_horizons=["3d", "5d"],
    )

    assert report["guard_count"] > 0
    assert report["shadow_candidate_count"] > 0
    top = report["top_guards"][0]
    assert top["shadow_candidate"] is True
    assert top["test_win_delta"] > 0
    assert top["test_bad_path_reduction"] > 0
    assert any("trend" in condition or "alpha_score" in condition for condition in top["exclude_conditions"])


def test_loss_exclusion_guard_keeps_empty_production_when_holdout_weak():
    rows = []
    for idx in range(80):
        day = (idx % 16) + 1
        rows.append(
            {
                "market2": "KOSDAQ",
                "trade_date": f"2026-05-{day:02d}",
                "priority_rank": (idx % 5) + 1,
                "alpha_score": 70 + (idx % 8),
                "tech_score": 70 + (idx % 10),
                "whale_score": 70 + (idx % 6),
                "prob_clean": 40 + (idx % 12),
                "volume_ratio": 1.1 + ((idx % 4) / 10),
                "trend": "UP" if idx % 2 else "DOWN",
                "market_gate": "GREEN",
                "decision_bucket": "top5",
                "return_1d_pct": 0.5 if idx % 2 else -0.5,
                "return_3d_pct": 0.5 if idx % 3 else -0.5,
                "return_5d_pct": 0.8 if idx % 2 else -0.8,
                "min_return_observed_pct": -1.0,
                "stop5_proxy": False,
                "bad_path": bool(idx % 2 == 0),
                "exception_leader": False,
                "core_trend_flag_bool": True,
                "explosive_leader_flag_bool": False,
            }
        )

    report = build_report(
        pd.DataFrame(rows),
        scan_mode="SWING",
        markets=["KOSDAQ"],
        scopes=["top5"],
        horizons=["5d"],
        train_ratio=0.7,
        min_train=12,
        min_test=6,
        min_days=3,
        min_excluded=5,
        min_retention=0.5,
        beam_width=6,
        max_terms=2,
        include_primary_theme=False,
        production_horizons=["3d", "5d"],
    )

    assert report["guard_count"] >= 0
    assert report["production_candidate_count"] == 0


def test_load_guard_dataset_can_load_intraday_archive(tmp_path):
    path = tmp_path / "archive.csv"
    pd.DataFrame(
        [
            {
                "ticker": "000001.KQ",
                "scan_mode": "INTRADAY",
                "recommended_at": "2026-05-27T09:40:00+09:00",
                "priority_rank": 1,
                "return_1d_pct": -4.0,
                "return_5d_pct": -1.0,
                "min_return_observed_pct": -6.0,
                "decision": "WATCHLIST",
            },
            {
                "ticker": "000002.KQ",
                "scan_mode": "SWING",
                "recommended_at": "2026-05-27T09:40:00+09:00",
                "priority_rank": 1,
                "return_1d_pct": 2.0,
            },
        ]
    ).to_csv(path, index=False)

    rows = _load_guard_dataset(path, "INTRADAY")

    assert rows["market2"].tolist() == ["KOSDAQ"]
    assert rows["trade_date"].tolist() == ["2026-05-27"]
    assert rows["bad_path"].tolist() == [True]
    assert rows["stop5_proxy"].tolist() == [True]
