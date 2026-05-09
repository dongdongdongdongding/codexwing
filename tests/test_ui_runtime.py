import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from modules.quant_analysis import QuantStrategy
from modules.scanner_runtime import run_parallel_scan
from modules.ui_helpers import (
    build_signal_display_rows,
    build_top_candidate_rows,
    build_watchlist_display_rows,
    compute_progress_fraction,
    format_volume_display,
    resolve_display_price,
    should_auto_refresh_scan_panel,
)


class UIHelperTests(unittest.TestCase):
    def test_compute_progress_fraction_clamps_bounds(self):
        self.assertEqual(compute_progress_fraction(0, 10), 0.0)
        self.assertEqual(compute_progress_fraction(3, 10), 0.3)
        self.assertEqual(compute_progress_fraction(12, 10), 1.0)
        self.assertEqual(compute_progress_fraction(1, 0), 0.0)

    def test_display_helpers_use_safe_fallbacks(self):
        self.assertEqual(resolve_display_price(101.25, 99.0), 101.25)
        self.assertEqual(resolve_display_price(0, 99.0), 99.0)
        self.assertEqual(resolve_display_price(None, 88.5), 88.5)
        self.assertEqual(format_volume_display(15320.2), "15,320")
        self.assertEqual(format_volume_display(None), "0")

    def test_build_top_candidate_rows_sorts_by_priority_then_score(self):
        rows = build_top_candidate_rows(
            {
                "decisions": [
                    {"ticker": "BBB", "stock_name": "Beta", "priority_rank": 2, "decision_score": 91, "expected_return_1d_pct": 1.2},
                    {"ticker": "AAA", "stock_name": "Alpha", "priority_rank": 1, "decision_score": 88, "expected_return_1d_pct": 0.8},
                    {"ticker": "CCC", "stock_name": "Gamma", "priority_rank": 1, "decision_score": 95, "expected_return_1d_pct": 1.5},
                ]
            },
            limit=2,
        )
        self.assertEqual([row["Ticker"] for row in rows], ["CCC", "AAA"])

    def test_should_auto_refresh_scan_panel_only_for_live_states(self):
        self.assertTrue(should_auto_refresh_scan_panel("queued"))
        self.assertTrue(should_auto_refresh_scan_panel("running"))
        self.assertFalse(should_auto_refresh_scan_panel("completed"))
        self.assertFalse(should_auto_refresh_scan_panel("failed"))

    def test_build_watchlist_display_rows_uses_only_exact_source_fields(self):
        rows, visible = build_watchlist_display_rows(
            watchlist=["005930.KS"],
            watchlist_meta=[{"ticker": "005930.KS", "stock_name": "삼성전자", "reason": "planner_lane_watchlist"}],
            decisions=[{"ticker": "005930.KS", "prob_5": 50.0, "prob_clean": 50.0, "decision_score": 88.0, "alpha_score": 81.0, "conviction_score": 64.0}],
            scanner_payload={"candidates": [{"ticker": "005930.KS", "feature_snapshot": {"alpha_score": 79.0, "conviction_score": 63.0, "decision_score": 77.0}}]},
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Alpha"], 81.0)
        self.assertEqual(rows[0]["Conviction"], 64.0)
        self.assertEqual(rows[0]["Decision Score"], 88.0)
        self.assertEqual(rows[0]["Prob5"], 50.0)
        self.assertEqual(rows[0]["Clean"], 50.0)
        self.assertEqual(visible, ["Alpha", "Conviction", "Decision Score", "Prob5", "Clean"])

    def test_build_signal_display_rows_keeps_core_scan_fields(self):
        rows = build_signal_display_rows(
            [
                {
                    "티커": "322310.KQ",
                    "종목명": "오성첨단소재",
                    "Tier": "T1",
                    "전략": "Momentum",
                    "정밀확률": "31.1%",
                    "전일비": "-10.25%",
                    "Decision Score": 99.1,
                    "테마": "반도체",
                    "추세": "UP",
                }
            ]
        )

        self.assertEqual(rows[0]["ticker"], "322310.KQ")
        self.assertEqual(rows[0]["buy_signal"], "T1 · Momentum")
        self.assertEqual(rows[0]["accuracy"], "31.1%")
        self.assertEqual(rows[0]["day_change"], "-10.25%")
        self.assertEqual(rows[0]["day_change_value"], -10.25)
        self.assertEqual(rows[0]["score"], "99.1")

    def test_build_signal_display_rows_does_not_fabricate_day_change(self):
        # 2026-05-09: phase25_prob은 raw score(0-100)로 calibrated probability가
        # 아니다. 카드 '정확성' coalesce에서 제외함 — 사용자에게 모델 raw score를
        # '정확도'로 보여주면 KOSPI SWING 35% / KOSDAQ SWING 12%처럼 오해 발생.
        # 진짜 정확성 source: phase25_oos_win_rate_pct, prob_clean, ml_prob.
        rows = build_signal_display_rows([{
            "ticker": "005930.KS",
            "phase25_prob": 61.2,             # raw score (사용 안 함)
            "phase25_oos_win_rate_pct": 75.4,  # OOS holdout win rate
            "return_1d_pct": 3.4,
        }])
        self.assertEqual(rows[0]["accuracy"], "75.4%")
        self.assertEqual(rows[0]["day_change"], "-")
        self.assertEqual(rows[0]["day_change_value"], None)

    def test_build_signal_display_rows_ignores_raw_phase25_prob(self):
        # phase25_prob 단독이면 accuracy는 None. raw score를 정확도로 표시 금지.
        rows = build_signal_display_rows([{
            "ticker": "005930.KS",
            "phase25_prob": 35.7,             # KOSPI SWING 평균 raw score
        }])
        self.assertEqual(rows[0]["accuracy"], "-")


class ScannerRuntimeTests(unittest.TestCase):
    def test_run_parallel_scan_emits_callback_for_each_symbol(self):
        progress_updates = []

        def worker(sym):
            return {"ticker": sym}

        def on_item(i, total_scans, sym, data, exc):
            progress_updates.append((sym, compute_progress_fraction(i + 1, total_scans), exc, data))

        result = run_parallel_scan(
            ticker_list=["A", "B", "C"],
            max_scan=0,
            worker_fn=worker,
            max_workers=2,
            on_item=on_item,
        )

        self.assertEqual(result["total_scans"], 3)
        self.assertEqual(len(progress_updates), 3)
        self.assertEqual([round(item[1], 4) for item in progress_updates], [0.3333, 0.6667, 1.0])
        self.assertTrue(all(item[2] is None for item in progress_updates))


class QuantStrategyRealtimePriceTests(unittest.TestCase):
    @patch("modules.quant_analysis.yf.Ticker")
    def test_get_realtime_price_prefers_fast_info(self, ticker_cls):
        ticker_mock = MagicMock()
        ticker_mock.fast_info = {"last_price": 123.45}
        ticker_mock.info = {"currentPrice": 120.0}
        ticker_cls.return_value = ticker_mock

        qs = QuantStrategy("AAPL")
        qs.df = pd.DataFrame({"Close": [111.0]})

        self.assertEqual(qs.get_realtime_price(), 123.45)

    @patch("modules.quant_analysis.yf.Ticker")
    def test_get_realtime_price_falls_back_to_info_then_dataframe(self, ticker_cls):
        ticker_mock = MagicMock()
        ticker_mock.fast_info = {"last_price": None}
        ticker_mock.info = {"regularMarketPrice": 77.7}
        ticker_cls.return_value = ticker_mock

        qs = QuantStrategy("AAPL")
        qs.df = pd.DataFrame({"Close": [55.0]})
        self.assertEqual(qs.get_realtime_price(), 77.7)

        ticker_mock.info = {}
        self.assertEqual(qs.get_realtime_price(), 55.0)


class QuantStrategyFetchDataVolumeTests(unittest.TestCase):
    @patch.object(QuantStrategy, "get_intraday_volume_multiplier", return_value=1.0)
    @patch("modules.quant_analysis.live_mode_enabled", return_value=True)
    @patch("modules.quant_analysis.get_history")
    def test_fetch_data_refreshes_last_daily_bar_from_intraday_tape(self, get_history_mock, _live_mode_mock, _multiplier_mock):
        daily_index = pd.date_range("2026-02-19", periods=60, freq="D")
        daily_df = pd.DataFrame(
            {
                "Open": [100.0 + i for i in range(60)],
                "High": [110.0 + i for i in range(60)],
                "Low": [99.0 + i for i in range(60)],
                "Close": [108.0 + i for i in range(60)],
                "Volume": [1000.0 + i for i in range(60)],
            },
            index=daily_index,
        )
        daily_df.iloc[-1] = [101.0, 111.0, 100.0, 109.0, 1200.0]
        intraday_index = pd.to_datetime(["2026-04-19 10:00", "2026-04-19 11:00"])
        intraday_df = pd.DataFrame(
            {
                "Open": [103.0, 106.0],
                "High": [115.0, 118.0],
                "Low": [102.0, 105.0],
                "Close": [107.0, 117.0],
                "Volume": [900.0, 800.0],
            },
            index=intraday_index,
        )
        get_history_mock.side_effect = [daily_df, intraday_df]

        qs = QuantStrategy("005930.KS")

        self.assertTrue(qs.fetch_data(period="5y"))
        self.assertEqual(float(qs.df.iloc[-1]["Open"]), 103.0)
        self.assertEqual(float(qs.df.iloc[-1]["High"]), 118.0)
        self.assertEqual(float(qs.df.iloc[-1]["Low"]), 100.0)
        self.assertEqual(float(qs.df.iloc[-1]["Close"]), 117.0)
        self.assertEqual(float(qs.df.iloc[-1]["Volume"]), 1700.0)


if __name__ == "__main__":
    unittest.main()
