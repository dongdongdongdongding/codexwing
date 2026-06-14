# KIS Three-Stage Guarded Selection Research

- status: `blocked`
- generated_at: `2026-06-14T09:36:05+00:00`
- date_range: `2026-01-01`..`2026-06-10`
- validation: `Reproduce three-stage walk-forward selections, split selected cases chronologically, learn single-feature keep guards on selected-train rows, evaluate on selected-holdout rows.`
- leakage_control: `Guard feature allow-list excludes realized outcome labels; model probabilities are allowed because they exist at scan time.`

## KOSPI

- source: `runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kospi_20260101_20260610.pkl`
- rows/days: `97638` / `103`
- selected_rows/configs: `924` / `60`
- best_config: pool=`prefilter` pool_k=`10` final_topn=`1` score=`ev` max_tail_prob=`0.8`
- base_metrics: n=`21`, days=`21`, hit5=`57.1429`, hit10=`47.619`, tail=`23.8095`, avg_exit=`-0.262821`, dynamic_exit=`1.634711`, min_low=`-21.860866`
- best_guard: `keep_kis_financial_roe_le_20p58` holdout_gate=`blocked` blockers=`['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'min_low_5d_lt_neg10']`
- holdout_metrics: n=`6`, days=`6`, hit5=`83.3333`, hit10=`100.0`, tail=`16.6667`, avg_exit=`2.167882`, dynamic_exit=`6.318733`, min_low=`-10.056783`
- all_guarded_metrics: n=`15`, days=`15`, hit5=`53.3333`, hit10=`60.0`, tail=`20.0`, avg_exit=`-0.261671`, dynamic_exit=`2.062806`, min_low=`-21.860866`
- holdout_deltas: avg_exit=`3.041971`, hit5=`20.8333`, min_low=`9.157613`

| rank | config | base_n | base_hit5 | base_avg_exit | guard | holdout_n | holdout_hit5 | holdout_avg_exit | holdout_min_low | holdout_gate |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| 1 | prefilter/k10/n1/ev/tail0.8 | 21 | 57.14 | -0.2628 | keep_kis_financial_roe_le_20p58 | 6 | 83.33 | 2.168 | -10.06 | blocked |
| 2 | prefilter/k5/n2/ev/tail0.85 | 24 | 62.5 | 0.3045 | keep_kis_daily_pct_from_52w_high_ge_neg17p8456 | 6 | 83.33 | 2.168 | -10.06 | blocked |
| 3 | prefilter/k5/n1/ev/tail0.85 | 22 | 63.64 | 0.5394 | keep_kis_prefilter_rank_fluctuation_le_15p6 | 6 | 83.33 | 2.168 | -10.06 | blocked |
| 4 | prefilter/k5/n1/success_tail/tail0.85 | 20 | 60 | 0.1332 | keep__rank_score_le_0p0581672 | 6 | 83.33 | 2.168 | -10.06 | blocked |
| 5 | prefilter/k10/n2/ev_hit10/tail0.8 | 26 | 50 | -1.444 | keep_close_failure_prior_ticker_stop5_rate_pct_le_31p4286 | 4 | 75 | 0.9511 | -10.06 | blocked |
| 6 | prefilter/k10/n2/ev/tail0.85 | 27 | 40.74 | -2.892 | keep__p_hit10_le_0p758917 | 4 | 75 | 0.9511 | -10.06 | blocked |
| 7 | prefilter/k10/n2/ev_hit10/tail0.85 | 28 | 46.43 | -1.886 | keep_close_failure_prior_ticker_stop5_rate_pct_le_30p7692 | 4 | 75 | 0.9511 | -10.06 | blocked |
| 8 | prefilter/k10/n2/success_tail/tail0.85 | 26 | 38.46 | -2.946 | keep_close_failure_prior_ticker_stop5_rate_pct_le_31p033 | 4 | 75 | 0.9511 | -10.06 | blocked |
| 9 | prefilter/k10/n2/success_tail/tail0.8 | 24 | 37.5 | -2.967 | keep_close_failure_prior_ticker_stop5_rate_pct_le_30p9011 | 4 | 75 | 0.9511 | -10.06 | blocked |
| 10 | prefilter/k10/n2/ev/tail0.8 | 24 | 41.67 | -2.612 | keep__p_hit10_le_0p763676 | 4 | 75 | 0.9511 | -10.06 | blocked |
| 11 | prefilter/k10/n1/ev/tail0.85 | 20 | 55 | -0.506 | keep_kis_financial_roe_le_20p58 | 4 | 75 | 0.9511 | -10.06 | blocked |
| 12 | prefilter/k10/n1/ev_hit10/tail0.75 | 17 | 64.71 | 0.5372 | keep_kis_whale_flow_10d_ge_neg45012 | 3 | 100 | 4.601 | -8.546 | blocked |

### Loss Traits

- `close_failure_prior_market_avg_mfe_5d_pct` bad_median=`14.276272` good_median=`14.483276` scaled_delta=`-0.91787`
- `close_failure_prior_theme_stop5_rate_pct` bad_median=`40.112994` good_median=`32.06725` scaled_delta=`0.669324`
- `close_failure_prior_kis_theme_stop5_rate_pct` bad_median=`40.112994` good_median=`32.06725` scaled_delta=`0.669324`
- `close_failure_prior_kis_sector_stop5_rate_pct` bad_median=`40.112994` good_median=`32.06725` scaled_delta=`0.669324`
- `kis_financial_revenue_growth_rate` bad_median=`3.45` good_median=`22.485` scaled_delta=`-0.657567`
- `kis_daily_return_20d_pct` bad_median=`2.298851` good_median=`10.401432` scaled_delta=`-0.496216`
- `kis_prefilter_rank_fluctuation` bad_median=`27.0` good_median=`21.0` scaled_delta=`0.47289`
- `kis_financial_net_income_margin` bad_median=`0.0` good_median=`52.395` scaled_delta=`-0.454434`

