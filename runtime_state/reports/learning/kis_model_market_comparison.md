# KIS Model Market Comparison

- generated_at: `2026-06-12T19:09:11.767207+00:00`
- metric_contract: `2d is intentionally excluded; report uses completed 1d/3d/5d scan_universe outcome labels only.`

## Promotion Decision
- status: `shadow_only`
- recommended_action: `keep_existing_production_and_show_kis_shadow_top_section`
- all_required_markets_production_ready: `False`
- all_required_markets_shadow_display_allowed: `True`

## KOSPI
- source: `runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_longfold_20260101_20260610.json`
- source_generated_at: `2026-06-12T14:20:20+00:00`
- current_kis: `touch5_dd10_5d` / `kis_sidecar_failure_risk_augmented` / `lightgbm` / `top1_p0p3_tail0p9`
- current_kis sample: n=`50`, active_days=`11`, active_runs=`50`
- current_kis returns: 1d 승률/평균/최저/최고 16%/0.7754%/-5.1361%/26.3434%; 3d 승률/평균/최저/최고 66%/18.5829%/-3.8029%/93.207%; 5d 승률/평균/최저/최고 82%/26.1152%/-8.4422%/94.0188%
- current_kis net expectancy: 3d=`-%`, 5d=`-%`, cost_model=`kr_tradable_pnl_cost_v1`
- current_kis 5d path: avg_max_high=`48.6752%`, min_low=`-8.9197%`, max_low=`2.2698%`
- kis_model_gate: status=`shadow_ready`, production_ready=`False`, shadow_display_allowed=`True`, risk_review_required=`False`
- kis_model_gate blockers: `['active_days_lt_15']`
- operational_action: `shadow_top_section_only_until_gate_passes`
- theme_news_readiness: `{'market_scope': {}, 'feature_fill_pct': {}, 'mature_for_training': False, 'news_checked_fill_pct': None, 'evidence_score_fill_pct': None, 'kis_backed_fill_pct': None}`

| baseline | n | active_days | 1d win/avg/min/max | 3d win/avg/min/max | 5d win/avg/min/max | 5d avg_high/min_low |
|---|---:|---:|---|---|---|---|

### UI 반영
- 웹 최상단 KIS Shadow 섹션에 gate status, production_ready, risk_review_required를 함께 표시
- 후보 카드와 TopDeep 상세에 KIS 테마/뉴스 summary, evidence score, KIS-backed 여부, 뉴스 checked 여부를 표시
- Discord 스캔 결과와 정밀분석 lookup에 동일한 KIS gate와 테마/뉴스 summary를 표시
- 운영 승격 전에는 기존 운영 Top 후보와 KIS 후보를 같은 run_id 기준으로 나란히 비교
- production_ready=false이면 매수 후보 문구 대신 shadow_only/risk_review 문구를 유지
- theme_news mature_for_training=false이면 UI에 evidence coverage 부족 배지를 표시하고 승격 판단에서 제외

## KOSDAQ
- source: `runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_tailgate_lightgbm_20260401_20260610.json`
- source_generated_at: `2026-06-12T00:40:16.402033+00:00`
- current_kis: `touch5_dd10_5d` / `kis_sidecar_failure_risk_augmented` / `lightgbm` / `top2_p0.50_tail0.90`
- current_kis sample: n=`40`, active_days=`11`, active_runs=`20`
- current_kis returns: 1d 승률/평균/최저/최고 82.5%/12.7097%/-5.6307%/32.2421%; 3d 승률/평균/최저/최고 92.5%/24.5809%/0.41%/76.7259%; 5d 승률/평균/최저/최고 100%/20.4115%/-6.3862%/81.2311%
- current_kis net expectancy: 3d=`-%`, 5d=`-%`, cost_model=`kr_tradable_pnl_cost_v1`
- current_kis 5d path: avg_max_high=`41.9969%`, min_low=`-9.3006%`, max_low=`22.969%`
- kis_model_gate: status=`shadow_ready`, production_ready=`False`, shadow_display_allowed=`True`, risk_review_required=`False`
- kis_model_gate blockers: `['n_lt_45', 'active_days_lt_20']`
- operational_action: `shadow_top_section_only_until_gate_passes`
- theme_news_readiness: `{'market_scope': {'date_coverage': {'2026-04-02': {'outcome_label_rows': 17, 'rows': 17, 'rows_by_market': {'KOSDAQ': 17}, 'unique_runs': 2}, '2026-04-07': {'outcome_label_rows': 5, 'rows': 5, 'rows_by_market': {'KOSDAQ': 5}, 'unique_runs': 1}, '2026-04-09': {'outcome_label_rows': 25, 'rows': 25, 'rows_by_market': {'KOSDAQ': 25}, 'unique_runs': 3}, '2026-04-10': {'outcome_label_rows': 77, 'rows': 77, 'rows_by_market': {'KOSDAQ': 77}, 'unique_runs': 7}, '2026-04-21': {'outcome_label_rows': 171, 'rows': 171, 'rows_by_market': {'KOSDAQ': 171}, 'unique_runs': 2}, '2026-05-08': {'outcome_label_rows': 10, 'rows': 10, 'rows_by_market': {'KOSDAQ': 10}, 'unique_runs': 2}, '2026-05-11': {'outcome_label_rows': 1602, 'rows': 1602, 'rows_by_market': {'KOSDAQ': 1602}, 'unique_runs': 13}, '2026-05-13': {'outcome_label_rows': 4438, 'rows': 4438, 'rows_by_market': {'KOSDAQ': 4438}, 'unique_runs': 3}, '2026-05-14': {'outcome_label_rows': 6183, 'rows': 6183, 'rows_by_market': {'KOSDAQ': 6183}, 'unique_runs': 5}, '2026-05-15': {'outcome_label_rows': 3149, 'rows': 3149, 'rows_by_market': {'KOSDAQ': 3149}, 'unique_runs': 3}, '2026-05-16': {'outcome_label_rows': 1541, 'rows': 1541, 'rows_by_market': {'KOSDAQ': 1541}, 'unique_runs': 1}, '2026-05-17': {'outcome_label_rows': 1541, 'rows': 1541, 'rows_by_market': {'KOSDAQ': 1541}, 'unique_runs': 1}, '2026-05-18': {'outcome_label_rows': 3129, 'rows': 3129, 'rows_by_market': {'KOSDAQ': 3129}, 'unique_runs': 4}, '2026-05-19': {'outcome_label_rows': 1566, 'rows': 1566, 'rows_by_market': {'KOSDAQ': 1566}, 'unique_runs': 1}, '2026-05-20': {'outcome_label_rows': 3150, 'rows': 3150, 'rows_by_market': {'KOSDAQ': 3150}, 'unique_runs': 2}, '2026-05-21': {'outcome_label_rows': 4737, 'rows': 4737, 'rows_by_market': {'KOSDAQ': 4737}, 'unique_runs': 4}, '2026-05-22': {'outcome_label_rows': 4723, 'rows': 4723, 'rows_by_market': {'KOSDAQ': 4723}, 'unique_runs': 3}, '2026-05-23': {'outcome_label_rows': 1519, 'rows': 1519, 'rows_by_market': {'KOSDAQ': 1519}, 'unique_runs': 1}, '2026-05-24': {'outcome_label_rows': 1519, 'rows': 1519, 'rows_by_market': {'KOSDAQ': 1519}, 'unique_runs': 1}, '2026-05-25': {'outcome_label_rows': 1471, 'rows': 1471, 'rows_by_market': {'KOSDAQ': 1471}, 'unique_runs': 1}, '2026-05-26': {'outcome_label_rows': 1812, 'rows': 1812, 'rows_by_market': {'KOSDAQ': 1812}, 'unique_runs': 4}, '2026-05-27': {'outcome_label_rows': 3177, 'rows': 3177, 'rows_by_market': {'KOSDAQ': 3177}, 'unique_runs': 2}, '2026-05-28': {'outcome_label_rows': 1595, 'rows': 1595, 'rows_by_market': {'KOSDAQ': 1595}, 'unique_runs': 1}, '2026-06-06': {'outcome_label_rows': 0, 'rows': 34, 'rows_by_market': {'KOSDAQ': 34}, 'unique_runs': 1}, '2026-06-07': {'outcome_label_rows': 0, 'rows': 62, 'rows_by_market': {'KOSDAQ': 62}, 'unique_runs': 1}, '2026-06-08': {'outcome_label_rows': 0, 'rows': 69, 'rows_by_market': {'KOSDAQ': 69}, 'unique_runs': 2}, '2026-06-09': {'outcome_label_rows': 0, 'rows': 226, 'rows_by_market': {'KOSDAQ': 226}, 'unique_runs': 3}, '2026-06-10': {'outcome_label_rows': 0, 'rows': 394, 'rows_by_market': {'KOSDAQ': 394}, 'unique_runs': 5}}, 'mature_for_training': True, 'outcome_label_rows': 47157, 'rows': 47942, 'unique_days': 28, 'unique_runs': 71}, 'feature_fill_pct': {'kis_theme_news_available': 100.0, 'kis_theme_news_evidence_score': 100.0, 'kis_theme_news_headline_count': 100.0, 'kis_theme_news_kis_backed': 100.0, 'kis_theme_news_kis_sector_name': 60.938, 'kis_theme_news_level': 100.0, 'kis_theme_news_news_checked': 100.0, 'kis_theme_news_news_count': 100.0, 'kis_theme_news_positive_tag_count': 100.0, 'kis_theme_news_prefilter_source_count': 1.019, 'kis_theme_news_primary_theme': 2.374, 'kis_theme_news_promotion_blocked': 100.0, 'kis_theme_news_raw_news_count': 0.033, 'kis_theme_news_risk_tag_count': 100.0, 'kis_theme_news_rows_filtered_out_count': 0.033, 'kis_theme_news_source_scope': 100.0, 'kis_theme_news_source_scope_confidence': 100.0, 'kis_theme_news_standard_industry_code': 61.152, 'kis_theme_news_top_positive_tag': 1.959, 'kis_theme_news_top_risk_tag': 1.682, 'kis_theme_news_vi_triggered': 0.923}, 'mature_for_training': True, 'news_checked_fill_pct': 100.0, 'evidence_score_fill_pct': 100.0, 'kis_backed_fill_pct': 100.0}`

| baseline | n | active_days | 1d win/avg/min/max | 3d win/avg/min/max | 5d win/avg/min/max | 5d avg_high/min_low |
|---|---:|---:|---|---|---|---|

### UI 반영
- 웹 최상단 KIS Shadow 섹션에 gate status, production_ready, risk_review_required를 함께 표시
- 후보 카드와 TopDeep 상세에 KIS 테마/뉴스 summary, evidence score, KIS-backed 여부, 뉴스 checked 여부를 표시
- Discord 스캔 결과와 정밀분석 lookup에 동일한 KIS gate와 테마/뉴스 summary를 표시
- 운영 승격 전에는 기존 운영 Top 후보와 KIS 후보를 같은 run_id 기준으로 나란히 비교
- production_ready=false이면 매수 후보 문구 대신 shadow_only/risk_review 문구를 유지
