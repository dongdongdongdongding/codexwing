# KIS historical best-effort suite

- version: `kis_historical_best_effort_suite_v1`
- generated_at: `2026-06-12T08:15:28+00:00`
- source: `actual_kis_historical_universe_prepared_cache`
- label: `+5% target touch within 5D after +2% buy premium, with -10% stop path risk`
- validation: walk-forward with `5` trading-day embargo

## KOSPI

- rows/days: `97638` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `1675`
- best: `lightgbm` / `success_probability` / `kis_failure_prior_numeric` / topN `1`
- gate: `shadow_ready` production=`False` shadow=`True`
- hit5_dd10: `47.619`
- hit10: `42.8571`
- stop5: `4.7619`
- bad_path: `52.381`
- avg close 5D: `2.257378`
- avg exit-policy 5D: `0.700469`
- min low 5D: `-10.553863`
- blockers: `['n_lt_30', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`

## KOSDAQ

- rows/days: `186203` / `103` (`2026-01-02`..`2026-06-05`)
- candidates: `1675`
- best: `lightgbm` / `success_probability` / `kis_failure_prior_numeric` / topN `5`
- gate: `shadow_ready` production=`False` shadow=`True`
- hit5_dd10: `48.0`
- hit10: `30.6667`
- stop5: `10.6667`
- bad_path: `46.6667`
- avg close 5D: `0.824401`
- avg exit-policy 5D: `-0.277837`
- min low 5D: `-13.454082`
- blockers: `['active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`

## Decision

- status: `shadow_ready`
- action: `show_shadow_only_with_risk_review`
- reason: `all required markets cleared shadow gates but at least one production gate remains blocked`
