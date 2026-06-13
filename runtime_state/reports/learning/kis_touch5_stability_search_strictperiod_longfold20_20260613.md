# KIS Touch5 Stability Search

- version: `kis_touch5_stability_search_v1`
- generated_at: `2026-06-13T10:54:42+00:00`
- dummy_data_used: `False`
- decision: `no_period_stable_both_market_candidate`
- production_replacement_ready: `False`
- recommended_action: `keep KIS candidates in shadow; continue backfill and forward validation`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10`
- missing_or_sparse_actual_months: `['2026-01', '2026-02', '2026-03', '2026-04']`

## Market Summary
| market | evaluated | production_ready | period_stable | shadow_period_stable | best rule | best hit5 | best avg5 | best min_low |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| KOSPI | 1344 | 0 | 25 | 25 | top2_p0p9 | 92.1348 | 29.343019 | -9.757906 |
| KOSDAQ | 1344 | 0 | 0 | 0 | top5_prob_plus_tail_p0p3 | 68.0556 | 5.931853 | -33.704825 |

## Period Stable Top
### KOSPI
1. `top2_p0p9` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`89` days=`13` hit5=`92.1348` avg5=`29.343019` min_low=`-9.757906` worst=`2026-05..2026-06` worst_hit5=`92.1348` selected_months=`['2026-05', '2026-06']`
2. `top2_p0p8_tail0p85` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`93` days=`14` hit5=`86.0215` avg5=`26.733072` min_low=`-9.757906` worst=`2026-05` worst_hit5=`85.8696` selected_months=`['2026-05', '2026-06']`
3. `top2_prob_plus_tail_p0p9` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`89` days=`13` hit5=`93.2584` avg5=`17.575016` min_low=`-9.548959` worst=`2026-05..2026-06` worst_hit5=`93.2584` selected_months=`['2026-05', '2026-06']`
4. `top3_ev_p0p9` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`127` days=`13` hit5=`87.4016` avg5=`12.941611` min_low=`-9.864936` worst=`2026-05..2026-06` worst_hit5=`87.4016` selected_months=`['2026-05', '2026-06']`
5. `top2_prob_plus_tail_p0p8_tail0p85` status=`period_stable_candidate` gate=`shadow_ready` pass=`3/3` n=`93` days=`14` hit5=`87.0968` avg5=`15.093948` min_low=`-8.919727` worst=`2026-05` worst_hit5=`86.9565` selected_months=`['2026-05', '2026-06']`
### KOSDAQ
- none

## Best Overall
### KOSPI
1. `top2_p0p9` status=`period_stable_candidate` pass=`3/3` n=`89` days=`13` hit5=`92.1348` avg5=`29.343019` min_low=`-9.757906` worst=`2026-05..2026-06` worst_hit5=`92.1348` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_15']`
2. `top2_p0p8_tail0p85` status=`period_stable_candidate` pass=`3/3` n=`93` days=`14` hit5=`86.0215` avg5=`26.733072` min_low=`-9.757906` worst=`2026-05` worst_hit5=`85.8696` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_15']`
3. `top2_prob_plus_tail_p0p9` status=`period_stable_candidate` pass=`3/3` n=`89` days=`13` hit5=`93.2584` avg5=`17.575016` min_low=`-9.548959` worst=`2026-05..2026-06` worst_hit5=`93.2584` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_15']`
4. `top3_ev_p0p9` status=`period_stable_candidate` pass=`3/3` n=`127` days=`13` hit5=`87.4016` avg5=`12.941611` min_low=`-9.864936` worst=`2026-05..2026-06` worst_hit5=`87.4016` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_15']`
5. `top2_prob_plus_tail_p0p8_tail0p85` status=`period_stable_candidate` pass=`3/3` n=`93` days=`14` hit5=`87.0968` avg5=`15.093948` min_low=`-8.919727` worst=`2026-05` worst_hit5=`86.9565` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_15']`
### KOSDAQ
1. `top5_prob_plus_tail_p0p3` status=`unstable_candidate` pass=`0/3` n=`144` days=`16` hit5=`68.0556` avg5=`5.931853` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`68.0556` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
2. `top5_prob_tail_margin_p0p3` status=`unstable_candidate` pass=`0/3` n=`144` days=`16` hit5=`66.6667` avg5=`3.620498` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`66.6667` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
3. `top5_p0p3` status=`unstable_candidate` pass=`0/3` n=`144` days=`16` hit5=`65.9722` avg5=`4.986543` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`65.9722` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
4. `top5_ev_p0p3` status=`unstable_candidate` pass=`0/3` n=`144` days=`16` hit5=`65.2778` avg5=`3.36204` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`65.2778` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
5. `top5_prob_plus_tail_p0p2` status=`unstable_candidate` pass=`0/3` n=`157` days=`17` hit5=`62.4204` avg5=`4.468132` min_low=`-33.704825` worst=`2026-05..2026-06` worst_hit5=`62.4204` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
