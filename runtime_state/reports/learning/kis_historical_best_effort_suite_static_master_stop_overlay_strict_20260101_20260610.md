# KIS historical best-effort suite

- version: `kis_historical_best_effort_suite_v1`
- generated_at: `2026-06-13T13:03:23+00:00`
- source: `actual_kis_historical_universe_prepared_cache`
- label: `+5% target touch within 5D after +2% buy premium, with -10% stop path risk`
- validation: walk-forward with `5` trading-day embargo

## KOSPI

- rows/days: `97421` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `1306`
- best: `lightgbm` / `success_probability` / `kis_failure_prior_numeric` / topN `2`
- gate: `shadow_ready` production=`False` shadow=`True`
- hit5_dd10: `56.25`
- hit10: `12.5`
- stop5: `6.25`
- bad_path: `25.0`
- avg close 5D: `2.071228`
- avg exit-policy 5D: `1.889486`
- min low 5D: `-10.735899`
- blockers: `['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`

## KOSDAQ

- rows/days: `184794` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `1306`
- best: `lightgbm` / `success_probability` / `kis_failure_prior_numeric` / topN `1`
- gate: `shadow_ready` production=`False` shadow=`True`
- hit5_dd10: `53.8462`
- hit10: `23.0769`
- stop5: `7.6923`
- bad_path: `38.4615`
- avg close 5D: `2.473384`
- avg exit-policy 5D: `1.219388`
- min low 5D: `-10.797336`
- blockers: `['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`

## Decision

- status: `shadow_ready`
- action: `show_shadow_only_with_risk_review`
- reason: `all required markets cleared shadow gates but at least one production gate remains blocked`
