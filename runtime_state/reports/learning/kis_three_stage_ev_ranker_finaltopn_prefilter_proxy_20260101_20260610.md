# KIS Three-Stage EV Ranker Research

- status: `no_improvement`
- generated_at: `2026-06-12T19:54:23+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `hit5_dd10_5d_pct`

## KOSPI

- rows/days: `97421` / `103`
- evidence_gate: min_n=`30` min_active_days=`15` eligible_configs=`30`
- gate_counts: production_ready=`0` shadow_display_allowed=`0`
- unconstrained_best: n=`5`, active_days=`5`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`prefilter` pool_k=`20` final_topn=`2` score=`ev` max_tail_prob=`None` gate=`blocked` production=`False`
- avg_exit improvement: `0.700469` -> `-0.618404` (delta `-1.318873`)
- dynamic_exit: `1.249479` (fixed 대비 delta `1.867883`)
- hit5_dd10: `47.619` -> `57.5` (delta `9.881`)
- best metrics: n=`40`, active_days=`21`, hit5_dd10=`57.5`, hit10=`40.0`, safe_hit10=`37.5`, tail=`27.5`, bad_path=`60.0`, avg_exit=`-0.618404`, dynamic_exit=`1.249479`, min_low=`-27.443637`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | prefilter | 20 | 2 | ev | - | 40 | 21 | 43.75 | 57.5 | 40 | 37.5 | 27.5 | 60 | -0.6184 | 1.249 | -27.44 |
| 2 | blocked | prefilter | 20 | 2 | success_tail | - | 40 | 21 | 43.75 | 57.5 | 40 | 37.5 | 27.5 | 60 | -0.6184 | 1.249 | -27.44 |
| 3 | blocked | prefilter | 10 | 2 | success_tail | - | 31 | 19 | 39.58 | 54.84 | 45.16 | 41.94 | 29.03 | 51.61 | -0.6802 | 1.409 | -24.58 |
| 4 | blocked | prefilter | 20 | 3 | success_tail | - | 43 | 18 | 37.5 | 51.16 | 37.21 | 34.88 | 37.21 | 65.12 | -1.634 | 0.1036 | -27.44 |
| 5 | blocked | prefilter | 10 | 2 | ev_hit10 | - | 32 | 19 | 39.58 | 50 | 43.75 | 34.38 | 40.62 | 56.25 | -2.11 | -0.3975 | -24.58 |
| 6 | blocked | prefilter | 100 | 2 | ev_hit10 | - | 32 | 20 | 41.67 | 50 | 43.75 | 34.38 | 40.62 | 65.62 | -2.135 | -0.4226 | -21.3 |
| 7 | blocked | prefilter | 20 | 3 | ev | - | 43 | 17 | 35.42 | 48.84 | 37.21 | 34.88 | 39.53 | 67.44 | -1.885 | -0.1476 | -27.44 |
| 8 | blocked | prefilter | 20 | 3 | ev_hit10 | - | 43 | 19 | 39.58 | 46.51 | 39.53 | 32.56 | 44.19 | 72.09 | -2.606 | -0.9838 | -27.44 |
| 9 | blocked | prefilter | 10 | 3 | ev | - | 44 | 22 | 45.83 | 45.45 | 45.45 | 36.36 | 38.64 | 59.09 | -2.073 | -0.2619 | -26.61 |
| 10 | blocked | prefilter | 10 | 3 | ev_hit10 | - | 36 | 15 | 31.25 | 44.44 | 52.78 | 38.89 | 47.22 | 58.33 | -2.779 | -0.842 | -26.61 |

## KOSDAQ

- rows/days: `184794` / `103`
- evidence_gate: min_n=`30` min_active_days=`15` eligible_configs=`30`
- gate_counts: production_ready=`0` shadow_display_allowed=`0`
- unconstrained_best: n=`7`, active_days=`7`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`composite` pool_k=`50` final_topn=`2` score=`ev_hit10` max_tail_prob=`None` gate=`blocked` production=`False`
- avg_exit improvement: `-0.277837` -> `-0.85266` (delta `-0.574823`)
- dynamic_exit: `1.529568` (fixed 대비 delta `2.382228`)
- hit5_dd10: `48.0` -> `54.3478` (delta `6.3478`)
- best metrics: n=`46`, active_days=`24`, hit5_dd10=`54.3478`, hit10=`50.0`, safe_hit10=`47.8261`, tail=`28.2609`, bad_path=`50.0`, avg_exit=`-0.85266`, dynamic_exit=`1.529568`, min_low=`-32.404541`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | composite | 50 | 2 | ev_hit10 | - | 46 | 24 | 50 | 54.35 | 50 | 47.83 | 28.26 | 50 | -0.8527 | 1.53 | -32.4 |
| 2 | blocked | composite | 50 | 3 | ev_hit10 | - | 87 | 32 | 66.67 | 54.02 | 44.83 | 42.53 | 24.14 | 45.98 | -0.2957 | 1.823 | -32.4 |
| 3 | blocked | composite | 50 | 3 | success_tail | - | 89 | 32 | 66.67 | 50.56 | 39.33 | 35.96 | 23.6 | 49.44 | -0.4319 | 1.359 | -32.4 |
| 4 | blocked | composite | 50 | 1 | success_tail | - | 30 | 30 | 62.5 | 50 | 46.67 | 46.67 | 20 | 50 | -0.7489 | 1.576 | -24.4 |
| 5 | blocked | composite | 20 | 1 | ev_hit10 | - | 30 | 30 | 62.5 | 50 | 46.67 | 43.33 | 36.67 | 53.33 | -1.863 | 0.2959 | -24.19 |
| 6 | blocked | prefilter | 100 | 2 | ev_hit10 | - | 35 | 21 | 43.75 | 48.57 | 54.29 | 45.71 | 34.29 | 54.29 | -1.925 | 0.3515 | -22.77 |
| 7 | blocked | prefilter | 50 | 3 | ev_hit10 | - | 59 | 23 | 47.92 | 47.46 | 44.07 | 38.98 | 47.46 | 61.02 | -2.615 | -0.6736 | -28.39 |
| 8 | blocked | prefilter | 100 | 3 | ev_hit10 | - | 49 | 22 | 45.83 | 46.94 | 55.1 | 42.86 | 36.73 | 57.14 | -2.208 | -0.07339 | -24.11 |
| 9 | blocked | composite | 10 | 3 | success_tail | - | 49 | 25 | 52.08 | 46.94 | 48.98 | 38.78 | 44.9 | 59.18 | -2.675 | -0.7435 | -37.44 |
| 10 | blocked | composite | 20 | 2 | ev | - | 43 | 23 | 47.92 | 46.51 | 37.21 | 37.21 | 39.53 | 58.14 | -2.154 | -0.3008 | -24.19 |

