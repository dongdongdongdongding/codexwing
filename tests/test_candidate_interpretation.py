from modules.candidate_data_quality import build_candidate_data_quality
from modules.candidate_interpretation import INTERPRETATION_VERSION, build_candidate_interpretation
from modules.ui_helpers import build_signal_display_rows


def _fixture_row():
    return {
        "run_id": "RUN-PARITY",
        "rank": 7,
        "ticker": "000660.KS",
        "stock_name": "SK하이닉스",
        "market": "KOSPI",
        "signal_label": "WAIT_CONFIRM",
        "display_contract": {
            "display_status": "VISIBLE",
            "original_scan_rank": 12,
            "planner_priority_rank": 3,
        },
        "selection_alignment": {
            "analysis_section": "Exception Leader",
            "analysis_section_rank": 2,
            "source_order": "top5_main_plus_exception_addon",
        },
        "trade_plan": {
            "entry_reference_price": 100000,
            "target_price": 112000,
            "stop_price": 95000,
            "target_tp_pct": 12,
            "stop_sl_pct": -5,
            "readiness_analysis": {"final_buy_judgment": {"action": "눌림 대기"}},
        },
        "realized_expectancy_admission": {
            "policy_version": "kr_realized_expectancy_admission_v1",
            "3d_prob": 62.5,
            "5d_prob": 80.1,
            "expected_value_3d_pct": 2.1,
            "expected_value_5d_pct": 6.3,
            "ranking_score_5d": 77.4,
            "stop_first_risk_pct": 18.2,
        },
        "theme": {"primary_theme": "HBM"},
        "data_warnings": ["flow_stale"],
        "risk_flags": ["gap_up"],
    }


def test_candidate_interpretation_contract_extracts_surface_parity_fields():
    interpretation = build_candidate_interpretation(_fixture_row())

    assert interpretation["version"] == INTERPRETATION_VERSION
    assert interpretation["section"] == "Exception Leader"
    assert interpretation["section_rank"] == 2
    assert interpretation["original_rank"] == 12
    assert interpretation["planner_rank"] == 3
    assert interpretation["action_label"] == "눌림 대기"
    assert interpretation["entry_reference_price"] == 100000.0
    assert interpretation["target_tp_pct"] == 12.0
    assert interpretation["stop_sl_pct"] == -5.0
    assert interpretation["realized_expectancy_3d_prob"] == 62.5
    assert interpretation["realized_expectancy_5d_prob"] == 80.1
    assert interpretation["ranking_score_5d"] == 77.4
    assert interpretation["data_warning_count"] == 1


def test_signal_display_rows_embed_same_candidate_interpretation_contract():
    row = _fixture_row()
    display = build_signal_display_rows([row])[0]
    interpretation = display["candidate_interpretation"]

    assert display["original_rank"] == 12
    assert display["planner_rank"] == 3
    assert display["realized_expectancy_5d_prob"] == 80.1
    assert interpretation == build_candidate_interpretation({**row, "candidate_data_quality": build_candidate_data_quality(row)})


def test_candidate_interpretation_prefers_unified_execution_stop():
    row = _fixture_row()
    row["execution_stop"] = {
        "display_stop_price": 97000,
        "display_stop_sl_pct": -3,
        "display_stop_source": "raw_scan_stricter",
        "stop_conflict": True,
    }

    interpretation = build_candidate_interpretation(row)

    assert interpretation["stop_price"] == 97000.0
    assert interpretation["stop_sl_pct"] == -3.0
    assert interpretation["stop_display_source"] == "raw_scan_stricter"
    assert interpretation["stop_conflict"] is True
