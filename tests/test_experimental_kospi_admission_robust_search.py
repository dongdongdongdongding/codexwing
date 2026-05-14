import pandas as pd

from multi_agent.tools.experimental_kospi_admission_robust_search import (
    _mask_for_conditions,
    _parse_condition,
)


def test_parse_condition_supports_numeric_thresholds_and_flags():
    df = pd.DataFrame(
        {
            "prob_clean": [20.0, 40.0],
            "decision_score": [100.0, 90.0],
            "explosive_leader_flag": [0, 1],
        }
    )

    mask = _parse_condition(df, "prob_clean<=31.8")
    assert mask.tolist() == [True, False]

    mask = _parse_condition(df, "decision_score>=100")
    assert mask.tolist() == [True, False]

    mask = _parse_condition(df, "explosive_leader_flag=0")
    assert mask.tolist() == [True, False]


def test_mask_for_conditions_falls_back_to_parser():
    df = pd.DataFrame(
        {
            "prob_clean": [20.0, 40.0],
            "decision_score": [100.0, 100.0],
            "explosive_leader_flag": [0, 0],
        }
    )

    mask = _mask_for_conditions(
        df,
        base_mask=pd.Series([True, True]),
        conditions=["prob_clean<=31.8", "decision_score>=100", "explosive_leader_flag=0"],
        condition_map={},
    )

    assert mask.tolist() == [True, False]
