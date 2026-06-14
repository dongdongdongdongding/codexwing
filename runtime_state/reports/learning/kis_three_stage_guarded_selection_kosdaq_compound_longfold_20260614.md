# KIS Three-Stage Guarded Selection Research

- status: `blocked`
- generated_at: `2026-06-14T09:56:36+00:00`
- date_range: `2026-01-01`..`2026-06-10`
- validation: `Reproduce three-stage walk-forward selections, split selected cases chronologically, learn single-feature keep guards on selected-train rows, evaluate on selected-holdout rows.`
- leakage_control: `Guard feature allow-list excludes realized outcome labels; model probabilities are allowed because they exist at scan time.`

## KOSDAQ

- source: `runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kosdaq_20260101_20260610.pkl`
- rows/days: `186203` / `103`
- selected_rows/configs: `483` / `20`
- best_config: pool=`day_return` pool_k=`5` final_topn=`1` score=`ev_hit10` max_tail_prob=`0.75`
- base_metrics: n=`24`, days=`24`, hit5=`54.1667`, hit10=`70.8333`, tail=`37.5`, avg_exit=`-1.420942`, dynamic_exit=`1.277111`, min_low=`-58.95783`
- best_guard: `keep_close_failure_prior_ticker_avg_close_5d_pct_ge_11p2598` holdout_gate=`blocked` blockers=`['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20']`
- holdout_metrics: n=`4`, days=`4`, hit5=`100.0`, hit10=`100.0`, tail=`0.0`, avg_exit=`4.601458`, dynamic_exit=`9.58248`, min_low=`-7.789335`
- all_guarded_metrics: n=`11`, days=`11`, hit5=`72.7273`, hit10=`90.9091`, tail=`18.1818`, avg_exit=`1.35008`, dynamic_exit=`4.972641`, min_low=`-15.535445`
- holdout_deltas: avg_exit=`8.111921`, hit5=`55.5556`, min_low=`51.168495`

| rank | config | base_n | base_hit5 | base_avg_exit | guard | holdout_n | holdout_hit5 | holdout_avg_exit | holdout_min_low | holdout_gate |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| 1 | day_return/k5/n1/ev_hit10/tail0.75 | 24 | 54.17 | -1.421 | keep_close_failure_prior_ticker_avg_close_5d_pct_ge_11p2598 | 4 | 100 | 4.601 | -7.789 | blocked |
| 2 | day_return/k5/n1/success_tail/tail0.75 | 27 | 59.26 | -0.7518 | keep_close_failure_prior_ticker_avg_close_5d_pct_ge_11p508 | 4 | 100 | 4.601 | -7.789 | blocked |
| 3 | day_return/k5/n1/success_tail/tail0.85 | 31 | 61.29 | -0.5321 | keep_close_failure_prior_ticker_avg_close_5d_pct_ge_10p9677 | 4 | 100 | 4.601 | -7.789 | blocked |
| 4 | day_return/k10/n1/success_tail/tail0.8 | 39 | 41.03 | -3.597 | keep_day_return_pct_ge_29p9687 | 3 | 100 | 4.601 | -7.789 | blocked |
| 5 | day_return/k5/n1/success_tail/tail0.8 | 29 | 58.62 | -0.8861 | keep_close_failure_prior_ticker_avg_close_5d_pct_ge_11p508 | 4 | 100 | 4.601 | -7.789 | blocked |
| 6 | day_return/k10/n1/ev_hit10/tail0.85 | 42 | 40.48 | -3.707 | keep_close_failure_prior_theme_failure_rate_pct_le_30p1329 | 4 | 100 | 4.601 | -7.789 | blocked |
| 7 | day_return/k5/n1/ev_hit10/tail0.8 | 31 | 58.06 | -1.003 | keep_close_failure_prior_ticker_avg_close_5d_pct_ge_10p7876 | 4 | 100 | 4.601 | -7.789 | blocked |
| 8 | day_return/k5/n1/ev_hit10/tail0.85 | 33 | 60.61 | -0.6634 | keep_close_failure_prior_ticker_avg_close_5d_pct_ge_11p3279 | 4 | 100 | 4.601 | -7.789 | blocked |
| 9 | day_return/k10/n1/ev_hit10/tail0.8 | 40 | 40 | -3.757 | keep_close_failure_prior_theme_failure_rate_pct_le_29p9114 | 4 | 100 | 4.601 | -7.789 | blocked |
| 10 | day_return/k10/n1/ev_hit10/tail0.75 | 34 | 32.35 | -4.803 | keep_close_failure_prior_theme_risk_score_le_29p8088 | 4 | 100 | 4.601 | -7.789 | blocked |
| 11 | day_return/k10/n1/success_tail/tail0.75 | 35 | 34.29 | -4.534 | keep_close_failure_prior_theme_risk_score_le_28p9936 | 4 | 100 | 4.601 | -7.789 | blocked |
| 12 | day_return/k10/n1/success_tail/tail0.85 | 41 | 41.46 | -3.554 | keep_close_failure_prior_ticker_avg_close_5d_pct_ge_12p0817 | 3 | 100 | 4.601 | -7.789 | blocked |

### Loss Traits

- `close_failure_prior_market_avg_close_5d_pct` bad_median=`6.339878` good_median=`5.965852` scaled_delta=`0.772401`
- `close_failure_prior_market_failure_rate_pct` bad_median=`28.24056` good_median=`29.57628` scaled_delta=`-0.643651`
- `close_failure_prior_theme_stop5_rate_pct` bad_median=`48.29319` good_median=`52.145265` scaled_delta=`-0.63625`
- `close_failure_prior_kis_theme_stop5_rate_pct` bad_median=`48.29319` good_median=`52.145265` scaled_delta=`-0.63625`
- `close_failure_prior_kis_sector_stop5_rate_pct` bad_median=`48.29319` good_median=`52.145265` scaled_delta=`-0.63625`
- `close_failure_prior_market_risk_score` bad_median=`26.003485` good_median=`27.56412` scaled_delta=`-0.602705`
- `close_failure_prior_theme_clean_defense_rate_pct` bad_median=`43.223966` good_median=`40.302267` scaled_delta=`0.602218`
- `close_failure_prior_kis_theme_clean_defense_rate_pct` bad_median=`43.223966` good_median=`40.302267` scaled_delta=`0.602218`
