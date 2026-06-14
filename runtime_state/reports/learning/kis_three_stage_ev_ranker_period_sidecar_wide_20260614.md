# KIS Three-Stage EV Ranker Research

- status: `improved_shadow_research`
- generated_at: `2026-06-14T08:47:12+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `avg_dynamic_exit_5d_pct`

## KOSPI

- rows/days: `97638` / `103`
- evidence_gate: min_n=`1` min_active_days=`1` eligible_configs=`20`
- gate_counts: production_ready=`0` shadow_display_allowed=`26`
- unconstrained_best: n=`18`, active_days=`18`, hit5_dd10=`66.6667`, tail=`16.6667`, avg_exit=`0.763014`
- best_config: pool=`prefilter` pool_k=`10` final_topn=`1` score=`ev_hit10` max_tail_prob=`0.85` gate=`blocked` production=`False`
- avg_exit improvement: `0.700469` -> `0.763014` (delta `0.062545`)
- dynamic_exit: `2.976802` (fixed 대비 delta `2.213788`)
- hit5_dd10: `47.619` -> `66.6667` (delta `19.0477`)
- best metrics: n=`18`, active_days=`18`, hit5_dd10=`66.6667`, hit10=`50.0`, safe_hit10=`44.4444`, tail=`16.6667`, bad_path=`50.0`, avg_exit=`0.763014`, dynamic_exit=`2.976802`, min_low=`-19.214396`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | prefilter | 10 | 1 | ev_hit10 | 0.85 | 18 | 18 | 37.5 | 66.67 | 50 | 44.44 | 16.67 | 50 | 0.763 | 2.977 | -19.21 |
| 2 | blocked | prefilter | 10 | 1 | ev_hit10 | 0.9 | 18 | 18 | 37.5 | 66.67 | 50 | 44.44 | 16.67 | 50 | 0.763 | 2.977 | -19.21 |
| 3 | blocked | prefilter | 10 | 1 | ev_hit10 | 0.95 | 18 | 18 | 37.5 | 66.67 | 50 | 44.44 | 16.67 | 50 | 0.763 | 2.977 | -19.21 |
| 4 | shadow_risk_review | defensive | 20 | 1 | ev | - | 13 | 13 | 27.08 | 61.54 | 38.46 | 38.46 | 23.08 | 38.46 | 0.5729 | 2.489 | -14.84 |
| 5 | blocked | prefilter | 10 | 1 | ev_hit10 | - | 22 | 22 | 45.83 | 63.64 | 45.45 | 40.91 | 22.73 | 50 | 0.1335 | 2.171 | -25.33 |
| 6 | shadow_risk_review | defensive | 20 | 1 | success_tail | - | 16 | 16 | 33.33 | 56.25 | 31.25 | 31.25 | 18.75 | 43.75 | 0.5864 | 2.143 | -14.84 |
| 7 | blocked | prefilter | 10 | 1 | success_tail | 0.85 | 19 | 19 | 39.58 | 57.89 | 47.37 | 36.84 | 21.05 | 52.63 | -0.006352 | 1.829 | -19.21 |
| 8 | blocked | prefilter | 10 | 1 | success_tail | 0.9 | 19 | 19 | 39.58 | 57.89 | 47.37 | 36.84 | 21.05 | 52.63 | -0.006352 | 1.829 | -19.21 |
| 9 | blocked | prefilter | 10 | 1 | success_tail | 0.95 | 19 | 19 | 39.58 | 57.89 | 47.37 | 36.84 | 21.05 | 52.63 | -0.006352 | 1.829 | -19.21 |
| 10 | shadow_risk_review | defensive | 20 | 1 | ev_hit10 | - | 15 | 15 | 31.25 | 53.33 | 33.33 | 33.33 | 20 | 46.67 | -0.1904 | 1.47 | -14.84 |

## KOSDAQ

- rows/days: `186203` / `103`
- evidence_gate: min_n=`1` min_active_days=`1` eligible_configs=`20`
- gate_counts: production_ready=`0` shadow_display_allowed=`1`
- unconstrained_best: n=`25`, active_days=`25`, hit5_dd10=`56.0`, tail=`28.0`, avg_exit=`-0.343911`
- best_config: pool=`defensive` pool_k=`10` final_topn=`1` score=`ev_hit10` max_tail_prob=`0.9` gate=`blocked` production=`False`
- avg_exit improvement: `-0.277837` -> `-0.343911` (delta `-0.066074`)
- dynamic_exit: `2.046979` (fixed 대비 delta `2.39089`)
- hit5_dd10: `48.0` -> `56.0` (delta `8.0`)
- best metrics: n=`25`, active_days=`25`, hit5_dd10=`56.0`, hit10=`48.0`, safe_hit10=`48.0`, tail=`28.0`, bad_path=`48.0`, avg_exit=`-0.343911`, dynamic_exit=`2.046979`, min_low=`-24.519736`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | defensive | 10 | 1 | ev_hit10 | 0.9 | 25 | 25 | 52.08 | 56 | 48 | 48 | 28 | 48 | -0.3439 | 2.047 | -24.52 |
| 2 | blocked | union:day_return+composite+defensive | 100 | 1 | success_tail | - | 27 | 27 | 56.25 | 37.04 | 25.93 | 25.93 | 7.407 | 51.85 | 0.1865 | 1.478 | -12.52 |
| 3 | blocked | union:day_return+composite+defensive | 100 | 1 | success_tail | 0.95 | 27 | 27 | 56.25 | 37.04 | 25.93 | 25.93 | 7.407 | 51.85 | 0.1865 | 1.478 | -12.52 |
| 4 | blocked | union:day_return+composite+defensive | 100 | 1 | success_tail | 0.9 | 19 | 19 | 39.58 | 36.84 | 26.32 | 26.32 | 10.53 | 47.37 | 0.06854 | 1.379 | -12.52 |
| 5 | blocked | union:day_return+composite+defensive | 10 | 1 | success_tail | 0.9 | 21 | 21 | 43.75 | 47.62 | 47.62 | 42.86 | 28.57 | 42.86 | -0.764 | 1.371 | -24.41 |
| 6 | blocked | union:day_return+composite+defensive | 50 | 1 | ev_hit10 | 0.9 | 13 | 13 | 27.08 | 53.85 | 46.15 | 46.15 | 23.08 | 53.85 | -0.9668 | 1.332 | -20.29 |
| 7 | blocked | defensive | 10 | 1 | ev_hit10 | 0.85 | 22 | 22 | 45.83 | 50 | 45.45 | 45.45 | 31.82 | 54.55 | -1.018 | 1.246 | -24.52 |
| 8 | blocked | union:day_return+composite+defensive | 100 | 1 | success_tail | 0.85 | 20 | 20 | 41.67 | 35 | 25 | 25 | 10 | 50 | -0.04506 | 1.2 | -12.52 |
| 9 | blocked | defensive | 50 | 1 | ev_hit10 | 0.9 | 17 | 17 | 35.42 | 52.94 | 47.06 | 41.18 | 23.53 | 52.94 | -0.9159 | 1.135 | -20.29 |
| 10 | blocked | defensive | 10 | 1 | ev | 0.9 | 21 | 21 | 43.75 | 47.62 | 42.86 | 38.1 | 28.57 | 47.62 | -0.764 | 1.134 | -24.41 |

