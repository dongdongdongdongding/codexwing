from multi_agent.tools.report_supabase_scan_quality import FEATURE_COVERAGE_COLUMNS, REQUIRED_SCAN_COLUMNS
from multi_agent.tools.report_supabase_scan_quality import _computed_complete_mask

import pandas as pd


def test_supabase_scan_quality_tracks_multi_window_kr_flow():
    required = set(REQUIRED_SCAN_COLUMNS)
    coverage = set(FEATURE_COVERAGE_COLUMNS)
    for column in (
        "foreign_flow",
        "institution_flow",
        "retail_flow",
        "foreigner_1d",
        "institution_1d",
        "retail_1d",
        "foreigner_3d",
        "institution_3d",
        "retail_3d",
        "foreigner_10d",
        "institution_10d",
        "retail_10d",
        "flow_asof",
    ):
        assert column in required
        assert column in coverage


def _complete_row(**overrides):
    row = {
        "alpha_score": 80,
        "tech_score": 70,
        "ml_prob": 60,
        "whale_score": 55,
        "decision_score": 90,
        "entry_reference_price": 100,
        "trend": "UP",
        "tier": "T1",
        "position": "RISING",
        "volume_ratio": 1.5,
        "foreigner_1d": 100,
        "institution_1d": 50,
        "retail_1d": -150,
        "foreigner_3d": 300,
        "institution_3d": 100,
        "retail_3d": -400,
        "foreigner_10d": 1000,
        "institution_10d": 500,
        "retail_10d": -1500,
        "flow_asof": "2026-05-20",
    }
    row.update(overrides)
    return row


def test_computed_complete_requires_multi_window_flow():
    frame = pd.DataFrame(
        [
            _complete_row(ticker="complete.KS"),
            _complete_row(ticker="missing-flow.KS", foreigner_3d=None),
            _complete_row(ticker="missing-asof.KS", flow_asof=""),
        ]
    )

    mask = _computed_complete_mask(frame)

    assert mask.tolist() == [True, False, False]
