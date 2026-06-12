# KIS Three-Stage EV Ranker Research

- status: `no_improvement`
- generated_at: `2026-06-12T18:03:14+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `hit5_dd10_5d_pct`

## KOSPI

- rows/days: `97421` / `103`
- evidence_gate: min_n=`15` min_active_days=`15` eligible_configs=`39`
- unconstrained_best: n=`4`, active_days=`4`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`prefilter` pool_k=`20` score=`ev` max_tail_prob=`None`
- avg_exit improvement: `0.700469` -> `-0.53572` (delta `-1.236189`)
- dynamic_exit: `1.678068` (fixed 대비 delta `2.213788`)
- hit5_dd10: `47.619` -> `55.5556` (delta `7.9366`)
- best metrics: n=`18`, active_days=`18`, hit5_dd10=`55.5556`, hit10=`44.4444`, safe_hit10=`44.4444`, tail=`27.7778`, bad_path=`66.6667`, avg_exit=`-0.53572`, dynamic_exit=`1.678068`, min_low=`-27.443637`

| rank | pool | pool_k | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | prefilter | 20 | ev | - | 18 | 18 | 45 | 55.56 | 44.44 | 44.44 | 27.78 | 66.67 | -0.5357 | 1.678 | -27.44 |
| 2 | prefilter | 20 | success_tail | - | 18 | 18 | 45 | 55.56 | 44.44 | 44.44 | 27.78 | 66.67 | -0.5357 | 1.678 | -27.44 |
| 3 | prefilter | 20 | ev_hit10 | - | 18 | 18 | 45 | 55.56 | 44.44 | 44.44 | 27.78 | 66.67 | -0.5357 | 1.678 | -27.44 |
| 4 | prefilter | 10 | success_tail | - | 22 | 22 | 55 | 54.55 | 40.91 | 36.36 | 27.27 | 54.55 | -0.9116 | 0.8997 | -24.58 |
| 5 | prefilter | 10 | ev_hit10 | - | 21 | 21 | 52.5 | 52.38 | 42.86 | 38.1 | 28.57 | 57.14 | -1.174 | 0.7234 | -24.58 |
| 6 | prefilter | 10 | ev | - | 20 | 20 | 50 | 50 | 35 | 35 | 25 | 55 | -0.8341 | 0.9092 | -24.58 |
| 7 | defensive | 50 | ev_hit10 | 0.3 | 15 | 15 | 37.5 | 40 | 26.67 | 26.67 | 40 | 60 | -3.497 | -2.169 | -33.26 |
| 8 | defensive | 50 | ev_hit10 | - | 15 | 15 | 37.5 | 40 | 26.67 | 26.67 | 46.67 | 60 | -3.61 | -2.281 | -33.26 |
| 9 | composite | 20 | success_tail | - | 16 | 16 | 40 | 37.5 | 31.25 | 31.25 | 31.25 | 62.5 | -1.869 | -0.3128 | -18.78 |
| 10 | composite | 20 | ev_hit10 | - | 16 | 16 | 40 | 37.5 | 31.25 | 31.25 | 31.25 | 62.5 | -1.869 | -0.3128 | -18.78 |

## KOSDAQ

- rows/days: `184794` / `103`
- evidence_gate: min_n=`15` min_active_days=`15` eligible_configs=`50`
- unconstrained_best: n=`7`, active_days=`7`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`prefilter` pool_k=`50` score=`ev` max_tail_prob=`None`
- avg_exit improvement: `-0.277837` -> `-0.971936` (delta `-0.694099`)
- dynamic_exit: `1.372075` (fixed 대비 delta `2.344011`)
- hit5_dd10: `48.0` -> `58.8235` (delta `10.8235`)
- best metrics: n=`17`, active_days=`17`, hit5_dd10=`58.8235`, hit10=`52.9412`, safe_hit10=`47.0588`, tail=`35.2941`, bad_path=`58.8235`, avg_exit=`-0.971936`, dynamic_exit=`1.372075`, min_low=`-28.390711`

| rank | pool | pool_k | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | prefilter | 50 | ev | - | 17 | 17 | 42.5 | 58.82 | 52.94 | 47.06 | 35.29 | 58.82 | -0.9719 | 1.372 | -28.39 |
| 2 | prefilter | 50 | ev_hit10 | - | 18 | 18 | 45 | 55.56 | 50 | 44.44 | 33.33 | 61.11 | -0.8107 | 1.403 | -28.39 |
| 3 | prefilter | 50 | success_tail | - | 15 | 15 | 37.5 | 53.33 | 53.33 | 46.67 | 33.33 | 60 | -1.206 | 1.118 | -28.39 |
| 4 | composite | 50 | success_tail | - | 28 | 28 | 70 | 46.43 | 42.86 | 42.86 | 21.43 | 53.57 | -1.131 | 1.004 | -24.4 |
| 5 | composite | 50 | success_tail | 0.25 | 18 | 18 | 45 | 44.44 | 38.89 | 38.89 | 27.78 | 61.11 | -1.635 | 0.3024 | -24.4 |
| 6 | defensive | 10 | ev_hit10 | - | 23 | 23 | 57.5 | 43.48 | 34.78 | 34.78 | 30.43 | 60.87 | -1.73 | 0.002295 | -24.52 |
| 7 | composite | 10 | success_tail | - | 23 | 23 | 57.5 | 43.48 | 34.78 | 30.43 | 47.83 | 65.22 | -3.367 | -1.851 | -24.52 |
| 8 | composite | 50 | ev_hit10 | - | 30 | 30 | 75 | 43.33 | 40 | 36.67 | 23.33 | 60 | -1.09 | 0.7361 | -24.52 |
| 9 | composite | 10 | ev_hit10 | - | 21 | 21 | 52.5 | 42.86 | 38.1 | 33.33 | 47.62 | 66.67 | -3.43 | -1.77 | -19.8 |
| 10 | composite | 50 | ev | - | 26 | 26 | 65 | 42.31 | 38.46 | 38.46 | 26.92 | 57.69 | -1.512 | 0.4037 | -24.4 |

