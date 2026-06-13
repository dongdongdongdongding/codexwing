# KIS Touch5 Stability Search

- version: `kis_touch5_stability_search_v1`
- generated_at: `2026-06-13T11:42:13+00:00`
- dummy_data_used: `False`
- decision: `no_period_stable_both_market_candidate`
- production_replacement_ready: `False`
- recommended_action: `keep KIS candidates in shadow; continue backfill and forward validation`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10`
- missing_or_sparse_actual_months: `['2026-01', '2026-02', '2026-03', '2026-04']`

## Market Summary
| market | evaluated | production_ready | period_stable | shadow_period_stable | best rule | best hit5 | best avg5 | best min_low |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| KOSDAQ | 1344 | 0 | 0 | 0 | top5_p0p65 | 66.6667 | 18.984628 | -46.675277 |

## Period Stable Top
### KOSDAQ
- none

## Best Overall
### KOSDAQ
1. `top5_p0p65` status=`unstable_candidate` pass=`0/3` n=`93` days=`13` hit5=`66.6667` avg5=`18.984628` min_low=`-46.675277` worst=`2026-05..2026-06` worst_hit5=`66.6667` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
2. `top5_p0p5` status=`unstable_candidate` pass=`0/3` n=`100` days=`13` hit5=`64.0` avg5=`17.130309` min_low=`-46.675277` worst=`2026-05..2026-06` worst_hit5=`64.0` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
3. `top5_p0p8` status=`unstable_candidate` pass=`0/3` n=`86` days=`12` hit5=`68.6047` avg5=`20.34589` min_low=`-46.675277` worst=`2026-05..2026-06` worst_hit5=`68.6047` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
4. `top5_p0p75` status=`unstable_candidate` pass=`0/3` n=`87` days=`12` hit5=`67.8161` avg5=`19.915857` min_low=`-46.675277` worst=`2026-05..2026-06` worst_hit5=`67.8161` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
5. `top5_p0p9` status=`unstable_candidate` pass=`0/3` n=`83` days=`10` hit5=`68.6747` avg5=`19.745644` min_low=`-46.675277` worst=`2026-05..2026-06` worst_hit5=`68.6747` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
