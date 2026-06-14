# KIS Three-Stage Guarded Selection Research

- status: `holdout_shadow_candidate`
- generated_at: `2026-06-14T09:54:35+00:00`
- date_range: `2026-01-01`..`2026-06-10`
- validation: `Reproduce three-stage walk-forward selections, split selected cases chronologically, learn single-feature keep guards on selected-train rows, evaluate on selected-holdout rows.`
- leakage_control: `Guard feature allow-list excludes realized outcome labels; model probabilities are allowed because they exist at scan time.`

## KOSPI

- source: `runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kospi_20260101_20260610.pkl`
- rows/days: `97638` / `103`
- selected_rows/configs: `798` / `24`
- best_config: pool=`prefilter` pool_k=`10` final_topn=`2` score=`ev` max_tail_prob=`0.85`
- base_metrics: n=`61`, days=`36`, hit5=`52.459`, hit10=`42.623`, tail=`29.5082`, avg_exit=`-1.108252`, dynamic_exit=`0.688182`, min_low=`-23.793047`
- best_guard: `keep_close_failure_prior_ticker_clean_defense_rate_pct_ge_57p5758` holdout_gate=`shadow_risk_review` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10']`
- holdout_metrics: n=`11`, days=`7`, hit5=`72.7273`, hit10=`72.7273`, tail=`9.0909`, avg_exit=`2.261713`, dynamic_exit=`5.431454`, min_low=`-10.056783`
- all_guarded_metrics: n=`31`, days=`20`, hit5=`54.8387`, hit10=`48.3871`, tail=`12.9032`, avg_exit=`0.288528`, dynamic_exit=`2.377343`, min_low=`-15.32357`
- holdout_deltas: avg_exit=`4.139749`, hit5=`22.7273`, min_low=`11.881804`

| rank | config | base_n | base_hit5 | base_avg_exit | guard | holdout_n | holdout_hit5 | holdout_avg_exit | holdout_min_low | holdout_gate |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| 1 | prefilter/k10/n2/ev/tail0.85 | 61 | 52.46 | -1.108 | keep_close_failure_prior_ticker_clean_defense_rate_pct_ge_57p5758 | 11 | 72.73 | 2.262 | -10.06 | shadow_risk_review |
| 2 | prefilter/k5/n2/ev_hit10/tail0.85 | 42 | 52.38 | -1.675 | keep_kis_daily_pct_from_52w_high_ge_neg16p2627 | 8 | 75 | 1.361 | -10.06 | shadow_risk_review |
| 3 | prefilter/k10/n2/ev/tail0.8 | 50 | 48 | -1.488 | keep_day_return_pct_le_6p91824 | 10 | 70 | 2.028 | -13.4 | shadow_risk_review |
| 4 | prefilter/k10/n1/ev/tail0.8 | 33 | 57.58 | -0.6136 | keep_kis_financial_roe_le_24p55 | 9 | 77.78 | 1.357 | -13.4 | shadow_risk_review |
| 5 | prefilter/k10/n1/ev/tail0.75 | 29 | 58.62 | -0.3259 | keep_kis_daily_return_20d_pct_ge_neg4p20458 | 8 | 75 | 1.133 | -13.4 | shadow_risk_review |
| 6 | prefilter/k10/n2/ev_hit10/tail0.85 | 51 | 54.9 | -0.6894 | keep__p_hit10_le_0p766799 | 11 | 63.64 | 0.5327 | -11.41 | shadow_risk_review |
| 7 | prefilter/k5/n2/ev/tail0.85 | 43 | 46.51 | -2.289 | keep_kis_daily_pct_from_52w_high_ge_neg13p5424 | 8 | 62.5 | 0.3872 | -10.5 | shadow_risk_review |
| 8 | prefilter/k10/n2/ev/tail0.75 | 40 | 50 | -1.039 | keep_kis_prev_volume_ratio_le_101p671 | 8 | 62.5 | 1.384 | -15.57 | shadow_risk_review |
| 9 | prefilter/k10/n1/ev/tail0.85 | 39 | 56.41 | -0.9345 | keep_kis_financial_roe_le_24p55 | 11 | 72.73 | 0.6192 | -16.17 | shadow_risk_review |
| 10 | prefilter/k10/n2/ev_hit10/tail0.8 | 40 | 50 | -1.049 | keep_kis_financial_roe_le_23p02 | 10 | 60 | 0.1258 | -13.4 | shadow_risk_review |
| 11 | prefilter/k5/n1/ev_hit10/tail0.85 | 32 | 59.38 | -0.7098 | keep_close_failure_prior_market_avg_close_5d_pct_ge_5p59833 | 9 | 66.67 | 0.2718 | -17.94 | shadow_risk_review |
| 12 | prefilter/k5/n2/ev_hit10/tail0.8 | 32 | 50 | -2.281 | keep_close_failure_prior_ticker_clean_defense_rate_pct_ge_44p4444 | 8 | 62.5 | -0.2694 | -13.4 | shadow_risk_review |

### Loss Traits

- `close_failure_prior_ticker_stop5_rate_pct` bad_median=`40.140845` good_median=`31.186869` scaled_delta=`0.623318`
- `close_failure_prior_ticker_avg_mae_5d_pct` bad_median=`-4.83666` good_median=`-4.142767` scaled_delta=`-0.535461`
- `kis_whale_score` bad_median=`78.0` good_median=`63.0` scaled_delta=`0.527616`
- `close_failure_prior_ticker_risk_score` bad_median=`13.183584` good_median=`8.289474` scaled_delta=`0.46575`
- `_p_tail` bad_median=`0.60762` good_median=`0.526111` scaled_delta=`0.381296`
- `kis_financial_roe` bad_median=`13.26` good_median=`8.64` scaled_delta=`0.301314`
- `close_failure_prior_ticker_avg_mfe_5d_pct` bad_median=`12.468005` good_median=`14.486963` scaled_delta=`-0.275104`
- `kis_financial_net_income_margin` bad_median=`15.86` good_median=`73.92` scaled_delta=`-0.265623`
