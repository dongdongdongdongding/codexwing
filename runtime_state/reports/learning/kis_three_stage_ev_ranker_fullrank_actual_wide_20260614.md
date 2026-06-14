# KIS Three-Stage EV Ranker Research

- status: `improved_shadow_research`
- generated_at: `2026-06-14T03:49:22+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `avg_dynamic_exit_5d_pct`

## KOSPI

- rows/days: `97638` / `103`
- evidence_gate: min_n=`1` min_active_days=`1` eligible_configs=`20`
- gate_counts: production_ready=`0` shadow_display_allowed=`16`
- unconstrained_best: n=`23`, active_days=`23`, hit5_dd10=`69.5652`, tail=`13.0435`, avg_exit=`1.373243`
- best_config: pool=`composite` pool_k=`50` final_topn=`1` score=`ev_hit10` max_tail_prob=`None` gate=`shadow_risk_review` production=`False`
- avg_exit improvement: `0.700469` -> `1.373243` (delta `0.672774`)
- dynamic_exit: `2.889206` (fixed 대비 delta `1.515963`)
- hit5_dd10: `47.619` -> `69.5652` (delta `21.9462`)
- best metrics: n=`23`, active_days=`23`, hit5_dd10=`69.5652`, hit10=`30.4348`, safe_hit10=`30.4348`, tail=`13.0435`, bad_path=`34.7826`, avg_exit=`1.373243`, dynamic_exit=`2.889206`, min_low=`-15.847695`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | shadow_risk_review | composite | 50 | 1 | ev_hit10 | - | 23 | 23 | 39.66 | 69.57 | 30.43 | 30.43 | 13.04 | 34.78 | 1.373 | 2.889 | -15.85 |
| 2 | shadow_risk_review | composite | 50 | 1 | success_tail | 0.85 | 26 | 26 | 44.83 | 61.54 | 30.77 | 30.77 | 7.692 | 42.31 | 1.011 | 2.543 | -12.52 |
| 3 | shadow_risk_review | composite | 50 | 1 | success_tail | 0.9 | 26 | 26 | 44.83 | 61.54 | 30.77 | 30.77 | 7.692 | 42.31 | 1.011 | 2.543 | -12.52 |
| 4 | shadow_risk_review | composite | 50 | 1 | success_tail | 0.95 | 26 | 26 | 44.83 | 61.54 | 30.77 | 30.77 | 7.692 | 42.31 | 1.011 | 2.543 | -12.52 |
| 5 | shadow_risk_review | composite | 50 | 1 | ev_hit10 | 0.85 | 21 | 21 | 36.21 | 66.67 | 28.57 | 28.57 | 14.29 | 38.1 | 1.066 | 2.489 | -15.85 |
| 6 | shadow_risk_review | composite | 50 | 1 | ev_hit10 | 0.9 | 21 | 21 | 36.21 | 66.67 | 28.57 | 28.57 | 14.29 | 38.1 | 1.066 | 2.489 | -15.85 |
| 7 | shadow_risk_review | composite | 50 | 1 | ev_hit10 | 0.95 | 21 | 21 | 36.21 | 66.67 | 28.57 | 28.57 | 14.29 | 38.1 | 1.066 | 2.489 | -15.85 |
| 8 | shadow_risk_review | composite | 50 | 1 | success_tail | - | 29 | 29 | 50 | 62.07 | 31.03 | 31.03 | 10.34 | 41.38 | 0.8786 | 2.424 | -15.54 |
| 9 | blocked | composite | 200 | 1 | ev_hit10 | - | 27 | 27 | 46.55 | 51.85 | 40.74 | 40.74 | 18.52 | 51.85 | -0.1041 | 1.925 | -20.58 |
| 10 | blocked | composite | 20 | 2 | ev_hit10 | - | 43 | 25 | 43.1 | 58.14 | 32.56 | 32.56 | 23.26 | 46.51 | 0.2178 | 1.84 | -18.78 |

## KOSDAQ

- rows/days: `186203` / `103`
- evidence_gate: min_n=`1` min_active_days=`1` eligible_configs=`20`
- gate_counts: production_ready=`0` shadow_display_allowed=`22`
- unconstrained_best: n=`20`, active_days=`20`, hit5_dd10=`60.0`, tail=`15.0`, avg_exit=`1.201685`
- best_config: pool=`composite` pool_k=`100` final_topn=`1` score=`ev_hit10` max_tail_prob=`None` gate=`shadow_risk_review` production=`False`
- avg_exit improvement: `-0.277837` -> `1.201685` (delta `1.479522`)
- dynamic_exit: `3.692196` (fixed 대비 delta `2.490511`)
- hit5_dd10: `48.0` -> `60.0` (delta `12.0`)
- best metrics: n=`20`, active_days=`20`, hit5_dd10=`60.0`, hit10=`50.0`, safe_hit10=`50.0`, tail=`15.0`, bad_path=`40.0`, avg_exit=`1.201685`, dynamic_exit=`3.692196`, min_low=`-14.301385`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | shadow_risk_review | composite | 100 | 1 | ev_hit10 | - | 20 | 20 | 34.48 | 60 | 50 | 50 | 15 | 40 | 1.202 | 3.692 | -14.3 |
| 2 | shadow_risk_review | composite | 100 | 1 | ev_hit10 | 0.9 | 20 | 20 | 34.48 | 60 | 50 | 50 | 15 | 40 | 1.202 | 3.692 | -14.3 |
| 3 | shadow_risk_review | composite | 100 | 1 | ev_hit10 | 0.95 | 20 | 20 | 34.48 | 60 | 50 | 50 | 15 | 40 | 1.202 | 3.692 | -14.3 |
| 4 | shadow_risk_review | composite | 100 | 1 | ev_hit10 | 0.85 | 21 | 21 | 36.21 | 57.14 | 47.62 | 47.62 | 14.29 | 42.86 | 1.136 | 3.508 | -14.3 |
| 5 | blocked | composite | 100 | 2 | ev_hit10 | - | 29 | 20 | 34.48 | 55.17 | 41.38 | 41.38 | 13.79 | 48.28 | 0.7045 | 2.766 | -18.3 |
| 6 | blocked | composite | 100 | 2 | ev_hit10 | 0.95 | 29 | 20 | 34.48 | 55.17 | 41.38 | 41.38 | 13.79 | 48.28 | 0.7045 | 2.766 | -18.3 |
| 7 | shadow_risk_review | composite | 100 | 1 | success_tail | 0.9 | 20 | 20 | 34.48 | 50 | 40 | 40 | 10 | 45 | 0.7413 | 2.734 | -12.71 |
| 8 | blocked | composite | 100 | 2 | ev_hit10 | 0.9 | 28 | 20 | 34.48 | 53.57 | 42.86 | 42.86 | 14.29 | 50 | 0.5653 | 2.7 | -18.3 |
| 9 | shadow_risk_review | composite | 100 | 2 | ev | - | 37 | 22 | 37.93 | 54.05 | 35.14 | 35.14 | 10.81 | 43.24 | 0.7513 | 2.501 | -14.3 |
| 10 | shadow_risk_review | composite | 100 | 1 | success_tail | - | 20 | 20 | 34.48 | 50 | 35 | 35 | 10 | 45 | 0.7413 | 2.485 | -12.71 |

