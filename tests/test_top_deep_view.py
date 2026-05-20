import pandas as pd

from ui.top_deep_view import (
    fmt_flow_leader_caption,
    fmt_flow_value,
    fmt_krw,
    fmt_metric_num,
    fmt_metric_pct,
    infer_top_deep_market,
    scan_display_label,
    top_deep_section_name,
    top_deep_section_order,
    top_deep_section_rank,
)


def test_top_deep_formatters_are_stable_for_missing_and_numeric_values():
    assert fmt_metric_pct(None) == "-"
    assert fmt_metric_pct(1.234) == "+1.23%"
    assert fmt_metric_num("12.345", 1) == "12.3"
    assert fmt_krw(12345) == "12,345원"
    assert fmt_flow_value(250000000, "krw") == "+2.5억"
    assert fmt_flow_value(-1200, "shares") == "-1,200주"


def test_flow_leader_caption_prefers_intraday_label_when_window_is_day():
    caption = fmt_flow_leader_caption(
        {
            "flow_asof": "2026-05-20",
            "flow_unit": "krw",
            "flow_window": "1d",
            "whale_flow_1d": 300000000,
            "whale_flow_3d": -100000000,
        }
    )

    assert "기준일: 2026-05-20" in caption
    assert "당일 외인+기관: +3.0억" in caption
    assert "3일 외인+기관: -1.0억" in caption


def test_top_deep_market_and_section_helpers():
    assert infer_top_deep_market({"ticker": "005930.KS"}) == "KOSPI"
    assert infer_top_deep_market({"ticker": "091990.KQ"}) == "KOSDAQ"
    assert infer_top_deep_market({"market": "kospi", "ticker": "X"}) == "KOSPI"
    assert top_deep_section_name({}) == "Top5"
    assert top_deep_section_name({"analysis_section": "Exception Leader"}) == "Exception Leader"
    assert top_deep_section_order({"analysis_section": "Practical 80 Gate"}) < top_deep_section_order({"analysis_section": "KOSDAQ Ordered Shadow"})
    assert top_deep_section_order({"analysis_section": "KOSDAQ Ordered Shadow"}) < top_deep_section_order({"analysis_section": "Top5"})
    assert top_deep_section_rank({"analysis_section_rank": 3}) == 3


def test_scan_display_label_uses_kst_timestamp_and_run_metadata():
    df = pd.DataFrame(
        [
            {
                "run_id": "RUN-1",
                "_market": "KOSPI",
                "generated_at": "2026-05-20T00:30:00Z",
            }
        ]
    )

    assert scan_display_label(df) == "2026-05-20 09:30 · KOSPI · 1건 · RUN-1"
