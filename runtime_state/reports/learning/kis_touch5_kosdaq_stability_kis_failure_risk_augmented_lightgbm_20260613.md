# KIS Touch5 Stability Search

- version: `kis_touch5_stability_search_v1`
- generated_at: `2026-06-13T11:06:19+00:00`
- dummy_data_used: `False`
- decision: `no_period_stable_both_market_candidate`
- production_replacement_ready: `False`
- recommended_action: `keep KIS candidates in shadow; continue backfill and forward validation`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10`
- missing_or_sparse_actual_months: `['2026-01', '2026-02', '2026-03', '2026-04']`

## Market Summary
| market | evaluated | production_ready | period_stable | shadow_period_stable | best rule | best hit5 | best avg5 | best min_low |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| KOSDAQ | 1344 | 0 | 0 | 0 | top3_prob_tail_margin_p0p5 | 75.9036 | 6.54185 | -21.915669 |

## Period Stable Top
### KOSDAQ
- none

## Best Overall
### KOSDAQ
1. `top3_prob_tail_margin_p0p5` status=`unstable_candidate` pass=`0/3` n=`83` days=`14` hit5=`75.9036` avg5=`6.54185` min_low=`-21.915669` worst=`2026-05..2026-06` worst_hit5=`75.9036` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'min_low_5d_lt_neg10']`
2. `top3_prob_tail_margin_p0p3` status=`unstable_candidate` pass=`0/3` n=`88` days=`15` hit5=`71.5909` avg5=`5.720741` min_low=`-21.915669` worst=`2026-05..2026-06` worst_hit5=`71.5909` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
3. `top5_p0p5` status=`unstable_candidate` pass=`0/3` n=`137` days=`14` hit5=`69.3431` avg5=`8.423835` min_low=`-31.118999` worst=`2026-05..2026-06` worst_hit5=`69.3431` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
4. `top5_prob_plus_tail_p0p5` status=`unstable_candidate` pass=`0/3` n=`137` days=`14` hit5=`70.073` avg5=`6.562725` min_low=`-31.118999` worst=`2026-05..2026-06` worst_hit5=`70.073` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
5. `top5_p0p3` status=`unstable_candidate` pass=`0/3` n=`142` days=`15` hit5=`66.9014` avg5=`7.848712` min_low=`-31.118999` worst=`2026-05..2026-06` worst_hit5=`66.9014` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
