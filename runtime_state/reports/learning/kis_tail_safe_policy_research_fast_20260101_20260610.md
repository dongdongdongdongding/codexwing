# KIS Tail-Safe Policy Search

- status: `blocked`
- generated_at: `2026-06-12T08:03:33+00:00`
- date_range: `2026-01-01`..`2026-06-10`
- success_label: `buy_premium_target_hit_5d == true AND buy_premium_min_low_return_5d_pct >= -10`
- validation: `walk-forward adaptive rule selection: train window chooses rule, next test window evaluates it`

## KOSPI

- source: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/kis_historical_universe_prepared_kospi_20260101_20260610.pkl`
- rows/days: `97638` / `103`
- windows: `6`
- best: `risk_adjusted_momentum` topN=`2` status=`blocked`
- blockers: `['hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`
- metrics: n=`87`, active_days=`44`, hit5_dd10=`32.1839`, target_before_stop=`33.3333`, win5=`33.3333`, hit10=`19.5402`, stop5=`22.9885`, bad_path=`64.3678`, avg5=`-0.643737`, avg_exit=`-1.986569`, min_low=`-19.720466`

| rank | score_mode | topN | gate | n | days | hit5_dd10 | hit10 | stop5 | bad_path | avg_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | risk_adjusted_momentum | 2 | blocked | 87 | 44 | 32.18 | 19.54 | 22.99 | 64.37 | -1.987 | -19.72 |
| 2 | volume_leadership_defense | 1 | blocked | 31 | 31 | 29.03 | 9.677 | 12.9 | 77.42 | -1.812 | -21.25 |
| 3 | risk_adjusted_momentum | 1 | blocked | 40 | 40 | 25 | 12.5 | 30 | 70 | -3.288 | -19.72 |
| 4 | volume_leadership_defense | 3 | blocked | 100 | 39 | 20 | 13 | 19 | 72 | -2.274 | -21.25 |
| 5 | moderated_momentum | 1 | blocked | 35 | 35 | 20 | 17.14 | 28.57 | 80 | -3.895 | -18.73 |
| 6 | volume_leadership_defense | 2 | blocked | 69 | 36 | 21.74 | 13.04 | 17.39 | 78.26 | -2.631 | -21.31 |
| 7 | moderated_momentum | 3 | blocked | 127 | 46 | 19.68 | 9.449 | 23.62 | 70.87 | -2.746 | -22.11 |
| 8 | volume_leadership_defense | 5 | blocked | 128 | 32 | 21.88 | 13.28 | 18.75 | 73.44 | -2.622 | -25.02 |

### Latest Recommended Rule

- rule: `r5[-8,5]|loc>=50|vol>=0.9|tickerRisk<=999|themeStop<=999|tickerMae>=-5.5|from52w>=-20`
- train_objective: `-168.537579`
- train_metrics: `{"n": 178, "active_days": 89, "active_runs": 89, "hit5_dd10_5d_pct": 25.8427, "target_before_stop_5d_pct": 25.8427, "win_5d_pct": 25.8427, "hit10_5d_pct": 8.9888, "stop5_pct": 11.7978, "stop_before_target_5d_pct": 11.7978, "bad_path_pct": 60.6742, "avg_5d_pct": -0.955554, "median_5d_pct": -1.404075, "min_5d_pct": -14.66565, "max_5d_pct": 34.666373, "avg_mfe_5d_pct": 3.491896, "avg_mae_5d_pct": -5.842113, "min_min_low_5d_pct": -16.436373, "max_mfe_5d_pct": 42.264281, "avg_ordered_exit_5d_pct": -1.288797, "min_ordered_exit_5d_pct": -10.0, "buy_premium_pct": 2.0}`

## KOSDAQ

- source: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/kis_historical_universe_prepared_kosdaq_20260101_20260610.pkl`
- rows/days: `186203` / `103`
- windows: `6`
- best: `moderated_momentum` topN=`1` status=`blocked`
- blockers: `['n_lt_45', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
- metrics: n=`24`, active_days=`24`, hit5_dd10=`12.5`, target_before_stop=`12.5`, win5=`12.5`, hit10=`0.0`, stop5=`16.6667`, bad_path=`70.8333`, avg5=`-2.176368`, avg_exit=`-2.718803`, min_low=`-12.697575`

| rank | score_mode | topN | gate | n | days | hit5_dd10 | hit10 | stop5 | bad_path | avg_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | moderated_momentum | 1 | blocked | 24 | 24 | 12.5 | 0 | 16.67 | 70.83 | -2.719 | -12.7 |
| 2 | moderated_momentum | 2 | blocked | 44 | 24 | 6.818 | 0 | 9.091 | 72.73 | -3.023 | -12.33 |
| 3 | volume_leadership_defense | 5 | blocked | 71 | 24 | 7.042 | 1.409 | 9.859 | 71.83 | -2.64 | -13.68 |
| 4 | risk_adjusted_momentum | 2 | blocked | 49 | 27 | 10.2 | 2.041 | 14.29 | 75.51 | -3.045 | -13.97 |
| 5 | volume_leadership_defense | 2 | blocked | 48 | 26 | 8.333 | 4.167 | 14.58 | 72.92 | -3.259 | -13.97 |
| 6 | volume_leadership_defense | 1 | blocked | 36 | 36 | 19.44 | 8.333 | 16.67 | 75 | -2.211 | -18.88 |
| 7 | risk_adjusted_momentum | 3 | blocked | 87 | 31 | 14.94 | 8.046 | 18.39 | 78.16 | -2.962 | -17.62 |
| 8 | volume_leadership_defense | 3 | blocked | 69 | 27 | 13.04 | 5.797 | 17.39 | 73.91 | -2.982 | -19.76 |

### Latest Recommended Rule

- rule: `r5[-10,6]|loc>=70|vol>=1.5|tickerRisk<=30|themeStop<=30|tickerMae>=-999|from52w>=-45`
- train_objective: `-66.820443`
- train_metrics: `{"n": 63, "active_days": 63, "active_runs": 63, "hit5_dd10_5d_pct": 39.6825, "target_before_stop_5d_pct": 39.6825, "win_5d_pct": 39.6825, "hit10_5d_pct": 17.4603, "stop5_pct": 12.6984, "stop_before_target_5d_pct": 12.6984, "bad_path_pct": 47.619, "avg_5d_pct": 2.15109, "median_5d_pct": 0.709545, "min_5d_pct": -12.510459, "max_5d_pct": 45.050791, "avg_mfe_5d_pct": 6.68656, "avg_mae_5d_pct": -5.287761, "min_min_low_5d_pct": -16.330168, "max_mfe_5d_pct": 49.190111, "avg_ordered_exit_5d_pct": -0.111416, "min_ordered_exit_5d_pct": -10.0, "buy_premium_pct": 2.0}`

