# KIS Three-Stage EV Ranker Research

- status: `improved_shadow_research`
- generated_at: `2026-06-14T09:03:53+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `avg_dynamic_exit_5d_pct`

## KOSDAQ

- rows/days: `186203` / `103`
- evidence_gate: min_n=`1` min_active_days=`1` eligible_configs=`20`
- gate_counts: production_ready=`0` shadow_display_allowed=`6`
- unconstrained_best: n=`2`, active_days=`2`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`day_return` pool_k=`5` final_topn=`1` score=`ev` max_tail_prob=`0.4` gate=`blocked` production=`False`
- avg_exit improvement: `-0.277837` -> `4.601458` (delta `4.879295`)
- dynamic_exit: `9.58248` (fixed 대비 delta `4.981022`)
- hit5_dd10: `48.0` -> `100.0` (delta `52.0`)
- best metrics: n=`2`, active_days=`2`, hit5_dd10=`100.0`, hit10=`100.0`, safe_hit10=`100.0`, tail=`0.0`, bad_path=`0.0`, avg_exit=`4.601458`, dynamic_exit=`9.58248`, min_low=`17.538126`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | day_return | 5 | 1 | ev | 0.4 | 2 | 2 | 4.167 | 100 | 100 | 100 | 0 | 0 | 4.601 | 9.582 | 17.54 |
| 2 | blocked | day_return | 5 | 1 | success_tail | 0.4 | 2 | 2 | 4.167 | 100 | 100 | 100 | 0 | 0 | 4.601 | 9.582 | 17.54 |
| 3 | blocked | day_return | 5 | 1 | ev_hit10 | 0.4 | 2 | 2 | 4.167 | 100 | 100 | 100 | 0 | 0 | 4.601 | 9.582 | 17.54 |
| 4 | blocked | day_return | 5 | 1 | ev | 0.6 | 11 | 11 | 22.92 | 72.73 | 81.82 | 72.73 | 27.27 | 36.36 | 0.6192 | 4.242 | -37.33 |
| 5 | blocked | day_return | 5 | 1 | success_tail | 0.6 | 13 | 13 | 27.08 | 69.23 | 84.62 | 69.23 | 30.77 | 38.46 | 0.1087 | 3.557 | -37.33 |
| 6 | blocked | day_return | 5 | 1 | ev_hit10 | 0.6 | 13 | 13 | 27.08 | 69.23 | 84.62 | 69.23 | 30.77 | 38.46 | 0.1087 | 3.557 | -37.33 |
| 7 | shadow_risk_review | prefilter | 50 | 1 | success_tail | 0.3 | 9 | 9 | 18.75 | 66.67 | 55.56 | 55.56 | 22.22 | 44.44 | 0.5635 | 3.331 | -17.96 |
| 8 | blocked | prefilter | 50 | 1 | ev_hit10 | 0.3 | 7 | 7 | 14.58 | 71.43 | 57.14 | 57.14 | 28.57 | 42.86 | 0.4296 | 3.276 | -17.96 |
| 9 | blocked | day_return | 5 | 1 | success_tail | 0.75 | 23 | 23 | 47.92 | 60.87 | 78.26 | 60.87 | 30.43 | 43.48 | -0.4131 | 2.619 | -37.33 |
| 10 | blocked | day_return | 5 | 1 | ev | 0.7 | 14 | 14 | 29.17 | 64.29 | 78.57 | 64.29 | 35.71 | 42.86 | -0.6133 | 2.589 | -37.33 |

