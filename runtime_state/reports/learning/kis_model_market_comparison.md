# KIS Model Market Comparison

- generated_at: `2026-06-09T11:56:16.510724+00:00`
- metric_contract: `2d is intentionally excluded; report uses completed 1d/3d/5d scan_universe outcome labels only.`

## Promotion Decision
- status: `shadow_only`
- recommended_action: `keep_existing_production_and_show_kis_shadow_top_section`
- all_required_markets_production_ready: `False`
- all_required_markets_shadow_display_allowed: `True`

## KOSPI
- source: `runtime_state/reports/learning/scan_universe_admission_challenger_failure_risk_numeric_20260401_20260528.json`
- source_generated_at: `2026-06-09T10:18:11.060672+00:00`
- current_kis: `target_first_sustain_5d` / `kis_failure_risk_numeric` / `hist_gb` / `top1_p0.60`
- current_kis sample: n=`27`, active_days=`9`, active_runs=`26`
- current_kis returns: 1d 승률/평균/최저/최고 77.7778%/9.3348%/0.0498%/31.4432%; 3d 승률/평균/최저/최고 77.7778%/13.9579%/1.0802%/68.5341%; 5d 승률/평균/최저/최고 92.5926%/8.3922%/-11.3407%/58.2633%
- current_kis net expectancy: 3d=`13.5253%`, 5d=`7.9808%`, cost_model=`kr_tradable_pnl_cost_v1`
- current_kis 5d path: avg_max_high=`34.0718%`, min_low=`-11.3407%`, max_low=`5.1002%`
- kis_model_gate: status=`shadow_risk_review`, production_ready=`False`, shadow_display_allowed=`True`, risk_review_required=`True`
- kis_model_gate blockers: `['n_lt_30', 'active_days_lt_15', 'bad_path_gt_15', 'stop5_gt_10', 'stop_before_target_5d_gt_15']`
- operational_action: `shadow_top_section_only_until_gate_passes`
- theme_news_readiness: `{'market_scope': {'date_coverage': {'2026-04-07': {'outcome_label_rows': 5, 'rows': 5, 'rows_by_market': {'KOSPI': 5}, 'unique_runs': 1}, '2026-04-09': {'outcome_label_rows': 80, 'rows': 80, 'rows_by_market': {'KOSPI': 80}, 'unique_runs': 4}, '2026-04-10': {'outcome_label_rows': 103, 'rows': 103, 'rows_by_market': {'KOSPI': 103}, 'unique_runs': 8}, '2026-04-21': {'outcome_label_rows': 130, 'rows': 130, 'rows_by_market': {'KOSPI': 130}, 'unique_runs': 2}, '2026-05-08': {'outcome_label_rows': 5, 'rows': 5, 'rows_by_market': {'KOSPI': 5}, 'unique_runs': 1}, '2026-05-10': {'outcome_label_rows': 30, 'rows': 30, 'rows_by_market': {'KOSPI': 30}, 'unique_runs': 6}, '2026-05-11': {'outcome_label_rows': 789, 'rows': 789, 'rows_by_market': {'KOSPI': 789}, 'unique_runs': 2}, '2026-05-12': {'outcome_label_rows': 5, 'rows': 5, 'rows_by_market': {'KOSPI': 5}, 'unique_runs': 1}, '2026-05-13': {'outcome_label_rows': 6813, 'rows': 6813, 'rows_by_market': {'KOSPI': 6813}, 'unique_runs': 9}, '2026-05-14': {'outcome_label_rows': 6476, 'rows': 6476, 'rows_by_market': {'KOSPI': 6476}, 'unique_runs': 14}, '2026-05-15': {'outcome_label_rows': 4772, 'rows': 4772, 'rows_by_market': {'KOSPI': 4772}, 'unique_runs': 7}, '2026-05-16': {'outcome_label_rows': 786, 'rows': 786, 'rows_by_market': {'KOSPI': 786}, 'unique_runs': 1}, '2026-05-17': {'outcome_label_rows': 1569, 'rows': 1569, 'rows_by_market': {'KOSPI': 1569}, 'unique_runs': 2}, '2026-05-18': {'outcome_label_rows': 6339, 'rows': 6339, 'rows_by_market': {'KOSPI': 6339}, 'unique_runs': 10}, '2026-05-19': {'outcome_label_rows': 3960, 'rows': 3960, 'rows_by_market': {'KOSPI': 3960}, 'unique_runs': 5}, '2026-05-20': {'outcome_label_rows': 3202, 'rows': 3202, 'rows_by_market': {'KOSPI': 3202}, 'unique_runs': 5}, '2026-05-21': {'outcome_label_rows': 1602, 'rows': 1602, 'rows_by_market': {'KOSPI': 1602}, 'unique_runs': 3}, '2026-05-22': {'outcome_label_rows': 3189, 'rows': 3189, 'rows_by_market': {'KOSPI': 3189}, 'unique_runs': 4}, '2026-05-23': {'outcome_label_rows': 765, 'rows': 765, 'rows_by_market': {'KOSPI': 765}, 'unique_runs': 1}, '2026-05-24': {'outcome_label_rows': 776, 'rows': 776, 'rows_by_market': {'KOSPI': 776}, 'unique_runs': 1}, '2026-05-25': {'outcome_label_rows': 1504, 'rows': 1504, 'rows_by_market': {'KOSPI': 1504}, 'unique_runs': 2}, '2026-05-26': {'outcome_label_rows': 948, 'rows': 948, 'rows_by_market': {'KOSPI': 948}, 'unique_runs': 5}, '2026-05-27': {'outcome_label_rows': 3203, 'rows': 3203, 'rows_by_market': {'KOSPI': 3203}, 'unique_runs': 4}, '2026-05-28': {'outcome_label_rows': 1599, 'rows': 1599, 'rows_by_market': {'KOSPI': 1599}, 'unique_runs': 2}}, 'mature_for_training': True, 'outcome_label_rows': 48650, 'rows': 48650, 'unique_days': 24, 'unique_runs': 85}, 'feature_fill_pct': {'kis_theme_news_available': 100.0, 'kis_theme_news_evidence_score': 100.0, 'kis_theme_news_headline_count': 100.0, 'kis_theme_news_kis_backed': 100.0, 'kis_theme_news_kis_sector_name': 99.621, 'kis_theme_news_level': 100.0, 'kis_theme_news_news_checked': 100.0, 'kis_theme_news_news_count': 100.0, 'kis_theme_news_positive_tag_count': 100.0, 'kis_theme_news_primary_theme': 2.95, 'kis_theme_news_promotion_blocked': 100.0, 'kis_theme_news_risk_tag_count': 100.0, 'kis_theme_news_source_scope': 100.0, 'kis_theme_news_source_scope_confidence': 100.0, 'kis_theme_news_standard_industry_code': 99.971, 'kis_theme_news_top_positive_tag': 3.155, 'kis_theme_news_top_risk_tag': 2.725, 'kis_theme_news_vi_triggered': 1.345}, 'mature_for_training': True, 'news_checked_fill_pct': 100.0, 'evidence_score_fill_pct': 100.0, 'kis_backed_fill_pct': 100.0}`

| baseline | n | active_days | 1d win/avg/min/max | 3d win/avg/min/max | 5d win/avg/min/max | 5d avg_high/min_low |
|---|---:|---:|---|---|---|---|
| current_top1 | 25 | 7 | 32%/0.5388%/-9.4581%/11.8759% | 68%/3.9674%/-24.5852%/34.5822% | 68%/6.3043%/-25.579%/60.4816% | 16.41%/-28.1186% |
| current_top3 | 70 | 7 | 32.8571%/0.7099%/-20.7406%/27.451% | 62.8571%/7.2756%/-24.5852%/65.3944% | 67.1429%/7.0747%/-29.2006%/94.8311% | 20.7473%/-33.7005% |

| baseline | d_win1 | d_avg1 | d_win3 | d_avg3 | d_win5 | d_avg5 | d_min5 | d_avg_high5 | d_min_low5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| current_top1 | 45.7778 | 8.796 | 9.7778 | 9.9905 | 24.5926 | 2.0879 | 14.2383 | 17.6618 | 16.7779 |
| current_top3 | 44.9207 | 8.625 | 14.9207 | 6.6823 | 25.4497 | 1.3175 | 17.8599 | 13.3245 | 22.3598 |

### UI 반영
- 웹 최상단 KIS Shadow 섹션에 gate status, production_ready, risk_review_required를 함께 표시
- 후보 카드와 TopDeep 상세에 KIS 테마/뉴스 summary, evidence score, KIS-backed 여부, 뉴스 checked 여부를 표시
- Discord 스캔 결과와 정밀분석 lookup에 동일한 KIS gate와 테마/뉴스 summary를 표시
- 운영 승격 전에는 기존 운영 Top 후보와 KIS 후보를 같은 run_id 기준으로 나란히 비교
- production_ready=false이면 매수 후보 문구 대신 shadow_only/risk_review 문구를 유지

## KOSDAQ
- source: `runtime_state/reports/learning/scan_universe_admission_challenger_failure_risk_top5_20260401_20260528.json`
- source_generated_at: `2026-06-09T10:37:23.874063+00:00`
- current_kis: `touch10_guard_5d` / `kis_sidecar_failure_risk_numeric` / `hist_gb` / `top5_p0.60`
- current_kis sample: n=`52`, active_days=`6`, active_runs=`11`
- current_kis returns: 1d 승률/평균/최저/최고 88.4615%/13.5724%/-4.5073%/30.1081%; 3d 승률/평균/최저/최고 98.0769%/29.1971%/-3.3379%/114.986%; 5d 승률/평균/최저/최고 98.0769%/22.4918%/-7.9465%/127.9241%
- current_kis net expectancy: 3d=`28.7068%`, 5d=`22.0268%`, cost_model=`kr_tradable_pnl_cost_v1`
- current_kis 5d path: avg_max_high=`52.7199%`, min_low=`-16.1445%`, max_low=`27.434%`
- kis_model_gate: status=`shadow_risk_review`, production_ready=`False`, shadow_display_allowed=`True`, risk_review_required=`True`
- kis_model_gate blockers: `['active_days_lt_20', 'active_runs_lt_20', 'min_1d_lt_neg4', 'min_low_5d_lt_neg12', 'bad_path_gt_15', 'stop5_gt_10', 'stop_before_target_5d_gt_12']`
- operational_action: `shadow_top_section_only_until_gate_passes`
- theme_news_readiness: `{'market_scope': {'date_coverage': {'2026-04-02': {'outcome_label_rows': 17, 'rows': 17, 'rows_by_market': {'KOSDAQ': 17}, 'unique_runs': 2}, '2026-04-07': {'outcome_label_rows': 5, 'rows': 5, 'rows_by_market': {'KOSDAQ': 5}, 'unique_runs': 1}, '2026-04-09': {'outcome_label_rows': 25, 'rows': 25, 'rows_by_market': {'KOSDAQ': 25}, 'unique_runs': 3}, '2026-04-10': {'outcome_label_rows': 77, 'rows': 77, 'rows_by_market': {'KOSDAQ': 77}, 'unique_runs': 7}, '2026-04-21': {'outcome_label_rows': 171, 'rows': 171, 'rows_by_market': {'KOSDAQ': 171}, 'unique_runs': 2}, '2026-05-08': {'outcome_label_rows': 10, 'rows': 10, 'rows_by_market': {'KOSDAQ': 10}, 'unique_runs': 2}, '2026-05-11': {'outcome_label_rows': 1602, 'rows': 1602, 'rows_by_market': {'KOSDAQ': 1602}, 'unique_runs': 13}, '2026-05-13': {'outcome_label_rows': 4440, 'rows': 4440, 'rows_by_market': {'KOSDAQ': 4440}, 'unique_runs': 3}, '2026-05-14': {'outcome_label_rows': 6185, 'rows': 6185, 'rows_by_market': {'KOSDAQ': 6185}, 'unique_runs': 5}, '2026-05-15': {'outcome_label_rows': 3150, 'rows': 3150, 'rows_by_market': {'KOSDAQ': 3150}, 'unique_runs': 3}, '2026-05-16': {'outcome_label_rows': 1543, 'rows': 1543, 'rows_by_market': {'KOSDAQ': 1543}, 'unique_runs': 1}, '2026-05-17': {'outcome_label_rows': 1543, 'rows': 1543, 'rows_by_market': {'KOSDAQ': 1543}, 'unique_runs': 1}, '2026-05-18': {'outcome_label_rows': 3131, 'rows': 3131, 'rows_by_market': {'KOSDAQ': 3131}, 'unique_runs': 4}, '2026-05-19': {'outcome_label_rows': 1567, 'rows': 1567, 'rows_by_market': {'KOSDAQ': 1567}, 'unique_runs': 1}, '2026-05-20': {'outcome_label_rows': 3151, 'rows': 3151, 'rows_by_market': {'KOSDAQ': 3151}, 'unique_runs': 2}, '2026-05-21': {'outcome_label_rows': 4737, 'rows': 4737, 'rows_by_market': {'KOSDAQ': 4737}, 'unique_runs': 4}, '2026-05-22': {'outcome_label_rows': 4723, 'rows': 4723, 'rows_by_market': {'KOSDAQ': 4723}, 'unique_runs': 3}, '2026-05-23': {'outcome_label_rows': 1519, 'rows': 1519, 'rows_by_market': {'KOSDAQ': 1519}, 'unique_runs': 1}, '2026-05-24': {'outcome_label_rows': 1519, 'rows': 1519, 'rows_by_market': {'KOSDAQ': 1519}, 'unique_runs': 1}, '2026-05-25': {'outcome_label_rows': 1471, 'rows': 1471, 'rows_by_market': {'KOSDAQ': 1471}, 'unique_runs': 1}, '2026-05-26': {'outcome_label_rows': 1812, 'rows': 1812, 'rows_by_market': {'KOSDAQ': 1812}, 'unique_runs': 4}, '2026-05-27': {'outcome_label_rows': 3177, 'rows': 3177, 'rows_by_market': {'KOSDAQ': 3177}, 'unique_runs': 2}, '2026-05-28': {'outcome_label_rows': 1596, 'rows': 1596, 'rows_by_market': {'KOSDAQ': 1596}, 'unique_runs': 1}}, 'mature_for_training': True, 'outcome_label_rows': 47171, 'rows': 47171, 'unique_days': 23, 'unique_runs': 59}, 'feature_fill_pct': {'kis_theme_news_available': 100.0, 'kis_theme_news_evidence_score': 100.0, 'kis_theme_news_headline_count': 100.0, 'kis_theme_news_kis_backed': 100.0, 'kis_theme_news_kis_sector_name': 99.621, 'kis_theme_news_level': 100.0, 'kis_theme_news_news_checked': 100.0, 'kis_theme_news_news_count': 100.0, 'kis_theme_news_positive_tag_count': 100.0, 'kis_theme_news_primary_theme': 2.95, 'kis_theme_news_promotion_blocked': 100.0, 'kis_theme_news_risk_tag_count': 100.0, 'kis_theme_news_source_scope': 100.0, 'kis_theme_news_source_scope_confidence': 100.0, 'kis_theme_news_standard_industry_code': 99.971, 'kis_theme_news_top_positive_tag': 3.155, 'kis_theme_news_top_risk_tag': 2.725, 'kis_theme_news_vi_triggered': 1.345}, 'mature_for_training': True, 'news_checked_fill_pct': 100.0, 'evidence_score_fill_pct': 100.0, 'kis_backed_fill_pct': 100.0}`

| baseline | n | active_days | 1d win/avg/min/max | 3d win/avg/min/max | 5d win/avg/min/max | 5d avg_high/min_low |
|---|---:|---:|---|---|---|---|
| current_top5 | 72 | 7 | 37.5%/-3.5939%/-16.2971%/15.3098% | 48.6111%/-9.1068%/-26.6488%/36.0184% | 56.9444%/-13.9505%/-32.3253%/29.8179% | 8.5292%/-36.2433% |

| baseline | d_win1 | d_avg1 | d_win3 | d_avg3 | d_win5 | d_avg5 | d_min5 | d_avg_high5 | d_min_low5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| current_top5 | 50.9615 | 17.1663 | 49.4658 | 38.304 | 41.1325 | 36.4423 | 24.3788 | 44.1907 | 20.0988 |

### UI 반영
- 웹 최상단 KIS Shadow 섹션에 gate status, production_ready, risk_review_required를 함께 표시
- 후보 카드와 TopDeep 상세에 KIS 테마/뉴스 summary, evidence score, KIS-backed 여부, 뉴스 checked 여부를 표시
- Discord 스캔 결과와 정밀분석 lookup에 동일한 KIS gate와 테마/뉴스 summary를 표시
- 운영 승격 전에는 기존 운영 Top 후보와 KIS 후보를 같은 run_id 기준으로 나란히 비교
- production_ready=false이면 매수 후보 문구 대신 shadow_only/risk_review 문구를 유지
