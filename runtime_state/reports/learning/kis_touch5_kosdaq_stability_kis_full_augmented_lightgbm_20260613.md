# KIS Touch5 Stability Search

- version: `kis_touch5_stability_search_v1`
- generated_at: `2026-06-13T11:02:12+00:00`
- dummy_data_used: `False`
- decision: `no_period_stable_both_market_candidate`
- production_replacement_ready: `False`
- recommended_action: `keep KIS candidates in shadow; continue backfill and forward validation`
- prepared_cache: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_sidecar_db_20260101_20260610.pkl` rows=`157551` date=`2026-03-31`..`2026-06-10`
- missing_or_sparse_actual_months: `['2026-01', '2026-02', '2026-03', '2026-04']`

## Market Summary
| market | evaluated | production_ready | period_stable | shadow_period_stable | best rule | best hit5 | best avg5 | best min_low |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| KOSDAQ | 1344 | 0 | 0 | 0 | top5_prob_plus_tail_p0p5 | 53.5211 | 0.20195 | -36.329672 |

## Period Stable Top
### KOSDAQ
- none

## Best Overall
### KOSDAQ
1. `top5_prob_plus_tail_p0p5` status=`unstable_candidate` pass=`0/3` n=`142` days=`14` hit5=`53.5211` avg5=`0.20195` min_low=`-36.329672` worst=`2026-05..2026-06` worst_hit5=`53.5211` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
2. `top5_ev_p0p5` status=`unstable_candidate` pass=`0/3` n=`142` days=`14` hit5=`54.2254` avg5=`-1.404762` min_low=`-36.329672` worst=`2026-05..2026-06` worst_hit5=`54.2254` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
3. `top5_prob_tail_margin_p0p5` status=`unstable_candidate` pass=`0/3` n=`142` days=`14` hit5=`52.8169` avg5=`-1.386186` min_low=`-36.329672` worst=`2026-05..2026-06` worst_hit5=`52.8169` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
4. `top5_p0p5` status=`unstable_candidate` pass=`0/3` n=`142` days=`14` hit5=`50.0` avg5=`0.293455` min_low=`-36.329672` worst=`2026-05..2026-06` worst_hit5=`50.0` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
5. `top3_ev_p0p5` status=`unstable_candidate` pass=`0/3` n=`86` days=`14` hit5=`54.6512` avg5=`-1.243212` min_low=`-34.031584` worst=`2026-05..2026-06` worst_hit5=`54.6512` selected_months=`['2026-05', '2026-06']` coverage_blockers=`[]` blockers=`['active_days_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
