import pandas as pd

from multi_agent.tools import report_kis_sidecar_proxy_feature_gap as tool


def test_present_pct_treats_coverage_zero_as_absent_and_numeric_value_as_present() -> None:
    frame = pd.DataFrame(
        {
            "kis_sidecar_coverage_investor_flow": [1, 0, None],
            "kis_whale_score": [0.0, None, 5.0],
            "kis_stock_sector_name": ["반도체", "UNKNOWN", ""],
        }
    )

    assert tool._present_pct(frame, "kis_sidecar_coverage_investor_flow") == 33.333
    assert tool._present_pct(frame, "kis_whale_score") == 66.667
    assert tool._present_pct(frame, "kis_stock_sector_name") == 33.333


def test_feature_gap_prioritizes_real_sidecar_flow_missing_from_proxy() -> None:
    sidecar = pd.DataFrame(
        {
            "kis_whale_score": [1.0, 2.0, 3.0, 4.0],
            "kis_foreigner_1d": [10.0, 11.0, 12.0, 13.0],
            "kis_sidecar_coverage_investor_flow": [1, 1, 1, 1],
        }
    )
    proxy = pd.DataFrame(
        {
            "kis_whale_score": [None, None, None, None],
            "kis_foreigner_1d": [None, None, None, None],
            "kis_sidecar_coverage_investor_flow": [0, 0, 0, 0],
        }
    )

    gap = tool._feature_gap(sidecar, proxy)
    priorities = tool._backfill_priorities(gap)

    assert gap["families"]["sidecar_flow"]["top_gaps"][0]["feature"] == "kis_whale_score"
    assert priorities[0]["family"] == "sidecar_flow"
    assert priorities[0]["missing_high_value_features"] == 2
