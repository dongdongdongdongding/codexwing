# KIS Model Market Comparison

- generated_at: `2026-06-12T05:16:42.850060+00:00`
- metric_contract: `2d is intentionally excluded; report uses completed 1d/3d/5d scan_universe outcome labels only.`

## Promotion Decision
- status: `shadow_only`
- recommended_action: `keep_existing_production_and_show_kis_shadow_top_section`
- all_required_markets_production_ready: `False`
- all_required_markets_shadow_display_allowed: `True`

## KOSPI
- source: `runtime_state/reports/learning/kis_historical_best_effort_suite_stop_overlay_strict_20260101_20260610.json`
- source_generated_at: `2026-06-12T05:13:01+00:00`
- current_kis: `touch5_dd10_5d` / `kis_failure_prior_numeric` / `lightgbm` / `success_minus_stop_risk`
- current_kis sample: n=`10`, active_days=`10`, active_runs=`10`
- current_kis returns: 1d 승률/평균/최저/최고 -%/-%/-%/-%; 3d 승률/평균/최저/최고 -%/-%/-%/-%; 5d 승률/평균/최저/최고 50%/1.6583%/-6.573%/9.4484%
- current_kis net expectancy: 3d=`-%`, 5d=`-%`, cost_model=`kr_tradable_pnl_cost_v1`
- current_kis 5d path: avg_max_high=`-%`, min_low=`-12.8193%`, max_low=`-%`
- kis_model_gate: status=`shadow_ready`, production_ready=`False`, shadow_display_allowed=`True`, risk_review_required=`False`
- kis_model_gate blockers: `['n_lt_30', 'active_days_lt_15', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p25']`
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
- source: `runtime_state/reports/learning/kis_historical_best_effort_suite_stop_overlay_strict_20260101_20260610.json`
- source_generated_at: `2026-06-12T05:13:01+00:00`
- current_kis: `touch5_dd10_5d` / `kis_failure_prior_numeric` / `lightgbm` / `success_probability`
- current_kis sample: n=`13`, active_days=`13`, active_runs=`13`
- current_kis returns: 1d 승률/평균/최저/최고 -%/-%/-%/-%; 3d 승률/평균/최저/최고 -%/-%/-%/-%; 5d 승률/평균/최저/최고 61.5385%/3.8648%/-6.2075%/14.1083%
- current_kis net expectancy: 3d=`-%`, 5d=`-%`, cost_model=`kr_tradable_pnl_cost_v1`
- current_kis 5d path: avg_max_high=`-%`, min_low=`-8.1071%`, max_low=`-%`
- kis_model_gate: status=`shadow_ready`, production_ready=`False`, shadow_display_allowed=`True`, risk_review_required=`False`
- kis_model_gate blockers: `['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'hit5_dd10_5d_lt_73', 'expected_touch_policy_net_5d_lt_0p5']`
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
