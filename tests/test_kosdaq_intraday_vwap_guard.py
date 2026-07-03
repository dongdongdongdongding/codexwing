import numpy as np
import pandas as pd

from modules.kosdaq_intraday_vwap_guard import (
    compute_daily_prev_context,
    compute_pre_entry_features,
    live_pick_payload,
    select_vwap_guard_candidates,
)


def _daily_frame(days=90):
    idx = pd.bdate_range("2026-01-01", periods=days)
    close = pd.Series(np.linspace(1000, 1400, len(idx)), index=idx)
    return pd.DataFrame(
        {
            "Open": close * 0.99,
            "High": close * 1.03,
            "Low": close * 0.97,
            "Close": close,
            "Volume": np.linspace(500_000, 700_000, len(idx)),
        },
        index=idx,
    )


def test_daily_prev_context_uses_completed_day_before_trade_date():
    daily = _daily_frame()
    trade_date = daily.index[-1].strftime("%Y%m%d")

    context = compute_daily_prev_context(
        daily,
        trade_date=trade_date,
        index_context={"idx_mom20_prev": 3.2, "idx_vol20_prev": 7.1},
    )

    assert context["prev_date"] == daily.index[-2].strftime("%Y-%m-%d")
    assert context["prev_close"] == daily["Close"].iloc[-2]
    assert context["liq_prev_eok"] > 0
    assert context["ret_1d_prev"] is not None
    assert context["idx_mom20_prev"] == 3.2
    assert context["idx_vol20_prev"] == 7.1


def test_pre_entry_features_stop_at_1500_and_apply_vwap_guard_inputs():
    idx = pd.date_range("2026-06-24 09:00", "2026-06-24 15:20", freq="10min")
    close = pd.Series(np.linspace(1000, 1100, len(idx)), index=idx)
    minute = pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": 10_000,
        },
        index=idx,
    )

    features = compute_pre_entry_features(
        minute,
        prev_close=990,
        liq_prev_eok=50,
        trade_date="20260624",
    )

    assert features["entry_bar_at"].startswith("2026-06-24T15:00:00")
    assert features["pre_bar_count"] == len(minute[minute.index.time <= pd.Timestamp("15:00").time()])
    assert features["gap_open_pct"] > 0
    assert features["pre_ret_pct"] > 0
    assert features["pre_vwap_dist_pct"] > 0
    assert features["pre_value_vs_liq_prev_pct"] > 0


def test_selection_and_live_pick_keep_intraday_liquidity_lanes():
    rows = [
        {"code": "111111", "p_cal": 0.91, "p_raw": 0.7, "pre_vwap_dist_pct": 1.2, "liq_prev_eok": 80, "entry_reference_price": 1000},
        {"code": "222222", "p_cal": 0.89, "p_raw": 0.65, "pre_vwap_dist_pct": 0.5, "liq_prev_eok": 150, "entry_reference_price": 2000},
        {"code": "333333", "p_cal": 0.95, "p_raw": 0.8, "pre_vwap_dist_pct": -0.1, "liq_prev_eok": 200, "entry_reference_price": 3000},
    ]

    selected = select_vwap_guard_candidates(rows, top_n=2)
    picks = [live_pick_payload(row, rank=i, trade_date="20260624", run_id="RUN") for i, row in enumerate(selected, 1)]

    assert [pick["ticker"] for pick in picks] == ["111111.KQ", "222222.KQ"]
    assert picks[0]["scan_mode"] == "INTRADAY"
    assert picks[0]["strategy_family"] == "KR_INTRADAY_3D_T5"
    assert picks[0]["liquidity_lane"] == "gte30eok"
    assert picks[1]["liquidity_lane"] == "gte100eok"
    assert picks[1]["tradeability_floor_pass"] is True
    # promoted contract (2026-07-03, RESEARCH_LOG §7-E): +10% touch-exit within 5 sessions
    assert picks[0]["target_tp_pct"] == 10.0
    assert picks[0]["hold_days"] == 5

