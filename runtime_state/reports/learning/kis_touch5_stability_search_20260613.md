# KIS Touch5 Stability Search

- version: `kis_touch5_stability_search_v1`
- generated_at: `2026-06-13T10:19:36+00:00`
- dummy_data_used: `False`
- decision: `no_period_stable_both_market_candidate`
- production_replacement_ready: `False`
- recommended_action: `keep KIS candidates in shadow; continue backfill and forward validation`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10`
- missing_or_sparse_actual_months: `['2026-01', '2026-02', '2026-03', '2026-04']`

## Market Summary
| market | evaluated | production_ready | period_stable | shadow_period_stable | best rule | best hit5 | best avg5 | best min_low |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| KOSPI | 1092 | 0 | 70 | 0 | top1_tail0p85 | 100.0 | 10.534841 | -8.188031 |
| KOSDAQ | 868 | 0 | 0 | 0 | top5_prob_plus_tail_tail0p6 | 40.0 | 14.086518 | -14.578702 |

## Period Stable Top
### KOSPI
1. `top1_tail0p85` status=`period_stable_candidate` gate=`blocked` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0`
2. `top1_p0p2_tail0p85` status=`period_stable_candidate` gate=`blocked` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0`
3. `top1_p0p3_tail0p85` status=`period_stable_candidate` gate=`blocked` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0`
4. `top1_p0p5_tail0p85` status=`period_stable_candidate` gate=`blocked` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0`
5. `top1_p0p65_tail0p85` status=`period_stable_candidate` gate=`blocked` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0`
### KOSDAQ
- none

## Best Overall
### KOSPI
1. `top1_tail0p85` status=`period_stable_candidate` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`
2. `top1_p0p2_tail0p85` status=`period_stable_candidate` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`
3. `top1_p0p3_tail0p85` status=`period_stable_candidate` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`
4. `top1_p0p5_tail0p85` status=`period_stable_candidate` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`
5. `top1_p0p65_tail0p85` status=`period_stable_candidate` pass=`3/3` n=`4` days=`3` hit5=`100.0` avg5=`10.534841` min_low=`-8.188031` worst=`2026-05` worst_hit5=`100.0` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20']`
### KOSDAQ
1. `top5_prob_plus_tail_tail0p6` status=`unstable_candidate` pass=`0/3` n=`5` days=`1` hit5=`40.0` avg5=`14.086518` min_low=`-14.578702` worst=`2026-05` worst_hit5=`40.0` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
2. `top5_prob_plus_tail_tail0p75` status=`unstable_candidate` pass=`0/3` n=`5` days=`1` hit5=`40.0` avg5=`14.086518` min_low=`-14.578702` worst=`2026-05` worst_hit5=`40.0` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
3. `top5_prob_plus_tail_p0p2_tail0p6` status=`unstable_candidate` pass=`0/3` n=`5` days=`1` hit5=`40.0` avg5=`14.086518` min_low=`-14.578702` worst=`2026-05` worst_hit5=`40.0` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
4. `top5_prob_plus_tail_p0p2_tail0p75` status=`unstable_candidate` pass=`0/3` n=`5` days=`1` hit5=`40.0` avg5=`14.086518` min_low=`-14.578702` worst=`2026-05` worst_hit5=`40.0` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
5. `top5_prob_plus_tail_p0p3_tail0p6` status=`unstable_candidate` pass=`0/3` n=`5` days=`1` hit5=`40.0` avg5=`14.086518` min_low=`-14.578702` worst=`2026-05` worst_hit5=`40.0` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
