from modules.experimental_target_touch import (
    TargetTouchPolicy,
    compute_target_before_stop_label,
    derive_proxy_label_from_archive_row,
    summarize_shadow_rows,
)


def test_target_before_stop_label_hits_target_first():
    label = compute_target_before_stop_label(
        [
            {"date": "2026-05-01", "high": 101, "low": 99, "close": 100},
            {"date": "2026-05-02", "high": 106, "low": 100, "close": 105},
            {"date": "2026-05-03", "high": 107, "low": 93, "close": 96},
        ],
        entry_price=100,
        policy=TargetTouchPolicy(target_pct=5, stop_pct=5, horizon_days=5, include_entry_day=True),
    )

    assert label["target_before_stop"] is True
    assert label["stop_before_target"] is False
    assert label["target_hit_at"] == "2026-05-02"
    assert label["terminal_status"] == "target_before_stop"
    assert label["mfe_pct"] == 6.0
    assert label["mae_pct"] == -1.0


def test_target_before_stop_label_hits_stop_first():
    label = compute_target_before_stop_label(
        [
            {"date": "2026-05-01", "high": 101, "low": 99, "close": 100},
            {"date": "2026-05-02", "high": 103, "low": 94, "close": 95},
            {"date": "2026-05-03", "high": 108, "low": 96, "close": 107},
        ],
        entry_price=100,
        policy=TargetTouchPolicy(target_pct=5, stop_pct=5, horizon_days=5, include_entry_day=True),
    )

    assert label["target_before_stop"] is False
    assert label["stop_before_target"] is True
    assert label["stop_hit_at"] == "2026-05-02"
    assert label["terminal_status"] == "stop_before_target"


def test_target_before_stop_label_same_bar_is_conservative():
    label = compute_target_before_stop_label(
        [{"date": "2026-05-01", "high": 106, "low": 94, "close": 100}],
        entry_price=100,
        policy=TargetTouchPolicy(target_pct=5, stop_pct=5, horizon_days=5, include_entry_day=True),
    )

    assert label["target_before_stop"] is False
    assert label["stop_before_target"] is True
    assert label["terminal_status"] == "same_bar_stop_first"
    assert "same_bar_target_and_stop_touch" in label["warnings"]


def test_archive_proxy_does_not_claim_order_when_stop_unknown():
    label = derive_proxy_label_from_archive_row(
        {"hit_5pct_within_5d": True, "max_high_return_5d_pct": 6.2, "return_5d_pct": 2.1},
        policy=TargetTouchPolicy(target_pct=5, stop_pct=5, horizon_days=5),
    )

    assert label["target_touch_proxy"] is True
    assert label["target_before_stop"] is None
    assert label["terminal_status"] == "proxy_target_touch_only"


def test_shadow_summary_reports_ordered_and_proxy_metrics():
    rows = [
        {
            "market": "KOSPI",
            "scan_mode": "SWING",
            "decision_bucket": "picked",
            "target_before_stop": True,
            "target_touch_proxy": True,
            "stop_touch_proxy": False,
            "close_return_pct": 3.0,
            "mfe_pct": 6.0,
            "mae_pct": -1.0,
        },
        {
            "market": "KOSPI",
            "scan_mode": "SWING",
            "decision_bucket": "picked",
            "target_before_stop": False,
            "target_touch_proxy": False,
            "stop_touch_proxy": True,
            "close_return_pct": -4.0,
            "mfe_pct": 1.0,
            "mae_pct": -5.5,
        },
    ]

    summary = summarize_shadow_rows(rows)

    assert len(summary) == 1
    assert summary[0]["n"] == 2
    assert summary[0]["ordered_label_n"] == 2
    assert summary[0]["target_before_stop_win_pct"] == 50.0
    assert summary[0]["target_touch_proxy_pct"] == 50.0
    assert summary[0]["stop_touch_proxy_pct"] == 50.0
    assert summary[0]["avg_close_return_pct"] == -0.5
