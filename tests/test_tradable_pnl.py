import json
import os

from modules.tradable_pnl import TradableCostModel, build_tradable_pnl_rows, compute_net_return_pct, load_post_scan_ledger_rows, summarize_tradable_pnl


def test_compute_net_return_applies_entry_exit_costs_and_tax():
    model = TradableCostModel(
        buy_fee_bps=1.0,
        sell_fee_bps=1.0,
        buy_slippage_bps=5.0,
        sell_slippage_bps=5.0,
        spread_bps=4.0,
        sell_tax_bps=10.0,
        fill_rate=1.0,
    )

    net = compute_net_return_pct(10.0, model)

    assert net < 10.0
    assert net == 9.714229


def test_partial_fill_scales_expected_net_return():
    full = compute_net_return_pct(5.0, TradableCostModel(fill_rate=1.0))
    half = compute_net_return_pct(5.0, TradableCostModel(fill_rate=0.5))

    assert half == round(full * 0.5, 6)


def test_build_tradable_pnl_rows_marks_missing_returns_without_fabrication():
    rows = build_tradable_pnl_rows(
        [
            {
                "run_id": "RUN-X",
                "ticker": "005930.KS",
                "market": "KOSPI",
                "section": "Top5",
                "decision": "PRIORITY_WATCHLIST",
                "scan_entry_reference_price": 100.0,
            }
        ]
    )

    assert rows[0]["gross_return_3d_pct"] is None
    assert rows[0]["net_return_3d_pct"] is None
    assert "MISSING_3D_5D_RETURNS" in rows[0]["data_warnings"]


def test_summarize_tradable_pnl_reports_gross_vs_net_by_section_action():
    rows = build_tradable_pnl_rows(
        [
            {
                "market": "KOSPI",
                "section": "Top5",
                "action_label": "관망",
                "return_3d_pct": 5.0,
                "return_5d_pct": 6.0,
                "scan_entry_reference_price": 100.0,
            },
            {
                "market": "KOSPI",
                "section": "Top5",
                "action_label": "관망",
                "return_3d_pct": -2.0,
                "return_5d_pct": -1.0,
                "scan_entry_reference_price": 100.0,
            },
        ],
        cost_model=TradableCostModel(buy_fee_bps=0, sell_fee_bps=0, buy_slippage_bps=0, sell_slippage_bps=0, spread_bps=0, sell_tax_bps=0),
    )

    summary = summarize_tradable_pnl(rows)
    group = summary["groups"][0]
    assert group["gross_3d_win_pct"] == 50.0
    assert group["net_3d_win_pct"] == 50.0
    assert group["gross_3d_avg_pct"] == 1.5
    assert group["net_3d_avg_pct"] == 1.5
    assert summary["release_gate_pass"] is True


def test_summarize_tradable_pnl_flags_gross_edge_lost_after_costs():
    rows = build_tradable_pnl_rows(
        [
            {
                "market": "KOSPI",
                "section": "Top5",
                "action_label": "즉시 매수 가능",
                "return_3d_pct": 0.1,
                "return_5d_pct": 2.0,
                "scan_entry_reference_price": 100.0,
            }
        ],
        cost_model=TradableCostModel(buy_fee_bps=5, sell_fee_bps=5, buy_slippage_bps=10, sell_slippage_bps=10, spread_bps=10, sell_tax_bps=20),
    )

    summary = summarize_tradable_pnl(rows)

    assert summary["release_gate_pass"] is False
    assert summary["net_regression_groups"][0]["horizon"] == "3d"


def test_load_post_scan_ledger_rows_prefers_latest_ledgers_by_mtime(tmp_path):
    old_dir = tmp_path / "RUN-ZZZZ"
    new_dir = tmp_path / "RUN-AAAA"
    old_dir.mkdir()
    new_dir.mkdir()
    (old_dir / "post_scan_outcome_ledger.json").write_text(json.dumps({"rows": [{"run_id": "old"}]}), encoding="utf-8")
    (new_dir / "post_scan_outcome_ledger.json").write_text(json.dumps({"rows": [{"run_id": "new"}]}), encoding="utf-8")
    os.utime(old_dir / "post_scan_outcome_ledger.json", (100, 100))
    os.utime(new_dir / "post_scan_outcome_ledger.json", (200, 200))

    rows = load_post_scan_ledger_rows(tmp_path, limit_runs=1)

    assert rows == [{"run_id": "new"}]
