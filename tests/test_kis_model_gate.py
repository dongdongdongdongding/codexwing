from modules.kis_model_gate import KIS_MODEL_GATE_VERSION, evaluate_kis_model_gate


def test_kis_gate_keeps_strong_kospi_candidate_shadow_until_sample_and_tail_clear():
    gate = evaluate_kis_model_gate(
        identity={
            "market": "KOSPI",
            "feature_set": "kis_sidecar_only",
            "label": "pos_5d",
            "model": "random_forest",
            "selection_rule": "top1",
        },
        metrics={
            "n": 29,
            "active_days": 9,
            "active_runs": 26,
            "win_3d_pct": 96.55,
            "win_5d_pct": 96.55,
            "avg_3d_pct": 20.0,
            "avg_5d_pct": 23.2,
            "min_1d_pct": 0.88,
            "min_min_low_5d_pct": -18.03,
            "bad_path_pct": 3.45,
            "stop5_pct": 3.45,
            "stop_before_target_5d_pct": 3.45,
            "target_before_stop_5d_pct": 96.55,
        },
    )

    assert gate["version"] == KIS_MODEL_GATE_VERSION
    assert gate["production_ready"] is False
    assert gate["shadow_display_allowed"] is True
    assert gate["risk_review_required"] is True
    assert gate["status"] == "shadow_risk_review"
    assert "n_lt_30" in gate["production_blocking_reasons"]
    assert "active_days_lt_15" in gate["production_blocking_reasons"]
    assert "min_low_5d_lt_neg15" in gate["production_blocking_reasons"]


def test_kis_gate_marks_kosdaq_drawdown_candidate_as_shadow_risk_review():
    gate = evaluate_kis_model_gate(
        identity={
            "market": "KOSDAQ",
            "feature_set": "kis_sidecar_only",
            "label": "touch10_guard_5d",
            "model": "random_forest",
            "selection_rule": "top3_p0.65",
        },
        metrics={
            "n": 11,
            "active_days": 3,
            "active_runs": 5,
            "win_3d_pct": 90.9,
            "win_5d_pct": 54.55,
            "avg_3d_pct": 20.67,
            "avg_5d_pct": 15.8,
            "min_1d_pct": -5.85,
            "min_min_low_5d_pct": -21.39,
            "bad_path_pct": 45.45,
            "stop5_pct": 9.09,
            "stop_before_target_5d_pct": 9.09,
            "target_before_stop_5d_pct": 90.9,
        },
    )

    assert gate["production_ready"] is False
    assert gate["shadow_display_allowed"] is True
    assert gate["risk_review_required"] is True
    assert gate["status"] == "shadow_risk_review"
    assert "bad_path_gt_15" in gate["production_blocking_reasons"]
    assert "min_low_5d_lt_neg18" in gate["risk_review_reasons"]
    assert "min_1d_lt_neg4" in gate["risk_review_reasons"]


def test_kis_gate_blocks_non_kis_identity():
    gate = evaluate_kis_model_gate(
        identity={"market": "KOSPI", "feature_set": "wide_theme"},
        metrics={"n": 100, "active_days": 30},
    )

    assert gate["source_ok"] is False
    assert gate["shadow_display_allowed"] is False
    assert gate["status"] == "blocked"
    assert "feature_set_not_kis" in gate["blocking_reasons"]
