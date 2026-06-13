# KIS Touch5 KOSDAQ Bottleneck Matrix

- generated_at: `2026-06-13T11:44:53+00:00`
- market: `KOSDAQ`
- status: `kosdaq_tail_risk_blocks_production_replacement`
- production_replacement_ready: `False`
- period_stable_candidate_count: `0`
- production_ready_count: `0`
- holdout_gate_pass_count: `0`
- recommended_action: keep KOSDAQ KIS touch5/dd10 in shadow; prioritize KOSDAQ-specific tail-risk veto features and cached prediction matrix before any promotion review

## Stability Matrix
| feature_set | model | stable | prod | rule | n | days | hit5 | avg5 | min_low | blockers |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---|
| kis_failure_risk_augmented | lightgbm | 0 | 0 | top3_prob_tail_margin_p0p5 | 83 | 14 | 75.9036 | 6.54185 | -21.915669 | ['active_days_lt_20', 'min_low_5d_lt_neg10'] |
| kis_failure_risk_numeric | lightgbm | 0 | 0 | top5_prob_plus_tail_p0p3 | 142 | 16 | 70.4225 | 4.667585 | -33.704825 | ['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5'] |
| kis_failure_risk_augmented | logistic | 0 | 0 | top5_p0p65 | 93 | 13 | 66.6667 | 18.984628 | -46.675277 | ['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5'] |
| kis_full_augmented | lightgbm | 0 | 0 | top5_prob_plus_tail_p0p5 | 142 | 14 | 53.5211 | 0.20195 | -36.329672 | ['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5'] |
| kis_sidecar_only | lightgbm | 0 | 0 | top5_prob_plus_tail_p0p5 | 136 | 13 | 52.9412 | 1.090013 | -30.373423 | ['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5'] |

## Drawdown Holdout
- status: `no_production_gate_pass_candidate`
- base: rule=`top3_prob_tail_margin_p0p5_tail0`, n=`83`, days=`14`, hit5=`75.9036`, avg5=`6.54185`, min_low=`-21.915669`
- holdout: status=`no_holdout_gate_pass`, candidates=`947`, evaluated=`80`, gate_pass=`0`
- selection_best_holdout: rule=`top3_prob_tail_margin_p0p5_tail0_close_failure_prior_ticker_avg_close_5d_pct_ge_10p4905`, n=`53`, days=`8`, hit5=`62.2642`, min_low=`-31.118999`
