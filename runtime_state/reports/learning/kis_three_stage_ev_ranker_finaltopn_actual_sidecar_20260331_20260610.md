# KIS Three-Stage EV Ranker Research

- status: `no_improvement`
- generated_at: `2026-06-12T19:56:00+00:00`
- objective: `Validate a no-dummy three-stage KIS workflow: wide recall pool, tail-risk model, expected-value/no-trade ranker.`
- validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`
- dummy_data_used: `False`
- rank_metric: `hit5_dd10_5d_pct`

## KOSPI

- rows/days: `38227` / `27`
- evidence_gate: min_n=`30` min_active_days=`15` eligible_configs=`38`
- gate_counts: production_ready=`0` shadow_display_allowed=`0`
- unconstrained_best: n=`6`, active_days=`3`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`union:day_return+prefilter+coverage` pool_k=`100` final_topn=`2` score=`ev_hit10` max_tail_prob=`None` gate=`blocked` production=`False`
- avg_exit improvement: `0.700469` -> `-1.796353` (delta `-2.496822`)
- dynamic_exit: `0.528124` (fixed 대비 delta `2.324477`)
- hit5_dd10: `47.619` -> `53.3333` (delta `5.7143`)
- best metrics: n=`30`, active_days=`15`, hit5_dd10=`53.3333`, hit10=`53.3333`, safe_hit10=`46.6667`, tail=`36.6667`, bad_path=`53.3333`, avg_exit=`-1.796353`, dynamic_exit=`0.528124`, min_low=`-18.184768`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | blocked | union:day_return+prefilter+coverage | 100 | 2 | ev_hit10 | - | 30 | 15 | 100 | 53.33 | 53.33 | 46.67 | 36.67 | 53.33 | -1.796 | 0.5281 | -18.18 |
| 2 | blocked | union:day_return+prefilter+coverage | 100 | 2 | ev_hit10 | 0.25 | 30 | 15 | 100 | 53.33 | 53.33 | 46.67 | 36.67 | 53.33 | -1.796 | 0.5281 | -18.18 |
| 3 | blocked | union:day_return+prefilter+coverage | 100 | 2 | ev_hit10 | 0.35 | 30 | 15 | 100 | 53.33 | 53.33 | 46.67 | 36.67 | 53.33 | -1.796 | 0.5281 | -18.18 |
| 4 | blocked | union:day_return+prefilter+coverage | 20 | 2 | ev | - | 30 | 15 | 100 | 50 | 36.67 | 36.67 | 40 | 53.33 | -1.782 | 0.04467 | -21.64 |
| 5 | blocked | union:day_return+prefilter+coverage | 100 | 3 | ev_hit10 | - | 43 | 15 | 100 | 48.84 | 53.49 | 41.86 | 41.86 | 55.81 | -2.421 | -0.3357 | -20.14 |
| 6 | blocked | union:day_return+prefilter+coverage | 100 | 3 | ev_hit10 | 0.25 | 43 | 15 | 100 | 48.84 | 51.16 | 41.86 | 41.86 | 55.81 | -2.421 | -0.3357 | -18.18 |
| 7 | blocked | union:day_return+prefilter+coverage | 100 | 3 | ev_hit10 | 0.35 | 43 | 15 | 100 | 48.84 | 53.49 | 41.86 | 41.86 | 55.81 | -2.421 | -0.3357 | -20.14 |
| 8 | blocked | union:day_return+prefilter+coverage | 20 | 2 | success_tail | - | 30 | 15 | 100 | 46.67 | 33.33 | 33.33 | 40 | 56.67 | -2.168 | -0.5076 | -21.64 |
| 9 | blocked | union:day_return+prefilter+coverage | 50 | 2 | success_tail | - | 30 | 15 | 100 | 46.67 | 40 | 33.33 | 40 | 63.33 | -2.436 | -0.7756 | -17.32 |
| 10 | blocked | union:day_return+prefilter+coverage | 50 | 2 | success_tail | 0.25 | 30 | 15 | 100 | 46.67 | 40 | 33.33 | 40 | 63.33 | -2.436 | -0.7756 | -17.32 |

## KOSDAQ

- rows/days: `32028` / `27`
- evidence_gate: min_n=`30` min_active_days=`15` eligible_configs=`0`
- gate_counts: production_ready=`0` shadow_display_allowed=`0`
- unconstrained_best: n=`1`, active_days=`1`, hit5_dd10=`100.0`, tail=`0.0`, avg_exit=`4.601458`
- best_config: pool=`None` pool_k=`None` final_topn=`None` score=`None` max_tail_prob=`None` gate=`None` production=`None`
- avg_exit improvement: `None` -> `None` (delta `None`)
- dynamic_exit: `None` (fixed 대비 delta `None`)
- hit5_dd10: `None` -> `None` (delta `None`)
- best metrics: n=`None`, active_days=`None`, hit5_dd10=`None`, hit10=`None`, safe_hit10=`None`, tail=`None`, bad_path=`None`, avg_exit=`None`, dynamic_exit=`None`, min_low=`None`

| rank | gate | pool | pool_k | final_topn | score | max_tail_prob | n | days | coverage | hit5 | hit10 | safe10 | tail | bad | avg_exit | dynamic_exit | min_low |
|---:|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| - | no eligible config | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |

