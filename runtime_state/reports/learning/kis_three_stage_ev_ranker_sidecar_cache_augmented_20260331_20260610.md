# KIS Three-Stage EV Ranker Research

- status: `no_improvement`
- generated_at: `2026-06-12T18:30:45+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `hit5_dd10_5d_pct`

## KOSPI

- rows/days: `42562` / `45`
- evidence_gate: min_n=`10` min_active_days=`8` eligible_configs=`50`
- unconstrained_best: n=`1`, active_days=`1`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`prefilter` pool_k=`10` score=`ev` max_tail_prob=`None`
- avg_exit improvement: `0.700469` -> `-0.188114` (delta `-0.888583`)
- dynamic_exit: `1.946609` (fixed 대비 delta `2.134723`)
- hit5_dd10: `47.619` -> `64.2857` (delta `16.6667`)
- best metrics: n=`14`, active_days=`14`, hit5_dd10=`64.2857`, hit10=`50.0`, safe_hit10=`42.8571`, tail=`28.5714`, bad_path=`42.8571`, avg_exit=`-0.188114`, dynamic_exit=`1.946609`, min_low=`-28.464098`

| rank | pool | pool_k | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | prefilter | 10 | ev | - | 14 | 14 | 70 | 64.29 | 50 | 42.86 | 28.57 | 42.86 | -0.1881 | 1.947 | -28.46 |
| 2 | prefilter | 10 | success_tail | - | 14 | 14 | 70 | 64.29 | 50 | 42.86 | 28.57 | 42.86 | -0.1881 | 1.947 | -28.46 |
| 3 | prefilter | 10 | ev_hit10 | - | 14 | 14 | 70 | 64.29 | 50 | 42.86 | 28.57 | 42.86 | -0.1881 | 1.947 | -28.46 |
| 4 | composite | 10 | success_tail | - | 11 | 11 | 55 | 63.64 | 54.55 | 36.36 | 36.36 | 36.36 | -0.7082 | 1.103 | -48.63 |
| 5 | composite | 10 | ev_hit10 | - | 11 | 11 | 55 | 63.64 | 54.55 | 36.36 | 36.36 | 36.36 | -0.7082 | 1.103 | -48.63 |
| 6 | prefilter | 20 | success_tail | - | 13 | 13 | 65 | 61.54 | 38.46 | 38.46 | 23.08 | 46.15 | -0.07123 | 1.845 | -28.46 |
| 7 | prefilter | 50 | success_tail | - | 10 | 10 | 50 | 60 | 10 | 10 | 40 | 60 | -1.239 | -0.741 | -19.23 |
| 8 | composite | 10 | ev | - | 12 | 12 | 60 | 58.33 | 50 | 33.33 | 33.33 | 41.67 | -0.6683 | 0.992 | -48.63 |
| 9 | prefilter | 50 | ev_hit10 | - | 12 | 12 | 60 | 58.33 | 25 | 25 | 33.33 | 50 | -0.9864 | 0.2589 | -23.04 |
| 10 | prefilter | 20 | ev | - | 14 | 14 | 70 | 57.14 | 35.71 | 35.71 | 28.57 | 50 | -0.7804 | 0.9985 | -28.46 |

## KOSDAQ

- rows/days: `80807` / `45`
- evidence_gate: min_n=`10` min_active_days=`8` eligible_configs=`50`
- unconstrained_best: n=`1`, active_days=`1`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`prefilter` pool_k=`10` score=`ev` max_tail_prob=`None`
- avg_exit improvement: `-0.277837` -> `-1.239125` (delta `-0.961288`)
- dynamic_exit: `1.749488` (fixed 대비 delta `2.988613`)
- hit5_dd10: `48.0` -> `60.0` (delta `12.0`)
- best metrics: n=`10`, active_days=`10`, hit5_dd10=`60.0`, hit10=`70.0`, safe_hit10=`60.0`, tail=`40.0`, bad_path=`50.0`, avg_exit=`-1.239125`, dynamic_exit=`1.749488`, min_low=`-25.583164`

| rank | pool | pool_k | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | prefilter | 10 | ev | - | 10 | 10 | 50 | 60 | 70 | 60 | 40 | 50 | -1.239 | 1.749 | -25.58 |
| 2 | prefilter | 50 | ev_hit10 | - | 10 | 10 | 50 | 60 | 60 | 60 | 40 | 60 | -1.239 | 1.749 | -19.21 |
| 3 | prefilter | 20 | ev_hit10 | - | 12 | 12 | 60 | 41.67 | 58.33 | 41.67 | 41.67 | 58.33 | -2.98 | -0.9051 | -17.85 |
| 4 | union:day_return+prefilter+coverage | 10 | ev | 0.1 | 10 | 10 | 50 | 40 | 40 | 40 | 10 | 60 | -0.3828 | 1.61 | -11.06 |
| 5 | union:day_return+prefilter+coverage | 10 | success_tail | 0.1 | 10 | 10 | 50 | 40 | 40 | 40 | 10 | 60 | -0.3828 | 1.61 | -11.06 |
| 6 | union:day_return+prefilter+coverage | 10 | ev_hit10 | 0.1 | 10 | 10 | 50 | 40 | 40 | 40 | 10 | 60 | -0.3828 | 1.61 | -11.06 |
| 7 | union:day_return+prefilter+coverage | 20 | ev | 0.1 | 10 | 10 | 50 | 40 | 40 | 40 | 10 | 60 | -0.3828 | 1.61 | -11.06 |
| 8 | union:day_return+prefilter+coverage | 20 | success_tail | 0.1 | 10 | 10 | 50 | 40 | 40 | 40 | 10 | 60 | -0.3828 | 1.61 | -11.06 |
| 9 | prefilter | 20 | ev | - | 11 | 11 | 55 | 36.36 | 45.45 | 36.36 | 45.45 | 63.64 | -3.67 | -1.858 | -17.85 |
| 10 | prefilter | 20 | success_tail | - | 11 | 11 | 55 | 36.36 | 54.55 | 36.36 | 45.45 | 63.64 | -3.67 | -1.858 | -17.85 |
