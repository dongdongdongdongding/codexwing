# KIS Three-Stage Guarded Selection Research

- status: `blocked`
- generated_at: `2026-06-14T09:39:59+00:00`
- date_range: `2026-01-01`..`2026-06-10`
- validation: `Reproduce three-stage walk-forward selections, split selected cases chronologically, learn single-feature keep guards on selected-train rows, evaluate on selected-holdout rows.`
- leakage_control: `Guard feature allow-list excludes realized outcome labels; model probabilities are allowed because they exist at scan time.`

## KOSDAQ

- source: `runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kosdaq_20260101_20260610.pkl`
- rows/days: `186203` / `103`
- selected_rows/configs: `1523` / `84`
- best_config: pool=`day_return` pool_k=`5` final_topn=`1` score=`success_tail` max_tail_prob=`0.6`
- base_metrics: n=`13`, days=`13`, hit5=`69.2308`, hit10=`84.6154`, tail=`30.7692`, avg_exit=`0.108702`, dynamic_exit=`3.557102`, min_low=`-37.326529`
- best_guard: `keep_kis_whale_flow_3d_le_19p8` holdout_gate=`blocked` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20']`
- holdout_metrics: n=`3`, days=`3`, hit5=`100.0`, hit10=`100.0`, tail=`0.0`, avg_exit=`4.601458`, dynamic_exit=`9.58248`, min_low=`-8.486291`
- all_guarded_metrics: n=`9`, days=`9`, hit5=`88.8889`, hit10=`100.0`, tail=`11.1111`, avg_exit=`2.979074`, dynamic_exit=`7.406649`, min_low=`-19.899875`
- holdout_deltas: avg_exit=`5.840583`, hit5=`40.0`, min_low=`28.840238`

| rank | config | base_n | base_hit5 | base_avg_exit | guard | holdout_n | holdout_hit5 | holdout_avg_exit | holdout_min_low | holdout_gate |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| 1 | day_return/k5/n1/success_tail/tail0.6 | 13 | 69.23 | 0.1087 | keep_kis_whale_flow_3d_le_19p8 | 3 | 100 | 4.601 | -8.486 | blocked |
| 2 | day_return/k5/n1/ev_hit10/tail0.6 | 13 | 69.23 | 0.1087 | keep_kis_whale_flow_3d_le_19p8 | 3 | 100 | 4.601 | -8.486 | blocked |
| 3 | day_return/k5/n1/success_tail/tail0.65 | 12 | 75 | 0.9511 | keep_kis_prefilter_rank_fluctuation_le_3 | 3 | 100 | 4.601 | -8.486 | blocked |
| 4 | day_return/k5/n1/ev_hit10/tail0.65 | 12 | 75 | 0.9511 | keep_kis_prefilter_rank_fluctuation_le_3 | 3 | 100 | 4.601 | -8.486 | blocked |
| 5 | day_return/k5/n1/success_tail/tail0.85 | 22 | 63.64 | 0.02268 | keep__p_tail_ge_0p471964 | 3 | 100 | 4.601 | -8.486 | blocked |
| 6 | day_return/k5/n1/ev_hit10/tail0.8 | 21 | 61.9 | -0.1954 | keep__p_tail_ge_0p466559 | 3 | 100 | 4.601 | -8.486 | blocked |
| 7 | day_return/k5/n1/success_tail/tail0.8 | 24 | 62.5 | -0.2042 | keep__p_tail_ge_0p477369 | 4 | 100 | 4.601 | -8.486 | blocked |
| 8 | day_return/k5/n1/success_tail/tail0.75 | 23 | 60.87 | -0.4131 | keep__p_tail_ge_0p471964 | 4 | 100 | 4.601 | -8.486 | blocked |
| 9 | day_return/k5/n1/ev_hit10/tail0.7 | 14 | 64.29 | -0.6133 | keep_kis_prefilter_rank_fluctuation_le_3 | 3 | 100 | 4.601 | -8.486 | blocked |
| 10 | day_return/k10/n1/ev_hit10/tail0.8 | 30 | 50 | -2.163 | keep_kis_prefilter_rank_fluctuation_le_3 | 3 | 100 | 4.601 | -1.961 | blocked |
| 11 | day_return/k10/n1/ev_hit10/tail0.75 | 29 | 48.28 | -2.397 | keep_kis_prefilter_rank_fluctuation_le_3 | 3 | 100 | 4.601 | -1.961 | blocked |
| 12 | day_return/k10/n1/ev_hit10/tail0.85 | 29 | 48.28 | -2.397 | keep_kis_prefilter_rank_fluctuation_le_3 | 3 | 100 | 4.601 | -1.961 | blocked |

### Loss Traits

- `kis_whale_score` bad_median=`55.0` good_median=`11.0` scaled_delta=`1.527469`
- `kis_daily_close_location_pct` bad_median=`74.876847` good_median=`100.0` scaled_delta=`-1.163769`
- `close_failure_prior_market_avg_close_5d_pct` bad_median=`5.378036` good_median=`5.823463` scaled_delta=`-1.10814`
- `close_failure_prior_market_avg_mfe_5d_pct` bad_median=`16.803486` good_median=`16.868298` scaled_delta=`-1.085346`
- `kis_daily_return_20d_pct` bad_median=`-16.902405` good_median=`10.8527` scaled_delta=`-1.068456`
- `close_failure_prior_market_avg_mae_5d_pct` bad_median=`-6.488094` good_median=`-6.225213` scaled_delta=`-1.047244`
- `kis_financial_roe` bad_median=`-26.14` good_median=`0.0` scaled_delta=`-1.019882`
- `close_failure_prior_market_failure_rate_pct` bad_median=`31.976327` good_median=`30.314727` scaled_delta=`0.9745`

