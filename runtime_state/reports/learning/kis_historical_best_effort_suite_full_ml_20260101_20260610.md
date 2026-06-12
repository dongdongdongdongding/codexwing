# KIS historical best-effort suite

- version: `kis_historical_best_effort_suite_v1`
- generated_at: `2026-06-12T04:13:49+00:00`
- source: `actual_kis_historical_universe_prepared_cache`
- label: `+5% target touch within 5D after +2% buy premium, with -10% stop path risk`
- validation: walk-forward with `5` trading-day embargo

## KOSPI

- rows/days: `97638` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `1228`
- best: `lightgbm` / `success_minus_stop_risk` / `kis_failure_prior_numeric` / topN `1`
- gate: `blocked` production=`False` shadow=`False`
- hit5_dd10: `41.6667`
- hit10: `31.25`
- stop5: `18.75`
- bad_path: `58.3333`
- avg close 5D: `1.53562`
- avg exit-policy 5D: `-0.722445`
- min low 5D: `-23.222301`
- blockers: `['hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`

## KOSDAQ

- rows/days: `186203` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `1228`
- best: `lightgbm_ranker` / `daily_lambdarank` / `kis_failure_prior_category` / topN `1`
- gate: `blocked` production=`False` shadow=`False`
- hit5_dd10: `60.4167`
- hit10: `58.3333`
- stop5: `35.4167`
- bad_path: `39.5833`
- avg close 5D: `3.068901`
- avg exit-policy 5D: `-0.981074`
- min low 5D: `-28.539191`
- blockers: `['hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`

## Decision

- status: `blocked`
- action: `do_not_show_as_trade_candidate`
- reason: `one or more required markets failed shadow or production gates under best-effort validation`
