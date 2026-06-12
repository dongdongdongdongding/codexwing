# KIS Shadow Deployment Consistency

- version: `kis_shadow_deployment_consistency_v1`
- generated_at: `2026-06-12T19:11:31+00:00`
- dummy_data_used: `False`
- status: `pass`
- deployment_consistent: `True`
- recommended_action: `use_current_kis_shadow_deployment`

| market | status | rule | gate | model | alias | issues |
|---|---|---|---|---|---|---|
| KOSPI | pass | top1_p0p3_tail0p9 | shadow_ready | models/scan_universe_challengers/kospi__touch5_dd10_5d__kis_sidecar_failure_risk_augmented__lightgbm__top1_p0p3_tail0p9.pkl | models/scan_universe_challengers/kospi__touch5_dd10_5d__kis_shadow_best_effort_current.pkl | - |
| KOSDAQ | pass | top2_p0.50_tail0.90 | shadow_ready | models/scan_universe_challengers/kosdaq__touch5_dd10_5d__kis_sidecar_failure_risk_augmented__lightgbm__top2_p0p50_tail0p90.pkl | models/scan_universe_challengers/kosdaq__touch5_dd10_5d__kis_shadow_best_effort_current.pkl | - |
