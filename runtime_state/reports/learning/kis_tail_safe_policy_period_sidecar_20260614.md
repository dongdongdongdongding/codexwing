# KIS Tail-Safe Policy Search

- status: `blocked`
- generated_at: `2026-06-14T09:28:24+00:00`
- date_range: `2026-01-01`..`2026-06-10`
- success_label: `buy_premium_target_hit_5d == true AND buy_premium_min_low_return_5d_pct >= -10`
- validation: `walk-forward adaptive rule selection: train window chooses rule, next test window evaluates it`

## KOSPI

- source: `runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kospi_20260101_20260610.pkl`
- rows/days: `97638` / `103`
- windows: `6`
- best: `volume_leadership_defense` topN=`1` status=`blocked`
- blockers: `['hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`
- metrics: n=`51`, active_days=`51`, hit5_dd10=`17.6471`, target_before_stop=`19.6078`, win5=`19.6078`, hit10=`7.8431`, stop5=`21.5686`, bad_path=`78.4314`, avg5=`-3.186194`, avg_exit=`-2.89715`, min_low=`-15.738485`

| rank | score_mode | topN | gate | n | days | hit5_dd10 | hit10 | stop5 | bad_path | avg_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | volume_leadership_defense | 1 | blocked | 51 | 51 | 17.65 | 7.843 | 21.57 | 78.43 | -2.897 | -15.74 |
| 2 | risk_adjusted_momentum | 2 | blocked | 97 | 53 | 22.68 | 11.34 | 21.65 | 72.16 | -2.956 | -18.73 |
| 3 | volume_leadership_defense | 2 | blocked | 72 | 44 | 12.5 | 2.778 | 22.22 | 88.89 | -3.919 | -17.98 |
| 4 | moderated_momentum | 1 | blocked | 45 | 45 | 15.56 | 13.33 | 26.67 | 82.22 | -4.039 | -18.73 |
| 5 | moderated_momentum | 3 | blocked | 159 | 57 | 25.79 | 14.47 | 22.01 | 71.07 | -2.557 | -25.2 |
| 6 | risk_adjusted_momentum | 3 | blocked | 123 | 49 | 22.76 | 13.82 | 18.7 | 70.73 | -2.546 | -25.02 |
| 7 | risk_adjusted_momentum | 1 | blocked | 54 | 54 | 25.93 | 14.81 | 31.48 | 68.52 | -3.289 | -25.2 |
| 8 | volume_leadership_defense | 3 | blocked | 130 | 52 | 10.77 | 4.615 | 25.38 | 87.69 | -4.122 | -24.11 |

### Latest Recommended Rule

- rule: `r5[-8,5]|loc>=30|vol>=0.9|tickerRisk<=30|themeStop<=30|tickerMae>=-8|from52w>=-20`
- train_objective: `-92.185957`
- train_metrics: `{"n": 87, "active_days": 87, "active_runs": 87, "hit5_dd10_5d_pct": 33.3333, "target_before_stop_5d_pct": 34.4828, "win_5d_pct": 34.4828, "hit10_5d_pct": 16.092, "stop5_pct": 9.1954, "stop_before_target_5d_pct": 8.046, "bad_path_pct": 60.9195, "avg_5d_pct": -0.446175, "median_5d_pct": -1.256985, "min_5d_pct": -14.66565, "max_5d_pct": 34.666373, "avg_mfe_5d_pct": 4.38672, "avg_mae_5d_pct": -5.46414, "min_min_low_5d_pct": -15.406767, "max_mfe_5d_pct": 42.264281, "avg_ordered_exit_5d_pct": -0.54428, "min_ordered_exit_5d_pct": -10.0, "buy_premium_pct": 2.0}`

## KOSDAQ

- source: `runtime_state/reports/learning/kis_historical_universe_fullrank_period_sidecar_augmented_prepared_kosdaq_20260101_20260610.pkl`
- rows/days: `186203` / `103`
- windows: `6`
- best: `volume_leadership_defense` topN=`2` status=`blocked`
- blockers: `['hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
- metrics: n=`84`, active_days=`46`, hit5_dd10=`22.619`, target_before_stop=`22.619`, win5=`22.619`, hit10=`13.0952`, stop5=`14.2857`, bad_path=`69.0476`, avg5=`-0.591063`, avg_exit=`-2.114004`, min_low=`-16.102893`

| rank | score_mode | topN | gate | n | days | hit5_dd10 | hit10 | stop5 | bad_path | avg_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | volume_leadership_defense | 2 | blocked | 84 | 46 | 22.62 | 13.1 | 14.29 | 69.05 | -2.114 | -16.1 |
| 2 | volume_leadership_defense | 1 | blocked | 50 | 50 | 22 | 10 | 16 | 74 | -2.411 | -18.92 |
| 3 | moderated_momentum | 1 | blocked | 52 | 52 | 23.08 | 13.46 | 23.08 | 67.31 | -2.594 | -24.32 |
| 4 | volume_leadership_defense | 3 | blocked | 116 | 42 | 15.52 | 11.21 | 25.86 | 75.86 | -3.522 | -25.74 |
| 5 | risk_adjusted_momentum | 1 | blocked | 57 | 57 | 19.3 | 8.772 | 19.3 | 77.19 | -2.784 | -29.73 |
| 6 | risk_adjusted_momentum | 2 | blocked | 98 | 50 | 18.37 | 11.22 | 24.49 | 76.53 | -3.21 | -29.73 |
| 7 | risk_adjusted_momentum | 3 | blocked | 116 | 42 | 18.1 | 11.21 | 27.59 | 76.72 | -3.482 | -32.4 |
| 8 | moderated_momentum | 2 | blocked | 73 | 41 | 15.07 | 8.219 | 27.4 | 76.71 | -3.746 | -38.02 |

### Latest Recommended Rule

- rule: `r5[-5,12]|loc>=70|vol>=1.5|tickerRisk<=999|themeStop<=45|tickerMae>=-5.5|from52w>=-20`
- train_objective: `26.168461`
- train_metrics: `{"n": 159, "active_days": 82, "active_runs": 82, "hit5_dd10_5d_pct": 45.283, "target_before_stop_5d_pct": 45.9119, "win_5d_pct": 47.1698, "hit10_5d_pct": 27.044, "stop5_pct": 11.3208, "stop_before_target_5d_pct": 10.6918, "bad_path_pct": 50.3145, "avg_5d_pct": 1.931372, "median_5d_pct": 0.066167, "min_5d_pct": -18.407102, "max_5d_pct": 46.344252, "avg_mfe_5d_pct": 8.76467, "avg_mae_5d_pct": -5.967277, "min_min_low_5d_pct": -20.894284, "max_mfe_5d_pct": 58.033363, "avg_ordered_exit_5d_pct": -0.097347, "min_ordered_exit_5d_pct": -10.0, "buy_premium_pct": 2.0}`

