# KIS historical best-effort suite

- version: `kis_historical_best_effort_suite_v1`
- generated_at: `2026-06-12T03:13:33+00:00`
- source: `actual_kis_historical_universe_prepared_cache`
- label: `+5% target touch within 5D after +2% buy premium, with -10% stop path risk`
- validation: walk-forward with `5` trading-day embargo

## KOSPI

- rows/days: `97638` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `14`
- best: `catboost` / `success_minus_stop_risk` / `kis_failure_prior_category` / topN `1`
- gate: `shadow_risk_review` production=`False` shadow=`True`
- hit5_dd10: `50.0`
- hit10: `25.0`
- stop5: `33.3333`
- bad_path: `91.6667`
- avg close 5D: `-5.42837`
- avg exit-policy 5D: `-0.996502`
- min low 5D: `-16.200203`
- blockers: `['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p25']`

## KOSDAQ

- rows/days: `186203` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `14`
- best: `baseline_failure_prior_inverse` / `deterministic_baseline` / `kis_manual_score` / topN `1`
- gate: `blocked` production=`False` shadow=`False`
- hit5_dd10: `53.3981`
- hit10: `50.4854`
- stop5: `45.6311`
- bad_path: `66.0194`
- avg close 5D: `2.285164`
- avg exit-policy 5D: `-1.526186`
- min low 5D: `-31.054716`
- blockers: `['hit5_dd10_5d_lt_73', 'min_low_5d_lt_neg10', 'expected_touch_policy_net_5d_lt_0p5']`

## Decision

- status: `blocked`
- action: `do_not_show_as_trade_candidate`
- reason: `one or more required markets failed shadow or production gates under best-effort validation`
