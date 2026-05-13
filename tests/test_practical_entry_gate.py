from modules.practical_entry_gate import evaluate_practical_entry_gate


PROFILE_PAYLOAD = {
    "markets": {
        "KOSPI": {
            "themes": {
                "AI전력": {
                    "level": "pass",
                    "evidence": {
                        "sample_n": 41,
                        "win5_pct": 87.8,
                        "practical_win_pct": 82.9,
                        "bad_path_pct": 12.2,
                        "avg_1d_pct": 2.1,
                        "avg_3d_pct": 4.7,
                        "avg_5d_pct": 8.4,
                    },
                    "thresholds": {
                        "min_prob_clean": 50,
                        "min_expected_edge_score": 6,
                        "max_loss_risk_score": 65,
                    },
                }
            }
        },
        "KOSDAQ": {
            "themes": {
                "로봇": {
                    "level": "small_sample",
                    "evidence": {
                        "sample_n": 14,
                        "win5_pct": 92.9,
                        "practical_win_pct": 85.7,
                        "bad_path_pct": 7.1,
                    },
                    "thresholds": {
                        "min_decision_score": 80,
                        "max_loss_risk_score": 65,
                    },
                }
            }
        },
    }
}


def test_dynamic_theme_profile_passes_practical_gate():
    gate = evaluate_practical_entry_gate(
        {
            "ticker": "000660.KS",
            "primary_theme": "AI전력",
            "prob_clean": 52,
            "expected_edge_score": 7,
        },
        profile_payload=PROFILE_PAYLOAD,
    )

    assert gate["pass"] is True
    assert gate["level"] == "pass"
    assert gate["evidence"]["practical_win_pct"] == 82.9


def test_kosdaq_80_gate_requires_small_sample_warning():
    gate = evaluate_practical_entry_gate(
        {
            "ticker": "123456.KQ",
            "primary_theme": "로봇",
            "decision_score": 85,
        },
        profile_payload=PROFILE_PAYLOAD,
    )

    assert gate["pass"] is False
    assert gate["promote"] is True
    assert gate["level"] == "small_sample"


def test_outcome_fields_do_not_change_gate():
    base = {
        "ticker": "000001.KS",
        "primary_theme": "AI전력",
        "prob_clean": 49,
        "expected_edge_score": 5,
    }
    with_outcomes = {
        **base,
        "return_5d_pct": 50,
        "max_high_return_5d_pct": 80,
        "min_return_observed_pct": 0,
    }

    assert evaluate_practical_entry_gate(base, profile_payload=PROFILE_PAYLOAD)["pass"] is False
    assert evaluate_practical_entry_gate(with_outcomes, profile_payload=PROFILE_PAYLOAD)["pass"] is False


def test_fixed_theme_name_without_dynamic_profile_does_not_pass():
    gate = evaluate_practical_entry_gate(
        {
            "ticker": "000660.KS",
            "primary_theme": "반도체",
            "prob_clean": 99,
            "expected_edge_score": 99,
        },
        profile_payload={"markets": {"KOSPI": {"themes": {}}}},
    )

    assert gate["pass"] is False
    assert gate["promote"] is False
