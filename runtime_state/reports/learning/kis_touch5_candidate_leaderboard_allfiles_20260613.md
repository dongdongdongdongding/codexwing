# KIS Touch5 Candidate Leaderboard

- version: `kis_touch5_candidate_leaderboard_v1`
- generated_at: `2026-06-13T04:08:36+00:00`
- dummy_data_used: `False`
- tracked_sources_only: `False`
- report_count: `39`
- unique_candidates: `3314`
- status: `keep_current_shadow`
- production_replacement_ready: `False`
- shadow_upgrade_found: `False`
- recommended_action: `continue_forward_tracking_until_sample_gate_clears`

## KOSPI
- status: `shadow_candidates_found_no_upgrade`
- candidates/shadow/sample_only/production: `1781` / `865` / `200` / `0`
- current: `kis_sidecar_failure_risk_augmented` `lightgbm` `top1_p0p3_tail0p9` status=`shadow_ready` n=`50` days=`11` runs=`50` sample=`91.111111%` hit5_dd10=`82.0` avg5=`26.115197` low=`-8.919727` source=`runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_longfold_20260101_20260610.json`
- best_sample_only_shadow: `kis_sidecar_failure_risk_numeric` `lightgbm` `top1_tail0.95` status=`shadow_ready` n=`55` days=`12` runs=`55` sample=`93.333333%` hit5_dd10=`85.4545` avg5=`7.937496` low=`-9.816164` source=`runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json`
- best_high_precision_shadow: `kis_sidecar_failure_risk_augmented` `lightgbm` `top1_prob_tail_margin_tail0p95` status=`shadow_ready` n=`46` days=`10` runs=`46` sample=`88.888889%` hit5_dd10=`93.4783` avg5=`5.385336` low=`-5.558554` source=`runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json`
- verified_upgrade_candidate: -

| rank | status | feature_set | model | rule | n | days | runs | sample% | hit5_dd10 | avg5 | low | source |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_ready | kis_sidecar_failure_risk_numeric | lightgbm | top1_tail0.95 | 55 | 12 | 55 | 93.333333 | 85.4545 | 7.937496 | -9.816164 | runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json |
| 2 | shadow_ready | kis_sidecar_failure_risk_numeric | lightgbm | top1_p0.50_tail0.95 | 53 | 11 | 53 | 91.111111 | 84.9057 | 8.044697 | -9.816164 | runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json |
| 3 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p3_tail0p9 | 142 | 11 | 50 | 91.111111 | 83.8028 | 9.912085 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 4 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p35_tail0p9 | 142 | 11 | 50 | 91.111111 | 83.8028 | 9.912085 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 5 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p4_tail0p9 | 142 | 11 | 50 | 91.111111 | 83.8028 | 9.912085 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 6 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p45_tail0p9 | 142 | 11 | 50 | 91.111111 | 83.8028 | 9.912085 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 7 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p5_tail0p9 | 142 | 11 | 50 | 91.111111 | 83.8028 | 9.912085 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 8 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p55_tail0p9 | 142 | 11 | 50 | 91.111111 | 83.8028 | 9.912085 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 9 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_ev_p0p6_tail0p9 | 142 | 11 | 50 | 91.111111 | 83.8028 | 9.912085 | -9.864936 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 10 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top1_p0p3_tail0p9 | 50 | 11 | 50 | 91.111111 | 82 | 26.115197 | -8.919727 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |

## KOSDAQ
- status: `shadow_candidates_found_no_upgrade`
- candidates/shadow/sample_only/production: `1533` / `641` / `214` / `0`
- current: `kis_sidecar_failure_risk_augmented` `lightgbm` `top2_p0.50_tail0.90` status=`shadow_ready` n=`40` days=`11` runs=`20` sample=`81.296296%` hit5_dd10=`100.0` avg5=`20.411507` low=`-9.300619` source=`runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json`
- best_sample_only_shadow: `kis_sidecar_failure_risk_augmented` `lightgbm` `top2_tail0.90` status=`shadow_ready` n=`48` days=`12` runs=`24` sample=`86.666667%` hit5_dd10=`83.3333` avg5=`16.217164` low=`-9.300619` source=`runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json`
- best_high_precision_shadow: `kis_sidecar_failure_risk_augmented` `lightgbm` `top2_p0.50_tail0.90` status=`shadow_ready` n=`40` days=`11` runs=`20` sample=`81.296296%` hit5_dd10=`100.0` avg5=`20.411507` low=`-9.300619` source=`runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json`
- verified_upgrade_candidate: -

| rank | status | feature_set | model | rule | n | days | runs | sample% | hit5_dd10 | avg5 | low | source |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_tail0.90 | 48 | 12 | 24 | 86.666667 | 83.3333 | 16.217164 | -9.300619 | runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json |
| 2 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_prob_plus_tail_p0p55_tail0p85 | 58 | 10 | 20 | 83.333333 | 98.2759 | 10.450233 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 3 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_tail0.95 | 44 | 10 | 22 | 82.592593 | 79.5455 | 13.825693 | -9.563826 | runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json |
| 4 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top2_p0.50_tail0.90 | 40 | 11 | 20 | 81.296296 | 100 | 20.411507 | -9.300619 | runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json |
| 5 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_prob_plus_tail_p0p3_tail0p9 | 57 | 9 | 19 | 80 | 100 | 11.94343 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 6 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_prob_plus_tail_p0p35_tail0p9 | 57 | 9 | 19 | 80 | 100 | 11.94343 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 7 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_prob_plus_tail_p0p4_tail0p9 | 57 | 9 | 19 | 80 | 100 | 11.94343 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 8 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_prob_plus_tail_p0p45_tail0p9 | 57 | 9 | 19 | 80 | 100 | 11.94343 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 9 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_prob_plus_tail_p0p5_tail0p9 | 57 | 9 | 19 | 80 | 100 | 11.94343 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
| 10 | shadow_ready | kis_sidecar_failure_risk_augmented | lightgbm | top3_prob_plus_tail_p0p55_tail0p9 | 57 | 9 | 19 | 80 | 100 | 11.94343 | -7.8413 | runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_3stage_evscore_longfold_20260101_20260610.json |
