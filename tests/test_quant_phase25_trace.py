import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd

from modules import quant_analysis
from modules.quant_analysis import QuantStrategy


class Phase25TraceTests(unittest.TestCase):
    def setUp(self):
        idx = pd.date_range("2026-01-01", periods=80, freq="D")
        self.df = pd.DataFrame(
            {
                "Open": [100.0 + i * 0.1 for i in range(80)],
                "High": [101.0 + i * 0.1 for i in range(80)],
                "Low": [99.0 + i * 0.1 for i in range(80)],
                "Close": [100.0 + i * 0.1 for i in range(80)],
                "Volume": [1_000_000.0 + i for i in range(80)],
                "Antigrav_Score": [70.0 for _ in range(80)],
            },
            index=idx,
        )
        features = pd.DataFrame(
            {
                "f1": [0.0 for _ in range(80)],
                "Spy_Rel_Strength": [0.0 for _ in range(80)],
                "Market_Mom_20": [1.0 for _ in range(80)],
            },
            index=idx,
        )
        fake_train_ml_targets = types.SimpleNamespace(
            FEATURES_V5=["f1"],
            _build_features_v5=lambda df, macro: features.copy(),
            _fetch_cross_asset_data=lambda: {},
        )
        self.previous_train_module = sys.modules.get("train_ml_targets")
        sys.modules["train_ml_targets"] = fake_train_ml_targets
        self.previous_macro_cache = quant_analysis._GLOBAL_MACRO_CACHE
        quant_analysis._GLOBAL_MACRO_CACHE = {}

    def tearDown(self):
        if self.previous_train_module is None:
            sys.modules.pop("train_ml_targets", None)
        else:
            sys.modules["train_ml_targets"] = self.previous_train_module
        quant_analysis._GLOBAL_MACRO_CACHE = self.previous_macro_cache

    @patch("joblib.load", side_effect=RuntimeError("broken bundle"))
    @patch("os.path.exists")
    def test_phase25_load_failure_is_not_reported_as_ok(self, exists_mock, _load_mock):
        def exists(path):
            return str(path).endswith("phase25_kospi_swing.pkl")

        exists_mock.side_effect = exists
        qs = QuantStrategy("005930.KS")
        qs.df = self.df.copy()
        qs.scan_mode = "SWING"

        result = qs.get_ml_prediction()

        self.assertEqual(result["model_trace_status"], "phase25_load_fail")
        self.assertIn("broken bundle", result["model_error"])
        self.assertTrue(result["phase25_degraded"])
        self.assertTrue(result["inference_failed"])

    @patch("os.path.exists", return_value=False)
    def test_missing_phase25_bundle_is_reported_as_degraded(self, _exists_mock):
        qs = QuantStrategy("005930.KQ")
        qs.df = self.df.copy()
        qs.scan_mode = "SWING"

        result = qs.get_ml_prediction()

        self.assertEqual(result["model_trace_status"], "phase25_missing")
        self.assertIn("no_phase25_bundle", result["model_error"])
        self.assertTrue(result["phase25_degraded"])


if __name__ == "__main__":
    unittest.main()
