# KIS Touch5 Stability Search

- version: `kis_touch5_stability_search_v1`
- generated_at: `2026-06-13T11:02:02+00:00`
- dummy_data_used: `False`
- decision: `no_period_stable_both_market_candidate`
- production_replacement_ready: `False`
- recommended_action: `keep KIS candidates in shadow; continue backfill and forward validation`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10`
- missing_or_sparse_actual_months: `['2026-01', '2026-02', '2026-03', '2026-04']`

## Market Summary
| market | evaluated | production_ready | period_stable | shadow_period_stable | best rule | best hit5 | best avg5 | best min_low |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| KOSDAQ | 1316 | 0 | 0 | 0 | top5_prob_plus_tail_p0p5 | 52.9412 | 1.090013 | -30.373423 |

## Period Stable Top
### KOSDAQ
- none

## Best Overall
### KOSDAQ
1. `top5_prob_plus_tail_p0p5` status=`unstable_candidate` pass=`0/3` n=`136` days=`13` hit5=`52.9412` avg5=`1.090013` min_low=`-30.373423` worst=`2026-05..2026-06` worst_hit5=`52.9412` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
2. `top3_p0p5` status=`unstable_candidate` pass=`0/3` n=`82` days=`13` hit5=`58.5366` avg5=`4.206538` min_low=`-30.373423` worst=`2026-05..2026-06` worst_hit5=`58.5366` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
3. `top3_p0p3` status=`unstable_candidate` pass=`0/3` n=`97` days=`17` hit5=`50.5155` avg5=`2.054925` min_low=`-37.734463` worst=`2026-05..2026-06` worst_hit5=`50.5155` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
4. `top5_prob_plus_tail_p0p3` status=`unstable_candidate` pass=`0/3` n=`153` days=`17` hit5=`47.7124` avg5=`-0.044215` min_low=`-37.734463` worst=`2026-05..2026-06` worst_hit5=`47.7124` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
5. `top5_p0p5` status=`unstable_candidate` pass=`0/3` n=`136` days=`13` hit5=`47.7941` avg5=`-0.283149` min_low=`-31.943651` worst=`2026-05..2026-06` worst_hit5=`47.7941` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
