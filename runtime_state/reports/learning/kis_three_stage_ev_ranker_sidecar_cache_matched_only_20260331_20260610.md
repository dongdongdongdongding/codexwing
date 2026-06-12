# KIS Three-Stage EV Ranker Research

- status: `no_improvement`
- generated_at: `2026-06-12T18:34:20+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `hit5_dd10_5d_pct`

## KOSPI

- rows/days: `13783` / `23`
- evidence_gate: min_n=`8` min_active_days=`6` eligible_configs=`80`
- unconstrained_best: n=`8`, active_days=`8`, hit5_dd10=`62.5`, tail=`37.5`, avg_exit=`-0.874089`
- best_config: pool=`prefilter` pool_k=`10` score=`success_tail` max_tail_prob=`None`
- avg_exit improvement: `0.700469` -> `-0.874089` (delta `-1.574558`)
- dynamic_exit: `2.23905` (fixed 대비 delta `3.113139`)
- hit5_dd10: `47.619` -> `62.5` (delta `14.881`)
- best metrics: n=`8`, active_days=`8`, hit5_dd10=`62.5`, hit10=`62.5`, safe_hit10=`62.5`, tail=`37.5`, bad_path=`37.5`, avg_exit=`-0.874089`, dynamic_exit=`2.23905`, min_low=`-28.615196`

| rank | pool | pool_k | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | prefilter | 10 | success_tail | - | 8 | 8 | 72.73 | 62.5 | 62.5 | 62.5 | 37.5 | 37.5 | -0.8741 | 2.239 | -28.62 |
| 2 | prefilter | 10 | ev_hit10 | - | 8 | 8 | 72.73 | 62.5 | 62.5 | 62.5 | 37.5 | 37.5 | -0.8741 | 2.239 | -28.62 |
| 3 | prefilter | 10 | ev | - | 8 | 8 | 72.73 | 50 | 62.5 | 50 | 50 | 50 | -2.699 | -0.2088 | -28.62 |
| 4 | composite | 5 | success_tail | - | 9 | 9 | 81.82 | 33.33 | 33.33 | 22.22 | 44.44 | 77.78 | -3.247 | -2.14 | -28.62 |
| 5 | coverage | 50 | ev_hit10 | 0.25 | 10 | 10 | 90.91 | 30 | 20 | 20 | 10 | 80 | -2.182 | -1.186 | -10.87 |
| 6 | prefilter | 5 | ev | - | 10 | 10 | 90.91 | 30 | 60 | 20 | 70 | 70 | -5.62 | -4.623 | -30.38 |
| 7 | prefilter | 5 | success_tail | - | 10 | 10 | 90.91 | 30 | 60 | 20 | 70 | 70 | -5.62 | -4.623 | -30.38 |
| 8 | prefilter | 5 | ev_hit10 | - | 11 | 11 | 100 | 27.27 | 72.73 | 27.27 | 72.73 | 72.73 | -6.018 | -4.659 | -30.38 |
| 9 | coverage | 50 | success_tail | - | 8 | 8 | 72.73 | 25 | 12.5 | 12.5 | 12.5 | 87.5 | -3.122 | -2.5 | -15.71 |
| 10 | coverage | 50 | success_tail | 0.2 | 8 | 8 | 72.73 | 25 | 12.5 | 12.5 | 12.5 | 87.5 | -3.122 | -2.5 | -15.71 |

## KOSDAQ

- rows/days: `27016` / `24`
- evidence_gate: min_n=`8` min_active_days=`6` eligible_configs=`80`
- unconstrained_best: n=`1`, active_days=`1`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`prefilter` pool_k=`50` score=`ev` max_tail_prob=`0.2`
- avg_exit improvement: `-0.277837` -> `-4.524453` (delta `-4.246616`)
- dynamic_exit: `-3.279198` (fixed 대비 delta `1.245255`)
- hit5_dd10: `48.0` -> `37.5` (delta `-10.5`)
- best metrics: n=`8`, active_days=`8`, hit5_dd10=`37.5`, hit10=`37.5`, safe_hit10=`25.0`, tail=`62.5`, bad_path=`75.0`, avg_exit=`-4.524453`, dynamic_exit=`-3.279198`, min_low=`-26.343594`

| rank | pool | pool_k | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | prefilter | 50 | ev | 0.2 | 8 | 8 | 66.67 | 37.5 | 37.5 | 25 | 62.5 | 75 | -4.524 | -3.279 | -26.34 |
| 2 | prefilter | 50 | ev | 0.25 | 8 | 8 | 66.67 | 37.5 | 37.5 | 25 | 62.5 | 75 | -4.524 | -3.279 | -26.34 |
| 3 | prefilter | 50 | ev | 0.3 | 8 | 8 | 66.67 | 37.5 | 37.5 | 25 | 62.5 | 75 | -4.524 | -3.279 | -26.34 |
| 4 | day_return | 5 | ev_hit10 | - | 10 | 10 | 83.33 | 30 | 80 | 30 | 70 | 80 | -5.62 | -4.125 | -40.46 |
| 5 | composite | 10 | ev_hit10 | 0.25 | 10 | 10 | 83.33 | 30 | 50 | 20 | 70 | 100 | -5.62 | -4.623 | -24.32 |
| 6 | union:day_return+prefilter+coverage | 50 | ev_hit10 | 0.1 | 10 | 10 | 83.33 | 30 | 30 | 30 | 70 | 70 | -5.62 | -4.125 | -29.13 |
| 7 | prefilter | 20 | ev | 0.3 | 8 | 8 | 66.67 | 25 | 37.5 | 25 | 62.5 | 75 | -5.585 | -4.339 | -25.58 |
| 8 | prefilter | 20 | success_tail | 0.3 | 8 | 8 | 66.67 | 25 | 37.5 | 25 | 62.5 | 75 | -5.585 | -4.339 | -25.58 |
| 9 | prefilter | 20 | ev_hit10 | 0.3 | 8 | 8 | 66.67 | 25 | 37.5 | 25 | 62.5 | 75 | -5.585 | -4.339 | -25.58 |
| 10 | prefilter | 50 | success_tail | 0.2 | 8 | 8 | 66.67 | 25 | 50 | 25 | 75 | 75 | -6.35 | -5.104 | -26.34 |
