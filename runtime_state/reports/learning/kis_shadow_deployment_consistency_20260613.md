# KIS Shadow Deployment Consistency

- version: `kis_shadow_deployment_consistency_v1`
- generated_at: `2026-06-12T18:55:05+00:00`
- dummy_data_used: `False`
- status: `pass`
- deployment_consistent: `True`
- recommended_action: `use_current_kis_shadow_deployment`

| market | status | rule | gate | model | alias | issues |
|---|---|---|---|---|---|---|
| KOSPI | pass | top1_p0p3_tail0p9 | shadow_ready | models/scan_universe_challengers/kospi__touch5_dd10_5d__kis_sidecar_failure_risk_augmented__lightgbm__top1_p0p3_tail0p9.pkl | models/scan_universe_challengers/kospi__touch5_dd10_5d__kis_shadow_best_effort_current.pkl | - |
| KOSDAQ | pass | top1_p0p75_tail0p85 | shadow_ready | models/scan_universe_challengers/kosdaq__touch5_dd10_5d__kis_sidecar_failure_risk_augmented__lightgbm__top1_p0p75_tail0p85.pkl | models/scan_universe_challengers/kosdaq__touch5_dd10_5d__kis_shadow_best_effort_current.pkl | - |
