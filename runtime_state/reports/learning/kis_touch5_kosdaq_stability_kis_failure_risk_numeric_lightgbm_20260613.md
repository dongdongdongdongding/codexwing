# KIS Touch5 Stability Search

- version: `kis_touch5_stability_search_v1`
- generated_at: `2026-06-13T11:05:55+00:00`
- dummy_data_used: `False`
- decision: `no_period_stable_both_market_candidate`
- production_replacement_ready: `False`
- recommended_action: `keep KIS candidates in shadow; continue backfill and forward validation`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10`
- missing_or_sparse_actual_months: `['2026-01', '2026-02', '2026-03', '2026-04']`

## Market Summary
| market | evaluated | production_ready | period_stable | shadow_period_stable | best rule | best hit5 | best avg5 | best min_low |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| KOSDAQ | 1344 | 0 | 0 | 0 | top5_prob_plus_tail_p0p3 | 70.4225 | 4.667585 | -33.704825 |

## Period Stable Top
### KOSDAQ
- none

## Best Overall
### KOSDAQ
1. `top5_prob_plus_tail_p0p3` status=`unstable_candidate` pass=`0/3` n=`142` days=`16` hit5=`70.4225` avg5=`4.667585` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`70.4225` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
2. `top5_p0p3` status=`unstable_candidate` pass=`0/3` n=`142` days=`16` hit5=`68.3099` avg5=`6.475124` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`68.3099` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
3. `top5_prob_tail_margin_p0p3` status=`unstable_candidate` pass=`0/3` n=`142` days=`16` hit5=`69.7183` avg5=`3.025005` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`69.7183` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
4. `top5_ev_p0p3` status=`unstable_candidate` pass=`0/3` n=`142` days=`16` hit5=`69.7183` avg5=`2.648386` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`69.7183` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
5. `top5_prob_plus_tail_p0p2` status=`unstable_candidate` pass=`0/3` n=`154` days=`17` hit5=`65.5844` avg5=`3.878145` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`65.5844` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
