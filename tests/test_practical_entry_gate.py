from modules.practical_entry_gate import evaluate_practical_entry_gate


def test_kospi_semiconductor_prob_clean_passes_practical_gate():
    gate = evaluate_practical_entry_gate(
        {
            "ticker": "000660.KS",
            "primary_theme": "반도체",
            "prob_clean": 52,
        }
    )

    assert gate["pass"] is True
    assert gate["level"] == "pass"
    assert gate["evidence"]["practical_win_pct"] == 92.1


def test_kosdaq_80_gate_requires_small_sample_warning():
    gate = evaluate_practical_entry_gate(
        {
            "ticker": "123456.KQ",
            "primary_theme": "금융",
            "decision_score": 85,
        }
    )

    assert gate["pass"] is False
    assert gate["promote"] is True
    assert gate["level"] == "small_sample"


def test_outcome_fields_do_not_change_gate():
    base = {
        "ticker": "000001.KS",
        "primary_theme": "반도체",
        "prob_clean": 49,
    }
    with_outcomes = {
        **base,
        "return_5d_pct": 50,
        "max_high_return_5d_pct": 80,
        "min_return_observed_pct": 0,
    }

    assert evaluate_practical_entry_gate(base)["pass"] is False
    assert evaluate_practical_entry_gate(with_outcomes)["pass"] is False
