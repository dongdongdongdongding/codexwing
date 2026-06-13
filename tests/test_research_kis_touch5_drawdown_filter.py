import pandas as pd

from multi_agent.tools.research_kis_touch5_drawdown_filter import (
    _apply_filter,
    _candidate_identity,
    _filter_rule_name,
    _fold_slices,
    _selection_rule,
)


def test_drawdown_filter_identity_is_research_only():
    identity = _candidate_identity(
        market="KOSPI",
        feature_set="kis_sidecar_failure_risk_augmented",
        model="lightgbm_drawdown_filter",
        selection_rule="top1_prob_tail0p85_x",
        score_mode="prob",
        topn=1,
        tail_threshold=0.85,
        filter_payload={"feature": "close_failure_prior_kis_sector_failure_rate_pct", "op": "le", "threshold": 46.666667},
    )

    assert identity["validation_mode"] == "research_sweep_only_walk_forward_predictions"
    assert identity["deployment_ready"] is False
    assert identity["drawdown_filter"]["feature"] == "close_failure_prior_kis_sector_failure_rate_pct"


def test_drawdown_filter_rule_names_are_stable():
    filter_name = _filter_rule_name("close_failure_prior_theme_avg_close_5d_pct", "le", -2.53492)

    assert filter_name == "close_failure_prior_theme_avg_close_5d_pct_le_neg2p53492"
    assert _selection_rule(topn=1, score_mode="prob", tail_threshold=0.85, filter_name=filter_name) == (
        "top1_prob_tail0p85_close_failure_prior_theme_avg_close_5d_pct_le_neg2p53492"
    )
    assert _selection_rule(
        topn=3,
        score_mode="prob_tail_margin",
        prob_threshold=0.5,
        tail_threshold=0.0,
        filter_name=filter_name,
    ) == "top3_prob_tail_margin_p0p5_tail0_close_failure_prior_theme_avg_close_5d_pct_le_neg2p53492"


def test_holdout_split_and_filter_application_are_deterministic():
    predictions = pd.DataFrame({"fold": [1, 2, 3, 4], "tail_prob": [0.9, 0.8, 0.95, 0.7]}, index=[10, 11, 12, 13])
    split = _fold_slices(predictions, selection_folds=2)

    assert split["selection_folds"] == [1, 2]
    assert split["holdout_folds"] == [3, 4]
    assert list(split["selection_index"]) == [10, 11]
    assert list(split["holdout_index"]) == [12, 13]

    scoped = pd.DataFrame({"risk": [1.0, 5.0, 3.0]}, index=[100, 101, 102])
    pool = pd.Index([100, 101, 102])

    assert list(_apply_filter(scoped, pool, {"feature": "risk", "op": "le", "threshold": 3.0})) == [100, 102]
    assert list(_apply_filter(scoped, pool, {"feature": "risk", "op": "ge", "threshold": 3.0})) == [101, 102]
