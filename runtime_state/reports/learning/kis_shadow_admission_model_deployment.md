# KIS Shadow Admission Model Deployment

- generated_at: `2026-06-12T18:49:05.428859+00:00`
- prepared_rows: `157551`
- close_failure_prior_profile: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/close_failure_prior_profile_latest.json`
- no_dummy_data: `True`

| market | label | feature_set | model | rule | model_path | gate | TP/SL/hold |
|---|---|---|---|---|---|---|---|
| KOSPI | touch5_dd10_5d | kis_sidecar_failure_risk_augmented | lightgbm | top1_p0p3_tail0p9 | /Users/dongdong/Projects/codex_swing/swing-main/models/scan_universe_challengers/kospi__touch5_dd10_5d__kis_sidecar_failure_risk_augmented__lightgbm__top1_p0p3_tail0p9.pkl | shadow_ready | 5.0%/-10.0%/5d |
| KOSDAQ | touch5_dd10_5d | kis_sidecar_failure_risk_augmented | lightgbm | top1_p0p75_tail0p85 | /Users/dongdong/Projects/codex_swing/swing-main/models/scan_universe_challengers/kosdaq__touch5_dd10_5d__kis_sidecar_failure_risk_augmented__lightgbm__top1_p0p75_tail0p85.pkl | shadow_ready | 5.0%/-10.0%/5d |
