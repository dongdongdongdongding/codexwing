from __future__ import annotations

import json

import pandas as pd

from multi_agent.tools.report_nasdaq_session_edge_shadow import (
    POLICIES,
    build_session_contract,
    load_policy_validation,
    select_shadow_picks,
    settle_ledger_rows,
    summarize_ledger,
)
from multi_agent.tools.research_nasdaq_session_edge import add_ranks_and_alpha


def _panel_fixture() -> pd.DataFrame:
    date = pd.Timestamp("2026-06-26")
    rows = []
    for idx in range(5):
        winner = idx == 4
        rows.append(
            {
                "date": date,
                "symbol": f"SYM{idx}",
                "name": f"Symbol {idx}",
                "session_mode": "regular_close",
                "entry_price": 100.0 + idx,
                "prev_daily_close": 95.0,
                "session_ret": 4.0 if winner else 0.5,
                "anchor_ret": 7.0 if winner else 1.0,
                "session_range_pct": 1.0,
                "session_close_loc": 0.95 if winner else 0.3,
                "session_volume": 10_000.0,
                "session_dollar_volume": 5_000_000.0 if winner else 100_000.0,
                "session_volume_share_regular": 1.0,
                "session_bars": 78,
                "liq20": 1_000_000_000.0 if winner else 100_000_000.0 + idx,
                "liq60": 1_000_000_000.0,
                "ret_5d": 5.0,
                "ret_20d": 20.0 if winner else 1.0,
                "ret_60d": 30.0,
                "atr_pct": 3.0,
                "vol_ratio": 2.0 if winner else 0.8,
                "rsi14": 60.0,
                "ma60_slope": 1.0,
                "ma200_slope": 1.0,
                "dist_hi20": 0.0 if winner else -10.0,
                "dist_hi120": 0.0,
                "fwd_close_ret_3d": 6.0 if winner else -1.0,
                "fwd_close_ret_5d": 8.0 if winner else -2.0,
                "fwd_high_ret_3d": 7.0 if winner else 1.0,
                "fwd_high_ret_5d": 10.0 if winner else 2.0,
                "fwd_low_ret_3d": -1.0,
                "fwd_low_ret_5d": -2.0,
                "touch5_3d": 1.0 if winner else 0.0,
                "touch5_5d": 1.0 if winner else 0.0,
                "dd5_3d": 0.0,
                "dd5_5d": 0.0,
                "ft_5_5": 1.0 if winner else 0.0,
                "same_day_touch_stop_ambiguous": 0.0,
            }
        )
    return add_ranks_and_alpha(pd.DataFrame(rows))


def _validation_fixture():
    return {
        "source_report": "fixture.json",
        "policies": {
            POLICIES[0]["candidate_id"]: {
                "recent_shadow_ready": True,
                "promotion_ready": False,
                "source_report": "fixture.json",
                "metrics": {
                    "n": 50,
                    "days": 50,
                    "ret5": 9.359,
                    "ret5_pos_rate": 0.68,
                    "alpha5_net_cost_0_2": 5.711,
                    "touch3": 0.72,
                    "ft55": 0.74,
                    "dd3": 0.34,
                },
            }
        },
    }


def test_regular_close_session_contract_blocks_non_close_sessions():
    contract = build_session_contract(market_session="nasdaq_regular_open")

    assert contract["scoring_allowed"] is False
    assert contract["session_blocked"] is True
    assert contract["block_reason"] == "regular_close_core_edge_requires_regular_close_session"


def test_select_shadow_picks_uses_validated_regular_close_core_candidate():
    picks = select_shadow_picks(
        _panel_fixture(),
        validation=_validation_fixture(),
        session_contract=build_session_contract(market_session="nasdaq_regular_close"),
    )

    assert len(picks) == 1
    assert picks[0]["candidate_id"] == "nasdaq_session_regular_close_strength_liq_trend_top1_v1"
    assert picks[0]["ticker"] == "SYM4"
    assert picks[0]["status"] == "open"
    assert picks[0]["capital_status"] == "operator_enabled_live_scan"
    assert picks[0]["operational_route"] == "new_web_scan_model_lane"
    assert picks[0]["p"] == 0.74
    assert picks[0]["model_hit_prob_source"] == "validation_ft55"


def test_settle_ledger_rows_resolves_session_shadow_pick():
    picks = select_shadow_picks(
        _panel_fixture(),
        validation=_validation_fixture(),
        session_contract=build_session_contract(market_session="nasdaq_regular_close"),
    )

    settled, changed = settle_ledger_rows(picks, _panel_fixture())
    summary = summarize_ledger(settled)

    assert changed == 1
    assert settled[0]["status"] == "settled"
    assert settled[0]["ret5"] == 8.0
    assert summary["settled"] == 1


def test_policy_validation_matches_all_regime_candidate(tmp_path):
    report = {
        "top_candidates": [
            {
                "session_mode": "regular_close",
                "condition": "regular_close_strength_liq_trend",
                "regime": "market_up20_calm",
                "score": "score_liquid_open_drive",
                "topn": 1,
                "metrics": {"ret5": 10.124361},
                "recent_shadow_ready": True,
                "promotion_ready": False,
            },
            {
                "session_mode": "regular_close",
                "condition": "regular_close_strength_liq_trend",
                "regime": "all",
                "score": "score_liquid_open_drive",
                "topn": 1,
                "metrics": {"ret5": 9.359025},
                "recent_shadow_ready": True,
                "promotion_ready": False,
            },
        ]
    }
    path = tmp_path / "nasdaq_session_edge_search_20260630_000000.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    validation = load_policy_validation(tmp_path)
    item = validation["policies"][POLICIES[0]["candidate_id"]]

    assert item["regime"] == "all"
    assert item["metrics"]["ret5"] == 9.359025
