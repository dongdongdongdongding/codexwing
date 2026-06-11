# Scan Universe Admission Challenger

- generated_at: `2026-06-11T15:22:14.114014+00:00`
- source: `scan_universe_snapshots`
- grid_preset: `custom`
- fetch_strategy: `{'mode': 'prepared_cache_hit', 'rows': 166318, 'elapsed_sec': 0.0}`
- prepared_cache: `{'enabled': True, 'mode': 'hit', 'path': 'runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_csv_cache_20260101_20260610.pkl', 'meta_path': 'runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_csv_cache_20260101_20260610.pkl.meta.json', 'prepared_rows': 163530, 'raw_rows': 166318, 'return_sanity': {'bounds': {'buy_premium_max_high_return_1d_pct': [-35.0, 35.0], 'buy_premium_max_high_return_3d_pct': [-75.0, 130.0], 'buy_premium_max_high_return_5d_pct': [-90.0, 300.0], 'buy_premium_min_low_return_1d_pct': [-35.0, 35.0], 'buy_premium_min_low_return_3d_pct': [-75.0, 130.0], 'buy_premium_min_low_return_5d_pct': [-90.0, 300.0], 'buy_premium_return_1d_pct': [-35.0, 35.0], 'buy_premium_return_3d_pct': [-75.0, 130.0], 'buy_premium_return_5d_pct': [-90.0, 300.0], 'max_high_return_1d_pct': [-35.0, 35.0], 'max_high_return_3d_pct': [-75.0, 130.0], 'max_high_return_5d_pct': [-90.0, 300.0], 'min_low_return_1d_pct': [-35.0, 35.0], 'min_low_return_3d_pct': [-75.0, 130.0], 'min_low_return_5d_pct': [-90.0, 300.0], 'return_1d_pct': [-35.0, 35.0], 'return_3d_pct': [-75.0, 130.0], 'return_5d_pct': [-90.0, 300.0]}, 'column_violations': {'buy_premium_max_high_return_1d_pct': 2673, 'buy_premium_max_high_return_3d_pct': 1838, 'buy_premium_max_high_return_5d_pct': 1664, 'buy_premium_min_low_return_1d_pct': 2508, 'buy_premium_min_low_return_3d_pct': 1817, 'buy_premium_min_low_return_5d_pct': 1067, 'buy_premium_return_1d_pct': 2532, 'buy_premium_return_3d_pct': 1814, 'buy_premium_return_5d_pct': 1245, 'max_high_return_1d_pct': 2724, 'max_high_return_3d_pct': 1849, 'max_high_return_5d_pct': 1678, 'min_low_return_1d_pct': 2500, 'min_low_return_3d_pct': 1824, 'min_low_return_5d_pct': 1139, 'return_1d_pct': 2554, 'return_3d_pct': 1816, 'return_5d_pct': 1314}, 'mode': 'kr_price_limit', 'remaining_rows': 163530, 'removed_rows': 2788}, 'created_at': '2026-06-11T15:14:35.234418+00:00'}`
- evaluation: `{'planned_combinations': 32, 'evaluated_combinations': 32, 'eval_workers': 1, 'elapsed_sec': 129.989, 'combinations_per_sec': 0.246}`
- prepared_rows: `163530`
- evaluated_combinations: `32`
- ok_combinations: `32`
- final_model: `{'saved': False, 'reason': 'not_promotable'}`
- promotion_verdict: `{'promotable': False, 'blocking_reasons': ['sample_too_small', 'min_mfe_5d_lt_1p5', 'min_low_5d_below_10', 'fold_min_low_5d_below_10'], 'risk_gate': {'pass': False, 'risk_score': 196.302528, 'blocking_reasons': ['min_low_5d_below_10', 'fold_min_low_5d_below_10'], 'components': {'stop5_pct': 69.2308, 'bad_path_pct': 69.2308, 'stop_before_target_5d_pct': 69.2308, 'target_before_stop_5d_pct': 84.6154, 'min_1d_pct': -5.854038, 'min_min_low_5d_pct': -22.268908, 'max_fold_stop5_pct': 100.0, 'max_fold_bad_path_pct': 100.0, 'min_fold_min_low_5d_pct': -22.268908, 'min_fold_target_before_stop_5d_pct': 75.0, 'raw_key': 'hit5_5d_pct', 'raw_pct': 84.6154, 'guard_key': 'hit5_dd10_5d_pct', 'guard_pct': 76.9231, 'guard_raw_ratio': 0.909091}}, 'baseline_rows_considered': [{'baseline': 'current_top1', 'topn': 1, 'win_3d_pct': 45.4545, 'win_5d_pct': 45.4545, 'avg_3d_pct': -10.331714, 'avg_5d_pct': -15.078038, 'min_5d_pct': -34.734599}, {'baseline': 'current_top1_exception', 'topn': 1, 'win_3d_pct': 45.4545, 'win_5d_pct': 45.4545, 'avg_3d_pct': -10.331714, 'avg_5d_pct': -15.078038, 'min_5d_pct': -34.734599}, {'baseline': 'decision_score_top1', 'topn': 1, 'win_3d_pct': 41.6667, 'win_5d_pct': 41.6667, 'avg_3d_pct': -9.533797, 'avg_5d_pct': -11.293783, 'min_5d_pct': -26.540665}, {'baseline': 'ml_prob_top1', 'topn': 1, 'win_3d_pct': 41.6667, 'win_5d_pct': 41.6667, 'avg_3d_pct': -7.990635, 'avg_5d_pct': -9.83883, 'min_5d_pct': -23.527494}, {'baseline': 'current_top3', 'topn': 3, 'win_3d_pct': 33.3333, 'win_5d_pct': 39.3939, 'avg_3d_pct': -8.689944, 'avg_5d_pct': -10.274963, 'min_5d_pct': -34.734599}, {'baseline': 'current_top3_exception', 'topn': 3, 'win_3d_pct': 33.3333, 'win_5d_pct': 39.3939, 'avg_3d_pct': -8.689944, 'avg_5d_pct': -10.274963, 'min_5d_pct': -34.734599}, {'baseline': 'decision_score_top3', 'topn': 3, 'win_3d_pct': 40.0, 'win_5d_pct': 45.7143, 'avg_3d_pct': -8.292346, 'avg_5d_pct': -9.609434, 'min_5d_pct': -31.988502}, {'baseline': 'ml_prob_top3', 'topn': 3, 'win_3d_pct': 31.4286, 'win_5d_pct': 40.0, 'avg_3d_pct': -8.76781, 'avg_5d_pct': -7.795623, 'min_5d_pct': -23.527494}]}`

## Best
- market: `KOSDAQ`
- label: `touch5_dd10_5d`
- feature_set: `failure_risk_augmented`
- model: `hist_gb`
- topn: `1`
- selection_rule: `top1`
- quality_score: `588.979568`
- n / active_runs / active_days: `13` / `12` / `6`
- win_metric_semantics: `target_touch_mfe_ge_5pct_after_buy_premium`
- close_win_metric_semantics: `defensive_close_return_gt_0_after_buy_premium`
- 1d target-touch win / close defense / close avg/min/max: `61.5385` / `61.5385` / `5.185582` / `-5.854038` / `26.641166`
- 3d target-touch win / close defense / close avg/min/max: `69.2308` / `69.2308` / `12.200735` / `-8.574541` / `70.405596`
- 5d target-touch win / close defense / close avg/min/max: `84.6154` / `84.6154` / `15.838428` / `-11.10333` / `70.577897`
- target_before_stop_5d_pct: `84.6154`
- hit5/hit10 5d pct: `84.6154` / `69.2308`
- guarded hit5/hit10 5d pct: `30.7692` / `30.7692`
- 5d max-high avg/min/max: `22.44024` / `-2.13775` / `80.743651`
- stop5_pct / bad_path_pct: `69.2308` / `69.2308`

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
- `current_top1` top1: n=11, 1d_target=36.3636% close=27.2727%/-6.621936%, 3d_target=45.4545% close=9.0909%/-10.331714%, 5d_target=45.4545% close=9.0909%/-15.078038%, hit5=45.4545%, hit10=27.2727%, mfe5=4.991105%, min5=-34.734599%, max5=14.560917%
- `current_top1_exception` top1: n=11, 1d_target=36.3636% close=27.2727%/-6.621936%, 3d_target=45.4545% close=9.0909%/-10.331714%, 5d_target=45.4545% close=9.0909%/-15.078038%, hit5=45.4545%, hit10=27.2727%, mfe5=4.991105%, min5=-34.734599%, max5=14.560917%
- `decision_score_top1` top1: n=12, 1d_target=41.6667% close=25.0%/-4.158594%, 3d_target=41.6667% close=8.3333%/-9.533797%, 5d_target=41.6667% close=8.3333%/-11.293783%, hit5=41.6667%, hit10=25.0%, mfe5=5.511696%, min5=-26.540665%, max5=21.273581%
- `ml_prob_top1` top1: n=12, 1d_target=33.3333% close=16.6667%/-5.467962%, 3d_target=41.6667% close=25.0%/-7.990635%, 5d_target=41.6667% close=25.0%/-9.83883%, hit5=41.6667%, hit10=25.0%, mfe5=3.811867%, min5=-23.527494%, max5=5.597795%
- `current_top3` top3: n=33, 1d_target=30.303% close=24.2424%/-5.017534%, 3d_target=33.3333% close=15.1515%/-8.689944%, 5d_target=39.3939% close=15.1515%/-10.274963%, hit5=39.3939%, hit10=27.2727%, mfe5=6.574574%, min5=-34.734599%, max5=29.973932%
- `current_top3_exception` top3: n=33, 1d_target=30.303% close=24.2424%/-5.017534%, 3d_target=33.3333% close=15.1515%/-8.689944%, 5d_target=39.3939% close=15.1515%/-10.274963%, hit5=39.3939%, hit10=27.2727%, mfe5=6.574574%, min5=-34.734599%, max5=29.973932%
- `decision_score_top3` top3: n=35, 1d_target=34.2857% close=28.5714%/-3.9412%, 3d_target=40.0% close=17.1429%/-8.292346%, 5d_target=45.7143% close=17.1429%/-9.609434%, hit5=45.7143%, hit10=34.2857%, mfe5=7.09501%, min5=-31.988502%, max5=21.273581%
- `ml_prob_top3` top3: n=35, 1d_target=22.8571% close=14.2857%/-5.661385%, 3d_target=31.4286% close=22.8571%/-8.76781%, 5d_target=40.0% close=25.7143%/-7.795623%, hit5=40.0%, hit10=31.4286%, mfe5=4.495823%, min5=-23.527494%, max5=13.934463%

## Top Results
1. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top1: score=588.979568, n=13, 1d_target=61.5385% close=61.5385%/5.185582%, 3d_target=69.2308% close=69.2308%/12.200735%, 5d_target=84.6154% close=84.6154%/15.838428%, hit5=84.6154%, hit10=69.2308%, mfe5=22.44024%, min5=-11.10333%, max5=70.577897%
2. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `lightgbm` top1: score=388.853477, n=13, 1d_target=38.4615% close=38.4615%/2.36411%, 3d_target=61.5385% close=76.9231%/3.175271%, 5d_target=84.6154% close=61.5385%/6.424331%, hit5=84.6154%, hit10=53.8462%, mfe5=14.261023%, min5=-11.10333%, max5=21.613002%
3. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `lightgbm` top1: score=284.259452, n=13, 1d_target=38.4615% close=38.4615%/-1.057605%, 3d_target=53.8462% close=76.9231%/3.567015%, 5d_target=84.6154% close=69.2308%/4.652014%, hit5=84.6154%, hit10=46.1538%, mfe5=11.283114%, min5=-11.10333%, max5=21.613002%
4. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top3: score=719.221643, n=38, 1d_target=44.7368% close=39.4737%/1.409145%, 3d_target=71.0526% close=68.4211%/6.308031%, 5d_target=89.4737% close=78.9474%/15.031321%, hit5=89.4737%, hit10=81.5789%, mfe5=28.305271%, min5=-18.399984%, max5=70.577897%
5. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `lightgbm` top3: score=493.873382, n=38, 1d_target=50.0% close=50.0%/1.087297%, 3d_target=76.3158% close=76.3158%/4.767651%, 5d_target=89.4737% close=76.3158%/7.828731%, hit5=89.4737%, hit10=76.3158%, mfe5=17.743628%, min5=-18.399984%, max5=38.031116%
6. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `hist_gb` top1: score=391.979138, n=13, 1d_target=30.7692% close=30.7692%/-0.41888%, 3d_target=38.4615% close=46.1538%/2.922042%, 5d_target=76.9231% close=76.9231%/11.355347%, hit5=76.9231%, hit10=53.8462%, mfe5=16.015898%, min5=-11.10333%, max5=65.347229%
7. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `hist_gb` top3: score=571.354775, n=38, 1d_target=42.1053% close=36.8421%/0.078387%, 3d_target=63.1579% close=55.2632%/3.755205%, 5d_target=81.5789% close=68.4211%/10.053483%, hit5=81.5789%, hit10=68.4211%, mfe5=23.628496%, min5=-18.399984%, max5=70.577897%
8. `KOSPI` `touch5_dd10_5d` `flow_no_gate` `lightgbm` top1: score=-64.092984, n=22, 1d_target=13.6364% close=18.1818%/-1.829652%, 3d_target=18.1818% close=9.0909%/-8.922232%, 5d_target=18.1818% close=13.6364%/-9.187176%, hit5=18.1818%, hit10=13.6364%, mfe5=3.146568%, min5=-19.69441%, max5=6.317361%
9. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `lightgbm` top3: score=521.054557, n=38, 1d_target=47.3684% close=47.3684%/0.002057%, 3d_target=68.4211% close=65.7895%/2.835477%, 5d_target=86.8421% close=81.5789%/11.919534%, hit5=86.8421%, hit10=73.6842%, mfe5=22.469284%, min5=-18.399984%, max5=62.523901%
10. `KOSPI` `touch5_dd10_5d` `failure_risk_numeric` `lightgbm` top1: score=538.523212, n=22, 1d_target=9.0909% close=22.7273%/-2.206952%, 3d_target=50.0% close=54.5455%/11.229826%, 5d_target=68.1818% close=63.6364%/2.381375%, hit5=68.1818%, hit10=63.6364%, mfe5=25.216459%, min5=-23.346474%, max5=24.04962%
11. `KOSPI` `touch5_dd10_5d` `failure_risk_augmented` `lightgbm` top1: score=537.927307, n=22, 1d_target=9.0909% close=22.7273%/-2.294042%, 3d_target=45.4545% close=59.0909%/11.197383%, 5d_target=63.6364% close=63.6364%/2.807121%, hit5=63.6364%, hit10=59.0909%, mfe5=25.355971%, min5=-23.346474%, max5=24.04962%
12. `KOSDAQ` `touch5_dd10_5d` `wide_theme` `hist_gb` top1: score=33.629238, n=13, 1d_target=30.7692% close=30.7692%/-3.128209%, 3d_target=30.7692% close=7.6923%/-5.958364%, 5d_target=38.4615% close=23.0769%/-5.82775%, hit5=38.4615%, hit10=23.0769%, mfe5=6.427709%, min5=-16.955017%, max5=17.158897%
13. `KOSDAQ` `touch5_dd10_5d` `wide_theme` `lightgbm` top3: score=127.941107, n=38, 1d_target=26.3158% close=26.3158%/-1.270659%, 3d_target=47.3684% close=31.5789%/-2.795025%, 5d_target=50.0% close=31.5789%/-3.09992%, hit5=50.0%, hit10=34.2105%, mfe5=11.272649%, min5=-19.937915%, max5=35.169376%
14. `KOSDAQ` `touch5_dd10_5d` `flow_no_gate` `lightgbm` top3: score=66.0654, n=38, 1d_target=23.6842% close=23.6842%/-1.759233%, 3d_target=42.1053% close=26.3158%/-4.286058%, 5d_target=47.3684% close=23.6842%/-6.113607%, hit5=47.3684%, hit10=31.5789%, mfe5=9.003804%, min5=-18.399984%, max5=16.86595%
15. `KOSDAQ` `touch5_dd10_5d` `flow_no_gate` `lightgbm` top1: score=87.750548, n=13, 1d_target=15.3846% close=15.3846%/-3.308107%, 3d_target=38.4615% close=23.0769%/-3.080724%, 5d_target=46.1538% close=30.7692%/-3.162521%, hit5=46.1538%, hit10=38.4615%, mfe5=10.445242%, min5=-16.955017%, max5=16.713352%
16. `KOSDAQ` `touch5_dd10_5d` `wide_theme` `lightgbm` top1: score=37.387786, n=13, 1d_target=23.0769% close=23.0769%/-2.908639%, 3d_target=30.7692% close=15.3846%/-4.551716%, 5d_target=38.4615% close=23.0769%/-5.319415%, hit5=38.4615%, hit10=30.7692%, mfe5=8.981583%, min5=-16.955017%, max5=13.694942%
17. `KOSPI` `touch5_dd10_5d` `failure_risk_augmented` `lightgbm` top3: score=290.826104, n=66, 1d_target=27.2727% close=37.8788%/0.354921%, 3d_target=53.0303% close=54.5455%/4.678525%, 5d_target=72.7273% close=62.1212%/1.83121%, hit5=72.7273%, hit10=50.0%, mfe5=17.97741%, min5=-26.369725%, max5=34.120172%
18. `KOSDAQ` `touch5_dd10_5d` `flow_no_gate` `hist_gb` top3: score=39.071633, n=38, 1d_target=18.4211% close=18.4211%/-3.696642%, 3d_target=39.4737% close=26.3158%/-4.354548%, 5d_target=47.3684% close=26.3158%/-4.989135%, hit5=47.3684%, hit10=28.9474%, mfe5=8.53742%, min5=-22.840233%, max5=26.76356%
19. `KOSPI` `touch5_dd10_5d` `wide_theme` `lightgbm` top1: score=-140.677927, n=22, 1d_target=18.1818% close=22.7273%/-1.566308%, 3d_target=18.1818% close=13.6364%/-8.115259%, 5d_target=18.1818% close=9.0909%/-9.080174%, hit5=18.1818%, hit10=18.1818%, mfe5=3.310619%, min5=-19.69441%, max5=6.317361%
20. `KOSDAQ` `touch5_dd10_5d` `wide_theme` `hist_gb` top3: score=43.683502, n=38, 1d_target=23.6842% close=23.6842%/-2.928074%, 3d_target=42.1053% close=21.0526%/-4.370751%, 5d_target=47.3684% close=23.6842%/-4.151762%, hit5=47.3684%, hit10=31.5789%, mfe5=9.121023%, min5=-18.399984%, max5=35.169376%

## Top KIS Results
