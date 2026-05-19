from modules.kosdaq_shadow_observer import (
    PromotionGuardrails,
    build_kosdaq_shadow_observer_report,
    is_kosdaq_ordered_rebound_observer_row,
)


def _row(**overrides):
    base = {
        "ticker": "123456.KQ",
        "stock_name": "테스트",
        "market": "KOSDAQ",
        "candidate_id": "5D_ordered_5v5",
        "volume_ratio": "1.20",
        "trend": "DOWN",
        "selection_lane": "1d",
        "trade_date": "2026-05-01",
        "primary_theme": "반도체",
        "ordered_label_ready": "true",
        "ordered_win": "true",
        "ordered_stop": "false",
        "ordered_mfe_pct": "8.0",
        "ordered_mae_pct": "-2.0",
        "return_1d_pct": "1.0",
        "return_3d_pct": "3.0",
        "return_5d_pct": "5.5",
    }
    base.update(overrides)
    return base


def test_observer_gate_uses_issue_contract():
    assert is_kosdaq_ordered_rebound_observer_row(_row()) is True
    assert is_kosdaq_ordered_rebound_observer_row(_row(volume_ratio="1.24")) is False
    assert is_kosdaq_ordered_rebound_observer_row(_row(trend="UP")) is False
    assert is_kosdaq_ordered_rebound_observer_row(_row(selection_lane="3d")) is False
    assert is_kosdaq_ordered_rebound_observer_row(_row(candidate_id="5D_ordered_8v5")) is False
    assert is_kosdaq_ordered_rebound_observer_row(_row(market="KOSPI", ticker="123456.KS")) is False


def test_report_summarizes_ordered_win_stop_and_returns():
    rows = [
        _row(trade_date="2026-05-01", ticker="A.KQ", ordered_win="true", ordered_stop="false", return_5d_pct="6.0"),
        _row(trade_date="2026-05-02", ticker="B.KQ", ordered_win="false", ordered_stop="true", return_5d_pct="-4.0"),
        _row(trade_date="2026-05-03", ticker="C.KQ", volume_ratio="1.50", return_5d_pct="20.0"),
    ]

    report = build_kosdaq_shadow_observer_report(
        rows,
        as_of_date="2026-05-19",
        generated_at="now",
        guardrails=PromotionGuardrails(min_ready_n=2, min_trade_dates=2, min_theme_count=1),
    )

    assert report["source"]["observer_rows"] == 2
    assert report["source"]["ready_rows"] == 2
    assert report["ordered_summary"]["win_rate_pct"] == 50.0
    assert report["ordered_summary"]["stop_first_pct"] == 50.0
    assert report["horizon_metrics"]["5d"]["avg_return_pct"] == 1.0
    assert report["promotion"]["status"] == "shadow_observe"


def test_report_tracks_display_gate_alignment_after_section_split():
    rows = [
        _row(trade_date="2026-05-01", ticker="A.KQ"),
        {
            "ticker": "D.KQ",
            "market": "KOSDAQ",
            "tech_score": "75",
            "trend": "UP",
            "primary_theme": "로봇",
            "theme_day_symbol_count": "7",
            "theme_day_avg_decision_score": "60",
        },
    ]

    report = build_kosdaq_shadow_observer_report(rows, generated_at="now")

    assert report["display_gate_alignment"]["current_display_shadow_rows"] == 2
    assert report["display_gate_alignment"]["observer_rows_also_in_display_shadow"] == 1
    assert report["display_gate_alignment"]["observer_display_overlap_pct"] == 100.0
    assert report["display_gate_alignment"]["warning"] == ""
