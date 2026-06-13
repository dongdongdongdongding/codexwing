# KIS Touch5 Stability Search

- version: `kis_touch5_stability_search_v1`
- generated_at: `2026-06-13T10:29:16+00:00`
- dummy_data_used: `False`
- decision: `period_stable_shadow_candidates_found`
- production_replacement_ready: `False`
- recommended_action: `keep KIS candidates in shadow; continue backfill and forward validation`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10`
- missing_or_sparse_actual_months: `['2026-01', '2026-02', '2026-03', '2026-04']`

## Market Summary
| market | evaluated | production_ready | period_stable | shadow_period_stable | best rule | best hit5 | best avg5 | best min_low |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| KOSPI | 1344 | 0 | 224 | 224 | top2_p0p9_tail0p6 | 94.2529 | 30.020109 | -9.757906 |
| KOSDAQ | 1344 | 0 | 411 | 411 | top3_prob_plus_tail_p0p2_tail0p9 | 100.0 | 11.94343 | -7.8413 |

## Period Stable Top
### KOSPI
1. `top2_p0p9_tail0p6` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`87` days=`12` hit5=`94.2529` avg5=`30.020109` min_low=`-9.757906` worst=`2026-05` worst_hit5=`94.2529`
2. `top2_p0p9` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`89` days=`13` hit5=`92.1348` avg5=`29.343019` min_low=`-9.757906` worst=`2026-05..2026-06` worst_hit5=`92.1348`
3. `top2_p0p9_tail0p75` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`85` days=`12` hit5=`94.1176` avg5=`29.874264` min_low=`-9.757906` worst=`2026-05` worst_hit5=`94.1176`
4. `top2_p0p9_tail0p85` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`82` days=`11` hit5=`95.122` avg5=`31.030682` min_low=`-9.757906` worst=`2026-05` worst_hit5=`95.122`
5. `top2_prob_plus_tail_p0p9_tail0p6` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`87` days=`12` hit5=`95.4023` avg5=`17.981578` min_low=`-9.548959` worst=`2026-05` worst_hit5=`95.4023`
### KOSDAQ
1. `top3_prob_plus_tail_p0p2_tail0p9` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`57` days=`9` hit5=`100.0` avg5=`11.94343` min_low=`-7.8413` worst=`2026-05` worst_hit5=`100.0`
2. `top3_prob_plus_tail_p0p3_tail0p9` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`57` days=`9` hit5=`100.0` avg5=`11.94343` min_low=`-7.8413` worst=`2026-05` worst_hit5=`100.0`
3. `top3_prob_plus_tail_p0p5_tail0p9` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`57` days=`9` hit5=`100.0` avg5=`11.94343` min_low=`-7.8413` worst=`2026-05` worst_hit5=`100.0`
4. `top3_prob_plus_tail_p0p65_tail0p9` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`57` days=`9` hit5=`100.0` avg5=`11.94343` min_low=`-7.8413` worst=`2026-05` worst_hit5=`100.0`
5. `top3_prob_plus_tail_tail0p9` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`58` days=`10` hit5=`98.2759` avg5=`11.685857` min_low=`-7.8413` worst=`2026-05` worst_hit5=`98.2759`

## Best Overall
### KOSPI
1. `top2_p0p9_tail0p6` status=`period_stable_candidate` pass=`3/3` n=`87` days=`12` hit5=`94.2529` avg5=`30.020109` min_low=`-9.757906` worst=`2026-05` worst_hit5=`94.2529` blockers=`['active_days_lt_15']`
2. `top2_p0p9` status=`period_stable_candidate` pass=`3/3` n=`89` days=`13` hit5=`92.1348` avg5=`29.343019` min_low=`-9.757906` worst=`2026-05..2026-06` worst_hit5=`92.1348` blockers=`['active_days_lt_15']`
3. `top2_p0p9_tail0p75` status=`period_stable_candidate` pass=`3/3` n=`85` days=`12` hit5=`94.1176` avg5=`29.874264` min_low=`-9.757906` worst=`2026-05` worst_hit5=`94.1176` blockers=`['active_days_lt_15']`
4. `top2_p0p9_tail0p85` status=`period_stable_candidate` pass=`3/3` n=`82` days=`11` hit5=`95.122` avg5=`31.030682` min_low=`-9.757906` worst=`2026-05` worst_hit5=`95.122` blockers=`['active_days_lt_15']`
5. `top2_prob_plus_tail_p0p9_tail0p6` status=`period_stable_candidate` pass=`3/3` n=`87` days=`12` hit5=`95.4023` avg5=`17.981578` min_low=`-9.548959` worst=`2026-05` worst_hit5=`95.4023` blockers=`['active_days_lt_15']`
### KOSDAQ
1. `top3_prob_plus_tail_p0p2_tail0p9` status=`period_stable_candidate` pass=`3/3` n=`57` days=`9` hit5=`100.0` avg5=`11.94343` min_low=`-7.8413` worst=`2026-05` worst_hit5=`100.0` blockers=`['active_days_lt_20', 'active_runs_lt_20']`
2. `top3_prob_plus_tail_p0p3_tail0p9` status=`period_stable_candidate` pass=`3/3` n=`57` days=`9` hit5=`100.0` avg5=`11.94343` min_low=`-7.8413` worst=`2026-05` worst_hit5=`100.0` blockers=`['active_days_lt_20', 'active_runs_lt_20']`
3. `top3_prob_plus_tail_p0p5_tail0p9` status=`period_stable_candidate` pass=`3/3` n=`57` days=`9` hit5=`100.0` avg5=`11.94343` min_low=`-7.8413` worst=`2026-05` worst_hit5=`100.0` blockers=`['active_days_lt_20', 'active_runs_lt_20']`
4. `top3_prob_plus_tail_p0p65_tail0p9` status=`period_stable_candidate` pass=`3/3` n=`57` days=`9` hit5=`100.0` avg5=`11.94343` min_low=`-7.8413` worst=`2026-05` worst_hit5=`100.0` blockers=`['active_days_lt_20', 'active_runs_lt_20']`
5. `top3_prob_plus_tail_tail0p9` status=`period_stable_candidate` pass=`3/3` n=`58` days=`10` hit5=`98.2759` avg5=`11.685857` min_low=`-7.8413` worst=`2026-05` worst_hit5=`98.2759` blockers=`['active_days_lt_20']`
