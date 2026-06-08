# Daily Model Foundation Gate

- generated_at: 2026-06-08T16:31:10.737424+00:00
- version: daily_model_foundation_gate_v1
- status: **shadow_only**
- daily_verification_ready: True
- production_promotion_ready: False
- no_dummy_data: True
- recommended_action: keep_existing_production_and_run_daily_shadow_verification

## Blocking Reasons

- hard_daily: none
- hard_production: RETRAIN_THRESHOLD_RETURN_POSITIVE, RETRAIN_OOS_RETURN_POSITIVE, RETRAIN_AUC_FLOOR, KIS_PROMOTION_READY, KOSPI_WALKFORWARD_RELEASE, KOSDAQ_WALKFORWARD_RELEASE, PROMOTION_CHALLENGER_CANDIDATE
- soft_daily: none

## Checks

| severity | status | code | detail |
| --- | --- | --- | --- |
| hard_daily | PASS | NIGHTLY_LEARNING_ACTION | action=dataset_refresh expected=dataset_refresh,nightly_retrain,weekly_retrain |
| hard_daily | PASS | NIGHTLY_LEARNING_FRESHNESS | age_hours=1.677 max_age_hours=48.0 |
| hard_daily | PASS | NIGHTLY_LEARNING_NEW_OUTCOMES | new_resolved_since_last_cycle=98 min=1 |
| hard_daily | PASS | WEEKLY_LEARNING_ACTION | action=weekly_retrain expected=weekly_retrain,dataset_refresh |
| soft_daily | PASS | WEEKLY_LEARNING_FRESHNESS | age_hours=40.324 max_age_hours=192.0 |
| soft_daily | PASS | WEEKLY_LEARNING_NEW_OUTCOMES | new_resolved_since_last_cycle=977 min=1 |
| hard_daily | PASS | RETRAIN_EXECUTION_STATUS | execution_status=trained |
| soft_daily | PASS | RETRAIN_FRESHNESS | age_hours=31.324 max_age_hours=240 |
| hard_production | FAIL | RETRAIN_THRESHOLD_RETURN_POSITIVE | positive_threshold_rows=0 of 1 |
| hard_production | FAIL | RETRAIN_OOS_RETURN_POSITIVE | positive_oos_rows=0 of 1 |
| hard_production | FAIL | RETRAIN_AUC_FLOOR | auc_ge_0.55_rows=0 of 1 |
| hard_daily | PASS | NO_DUMMY_SCAN_ROWS | kr_swing_dummy_rows=0 |
| hard_daily | PASS | SUPABASE_SCHEMA_COMPATIBLE | missing_required_columns=[] |
| soft_daily | PASS | SUPABASE_QUALITY_FRESHNESS | age_hours=85.384 max_age_hours=168 |
| hard_daily | PASS | KIS_COMPARISON_NO_DUMMY | no_dummy_data=True |
| hard_daily | PASS | KIS_SHADOW_DISPLAY_ALLOWED | status=shadow_only shadow_allowed=True |
| hard_production | FAIL | KIS_PROMOTION_READY | status=shadow_only market_blockers={'KOSDAQ': ['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'win_5d_lt_73', 'min_1d_lt_neg4', 'min_low_5d_lt_neg12', 'bad_path_gt_15'], 'KOSPI': ['n_lt_30', 'active_days_lt_15', 'min_low_5d_lt_neg15']} |
| hard_production | FAIL | KOSPI_WALKFORWARD_RELEASE | release_ready=False failed_checks=['EXPLOSIVE_LEADER_AVG_1D_LOWER', 'EXPLOSIVE_LEADER_POSITIVE_1D_LOWER', 'EXPLOSIVE_LEADER_AVOID_DOWN_1D_LOWER', 'CORE_TREND_AVG_3D_LOWER', 'CORE_TREND_POSITIVE_3D_LOWER', 'CORE_TREND_AVOID_DOWN_3D_LOWER'] |
| hard_production | FAIL | KOSDAQ_WALKFORWARD_RELEASE | release_ready=False failed_checks=['EXPLOSIVE_LEADER_AVG_1D_LOWER', 'EXPLOSIVE_LEADER_POSITIVE_1D_LOWER', 'EXPLOSIVE_LEADER_AVOID_DOWN_1D_LOWER', 'CORE_TREND_AVG_3D_LOWER', 'CORE_TREND_POSITIVE_3D_LOWER', 'CORE_TREND_AVOID_DOWN_3D_LOWER'] |
| hard_production | FAIL | PROMOTION_CHALLENGER_CANDIDATE | promotion_review_candidate_count=0 near_candidate_count=62 |

## Next Actions

- 음수 기대수익 segment는 승격 대상에서 제외하고 피처/라벨/시장별 분리 재검증
- OOS 수익률이 양수인 segment만 shadow 승격 후보로 유지
- AUC 하한 미달 시 모델 승격 대신 룰 기반 게이트와 데이터 품질 개선 우선
- 시장별 production_blocking_reasons를 해소할 때까지 기존 운영 모델 유지
- KOSPI lane별 평균수익/positive/avoid_down CI 하한을 통과할 때까지 shadow 유지
- KOSDAQ lane별 평균수익/positive/avoid_down CI 하한을 통과할 때까지 shadow 유지
- promotion_review_candidate가 1개 이상 나올 때까지 후보 룰/모델/exit policy를 shadow에서 검증
