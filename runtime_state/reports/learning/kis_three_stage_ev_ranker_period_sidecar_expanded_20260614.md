# KIS Three-Stage EV Ranker Research

- status: `improved_shadow_research`
- generated_at: `2026-06-14T08:58:43+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `avg_dynamic_exit_5d_pct`

## KOSPI

- rows/days: `97638` / `103`
- evidence_gate: min_n=`1` min_active_days=`1` eligible_configs=`20`
- gate_counts: production_ready=`0` shadow_display_allowed=`44`
- unconstrained_best: n=`20`, active_days=`20`, hit5_dd10=`70.0`, tail=`15.0`, avg_exit=`1.146858`
- best_config: pool=`prefilter` pool_k=`10` final_topn=`1` score=`ev_hit10` max_tail_prob=`0.8` gate=`blocked` production=`False`
- avg_exit improvement: `0.700469` -> `1.146858` (delta `0.446389`)
- dynamic_exit: `3.637369` (fixed 대비 delta `2.490511`)
- hit5_dd10: `47.619` -> `70.0` (delta `22.381`)
- best metrics: n=`20`, active_days=`20`, hit5_dd10=`70.0`, hit10=`55.0`, safe_hit10=`50.0`, tail=`15.0`, bad_path=`50.0`, avg_exit=`1.146858`, dynamic_exit=`3.637369`, min_low=`-19.214396`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | prefilter | 10 | 1 | ev_hit10 | 0.8 | 20 | 20 | 41.67 | 70 | 55 | 50 | 15 | 50 | 1.147 | 3.637 | -19.21 |
| 2 | blocked | prefilter | 5 | 1 | ev_hit10 | - | 23 | 23 | 47.92 | 69.57 | 52.17 | 43.48 | 13.04 | 34.78 | 1.229 | 3.395 | -34.37 |
| 3 | shadow_ready | prefilter | 5 | 2 | ev | 0.75 | 10 | 9 | 18.75 | 60 | 30 | 30 | 0 | 40 | 1.59 | 3.084 | -8.546 |
| 4 | shadow_ready | prefilter | 5 | 2 | success_tail | 0.75 | 10 | 9 | 18.75 | 60 | 30 | 30 | 0 | 40 | 1.59 | 3.084 | -8.546 |
| 5 | shadow_ready | prefilter | 5 | 1 | ev | 0.75 | 9 | 9 | 18.75 | 66.67 | 33.33 | 33.33 | 0 | 44.44 | 1.393 | 3.053 | -8.546 |
| 6 | shadow_ready | prefilter | 5 | 1 | success_tail | 0.75 | 9 | 9 | 18.75 | 66.67 | 33.33 | 33.33 | 0 | 44.44 | 1.393 | 3.053 | -8.546 |
| 7 | blocked | prefilter | 10 | 1 | ev_hit10 | 0.85 | 18 | 18 | 37.5 | 66.67 | 50 | 44.44 | 16.67 | 50 | 0.763 | 2.977 | -19.21 |
| 8 | blocked | prefilter | 10 | 1 | ev_hit10 | 0.9 | 18 | 18 | 37.5 | 66.67 | 50 | 44.44 | 16.67 | 50 | 0.763 | 2.977 | -19.21 |
| 9 | blocked | prefilter | 10 | 1 | ev_hit10 | 0.95 | 18 | 18 | 37.5 | 66.67 | 50 | 44.44 | 16.67 | 50 | 0.763 | 2.977 | -19.21 |
| 10 | blocked | prefilter | 5 | 1 | ev_hit10 | 0.9 | 20 | 20 | 41.67 | 65 | 50 | 40 | 15 | 40 | 0.7231 | 2.715 | -34.37 |

## KOSDAQ

- rows/days: `186203` / `103`
- evidence_gate: min_n=`1` min_active_days=`1` eligible_configs=`20`
- gate_counts: production_ready=`0` shadow_display_allowed=`16`
- unconstrained_best: n=`22`, active_days=`22`, hit5_dd10=`63.6364`, tail=`27.2727`, avg_exit=`0.022675`
- best_config: pool=`day_return` pool_k=`5` final_topn=`1` score=`success_tail` max_tail_prob=`0.85` gate=`blocked` production=`False`
- avg_exit improvement: `-0.277837` -> `0.022675` (delta `0.300512`)
- dynamic_exit: `3.192416` (fixed 대비 delta `3.169741`)
- hit5_dd10: `48.0` -> `63.6364` (delta `15.6364`)
- best metrics: n=`22`, active_days=`22`, hit5_dd10=`63.6364`, hit10=`77.2727`, safe_hit10=`63.6364`, tail=`27.2727`, bad_path=`40.9091`, avg_exit=`0.022675`, dynamic_exit=`3.192416`, min_low=`-37.326529`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | day_return | 5 | 1 | success_tail | 0.85 | 22 | 22 | 45.83 | 63.64 | 77.27 | 63.64 | 27.27 | 40.91 | 0.02268 | 3.192 | -37.33 |
| 2 | blocked | day_return | 5 | 1 | success_tail | 0.9 | 22 | 22 | 45.83 | 63.64 | 77.27 | 63.64 | 27.27 | 40.91 | 0.02268 | 3.192 | -37.33 |
| 3 | blocked | day_return | 5 | 1 | success_tail | - | 24 | 24 | 50 | 62.5 | 79.17 | 62.5 | 29.17 | 41.67 | -0.2042 | 2.909 | -37.33 |
| 4 | blocked | day_return | 5 | 1 | success_tail | 0.8 | 24 | 24 | 50 | 62.5 | 79.17 | 62.5 | 29.17 | 45.83 | -0.2042 | 2.909 | -37.33 |
| 5 | blocked | day_return | 5 | 1 | success_tail | 0.95 | 24 | 24 | 50 | 62.5 | 79.17 | 62.5 | 29.17 | 41.67 | -0.2042 | 2.909 | -37.33 |
| 6 | blocked | day_return | 5 | 1 | ev_hit10 | 0.8 | 21 | 21 | 43.75 | 61.9 | 76.19 | 61.9 | 28.57 | 47.62 | -0.1954 | 2.888 | -37.33 |
| 7 | blocked | day_return | 5 | 1 | ev_hit10 | 0.9 | 21 | 21 | 43.75 | 61.9 | 76.19 | 61.9 | 28.57 | 47.62 | -0.1954 | 2.888 | -37.33 |
| 8 | blocked | day_return | 5 | 1 | ev_hit10 | 0.85 | 18 | 18 | 37.5 | 61.11 | 72.22 | 61.11 | 27.78 | 44.44 | -0.1836 | 2.86 | -37.33 |
| 9 | blocked | day_return | 5 | 1 | success_tail | 0.75 | 23 | 23 | 47.92 | 60.87 | 78.26 | 60.87 | 30.43 | 43.48 | -0.4131 | 2.619 | -37.33 |
| 10 | blocked | day_return | 5 | 1 | ev_hit10 | - | 23 | 23 | 47.92 | 60.87 | 78.26 | 60.87 | 30.43 | 47.83 | -0.4131 | 2.619 | -37.33 |

