# KIS historical best-effort suite

- version: `kis_historical_best_effort_suite_v1`
- generated_at: `2026-06-12T05:13:01+00:00`
- source: `actual_kis_historical_universe_prepared_cache`
- label: `+5% target touch within 5D after +2% buy premium, with -10% stop path risk`
- validation: walk-forward with `5` trading-day embargo

## KOSPI

- rows/days: `97638` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `436`
- best: `lightgbm` / `success_minus_stop_risk` / `kis_failure_prior_numeric` / topN `1`
- gate: `shadow_ready` production=`False` shadow=`True`
- hit5_dd10: `50.0`
- hit10: `30.0`
- stop5: `10.0`
- bad_path: `50.0`
- avg close 5D: `1.658313`
- avg exit-policy 5D: `0.385872`
- min low 5D: `-12.819311`
- blockers: `['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`

## KOSDAQ

- rows/days: `186203` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `436`
- best: `lightgbm` / `success_probability` / `kis_failure_prior_numeric` / topN `1`
- gate: `shadow_ready` production=`False` shadow=`True`
- hit5_dd10: `61.5385`
- hit10: `38.4615`
- stop5: `0.0`
- bad_path: `15.3846`
- avg close 5D: `3.864831`
- avg exit-policy 5D: `2.413023`
- min low 5D: `-8.107066`
- blockers: `['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`

## Decision

- status: `shadow_ready`
- action: `show_shadow_only_with_risk_review`
- reason: `all required markets cleared shadow gates but at least one production gate remains blocked`
