# KIS shadow research verification

- generated_at: `2026-06-12T14:33:19.722151+00:00`
- objective: KIS sidecar/prefilter 기반 touch5_dd10 5D 모델이 실제 서비스 shadow 후보로 쓸 수 있는지 연구, 탐색, 검증한다.
- data: 157551 real rows / no_dummy_data=True
- sweep: {'evaluated_results': 990, 'production_ready': 0, 'shadow_display_allowed': 521}

## KOSDAQ
- rule: `top1_p0p75_tail0p85` / kis_sidecar_failure_risk_augmented / lightgbm
- performance: n=19, active_days=9, hit5_dd10=100.0%, hit10=100.0%, avg5=15.458772%, min_low=-7.006077%, net_expectancy=4.601458%
- gate: production_ready=False, shadow_display_allowed=True, blockers=['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20']

## KOSPI
- rule: `top1_p0p3_tail0p9` / kis_sidecar_failure_risk_augmented / lightgbm
- performance: n=50, active_days=11, hit5_dd10=82.0%, hit10=76.0%, avg5=26.115197%, min_low=-8.919727%, net_expectancy=1.973196%
- gate: production_ready=False, shadow_display_allowed=True, blockers=['active_days_lt_15']

## Latest consumer verification
- KOSPI RUN-1D19BFFD: top_deep_rows=14, shadow=5, selected=0, blocked_watch=5, missing_trace_rows=0
- KOSDAQ RUN-19AB9953: top_deep_rows=15, shadow=5, selected=0, blocked_watch=5, missing_trace_rows=0

## Decision
- {'all_required_markets_production_ready': False, 'all_required_markets_shadow_display_allowed': True, 'market_gate_rows': {'KOSDAQ': {'gate_status': 'shadow_ready', 'production_blocking_reasons': ['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20'], 'production_economics': {'cost_model': {'buy_fee_bps': 1.5, 'buy_slippage_bps': 8.0, 'fill_rate': 1.0, 'sell_fee_bps': 1.5, 'sell_slippage_bps': 8.0, 'sell_tax_bps': 15.0, 'spread_bps': 4.0, 'version': 'kr_tradable_pnl_cost_v1'}, 'expected_touch_policy_net_5d_pct': 4.601458, 'hit5_dd10_5d_pct': 100.0, 'loss_floor_pct': -10.0, 'policy': 'target_touch_5d_dd10_after_buy_premium', 'target_touch_gross_pct': 5.0, 'target_touch_net_pct': 4.601458, 'thresholds': {'min_expected_touch_policy_net_5d_pct': 0.5}}, 'production_ready': False, 'risk_review_required': False, 'shadow_display_allowed': True}, 'KOSPI': {'gate_status': 'shadow_ready', 'production_blocking_reasons': ['active_days_lt_15'], 'production_economics': {'cost_model': {'buy_fee_bps': 1.5, 'buy_slippage_bps': 8.0, 'fill_rate': 1.0, 'sell_fee_bps': 1.5, 'sell_slippage_bps': 8.0, 'sell_tax_bps': 15.0, 'spread_bps': 4.0, 'version': 'kr_tradable_pnl_cost_v1'}, 'expected_touch_policy_net_5d_pct': 1.973196, 'hit5_dd10_5d_pct': 82.0, 'loss_floor_pct': -10.0, 'policy': 'target_touch_5d_dd10_after_buy_premium', 'target_touch_gross_pct': 5.0, 'target_touch_net_pct': 4.601458, 'thresholds': {'min_expected_touch_policy_net_5d_pct': 0.25}}, 'production_ready': False, 'risk_review_required': False, 'shadow_display_allowed': True}}, 'no_dummy_data': True, 'recommended_action': 'keep_existing_production_and_show_kis_shadow_top_section', 'required_markets': ['KOSPI', 'KOSDAQ'], 'status': 'shadow_only'}
