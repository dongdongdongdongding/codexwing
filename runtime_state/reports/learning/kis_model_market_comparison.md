# KIS Model Market Comparison

- generated_at: `2026-06-12T14:23:23.413705+00:00`
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
- source: `runtime_state/reports/learning/kis_sidecar_threshold_sweep_touch5_dd10_longfold_20260101_20260610.json`
- source_generated_at: `2026-06-12T14:20:20+00:00`
- current_kis: `touch5_dd10_5d` / `kis_sidecar_failure_risk_augmented` / `lightgbm` / `top1_p0p75_tail0p85`
- current_kis sample: n=`19`, active_days=`9`, active_runs=`19`
- current_kis returns: 1d 승률/평균/최저/최고 63.1579%/4.428%/-4.5981%/14.1238%; 3d 승률/평균/최저/최고 100%/16.6041%/0.5092%/40.6031%; 5d 승률/평균/최저/최고 100%/15.4588%/5.1983%/32.3265%
- current_kis net expectancy: 3d=`-%`, 5d=`-%`, cost_model=`kr_tradable_pnl_cost_v1`
- current_kis 5d path: avg_max_high=`32.2748%`, min_low=`-7.0061%`, max_low=`6.7591%`
- kis_model_gate: status=`shadow_ready`, production_ready=`False`, shadow_display_allowed=`True`, risk_review_required=`False`
- kis_model_gate blockers: `['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20']`
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
