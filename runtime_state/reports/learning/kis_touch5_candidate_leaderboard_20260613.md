# KIS Touch5 Candidate Leaderboard

- version: `kis_touch5_candidate_leaderboard_v3`
- generated_at: `2026-06-13T05:40:54+00:00`
- dummy_data_used: `False`
- tracked_sources_only: `True`
- report_count: `35`
- unique_candidates: `4008`
- status: `keep_current_shadow`
- production_replacement_ready: `False`
- shadow_upgrade_found: `False`
- recommended_action: `continue_forward_tracking_until_sample_gate_clears`

## KOSPI
- status: `shadow_candidates_found_no_upgrade`
- candidates/shadow/sample_only/production: `2329` / `381` / `252` / `0`
- current: `kis_sidecar_failure_risk_augmented` `lightgbm` `top1_p0p3_tail0p9` status=`shadow_ready` n=`50` days=`11` runs=`50` sample=`91.111111%` hit5_dd10=`82.0` avg5=`26.115197` low=`-8.919727` source=`runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_longfold_20260101_20260610.json`
- best_sample_only_shadow: `kis_sidecar_failure_risk_augmented` `lightgbm` `top2_prob_plus_tail_p0p8_tail0p85` status=`shadow_ready` n=`93` days=`14` runs=`54` sample=`97.777778%` hit5_dd10=`87.0968` avg5=`15.093948` low=`-8.919727` source=`runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json`
- best_high_precision_shadow: `kis_sidecar_failure_risk_augmented` `lightgbm` `top1_prob_tail_margin_p0p2_tail0p95` status=`shadow_ready` n=`46` days=`10` runs=`46` sample=`88.888889%` hit5_dd10=`93.4783` avg5=`5.385336` low=`-5.558554` source=`runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json`
- verified_upgrade_candidate: -

| rank | status | feature_set | model | rule | n | days | runs | sample% | hit5_dd10 | avg5 | low | source |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_prob_plus_tail_p0p8_tail0p85 | 93 | 14 | 54 | 97.777778 | 87.0968 | 15.093948 | -8.919727 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |
| 2 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_tail_prob_margin_p0p8_tail0p85 | 130 | 14 | 54 | 97.777778 | 83.0769 | 11.089194 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |
| 3 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top1_prob_plus_tail_p0p8_tail0p85 | 54 | 14 | 54 | 97.777778 | 81.4815 | 12.178189 | -8.919727 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |
| 4 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_prob_x_tail_p0p8_tail0p85 | 93 | 14 | 54 | 97.777778 | 78.4946 | 7.075914 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |
| 5 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_prob_tail_margin_p0p8_tail0p85 | 93 | 14 | 54 | 97.777778 | 77.4194 | 5.145959 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |
| 6 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_tail_prob_margin_p0p8_tail0p85 | 93 | 14 | 54 | 97.777778 | 77.4194 | 4.775884 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |
| 7 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top1_ev_strict_p0p1_tail0p9 | 51 | 12 | 51 | 93.333333 | 82.3529 | 3.782798 | -9.230497 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |
| 8 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_prob_plus_tail_p0p1_tail0p9 | 97 | 12 | 51 | 93.333333 | 80.4124 | 9.923863 | -9.230497 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |
| 9 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_prob_tail_margin_p0p1_tail0p9 | 97 | 12 | 51 | 93.333333 | 80.4124 | 5.096217 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |
| 10 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_tail_prob_margin_p0p1_tail0p9 | 97 | 12 | 51 | 93.333333 | 80.4124 | 4.741403 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_kospi_tailfirst_realistic_coverage_20260101_20260610.json |

## KOSDAQ
- status: `shadow_candidates_found_no_upgrade`
- candidates/shadow/sample_only/production: `1679` / `250` / `82` / `0`
- current: `kis_sidecar_failure_risk_augmented` `lightgbm` `top2_p0.50_tail0.90` status=`shadow_ready` n=`40` days=`11` runs=`20` sample=`81.296296%` hit5_dd10=`100.0` avg5=`20.411507` low=`-9.300619` source=`runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json`
- best_sample_only_shadow: `kis_sidecar_failure_risk_augmented` `lightgbm` `top3_ev_tail0p9` status=`shadow_ready` n=`58` days=`10` runs=`20` sample=`83.333333%` hit5_dd10=`94.8276` avg5=`8.515405` low=`-7.8413` source=`runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json`
- best_high_precision_shadow: `kis_sidecar_failure_risk_augmented` `lightgbm` `top3_ev_p0p2_tail0p9` status=`shadow_ready` n=`57` days=`9` runs=`19` sample=`80%` hit5_dd10=`96.4912` avg5=`8.717356` low=`-7.8413` source=`runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json`
- verified_upgrade_candidate: -

| rank | status | feature_set | model | rule | n | days | runs | sample% | hit5_dd10 | avg5 | low | source |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_tail0p9 | 58 | 10 | 20 | 83.333333 | 94.8276 | 8.515405 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
| 2 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_prob_tail_margin_tail0p9 | 58 | 10 | 20 | 83.333333 | 93.1034 | 10.131995 | -9.01155 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
| 3 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p2_tail0p9 | 57 | 9 | 19 | 80 | 96.4912 | 8.717356 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
| 4 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p3_tail0p9 | 57 | 9 | 19 | 80 | 96.4912 | 8.717356 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
| 5 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p4_tail0p9 | 57 | 9 | 19 | 80 | 96.4912 | 8.717356 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
| 6 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p5_tail0p9 | 57 | 9 | 19 | 80 | 96.4912 | 8.717356 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
| 7 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p6_tail0p9 | 57 | 9 | 19 | 80 | 96.4912 | 8.717356 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
| 8 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p7_tail0p9 | 57 | 9 | 19 | 80 | 96.4912 | 8.717356 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
| 9 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p7_tail0p95 | 51 | 9 | 19 | 80 | 96.0784 | 10.669507 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
| 10 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_prob_tail_margin_p0p2_tail0p9 | 57 | 9 | 19 | 80 | 94.7368 | 10.362307 | -9.01155 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_dayfold_realistic_coverage_20260101_20260610.json |
