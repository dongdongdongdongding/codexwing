# KIS Model Market Comparison

- generated_at: `2026-06-08T16:08:25.098540+00:00`
- metric_contract: `2d is intentionally excluded; report uses completed 1d/3d/5d scan_universe outcome labels only.`

## Promotion Decision
- status: `shadow_only`
- recommended_action: `keep_existing_production_and_show_kis_shadow_top_section`
- all_required_markets_production_ready: `False`
- all_required_markets_shadow_display_allowed: `True`

## KOSPI
- source: `runtime_state/reports/learning/scan_universe_admission_challenger_after_full_kis_sidecar_backfill.json`
- source_generated_at: `2026-06-07T20:47:05.647154+00:00`
- current_kis: `pos_5d` / `kis_sidecar_only` / `random_forest` / `top1`
- current_kis sample: n=`29`, active_days=`9`, active_runs=`26`
- current_kis returns: 1d 승률/평균/최저/최고 100%/5.7342%/0.8824%/11.2957%; 3d 승률/평균/최저/최고 96.5517%/20.0381%/-10.3448%/46.5517%; 5d 승률/평균/최저/최고 96.5517%/23.2462%/-1.5674%/76.9103%
- current_kis net expectancy: 3d=`19.5825%`, 5d=`22.7784%`, cost_model=`kr_tradable_pnl_cost_v1`
- current_kis 5d path: avg_max_high=`39.1636%`, min_low=`-18.0251%`, max_low=`1.1842%`
- kis_model_gate: status=`shadow_risk_review`, production_ready=`False`, shadow_display_allowed=`True`, risk_review_required=`True`
- kis_model_gate blockers: `['n_lt_30', 'active_days_lt_15', 'min_low_5d_lt_neg15']`
- operational_action: `shadow_top_section_only_until_gate_passes`
- theme_news_readiness: `{'market_scope': {}, 'feature_fill_pct': {}, 'mature_for_training': False, 'news_checked_fill_pct': None, 'evidence_score_fill_pct': None, 'kis_backed_fill_pct': None}`

| baseline | n | active_days | 1d win/avg/min/max | 3d win/avg/min/max | 5d win/avg/min/max | 5d avg_high/min_low |
|---|---:|---:|---|---|---|---|
| current_top1 | 25 | 7 | 60%/2.5496%/-7.6473%/14.1134% | 68%/6.0467%/-23.0769%/37.2738% | 68%/8.4304%/-24.0906%/63.6912% | 18.7382%/-26.6809% |
| current_top3 | 70 | 7 | 52.8571%/2.7241%/-19.1554%/30% | 62.8571%/9.4211%/-23.0769%/68.7023% | 64.2857%/9.2162%/-27.7846%/98.7277% | 23.1623%/-32.3745% |
| current_top5 | 110 | 7 | 50%/1.7271%/-19.1554%/30% | 55.4545%/6.0501%/-23.0769%/68.7023% | 54.5455%/5.687%/-27.7846%/98.7277% | 19.1878%/-32.3745% |

| baseline | d_win1 | d_avg1 | d_win3 | d_avg3 | d_win5 | d_avg5 | d_min5 | d_avg_high5 | d_min_low5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| current_top1 | 40 | 3.1846 | 28.5517 | 13.9914 | 28.5517 | 14.8158 | 22.5232 | 20.4254 | 8.6559 |
| current_top3 | 47.1429 | 3.0101 | 33.6946 | 10.617 | 32.266 | 14.03 | 26.2172 | 16.0013 | 14.3495 |
| current_top5 | 50 | 4.0071 | 41.0972 | 13.988 | 42.0062 | 17.5593 | 26.2172 | 19.9758 | 14.3495 |

### UI 반영
- 웹 최상단 KIS Shadow 섹션에 gate status, production_ready, risk_review_required를 함께 표시
- 후보 카드와 TopDeep 상세에 KIS 테마/뉴스 summary, evidence score, KIS-backed 여부, 뉴스 checked 여부를 표시
- Discord 스캔 결과와 정밀분석 lookup에 동일한 KIS gate와 테마/뉴스 summary를 표시
- 운영 승격 전에는 기존 운영 Top 후보와 KIS 후보를 같은 run_id 기준으로 나란히 비교
- production_ready=false이면 매수 후보 문구 대신 shadow_only/risk_review 문구를 유지
- theme_news mature_for_training=false이면 UI에 evidence coverage 부족 배지를 표시하고 승격 판단에서 제외

## KOSDAQ
- source: `runtime_state/reports/learning/scan_universe_admission_challenger_kosdaq_after_20260526_27_backfill.json`
- source_generated_at: `2026-06-06T18:22:53.364105+00:00`
- current_kis: `touch10_guard_5d` / `kis_sidecar_only` / `random_forest` / `top3_p0.65`
- current_kis sample: n=`11`, active_days=`3`, active_runs=`5`
- current_kis returns: 1d 승률/평균/최저/최고 90.9091%/10.9059%/-5.8501%/18.8312%; 3d 승률/평균/최저/최고 90.9091%/20.6714%/-16.819%/62.7677%; 5d 승률/평균/최저/최고 54.5455%/15.8066%/-21.0238%/62.1087%
- current_kis net expectancy: 3d=`20.2134%`, 5d=`15.3671%`, cost_model=`kr_tradable_pnl_cost_v1`
- current_kis 5d path: avg_max_high=`36.9399%`, min_low=`-21.3894%`, max_low=`4.6128%`
- kis_model_gate: status=`shadow_risk_review`, production_ready=`False`, shadow_display_allowed=`True`, risk_review_required=`True`
- kis_model_gate blockers: `['n_lt_45', 'active_days_lt_20', 'active_runs_lt_20', 'win_5d_lt_73', 'min_1d_lt_neg4', 'min_low_5d_lt_neg12', 'bad_path_gt_15']`
- operational_action: `shadow_top_section_only_until_gate_passes`
- theme_news_readiness: `{'market_scope': {}, 'feature_fill_pct': {}, 'mature_for_training': False, 'news_checked_fill_pct': None, 'evidence_score_fill_pct': None, 'kis_backed_fill_pct': None}`

| baseline | n | active_days | 1d win/avg/min/max | 3d win/avg/min/max | 5d win/avg/min/max | 5d avg_high/min_low |
|---|---:|---:|---|---|---|---|
| current_top1 | 13 | 6 | 61.5385%/0.9887%/-9.3458%/17.616% | 30.7692%/-4.2665%/-18.1619%/17.616% | 7.6923%/-11.0718%/-23.4136%/12.7835% | 10.5471%/-25.5288% |
| current_top3 | 35 | 6 | 51.4286%/-0.0833%/-14.6231%/19.5691% | 25.7143%/-4.581%/-23.7965%/17.9533% | 20%/-7.7265%/-30.9718%/21.7235% | 10.3465%/-34.9682% |
| current_top5 | 53 | 6 | 49.0566%/0.2248%/-14.6231%/19.5691% | 35.8491%/-3.0957%/-23.7965%/17.9533% | 24.5283%/-6.2743%/-30.9718%/32.4143% | 12.9566%/-34.9682% |

| baseline | d_win1 | d_avg1 | d_win3 | d_avg3 | d_win5 | d_avg5 | d_min5 | d_avg_high5 | d_min_low5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| current_top1 | 29.3706 | 9.9171 | 60.1399 | 24.9379 | 46.8532 | 26.8784 | 2.3898 | 26.3929 | 4.1394 |
| current_top3 | 39.4805 | 10.9892 | 65.1948 | 25.2525 | 34.5455 | 23.5331 | 9.9481 | 26.5935 | 13.5788 |
| current_top5 | 41.8525 | 10.681 | 55.06 | 23.7671 | 30.0172 | 22.0809 | 9.9481 | 23.9833 | 13.5788 |

### UI 반영
- 웹 최상단 KIS Shadow 섹션에 gate status, production_ready, risk_review_required를 함께 표시
- 후보 카드와 TopDeep 상세에 KIS 테마/뉴스 summary, evidence score, KIS-backed 여부, 뉴스 checked 여부를 표시
- Discord 스캔 결과와 정밀분석 lookup에 동일한 KIS gate와 테마/뉴스 summary를 표시
- 운영 승격 전에는 기존 운영 Top 후보와 KIS 후보를 같은 run_id 기준으로 나란히 비교
- production_ready=false이면 매수 후보 문구 대신 shadow_only/risk_review 문구를 유지
- theme_news mature_for_training=false이면 UI에 evidence coverage 부족 배지를 표시하고 승격 판단에서 제외
