# KIS Shadow Admission Model Deployment

- generated_at: `2026-06-09T11:56:10.084554+00:00`
- prepared_rows: `95822`
- close_failure_prior_profile: `/Users/dongdong/Projects/codex_swing/swing-main/runtime_state/reports/learning/close_failure_prior_profile_latest.json`
- no_dummy_data: `True`

| market | label | feature_set | model | rule | model_path | gate | TP/SL/hold |
|---|---|---|---|---|---|---|---|
| KOSPI | target_first_sustain_5d | kis_failure_risk_numeric | hist_gb | top1_p0.60 | /Users/dongdong/Projects/codex_swing/swing-main/models/scan_universe_challengers/kospi__target_first_sustain_5d__kis_failure_risk_numeric__hist_gb__top1_p0p60.pkl | shadow_risk_review | 5.0%/-3.0%/3d |
| KOSDAQ | touch10_guard_5d | kis_sidecar_failure_risk_numeric | hist_gb | top5_p0.60 | /Users/dongdong/Projects/codex_swing/swing-main/models/scan_universe_challengers/kosdaq__touch10_guard_5d__kis_sidecar_failure_risk_numeric__hist_gb__top5_p0p60.pkl | shadow_risk_review | 5.0%/-3.0%/3d |
