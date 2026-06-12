# KIS Three-Stage EV Ranker Research

- status: `improved_shadow_research`
- generated_at: `2026-06-12T09:53:12+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `avg_dynamic_exit_5d_pct`

## KOSPI

- rows/days: `97638` / `103`
- best_config: pool=`composite` pool_k=`20` score=`success_tail`
- avg_exit improvement: `0.700469` -> `0.757261` (delta `0.056792`)
- dynamic_exit: `2.854533` (fixed 대비 delta `2.097272`)
- hit5_dd10: `47.619` -> `63.1579` (delta `15.5389`)
- best metrics: n=`19`, active_days=`19`, hit5_dd10=`63.1579`, hit10=`42.1053`, safe_hit10=`42.1053`, tail=`15.7895`, bad_path=`42.1053`, avg_exit=`0.757261`, dynamic_exit=`2.854533`, min_low=`-18.779401`

| rank | pool | pool_k | score | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | composite | 20 | success_tail | 19 | 19 | 39.58 | 63.16 | 42.11 | 42.11 | 15.79 | 42.11 | 0.7573 | 2.855 | -18.78 |
| 2 | composite | 20 | ev | 20 | 20 | 41.67 | 60 | 40 | 40 | 10 | 40 | 0.859 | 2.851 | -18.78 |
| 3 | composite | 20 | ev_hit10 | 16 | 16 | 33.33 | 56.25 | 43.75 | 43.75 | 18.75 | 50 | 0.03647 | 2.216 | -18.78 |
| 4 | union:day_return+composite+defensive | 20 | success_tail | 18 | 18 | 37.5 | 50 | 38.89 | 38.89 | 22.22 | 50 | -0.393 | 1.544 | -17.54 |
| 5 | composite | 50 | ev_hit10 | 19 | 19 | 39.58 | 57.89 | 42.11 | 36.84 | 26.32 | 47.37 | -0.5193 | 1.316 | -17.54 |
| 6 | composite | 50 | ev | 20 | 20 | 41.67 | 40 | 40 | 35 | 15 | 55 | -0.8453 | 0.898 | -14.73 |
| 7 | defensive | 20 | success_tail | 17 | 17 | 35.42 | 47.06 | 29.41 | 29.41 | 23.53 | 58.82 | -0.5707 | 0.8943 | -16.72 |
| 8 | composite | 50 | success_tail | 20 | 20 | 41.67 | 40 | 40 | 35 | 20 | 55 | -1.162 | 0.5815 | -16.72 |
| 9 | union:day_return+composite+defensive | 20 | ev_hit10 | 17 | 17 | 35.42 | 47.06 | 35.29 | 35.29 | 29.41 | 52.94 | -1.378 | 0.3797 | -25.03 |
| 10 | union:day_return+composite+defensive | 20 | ev | 16 | 16 | 33.33 | 43.75 | 31.25 | 31.25 | 25 | 56.25 | -1.179 | 0.3772 | -17.54 |

## KOSDAQ

- rows/days: `186203` / `103`
- best_config: pool=`defensive` pool_k=`100` score=`ev_hit10`
- avg_exit improvement: `-0.277837` -> `0.692915` (delta `0.970752`)
- dynamic_exit: `2.712248` (fixed 대비 delta `2.019333`)
- hit5_dd10: `48.0` -> `59.4595` (delta `11.4595`)
- best metrics: n=`37`, active_days=`37`, hit5_dd10=`59.4595`, hit10=`40.5405`, safe_hit10=`40.5405`, tail=`13.5135`, bad_path=`40.5405`, avg_exit=`0.692915`, dynamic_exit=`2.712248`, min_low=`-24.403496`

| rank | pool | pool_k | score | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | defensive | 100 | ev_hit10 | 37 | 37 | 77.08 | 59.46 | 40.54 | 40.54 | 13.51 | 40.54 | 0.6929 | 2.712 | -24.4 |
| 2 | composite | 50 | ev | 28 | 28 | 58.33 | 57.14 | 46.43 | 46.43 | 21.43 | 46.43 | 0.1065 | 2.419 | -32.4 |
| 3 | defensive | 100 | success_tail | 34 | 34 | 70.83 | 52.94 | 35.29 | 35.29 | 8.823 | 41.18 | 0.5807 | 2.339 | -13.55 |
| 4 | union:day_return+composite+defensive | 20 | success_tail | 26 | 26 | 54.17 | 57.69 | 46.15 | 46.15 | 19.23 | 46.15 | 0.01248 | 2.311 | -19.26 |
| 5 | union:day_return+composite+defensive | 100 | ev_hit10 | 35 | 35 | 72.92 | 57.14 | 37.14 | 37.14 | 14.29 | 42.86 | 0.4211 | 2.271 | -24.4 |
| 6 | union:day_return+composite+defensive | 10 | success_tail | 27 | 27 | 56.25 | 51.85 | 44.44 | 44.44 | 22.22 | 51.85 | -0.1725 | 2.041 | -19.26 |
| 7 | union:day_return+composite+defensive | 20 | ev | 27 | 27 | 56.25 | 51.85 | 40.74 | 40.74 | 18.52 | 48.15 | -0.223 | 1.806 | -19.26 |
| 8 | defensive | 10 | success_tail | 25 | 25 | 52.08 | 48 | 40 | 40 | 20 | 56 | -0.3056 | 1.687 | -19.26 |
| 9 | day_return | 10 | ev_hit10 | 45 | 45 | 93.75 | 57.78 | 80 | 57.78 | 37.78 | 44.44 | -1.206 | 1.672 | -31.61 |
| 10 | union:day_return+composite+defensive | 50 | ev | 28 | 28 | 58.33 | 46.43 | 35.71 | 35.71 | 17.86 | 50 | -0.1757 | 1.603 | -17.38 |
