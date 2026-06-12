# KIS historical best-effort suite

- version: `kis_historical_best_effort_suite_v1`
- generated_at: `2026-06-12T04:35:33+00:00`
- source: `actual_kis_historical_universe_prepared_cache`
- label: `+5% target touch within 5D after +2% buy premium, with -10% stop path risk`
- validation: walk-forward with `5` trading-day embargo

## KOSPI

- rows/days: `97638` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `2202`
- best: `lightgbm` / `success_minus_stop_risk` / `kis_failure_prior_numeric` / topN `1`
- gate: `blocked` production=`False` shadow=`False`
- hit5_dd10: `45.8333`
- hit10: `29.1667`
- stop5: `18.75`
- bad_path: `52.0833`
- avg close 5D: `1.575215`
- avg exit-policy 5D: `-0.248146`
- min low 5D: `-23.222301`
- blockers: `['hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`

## KOSDAQ

- rows/days: `186203` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `2202`
- best: `lightgbm_ranker` / `daily_lambdarank` / `kis_failure_prior_numeric` / topN `1`
- gate: `blocked` production=`False` shadow=`False`
- hit5_dd10: `43.75`
- hit10: `43.75`
- stop5: `10.4167`
- bad_path: `50.0`
- avg close 5D: `6.795746`
- avg exit-policy 5D: `0.430712`
- min low 5D: `-20.932579`
- blockers: `['hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`

## Decision

- status: `blocked`
- action: `do_not_show_as_trade_candidate`
- reason: `one or more required markets failed shadow or production gates under best-effort validation`
