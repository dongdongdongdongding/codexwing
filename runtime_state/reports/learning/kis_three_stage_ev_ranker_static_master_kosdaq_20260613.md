# KIS Three-Stage EV Ranker Research

- status: `improved_shadow_research`
- generated_at: `2026-06-13T03:41:27+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `avg_dynamic_exit_5d_pct`

## KOSDAQ

- rows/days: `184794` / `103`
- evidence_gate: min_n=`20` min_active_days=`12` eligible_configs=`30`
- gate_counts: production_ready=`0` shadow_display_allowed=`4`
- unconstrained_best: n=`4`, active_days=`2`, hit5_dd10=`75.0`, tail=`25.0`, avg_exit=`0.951094`
- best_config: pool=`prefilter` pool_k=`50` final_topn=`1` score=`success_tail` max_tail_prob=`None` gate=`blocked` production=`False`
- avg_exit improvement: `-0.981074` -> `0.034024` (delta `1.015098`)
- dynamic_exit: `2.416252` (fixed 대비 delta `2.382228`)
- hit5_dd10: `60.4167` -> `65.2174` (delta `4.8007`)
- best metrics: n=`23`, active_days=`23`, hit5_dd10=`65.2174`, hit10=`52.1739`, safe_hit10=`47.8261`, tail=`30.4348`, bad_path=`39.1304`, avg_exit=`0.034024`, dynamic_exit=`2.416252`, min_low=`-28.390711`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | prefilter | 50 | 1 | success_tail | - | 23 | 23 | 47.92 | 65.22 | 52.17 | 47.83 | 30.43 | 39.13 | 0.03402 | 2.416 | -28.39 |
| 2 | blocked | composite | 50 | 1 | success_tail | - | 37 | 37 | 77.08 | 54.05 | 37.84 | 37.84 | 16.22 | 45.95 | 0.06545 | 1.95 | -24.52 |
| 3 | blocked | prefilter | 50 | 1 | ev | - | 23 | 23 | 47.92 | 60.87 | 47.83 | 43.48 | 34.78 | 43.48 | -0.6008 | 1.565 | -28.39 |
| 4 | shadow_risk_review | composite | 50 | 1 | ev | - | 25 | 25 | 52.08 | 52 | 36 | 36 | 24 | 52 | -0.7076 | 1.086 | -17.38 |
| 5 | blocked | composite | 50 | 2 | success_tail | - | 42 | 22 | 45.83 | 47.62 | 35.71 | 35.71 | 23.81 | 47.62 | -0.7338 | 1.045 | -32.4 |
| 6 | blocked | day_return | 5 | 1 | ev_hit10 | - | 37 | 37 | 77.08 | 54.05 | 81.08 | 54.05 | 40.54 | 51.35 | -1.673 | 1.02 | -37.33 |
| 7 | blocked | composite | 50 | 1 | ev_hit10 | - | 28 | 28 | 58.33 | 46.43 | 35.71 | 35.71 | 21.43 | 57.14 | -0.79 | 0.9889 | -24.52 |
| 8 | blocked | composite | 50 | 1 | success_tail | 0.5 | 29 | 29 | 60.42 | 44.83 | 37.93 | 37.93 | 20.69 | 55.17 | -0.9885 | 0.9008 | -24.52 |
| 9 | blocked | composite | 50 | 1 | success_tail | 0.65 | 29 | 29 | 60.42 | 44.83 | 37.93 | 37.93 | 20.69 | 55.17 | -0.9885 | 0.9008 | -24.52 |
| 10 | blocked | composite | 50 | 2 | ev | - | 44 | 24 | 50 | 47.73 | 36.36 | 34.09 | 25 | 50 | -0.8077 | 0.8904 | -32.4 |

