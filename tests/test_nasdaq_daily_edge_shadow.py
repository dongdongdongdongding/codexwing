from __future__ import annotations

import json
import os

import pandas as pd

from multi_agent.tools import report_nasdaq_daily_edge_shadow as tool


def test_select_policy_picks_applies_primary_and_high_liquidity_contracts():
    latest = pd.DataFrame(
        [
            {
                "date": "2026-06-26",
                "symbol": "AAA",
                "name": "Alpha",
                "close": 10.0,
                "liq20": 120_000_000,
                "liq60": 130_000_000,
                "score_alpha3": 0.98,
                "pred_alpha3": 1.2,
                "pred_alpha5": 1.5,
                "pred_alpha5_pos": 0.72,
                "pred_ft55": 0.4,
                "pred_dd3": 0.2,
            },
            {
                "date": "2026-06-26",
                "symbol": "BBB",
                "name": "Beta",
                "close": 20.0,
                "liq20": 50_000_000,
                "liq60": 55_000_000,
                "score_alpha3": 0.90,
                "pred_alpha3": 1.1,
                "pred_alpha5": 1.4,
                "pred_alpha5_pos": 0.65,
                "pred_ft55": 0.35,
                "pred_dd3": 0.25,
            },
            {
                "date": "2026-06-26",
                "symbol": "CCC",
                "name": "Gamma",
                "close": 30.0,
                "liq20": 200_000_000,
                "liq60": 210_000_000,
                "score_alpha3": 0.99,
                "pred_alpha3": 1.3,
                "pred_alpha5": 1.7,
                "pred_alpha5_pos": 0.59,
                "pred_ft55": 0.5,
                "pred_dd3": 0.1,
            },
        ]
    )

    picks = tool.select_policy_picks(
        latest,
        policies=[
            {
                "candidate_id": "primary",
                "lane": "liq30",
                "score_col": "score_alpha3",
                "entry_gate": "pred_alpha5_pos_ge_0_60",
                "pred_alpha5_pos_min": 0.60,
                "liq20_floor": 30_000_000,
                "topn": 2,
            },
            {
                "candidate_id": "high",
                "lane": "liq100",
                "score_col": "score_alpha3",
                "entry_gate": "pred_alpha5_pos_ge_0_60",
                "pred_alpha5_pos_min": 0.60,
                "liq20_floor": 100_000_000,
                "topn": 1,
            },
        ],
    )

    assert [(p["candidate_id"], p["ticker"], p["rank"]) for p in picks] == [
        ("primary", "AAA", 1),
        ("primary", "BBB", 2),
        ("high", "AAA", 1),
    ]
    assert picks[0]["strategy_family"] == "NASDAQ_SWING_DAILY_EDGE"
    assert picks[0]["p"] == 0.72
    assert picks[0]["ledger_key"] == "primary:2026-06-26:AAA"


def test_policy_diagnostics_explain_zero_pick_gate_failures():
    latest = pd.DataFrame(
        [
            {
                "date": "2026-06-26",
                "symbol": "AAA",
                "name": "Alpha",
                "close": 10.0,
                "liq20": 120_000_000,
                "score_alpha3": 0.98,
                "pred_alpha3": 1.2,
                "pred_alpha5": 1.5,
                "pred_alpha5_pos": 0.59,
            }
        ]
    )

    diagnostics = tool.build_policy_diagnostics(
        latest,
        policies=[
            {
                "candidate_id": "primary",
                "lane": "liq30",
                "score_col": "score_alpha3",
                "entry_gate": "pred_alpha5_pos_ge_0_60",
                "pred_alpha5_pos_min": 0.60,
                "liq20_floor": 30_000_000,
                "topn": 10,
            }
        ],
    )

    assert diagnostics[0]["pool_rows"] == 1
    assert diagnostics[0]["gate_pass_rows"] == 0
    assert diagnostics[0]["max_pred_alpha5_net_pos"] == 0.59
    assert diagnostics[0]["top_blocked"][0]["blocking_reasons"] == ["pred_alpha5_net_pos_below_0_60"]


def test_ledger_upsert_is_idempotent_and_settlement_tracks_alpha_net_costs():
    pick = {
        "ledger_key": "primary:2026-06-20:AAA",
        "candidate_id": "primary",
        "ticker": "AAA",
        "date": "2026-06-20",
        "status": "open",
    }
    merged, appended = tool.upsert_ledger_rows([], [pick, pick])
    assert appended == 1
    assert len(merged) == 1

    context = pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "date": "2026-06-20",
                "fwd_close_ret_3d": 2.0,
                "fwd_close_ret_5d": 3.0,
                "alpha3_liq": 1.1,
                "alpha5_liq": 1.7,
                "alpha3_day": 0.8,
                "alpha5_day": 1.3,
                "touch5_3d": 1.0,
                "touch5_5d": 1.0,
                "ft_5_5": 1.0,
                "dd5_3d": 0.0,
                "dd5_5d": 0.0,
                "fwd_high_ret_3d": 5.5,
                "fwd_low_ret_3d": -1.0,
            }
        ]
    )

    settled, changed = tool.settle_ledger_rows(merged, context)
    assert changed == 1
    assert settled[0]["status"] == "settled"
    assert settled[0]["ret5"] == 3.0
    assert settled[0]["alpha5_net_cost_0_20"] == 1.5
    assert settled[0]["touch3"] == 1.0
    assert settled[0]["dd3"] == 0.0

    summary = tool.summarize_ledger(settled)
    assert summary["settled"] == 1
    assert summary["by_candidate"][0]["alpha5_net_cost_0_20_avg"] == 1.5
    assert summary["by_candidate"][0]["alpha5_net_cost_0_20_win_pct"] == 100.0


def test_resolve_panel_path_uses_latest_non_snapshot_panel(tmp_path, monkeypatch):
    old = tmp_path / "daily_features_20180101_20260620_old.parquet"
    new = tmp_path / "daily_features_20180101_20260626_new.parquet"
    latest_snapshot = tmp_path / "daily_features_latest_20260626.parquet"
    for path in (old, new, latest_snapshot):
        path.write_text(json.dumps({"path": path.name}), encoding="utf-8")
    os.utime(old, (100, 100))
    os.utime(latest_snapshot, (300, 300))
    os.utime(new, (200, 200))
    monkeypatch.setattr(tool, "DEFAULT_PANEL_ROOT", tmp_path)

    assert tool.resolve_panel_path("latest") == new
