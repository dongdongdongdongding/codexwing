# KIS Tail-Safe Policy Search

- status: `blocked`
- generated_at: `2026-06-12T03:51:42+00:00`
- date_range: `2026-01-01`..`2026-06-10`
- success_label: `buy_premium_target_hit_5d == true AND buy_premium_min_low_return_5d_pct >= -10`
- validation: `walk-forward adaptive rule selection: train window chooses rule, next test window evaluates it`

## KOSPI

- source: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/kis_historical_universe_prepared_kospi_20260101_20260610.pkl`
- rows/days: `97638` / `103`
- windows: `4`
- best: `moderated_momentum` topN=`3` status=`blocked`
- blockers: `['hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`
- metrics: n=`144`, active_days=`48`, hit5_dd10=`27.0833`, target_before_stop=`30.5556`, win5=`31.25`, hit10=`18.75`, stop5=`24.3056`, bad_path=`69.4444`, avg5=`-1.632774`, avg_exit=`-2.415479`, min_low=`-18.779401`

| rank | score_mode | topN | gate | n | days | hit5_dd10 | hit10 | stop5 | bad_path | avg_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | moderated_momentum | 3 | blocked | 144 | 48 | 27.08 | 18.75 | 24.31 | 69.44 | -2.415 | -18.78 |
| 2 | moderated_momentum | 2 | blocked | 96 | 48 | 23.96 | 14.58 | 22.92 | 71.88 | -2.723 | -18.78 |
| 3 | moderated_momentum | 1 | blocked | 39 | 39 | 23.08 | 17.95 | 28.21 | 74.36 | -3.312 | -18.73 |
| 4 | risk_adjusted_momentum | 1 | blocked | 47 | 47 | 17.02 | 4.255 | 23.4 | 74.47 | -3.301 | -18.13 |
| 5 | volume_leadership_defense | 1 | blocked | 32 | 32 | 21.88 | 9.375 | 12.5 | 78.12 | -2.108 | -21.25 |
| 6 | volume_leadership_defense | 2 | blocked | 92 | 47 | 19.57 | 9.783 | 18.48 | 81.52 | -3.054 | -24.26 |
| 7 | volume_leadership_defense | 3 | blocked | 105 | 40 | 15.24 | 9.524 | 19.05 | 74.29 | -2.925 | -24.11 |
| 8 | risk_adjusted_momentum | 3 | blocked | 137 | 47 | 21.17 | 12.41 | 24.82 | 74.45 | -3.142 | -25.02 |

### Latest Recommended Rule

- rule: `r5[0,16]|loc>=70|vol>=0|tickerRisk<=999|themeStop<=999|tickerMae>=-5.5|from52w>=-20`
- train_objective: `-185.749051`
- train_metrics: `{"n": 252, "active_days": 84, "active_runs": 84, "hit5_dd10_5d_pct": 28.5714, "target_before_stop_5d_pct": 29.3651, "win_5d_pct": 29.3651, "hit10_5d_pct": 13.4921, "stop5_pct": 9.5238, "stop_before_target_5d_pct": 8.7302, "bad_path_pct": 55.9524, "avg_5d_pct": -0.142688, "median_5d_pct": -0.8841, "min_5d_pct": -14.66565, "max_5d_pct": 27.498804, "avg_mfe_5d_pct": 3.990898, "avg_mae_5d_pct": -5.513565, "min_min_low_5d_pct": -18.511038, "max_mfe_5d_pct": 33.621977, "avg_ordered_exit_5d_pct": -0.748339, "min_ordered_exit_5d_pct": -10.0, "buy_premium_pct": 2.0}`

## KOSDAQ

- source: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/kis_historical_universe_prepared_kosdaq_20260101_20260610.pkl`
- rows/days: `186203` / `103`
- windows: `4`
- best: `risk_adjusted_momentum` topN=`3` status=`blocked`
- blockers: `['hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`
- metrics: n=`91`, active_days=`33`, hit5_dd10=`15.3846`, target_before_stop=`15.3846`, win5=`15.3846`, hit10=`7.6923`, stop5=`12.0879`, bad_path=`71.4286`, avg5=`-1.481812`, avg_exit=`-2.234024`, min_low=`-13.682864`

| rank | score_mode | topN | gate | n | days | hit5_dd10 | hit10 | stop5 | bad_path | avg_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | risk_adjusted_momentum | 3 | blocked | 91 | 33 | 15.38 | 7.692 | 12.09 | 71.43 | -2.234 | -13.68 |
| 2 | risk_adjusted_momentum | 1 | blocked | 33 | 33 | 15.15 | 3.03 | 15.15 | 72.73 | -2.787 | -12.91 |
| 3 | volume_leadership_defense | 2 | blocked | 44 | 24 | 6.818 | 0 | 9.091 | 72.73 | -2.84 | -12.33 |
| 4 | moderated_momentum | 2 | blocked | 44 | 24 | 6.818 | 0 | 9.091 | 72.73 | -3.023 | -12.33 |
| 5 | volume_leadership_defense | 1 | blocked | 39 | 39 | 15.38 | 5.128 | 17.95 | 79.49 | -3.226 | -12.91 |
| 6 | risk_adjusted_momentum | 2 | blocked | 44 | 24 | 6.818 | 0 | 9.091 | 72.73 | -2.84 | -13.68 |
| 7 | volume_leadership_defense | 3 | blocked | 63 | 26 | 12.7 | 4.762 | 12.7 | 69.84 | -2.515 | -17.09 |
| 8 | moderated_momentum | 1 | blocked | 40 | 40 | 17.5 | 7.5 | 25 | 67.5 | -3.119 | -24.32 |

### Latest Recommended Rule

- rule: `r5[-10,6]|loc>=70|vol>=1.5|tickerRisk<=30|themeStop<=30|tickerMae>=-8|from52w>=-45`
- train_objective: `-116.761715`
- train_metrics: `{"n": 143, "active_days": 59, "active_runs": 59, "hit5_dd10_5d_pct": 30.7692, "target_before_stop_5d_pct": 31.4685, "win_5d_pct": 31.4685, "hit10_5d_pct": 17.4825, "stop5_pct": 9.7902, "stop_before_target_5d_pct": 9.0909, "bad_path_pct": 55.2448, "avg_5d_pct": 0.603715, "median_5d_pct": -0.519031, "min_5d_pct": -13.682864, "max_5d_pct": 45.965612, "avg_mfe_5d_pct": 5.957427, "avg_mae_5d_pct": -5.27224, "min_min_low_5d_pct": -16.330168, "max_mfe_5d_pct": 49.190111, "avg_ordered_exit_5d_pct": -0.685465, "min_ordered_exit_5d_pct": -10.0, "buy_premium_pct": 2.0}`

