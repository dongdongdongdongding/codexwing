import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from modules.scanner_runtime import SharedBackoffState, scan_symbol_with_retry


class ScannerRuntimeRunIdTests(unittest.TestCase):
    @patch("modules.scanner_runtime._get_db_manager")
    @patch("modules.scanner_runtime.evaluate_app_kr_candidate")
    @patch("modules.scanner_runtime.passes_liquidity_filter", return_value=True)
    @patch("modules.scanner_runtime.compute_exhaustion_context")
    @patch("modules.scanner_runtime.quant_analysis.QuantStrategy")
    def test_scan_symbol_threads_run_id_into_db_payload(
        self,
        strategy_cls,
        exhaustion_context_mock,
        _liquidity_mock,
        evaluate_mock,
        db_manager_mock,
    ):
        qs = MagicMock()
        qs.fetch_data.return_value = True
        qs.df = pd.DataFrame({"Antigrav_Score": [80.0]})
        strategy_cls.return_value = qs
        exhaustion_context_mock.return_value = {
            "curr_price": 100.0,
            "turnover": 1_000_000.0,
            "prev_pct_change": 1.2,
            "consec_days": 1,
            "is_exhausted": False,
            "exhaustion_tag": "OK",
        }
        evaluate_mock.return_value = {
            "db_payload": {"ticker": "005930.KS", "scan_mode": "SWING"},
            "res_data": {"ticker": "005930.KS"},
        }
        db = MagicMock()
        db_manager_mock.return_value = db

        row = scan_symbol_with_retry(
            "005930.KS",
            tickers_dict={"005930.KS": "Samsung Electronics"},
            is_us=False,
            is_amex=False,
            is_advanced_engine=False,
            r_status="NEUTRAL",
            intel_data=None,
            macro_ctx=None,
            market_gate={"gate": "GREEN"},
            rank_adjustment_fn=lambda *args, **kwargs: 0.0,
            news_adjustment_fn=lambda *args, **kwargs: {"score_adjustment": 0.0},
            backoff_state=SharedBackoffState(),
            max_retries=0,
            scan_mode="SWING",
            run_id="RUN-TEST123",
        )

        self.assertEqual(row, {"ticker": "005930.KS"})
        db.upsert_scan_result.assert_called_once()
        saved_payload = db.upsert_scan_result.call_args.args[0]
        self.assertEqual(saved_payload["run_id"], "RUN-TEST123")


if __name__ == "__main__":
    unittest.main()
