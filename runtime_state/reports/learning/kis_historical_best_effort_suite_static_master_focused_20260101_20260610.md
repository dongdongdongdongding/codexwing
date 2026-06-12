# KIS historical best-effort suite

- version: `kis_historical_best_effort_suite_v1`
- generated_at: `2026-06-12T20:39:03+00:00`
- source: `actual_kis_historical_universe_prepared_cache`
- label: `+5% target touch within 5D after +2% buy premium, with -10% stop path risk`
- validation: walk-forward with `5` trading-day embargo

## KOSPI

- rows/days: `97421` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `184`
- best: `lightgbm_ranker` / `daily_lambdarank` / `kis_failure_prior_numeric` / topN `1`
- gate: `shadow_risk_review` production=`False` shadow=`True`
- hit5_dd10: `52.0833`
- hit10: `52.0833`
- stop5: `25.0`
- bad_path: `52.0833`
- avg close 5D: `12.434044`
- avg exit-policy 5D: `-0.424067`
- min low 5D: `-24.653552`
- blockers: `['hit5_dd10_5d_lt_73', 'ordered_exit_floor_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`

## KOSDAQ

- rows/days: `184794` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `184`
- best: `lightgbm_ranker` / `daily_lambdarank` / `kis_failure_prior_category` / topN `1`
- gate: `shadow_risk_review` production=`False` shadow=`True`
- hit5_dd10: `60.4167`
- hit10: `66.6667`
- stop5: `35.4167`
- bad_path: `39.5833`
- avg close 5D: `9.304534`
- avg exit-policy 5D: `-1.156083`
- min low 5D: `-25.761154`
- blockers: `['hit5_dd10_5d_lt_73', 'ordered_exit_floor_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`

## Decision

- status: `shadow_ready`
- action: `show_shadow_only_with_risk_review`
- reason: `all required markets cleared shadow gates but at least one production gate remains blocked`
