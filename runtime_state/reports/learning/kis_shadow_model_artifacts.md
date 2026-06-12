# KIS shadow model artifacts

- version: `kis_shadow_model_artifact_v1`
- generated_at: `2026-06-12T05:16:07+00:00`
- source_report: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/kis_historical_best_effort_suite_stop_overlay_strict_20260101_20260610.json`
- dummy_data_used: `False`

## KOSPI

- model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/scan_universe_challengers/kospi__touch5_dd10_5d__kis_shadow_best_effort_current.pkl`
- model: `lightgbm` / `success_minus_stop_risk` / `kis_failure_prior_numeric`
- rule: topN `1`, prob `None`, score `0.3`, max_stop `0.02`
- train rows/days: `97638` / `103`
- validation hit5_dd10: `50.0`
- validation hit10: `30.0`
- validation stop5: `10.0`
- validation avg close 5D: `1.658313`
- validation avg ordered exit 5D: `0.385872`
- gate: `shadow_ready` production=`False` shadow=`True`

## KOSDAQ

- model_path: `/Users/dongdong/Projects/codex_swing/swing-main/models/scan_universe_challengers/kosdaq__touch5_dd10_5d__kis_shadow_best_effort_current.pkl`
- model: `lightgbm` / `success_probability` / `kis_failure_prior_numeric`
- rule: topN `1`, prob `0.55`, score `None`, max_stop `0.05`
- train rows/days: `186203` / `103`
- validation hit5_dd10: `61.5385`
- validation hit10: `38.4615`
- validation stop5: `0.0`
- validation avg close 5D: `3.864831`
- validation avg ordered exit 5D: `2.413023`
- gate: `shadow_ready` production=`False` shadow=`True`
