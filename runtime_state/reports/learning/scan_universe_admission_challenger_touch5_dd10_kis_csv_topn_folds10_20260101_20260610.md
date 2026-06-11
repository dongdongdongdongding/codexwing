# Scan Universe Admission Challenger

- generated_at: `2026-06-11T15:24:16.355786+00:00`
- source: `scan_universe_snapshots`
- grid_preset: `custom`
- fetch_strategy: `{'mode': 'prepared_cache_hit', 'rows': 166318, 'elapsed_sec': 0.0}`
- prepared_cache: `{'enabled': True, 'mode': 'hit', 'path': 'runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_csv_cache_20260101_20260610.pkl', 'meta_path': 'runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_csv_cache_20260101_20260610.pkl.meta.json', 'prepared_rows': 163530, 'raw_rows': 166318, 'return_sanity': {'bounds': {'buy_premium_max_high_return_1d_pct': [-35.0, 35.0], 'buy_premium_max_high_return_3d_pct': [-75.0, 130.0], 'buy_premium_max_high_return_5d_pct': [-90.0, 300.0], 'buy_premium_min_low_return_1d_pct': [-35.0, 35.0], 'buy_premium_min_low_return_3d_pct': [-75.0, 130.0], 'buy_premium_min_low_return_5d_pct': [-90.0, 300.0], 'buy_premium_return_1d_pct': [-35.0, 35.0], 'buy_premium_return_3d_pct': [-75.0, 130.0], 'buy_premium_return_5d_pct': [-90.0, 300.0], 'max_high_return_1d_pct': [-35.0, 35.0], 'max_high_return_3d_pct': [-75.0, 130.0], 'max_high_return_5d_pct': [-90.0, 300.0], 'min_low_return_1d_pct': [-35.0, 35.0], 'min_low_return_3d_pct': [-75.0, 130.0], 'min_low_return_5d_pct': [-90.0, 300.0], 'return_1d_pct': [-35.0, 35.0], 'return_3d_pct': [-75.0, 130.0], 'return_5d_pct': [-90.0, 300.0]}, 'column_violations': {'buy_premium_max_high_return_1d_pct': 2673, 'buy_premium_max_high_return_3d_pct': 1838, 'buy_premium_max_high_return_5d_pct': 1664, 'buy_premium_min_low_return_1d_pct': 2508, 'buy_premium_min_low_return_3d_pct': 1817, 'buy_premium_min_low_return_5d_pct': 1067, 'buy_premium_return_1d_pct': 2532, 'buy_premium_return_3d_pct': 1814, 'buy_premium_return_5d_pct': 1245, 'max_high_return_1d_pct': 2724, 'max_high_return_3d_pct': 1849, 'max_high_return_5d_pct': 1678, 'min_low_return_1d_pct': 2500, 'min_low_return_3d_pct': 1824, 'min_low_return_5d_pct': 1139, 'return_1d_pct': 2554, 'return_3d_pct': 1816, 'return_5d_pct': 1314}, 'mode': 'kr_price_limit', 'remaining_rows': 163530, 'removed_rows': 2788}, 'created_at': '2026-06-11T15:14:35.234418+00:00'}`
- evaluation: `{'planned_combinations': 8, 'evaluated_combinations': 8, 'eval_workers': 1, 'elapsed_sec': 97.432, 'combinations_per_sec': 0.082}`
- prepared_rows: `163530`
- evaluated_combinations: `8`
- ok_combinations: `8`
- final_model: `{'saved': False, 'reason': 'not_promotable'}`
- promotion_verdict: `{'promotable': False, 'blocking_reasons': ['label_win_lt_65', 'min_mfe_5d_lt_1p5', 'min_5d_tail_below_12', 'min_low_5d_below_10', 'fold_min_low_5d_below_10', 'hit5_dd10_5d_pct_raw_ratio_lt_70'], 'risk_gate': {'pass': False, 'risk_score': 230.207218, 'blocking_reasons': ['min_low_5d_below_10', 'fold_min_low_5d_below_10', 'hit5_dd10_5d_pct_raw_ratio_lt_70'], 'components': {'stop5_pct': 62.5, 'bad_path_pct': 65.0, 'stop_before_target_5d_pct': 62.5, 'target_before_stop_5d_pct': 75.0, 'min_1d_pct': -7.727797, 'min_min_low_5d_pct': -24.361436, 'max_fold_stop5_pct': 100.0, 'max_fold_bad_path_pct': 100.0, 'min_fold_min_low_5d_pct': -24.361436, 'min_fold_target_before_stop_5d_pct': 50.0, 'raw_key': 'hit5_5d_pct', 'raw_pct': 82.5, 'guard_key': 'hit5_dd10_5d_pct', 'guard_pct': 57.5, 'guard_raw_ratio': 0.69697}}, 'baseline_rows_considered': [{'baseline': 'current_top1', 'topn': 1, 'win_3d_pct': 50.0, 'win_5d_pct': 50.0, 'avg_3d_pct': -9.937309, 'avg_5d_pct': -14.018669, 'min_5d_pct': -34.734599}, {'baseline': 'current_top1_exception', 'topn': 1, 'win_3d_pct': 50.0, 'win_5d_pct': 50.0, 'avg_3d_pct': -9.937309, 'avg_5d_pct': -14.018669, 'min_5d_pct': -34.734599}, {'baseline': 'decision_score_top1', 'topn': 1, 'win_3d_pct': 40.0, 'win_5d_pct': 40.0, 'avg_3d_pct': -9.527519, 'avg_5d_pct': -12.688653, 'min_5d_pct': -29.062534}, {'baseline': 'ml_prob_top1', 'topn': 1, 'win_3d_pct': 51.4286, 'win_5d_pct': 62.8571, 'avg_3d_pct': -6.541569, 'avg_5d_pct': -7.801876, 'min_5d_pct': -30.354656}, {'baseline': 'current_top3', 'topn': 3, 'win_3d_pct': 38.3838, 'win_5d_pct': 46.4646, 'avg_3d_pct': -9.868971, 'avg_5d_pct': -11.17315, 'min_5d_pct': -34.734599}, {'baseline': 'current_top3_exception', 'topn': 3, 'win_3d_pct': 38.3838, 'win_5d_pct': 46.4646, 'avg_3d_pct': -9.868971, 'avg_5d_pct': -11.17315, 'min_5d_pct': -34.734599}, {'baseline': 'decision_score_top3', 'topn': 3, 'win_3d_pct': 40.3846, 'win_5d_pct': 46.1538, 'avg_3d_pct': -8.962413, 'avg_5d_pct': -10.650788, 'min_5d_pct': -36.313108}, {'baseline': 'ml_prob_top3', 'topn': 3, 'win_3d_pct': 42.3077, 'win_5d_pct': 53.8462, 'avg_3d_pct': -5.162401, 'avg_5d_pct': -4.752698, 'min_5d_pct': -30.354656}]}`

## Best
- market: `KOSDAQ`
- label: `touch5_dd10_5d`
- feature_set: `failure_risk_augmented`
- model: `hist_gb`
- topn: `1`
- selection_rule: `top1`
- quality_score: `559.472094`
- n / active_runs / active_days: `40` / `35` / `20`
- win_metric_semantics: `target_touch_mfe_ge_5pct_after_buy_premium`
- close_win_metric_semantics: `defensive_close_return_gt_0_after_buy_premium`
- 1d target-touch win / close defense / close avg/min/max: `65.0` / `65.0` / `5.013684` / `-7.727797` / `27.45098`
- 3d target-touch win / close defense / close avg/min/max: `70.0` / `57.5` / `6.08933` / `-20.143131` / `70.405596`
- 5d target-touch win / close defense / close avg/min/max: `82.5` / `77.5` / `10.260306` / `-20.234687` / `70.577897`
- target_before_stop_5d_pct: `75.0`
- hit5/hit10 5d pct: `82.5` / `75.0`
- guarded hit5/hit10 5d pct: `37.5` / `37.5`
- 5d max-high avg/min/max: `23.076859` / `-2.13775` / `80.743651`
- stop5_pct / bad_path_pct: `62.5` / `65.0`

## Best KIS
- market: `None`
- label: `None`
- feature_set: `None`
- model: `None`
- selection_rule: `None`
- quality_score: `None`
- n / active_runs / active_days: `None` / `None` / `None`
- win_metric_semantics: `None`
- 1d target-touch win / close defense / close avg/min/max: `None` / `None` / `None` / `None` / `None`
- 3d target-touch win / close defense / close avg/min/max: `None` / `None` / `None` / `None` / `None`
- 5d target-touch win / close defense / close avg/min/max: `None` / `None` / `None` / `None` / `None`
- hit5/hit10 5d pct: `None` / `None`
- promotion_verdict: `{'promotable': False, 'reason': 'no_valid_challenger'}`

## KIS Feature Readiness
- status: `blocked`
- required_rows / required_days: `1200` / `10`
- families: `{'sidecar': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'prefilter': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'theme_news': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'any_kis': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}}`
- by_market: `{'KOSDAQ': {'sidecar': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'prefilter': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'theme_news': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'any_kis': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}}, 'KOSPI': {'sidecar': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'prefilter': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'theme_news': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'any_kis': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}}}`
- theme_news_feature_fill: `{'kis_theme_news_available': 100.0, 'kis_theme_news_kis_backed': 100.0, 'kis_theme_news_evidence_score': 100.0, 'kis_theme_news_news_checked': 100.0, 'kis_theme_news_news_count': 100.0, 'kis_theme_news_headline_count': 100.0, 'kis_theme_news_positive_tag_count': 100.0, 'kis_theme_news_risk_tag_count': 100.0, 'kis_theme_news_source_scope_confidence': 100.0, 'kis_theme_news_promotion_blocked': 100.0, 'kis_theme_news_level': 100.0, 'kis_theme_news_primary_theme': 2.281, 'kis_theme_news_source_scope': 100.0}`

## Baselines
- `current_top1` top1: n=34, 1d_target=38.2353% close=32.3529%/-4.20345%, 3d_target=50.0% close=14.7059%/-9.937309%, 5d_target=50.0% close=5.8824%/-14.018669%, hit5=50.0%, hit10=23.5294%, mfe5=5.5771%, min5=-34.734599%, max5=14.560917%
- `current_top1_exception` top1: n=34, 1d_target=38.2353% close=32.3529%/-4.20345%, 3d_target=50.0% close=14.7059%/-9.937309%, 5d_target=50.0% close=5.8824%/-14.018669%, hit5=50.0%, hit10=23.5294%, mfe5=5.5771%, min5=-34.734599%, max5=14.560917%
- `decision_score_top1` top1: n=35, 1d_target=34.2857% close=28.5714%/-3.936197%, 3d_target=40.0% close=14.2857%/-9.527519%, 5d_target=40.0% close=11.4286%/-12.688653%, hit5=40.0%, hit10=28.5714%, mfe5=6.401719%, min5=-29.062534%, max5=21.273581%
- `ml_prob_top1` top1: n=35, 1d_target=40.0% close=31.4286%/-3.417942%, 3d_target=51.4286% close=28.5714%/-6.541569%, 5d_target=62.8571% close=31.4286%/-7.801876%, hit5=62.8571%, hit10=34.2857%, mfe5=6.842017%, min5=-30.354656%, max5=15.340254%
- `current_top3` top3: n=99, 1d_target=31.3131% close=24.2424%/-4.385309%, 3d_target=38.3838% close=13.1313%/-9.868971%, 5d_target=46.4646% close=16.1616%/-11.17315%, hit5=46.4646%, hit10=24.2424%, mfe5=5.851037%, min5=-34.734599%, max5=29.973932%
- `current_top3_exception` top3: n=99, 1d_target=31.3131% close=24.2424%/-4.385309%, 3d_target=38.3838% close=13.1313%/-9.868971%, 5d_target=46.4646% close=16.1616%/-11.17315%, hit5=46.4646%, hit10=24.2424%, mfe5=5.851037%, min5=-34.734599%, max5=29.973932%
- `decision_score_top3` top3: n=104, 1d_target=33.6538% close=29.8077%/-3.171247%, 3d_target=40.3846% close=18.2692%/-8.962413%, 5d_target=46.1538% close=18.2692%/-10.650788%, hit5=46.1538%, hit10=31.7308%, mfe5=7.422544%, min5=-36.313108%, max5=21.273581%
- `ml_prob_top3` top3: n=104, 1d_target=27.8846% close=28.8462%/-2.833164%, 3d_target=42.3077% close=25.9615%/-5.162401%, 5d_target=53.8462% close=32.6923%/-4.752698%, hit5=53.8462%, hit10=36.5385%, mfe5=7.782184%, min5=-30.354656%, max5=68.042424%

## Top Results
1. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top1: score=559.472094, n=40, 1d_target=65.0% close=65.0%/5.013684%, 3d_target=70.0% close=57.5%/6.08933%, 5d_target=82.5% close=77.5%/10.260306%, hit5=82.5%, hit10=75.0%, mfe5=23.076859%, min5=-20.234687%, max5=70.577897%
2. `KOSDAQ` `touch5_dd10_5d` `flow_no_gate` `hist_gb` top1: score=111.247683, n=40, 1d_target=32.5% close=40.0%/-0.769315%, 3d_target=45.0% close=27.5%/-3.919156%, 5d_target=50.0% close=40.0%/-3.381533%, hit5=50.0%, hit10=32.5%, mfe5=9.664963%, min5=-16.955017%, max5=17.158897%
3. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top3: score=325.449844, n=119, 1d_target=50.4202% close=49.5798%/2.516966%, 3d_target=72.2689% close=62.1849%/4.598099%, 5d_target=81.5126% close=65.5462%/6.656297%, hit5=81.5126%, hit10=73.1092%, mfe5=21.908181%, min5=-22.662002%, max5=70.577897%
4. `KOSPI` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top1: score=769.816913, n=69, 1d_target=73.913% close=71.0145%/8.094643%, 3d_target=79.7101% close=69.5652%/21.936915%, 5d_target=81.1594% close=53.6232%/10.87134%, hit5=81.1594%, hit10=79.7101%, mfe5=43.760762%, min5=-31.616293%, max5=59.05663%
5. `KOSPI` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top3: score=375.987504, n=205, 1d_target=51.2195% close=55.122%/3.375413%, 3d_target=67.8049% close=62.439%/9.395716%, 5d_target=74.6341% close=56.5854%/5.696328%, hit5=74.6341%, hit10=68.7805%, mfe5=27.052046%, min5=-36.10059%, max5=78.568674%
6. `KOSPI` `touch5_dd10_5d` `flow_no_gate` `hist_gb` top1: score=700.865087, n=69, 1d_target=47.8261% close=50.7246%/5.258984%, 3d_target=68.1159% close=65.2174%/19.763851%, 5d_target=71.0145% close=59.4203%/10.923482%, hit5=71.0145%, hit10=68.1159%, mfe5=38.001488%, min5=-36.10059%, max5=59.416708%
7. `KOSDAQ` `touch5_dd10_5d` `flow_no_gate` `hist_gb` top3: score=15.89739, n=119, 1d_target=33.6134% close=39.4958%/-0.563355%, 3d_target=48.7395% close=32.7731%/-2.854308%, 5d_target=56.3025% close=38.6555%/-3.6273%, hit5=56.3025%, hit10=37.8151%, mfe5=10.629641%, min5=-37.978298%, max5=41.400424%
8. `KOSPI` `touch5_dd10_5d` `flow_no_gate` `hist_gb` top3: score=127.846002, n=205, 1d_target=36.5854% close=41.9512%/0.587043%, 3d_target=62.439% close=53.1707%/5.924246%, 5d_target=65.8537% close=50.2439%/1.307706%, hit5=65.8537%, hit10=50.2439%, mfe5=19.019046%, min5=-44.048957%, max5=59.416708%

## Top KIS Results
