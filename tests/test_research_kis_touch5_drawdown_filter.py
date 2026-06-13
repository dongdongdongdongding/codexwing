from multi_agent.tools.research_kis_touch5_drawdown_filter import (
    _candidate_identity,
    _filter_rule_name,
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
