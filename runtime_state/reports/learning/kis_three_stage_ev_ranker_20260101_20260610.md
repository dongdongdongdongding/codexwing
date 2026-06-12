# KIS Three-Stage EV Ranker Research

- status: `improved_shadow_research`
- generated_at: `2026-06-12T09:29:37+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`

## KOSPI

- rows/days: `97638` / `103`
- best_config: pool=`composite` pool_k=`20` score=`ev`
- avg_exit improvement: `0.700469` -> `0.858965` (delta `0.158496`)
- hit5_dd10: `47.619` -> `60.0` (delta `12.381`)
- best metrics: n=`20`, active_days=`20`, hit5_dd10=`60.0`, hit10=`40.0`, tail=`10.0`, bad_path=`40.0`, avg_exit=`0.858965`, min_low=`-18.779401`

| rank | pool | pool_k | score | n | days | coverage | hit5 | hit10 | tail | bad | avg_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | composite | 20 | ev | 20 | 20 | 41.67 | 60 | 40 | 10 | 40 | 0.859 | -18.78 |
| 2 | composite | 20 | success_tail | 19 | 19 | 39.58 | 63.16 | 42.11 | 15.79 | 42.11 | 0.7573 | -18.78 |
| 3 | composite | 20 | ev_hit10 | 16 | 16 | 33.33 | 56.25 | 43.75 | 18.75 | 50 | 0.03647 | -18.78 |
| 4 | union:day_return+composite+defensive | 20 | success_tail | 18 | 18 | 37.5 | 50 | 38.89 | 22.22 | 50 | -0.393 | -17.54 |
| 5 | composite | 50 | ev_hit10 | 19 | 19 | 39.58 | 57.89 | 42.11 | 26.32 | 47.37 | -0.5193 | -17.54 |
| 6 | defensive | 20 | success_tail | 17 | 17 | 35.42 | 47.06 | 29.41 | 23.53 | 58.82 | -0.5707 | -16.72 |
| 7 | composite | 50 | ev | 20 | 20 | 41.67 | 40 | 40 | 15 | 55 | -0.8453 | -14.73 |
| 8 | defensive | 20 | ev | 15 | 15 | 31.25 | 40 | 20 | 26.67 | 60 | -1.15 | -16.72 |
| 9 | composite | 50 | success_tail | 20 | 20 | 41.67 | 40 | 40 | 20 | 55 | -1.162 | -16.72 |
| 10 | union:day_return+composite+defensive | 20 | ev | 16 | 16 | 33.33 | 43.75 | 31.25 | 25 | 56.25 | -1.179 | -17.54 |

## KOSDAQ

- rows/days: `186203` / `103`
- best_config: pool=`defensive` pool_k=`100` score=`ev_hit10`
- avg_exit improvement: `-0.277837` -> `0.692915` (delta `0.970752`)
- hit5_dd10: `48.0` -> `59.4595` (delta `11.4595`)
- best metrics: n=`37`, active_days=`37`, hit5_dd10=`59.4595`, hit10=`40.5405`, tail=`13.5135`, bad_path=`40.5405`, avg_exit=`0.692915`, min_low=`-24.403496`

| rank | pool | pool_k | score | n | days | coverage | hit5 | hit10 | tail | bad | avg_exit | min_low |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | defensive | 100 | ev_hit10 | 37 | 37 | 77.08 | 59.46 | 40.54 | 13.51 | 40.54 | 0.6929 | -24.4 |
| 2 | defensive | 100 | success_tail | 34 | 34 | 70.83 | 52.94 | 35.29 | 8.823 | 41.18 | 0.5807 | -13.55 |
| 3 | union:day_return+composite+defensive | 100 | ev_hit10 | 35 | 35 | 72.92 | 57.14 | 37.14 | 14.29 | 42.86 | 0.4211 | -24.4 |
| 4 | composite | 50 | ev | 28 | 28 | 58.33 | 57.14 | 46.43 | 21.43 | 46.43 | 0.1065 | -32.4 |
| 5 | union:day_return+composite+defensive | 20 | success_tail | 26 | 26 | 54.17 | 57.69 | 46.15 | 19.23 | 46.15 | 0.01248 | -19.26 |
| 6 | union:day_return+composite+defensive | 100 | success_tail | 34 | 34 | 70.83 | 47.06 | 32.35 | 11.76 | 47.06 | -0.06805 | -13.55 |
| 7 | union:day_return+composite+defensive | 10 | success_tail | 27 | 27 | 56.25 | 51.85 | 44.44 | 22.22 | 51.85 | -0.1725 | -19.26 |
| 8 | union:day_return+composite+defensive | 50 | ev | 28 | 28 | 58.33 | 46.43 | 35.71 | 17.86 | 50 | -0.1757 | -17.38 |
| 9 | union:day_return+composite+defensive | 20 | ev | 27 | 27 | 56.25 | 51.85 | 40.74 | 18.52 | 48.15 | -0.223 | -19.26 |
| 10 | defensive | 100 | ev | 32 | 32 | 66.67 | 40.62 | 31.25 | 9.375 | 50 | -0.2365 | -13.55 |
