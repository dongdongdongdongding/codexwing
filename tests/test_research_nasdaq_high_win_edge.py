from __future__ import annotations

from pathlib import Path

import pandas as pd

from multi_agent.tools.research_nasdaq_high_win_edge import (
    data_availability,
    frontier_sections,
    metric_block,
)


def test_metric_block_preserves_win_return_touch_and_year_stability():
    frame = pd.DataFrame(
        [
            {
                "date": "2024-01-02",
                "symbol": "AAA",
                "liq20": 100_000_000,
                "fwd_close_ret_3d": 1.0,
                "fwd_close_ret_5d": 2.0,
                "alpha3_liq": 0.8,
                "alpha5_liq": 1.5,
                "alpha5_net": 1.3,
                "touch5_3d": 1.0,
                "ft_5_5": 1.0,
                "dd5_3d": 0.0,
                "year": 2024,
            },
            {
                "date": "2025-01-02",
                "symbol": "BBB",
                "liq20": 200_000_000,
                "fwd_close_ret_3d": -1.0,
                "fwd_close_ret_5d": -2.0,
                "alpha3_liq": -0.5,
                "alpha5_liq": -1.0,
                "alpha5_net": -1.2,
                "touch5_3d": 0.0,
                "ft_5_5": 0.0,
                "dd5_3d": 1.0,
                "year": 2025,
            },
        ]
    )
    frame["date"] = pd.to_datetime(frame["date"])

    metrics = metric_block(frame)

    assert metrics["n"] == 2
    assert metrics["days"] == 2
    assert metrics["ret5"] == 0.0
    assert metrics["ret5_pos_rate"] == 0.5
    assert metrics["touch3"] == 0.5
    assert metrics["ft55"] == 0.5
    assert metrics["dd3"] == 0.5
    assert metrics["years_alpha5_net_0_2_pos"] == 1


def test_frontier_sections_keep_drawdown_safe_and_touch_frontiers_separate():
    dd_safe = {
        "condition": "pullback_not_broken",
        "score": "score_first_touch_trend",
        "liq20_floor": 30_000_000.0,
        "topn": 1,
        "selection_key": 1.0,
        "holdout": {
            "ret5": 1.2,
            "alpha5_net_cost_0_2": 0.8,
            "ret5_pos_rate": 0.54,
            "touch3": 0.34,
            "ft55": 0.40,
            "dd3": 0.28,
        },
        "full_oos": {
            "ret5": 0.9,
            "alpha5_net_cost_0_2": 0.6,
            "ret5_pos_rate": 0.54,
            "touch3": 0.33,
            "ft55": 0.39,
            "dd3": 0.27,
        },
    }
    high_touch = {
        "condition": "first_touch_cmf",
        "score": "score_pullback_quality",
        "liq20_floor": 100_000_000.0,
        "topn": 3,
        "selection_key": 2.0,
        "holdout": {
            "ret5": 1.6,
            "alpha5_net_cost_0_2": 1.0,
            "ret5_pos_rate": 0.55,
            "touch3": 0.56,
            "ft55": 0.54,
            "dd3": 0.48,
        },
        "full_oos": {
            "ret5": 1.2,
            "alpha5_net_cost_0_2": 0.7,
            "ret5_pos_rate": 0.52,
            "touch3": 0.52,
            "ft55": 0.51,
            "dd3": 0.49,
        },
    }

    sections = frontier_sections([high_touch, dd_safe], limit=5)

    assert sections["holdout_best_overall"][0]["condition"] == "first_touch_cmf"
    assert sections["holdout_dd_safe"][0]["condition"] == "pullback_not_broken"
    assert sections["full_oos_dd_safe"][0]["condition"] == "pullback_not_broken"
    assert sections["holdout_touch_win"][0]["condition"] == "first_touch_cmf"


def test_data_availability_marks_missing_nasdaq_session_panel(tmp_path):
    cache = tmp_path / "research_cache"
    panel = cache / "us_daily" / "NASDAQ" / "daily_features.parquet"
    raw = panel.parent / "raw_ohlcv"
    intraday = cache / "intraday"
    intraday_ext = cache / "intraday_ext"
    raw.mkdir(parents=True)
    intraday.mkdir(parents=True)
    intraday_ext.mkdir(parents=True)
    panel.write_text("stub", encoding="utf-8")
    (raw / "NVDA.parquet").write_text("stub", encoding="utf-8")
    (intraday / "005930.parquet").write_text("stub", encoding="utf-8")
    (intraday_ext / "000660.parquet").write_text("stub", encoding="utf-8")

    availability = data_availability(Path(panel))

    assert availability["us_daily_panel_found"] is True
    assert availability["us_daily_raw_ohlcv_found"] is True
    assert availability["nasdaq_session_panel_found"] is False
    assert availability["local_intraday_looks_kr_numeric"] is True
    assert availability["local_intraday_ext_looks_kr_numeric"] is True
    assert availability["session_data_status"] == "missing_nasdaq_premarket_regular_afterhours_panel"
