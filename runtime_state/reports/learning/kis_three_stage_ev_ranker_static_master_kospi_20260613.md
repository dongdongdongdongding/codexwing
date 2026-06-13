# KIS Three-Stage EV Ranker Research

- status: `improved_shadow_research`
- generated_at: `2026-06-13T03:39:15+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `avg_dynamic_exit_5d_pct`

## KOSPI

- rows/days: `97421` / `103`
- evidence_gate: min_n=`20` min_active_days=`12` eligible_configs=`30`
- gate_counts: production_ready=`0` shadow_display_allowed=`15`
- unconstrained_best: n=`4`, active_days=`4`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`prefilter` pool_k=`5` final_topn=`1` score=`success_tail` max_tail_prob=`None` gate=`blocked` production=`False`
- avg_exit improvement: `-0.722445` -> `0.104695` (delta `0.82714`)
- dynamic_exit: `1.915976` (fixed 대비 delta `1.811281`)
- hit5_dd10: `41.6667` -> `68.1818` (delta `26.5151`)
- best metrics: n=`22`, active_days=`22`, hit5_dd10=`68.1818`, hit10=`45.4545`, safe_hit10=`36.3636`, tail=`27.2727`, bad_path=`45.4545`, avg_exit=`0.104695`, dynamic_exit=`1.915976`, min_low=`-22.553301`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | prefilter | 5 | 1 | success_tail | - | 22 | 22 | 45.83 | 68.18 | 45.45 | 36.36 | 27.27 | 45.45 | 0.1047 | 1.916 | -22.55 |
| 2 | blocked | prefilter | 20 | 1 | success_tail | - | 21 | 21 | 43.75 | 57.14 | 38.1 | 38.1 | 23.81 | 61.9 | -0.07818 | 1.819 | -27.44 |
| 3 | blocked | prefilter | 10 | 1 | ev | - | 22 | 22 | 45.83 | 59.09 | 40.91 | 36.36 | 27.27 | 50 | -0.09104 | 1.72 | -24.58 |
| 4 | blocked | prefilter | 10 | 1 | success_tail | - | 22 | 22 | 45.83 | 59.09 | 36.36 | 31.82 | 27.27 | 54.55 | -0.09104 | 1.494 | -24.58 |
| 5 | blocked | prefilter | 20 | 1 | ev_hit10 | - | 21 | 21 | 43.75 | 57.14 | 38.1 | 38.1 | 28.57 | 61.9 | -0.4971 | 1.4 | -27.44 |
| 6 | blocked | prefilter | 5 | 1 | ev | - | 27 | 27 | 56.25 | 62.96 | 44.44 | 33.33 | 25.93 | 48.15 | -0.4041 | 1.256 | -28.62 |
| 7 | blocked | prefilter | 5 | 1 | ev_hit10 | - | 28 | 28 | 58.33 | 60.71 | 46.43 | 35.71 | 28.57 | 50 | -0.7468 | 1.032 | -34.37 |
| 8 | blocked | prefilter | 10 | 1 | ev_hit10 | - | 30 | 30 | 62.5 | 56.67 | 46.67 | 36.67 | 30 | 56.67 | -0.8406 | 0.9857 | -24.58 |
| 9 | blocked | composite | 20 | 1 | ev_hit10 | - | 20 | 20 | 41.67 | 50 | 40 | 40 | 30 | 50 | -1.045 | 0.9478 | -18.78 |
| 10 | blocked | prefilter | 20 | 2 | ev | - | 38 | 19 | 39.58 | 52.63 | 39.47 | 34.21 | 31.58 | 65.79 | -1.229 | 0.4748 | -27.44 |

