# KIS Touch5/DD10 Research Objective Verification

- version: `kis_touch5_research_objective_verification_v1`
- generated_at: `2026-06-12T15:43:30.983626+00:00`
- decision: `verified_shadow_performance`
- recommended_action: `keep_existing_production_and_show_kis_shadow_top_section`
- production_replacement_proven: `False`
- shadow_performance_proven: `True`

## 목표
- primary_goal: 실제 매수 관점에서 KIS 기반 후보가 5거래일 안에 +5% 이상 터치하고 -10%보다 깊은 하락을 피하는지 검증한다.
- win_definition: 스캔 기준가보다 2% 높게 매수한다고 가정하고 5거래일 내 +5% 이상 터치하면 승리로 본다.
- defense_definition: 0.1% 상승이나 종가 양전은 승리가 아니라 방어/참고 지표다.
- loss_guard: 5거래일 최저가가 진입가 대비 -10%보다 깊게 밀리면 실전 실패 경로로 본다.

## 연구 경로
- baseline_boundary_check: 단순 broad ML/top1 방식은 touch5_dd10 목표를 강제하면 기대값이 약하거나 음수라 운영 후보로 부적합했다.
- three_stage_ev_ranker: wide recall pool, tail-risk model, EV/no-trade ranker는 broad baseline 대비 개선됐지만 hit5/dd10이 73% 운영 기준에 미달했다.
- kis_sidecar_longfold_threshold_sweep: KIS sidecar failure-risk augmented LightGBM long-fold sweep가 양시장 shadow 성과를 만들었다.
- consumer_contract_verification: TopDeep, UI/Discord/정밀분석 경로는 KIS shadow gate와 동적 TP/SL/보유일 trace를 보존해야 한다.
- sidecar_score_mode_expansion: 동일 long-fold 조건에서 EV/safety 결합 score mode를 추가 검증한다. 생산 승격은 여전히 0개이며, 성과가 있는 경우 risk-adjusted shadow 후보로만 기록한다.

## 입력과 검증
- no_dummy_data: `True`
- shadow rows/evaluated/shadow_allowed/production_ready: `157551` / `990` / `521` / `0`
- sidecar score sweep evaluated/shadow_allowed/production_ready: `4950` / `3243` / `0`
- three_stage_validation: `walk-forward; each fold trains on fit window, chooses no-trade threshold on calibration days, then evaluates only the next test window.`

## KOSPI
- selected_shadow_model: `kis_sidecar_failure_risk_augmented` / `lightgbm` / `top1_p0p3_tail0p9`
- gate: status=`shadow_ready`, production_ready=`False`, shadow_display_allowed=`True`
- blockers: `['active_days_lt_15']`
- shadow metrics: n=`50`, active_days=`11`, active_runs=`50`, hit5_dd10=`82.0`, hit10=`76.0`, avg5=`26.115197`, min_low=`-8.919727`, expected_touch_net=`1.973196`
- three_stage_result: hit5_dd10=`63.1579`, dynamic_exit=`2.854533`, tail=`15.7895`, min_low=`-18.779401`
- three_stage_improvement_vs_broad: avg_exit_delta=`0.056792`, hit5_delta=`15.5389`
- score_mode_experiment: same_fold_scope=`True`, decision=`keep_current_best_shadow`, best=`top1_p0p3_tail0p9`
- risk_adjusted_alternative: found=`True`, candidate=`top1_prob_tail_margin_tail0p95`, hit5_dd10=`93.4783`, avg5=`5.385336`, min_low=`-5.558554`, deltas=`{'hit5_dd10_5d_pct': 11.4783, 'min_min_low_5d_pct': 3.361173, 'avg_5d_pct': -20.729861, 'n': -4, 'active_days': -1}`
- score_sweep_gate_summary: status_counts=`{'blocked': 1525, 'shadow_ready': 197, 'shadow_risk_review': 753}`, blockers=`{'active_days_lt_15': 2475, 'min_low_5d_lt_neg10': 2278, 'hit5_dd10_5d_lt_73': 767, 'expected_touch_policy_net_5d_lt_0p25': 453}`, sample_only_count=`155`, sample_sufficient_count=`0`
- score_sweep_near_candidates: sample_only_top=`top1_p0p3_tail0p9`, sample_sufficient_top=`None`, pareto_top=`top1_prob_tail_margin_tail0p95`

## KOSDAQ
- selected_shadow_model: `kis_sidecar_failure_risk_augmented` / `lightgbm` / `top1_p0p75_tail0p85`
- gate: status=`shadow_ready`, production_ready=`False`, shadow_display_allowed=`True`
- blockers: `['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20']`
- shadow metrics: n=`19`, active_days=`9`, active_runs=`19`, hit5_dd10=`100.0`, hit10=`100.0`, avg5=`15.458772`, min_low=`-7.006077`, expected_touch_net=`4.601458`
- three_stage_result: hit5_dd10=`59.4595`, dynamic_exit=`2.712248`, tail=`13.5135`, min_low=`-24.403496`
- three_stage_improvement_vs_broad: avg_exit_delta=`0.970752`, hit5_delta=`11.4595`
- score_mode_experiment: same_fold_scope=`True`, decision=`keep_current_best_shadow`, best=`top1_p0p75_tail0p85`
- risk_adjusted_alternative: found=`False`, candidate=`None`, hit5_dd10=`None`, avg5=`None`, min_low=`None`, deltas=`None`
- score_sweep_gate_summary: status_counts=`{'blocked': 182, 'shadow_ready': 444, 'shadow_risk_review': 1849}`, blockers=`{'active_days_lt_20': 2475, 'min_low_5d_lt_neg10': 2031, 'n_lt_45': 830, 'active_runs_lt_20': 525}`, sample_only_count=`444`, sample_sufficient_count=`0`
- score_sweep_near_candidates: sample_only_top=`top1_p0p75_tail0p85`, sample_sufficient_top=`None`, pareto_top=`top1_p0p3_tail0p95`

## UI 요구사항
- 웹 최상단에 KIS Shadow 섹션을 두고 production_ready, shadow_display_allowed, 차단 사유를 한국어로 표시
- 후보 카드에는 목표 +5%, 손절 -10%, 5일 보유, KIS gate, dd10 safety threshold를 같이 표시
- 정밀분석과 Discord lookup도 동일한 gate와 action_reason_codes를 사용
- 테마/뉴스 evidence coverage가 부족하면 학습/승격 제외 배지를 표시
- 운영 Top 후보와 KIS Shadow 후보를 같은 run_id에서 나란히 비교

- operator_report_rule: 성과가 검증된 항목만 후보로 보고한다. production_ready=false이면 운영 대체가 아니라 shadow_only로만 표시한다.
