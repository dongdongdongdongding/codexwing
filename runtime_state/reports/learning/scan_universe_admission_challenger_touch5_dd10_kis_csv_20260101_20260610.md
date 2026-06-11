# Scan Universe Admission Challenger

- generated_at: `2026-06-11T15:19:41.713773+00:00`
- source: `scan_universe_snapshots`
- grid_preset: `custom`
- fetch_strategy: `{'mode': 'prepared_cache_hit', 'rows': 166318, 'elapsed_sec': 0.0}`
- prepared_cache: `{'enabled': True, 'mode': 'hit', 'path': 'runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_csv_cache_20260101_20260610.pkl', 'meta_path': 'runtime_state/reports/learning/scan_universe_admission_challenger_touch5_dd10_kis_csv_cache_20260101_20260610.pkl.meta.json', 'prepared_rows': 163530, 'raw_rows': 166318, 'return_sanity': {'bounds': {'buy_premium_max_high_return_1d_pct': [-35.0, 35.0], 'buy_premium_max_high_return_3d_pct': [-75.0, 130.0], 'buy_premium_max_high_return_5d_pct': [-90.0, 300.0], 'buy_premium_min_low_return_1d_pct': [-35.0, 35.0], 'buy_premium_min_low_return_3d_pct': [-75.0, 130.0], 'buy_premium_min_low_return_5d_pct': [-90.0, 300.0], 'buy_premium_return_1d_pct': [-35.0, 35.0], 'buy_premium_return_3d_pct': [-75.0, 130.0], 'buy_premium_return_5d_pct': [-90.0, 300.0], 'max_high_return_1d_pct': [-35.0, 35.0], 'max_high_return_3d_pct': [-75.0, 130.0], 'max_high_return_5d_pct': [-90.0, 300.0], 'min_low_return_1d_pct': [-35.0, 35.0], 'min_low_return_3d_pct': [-75.0, 130.0], 'min_low_return_5d_pct': [-90.0, 300.0], 'return_1d_pct': [-35.0, 35.0], 'return_3d_pct': [-75.0, 130.0], 'return_5d_pct': [-90.0, 300.0]}, 'column_violations': {'buy_premium_max_high_return_1d_pct': 2673, 'buy_premium_max_high_return_3d_pct': 1838, 'buy_premium_max_high_return_5d_pct': 1664, 'buy_premium_min_low_return_1d_pct': 2508, 'buy_premium_min_low_return_3d_pct': 1817, 'buy_premium_min_low_return_5d_pct': 1067, 'buy_premium_return_1d_pct': 2532, 'buy_premium_return_3d_pct': 1814, 'buy_premium_return_5d_pct': 1245, 'max_high_return_1d_pct': 2724, 'max_high_return_3d_pct': 1849, 'max_high_return_5d_pct': 1678, 'min_low_return_1d_pct': 2500, 'min_low_return_3d_pct': 1824, 'min_low_return_5d_pct': 1139, 'return_1d_pct': 2554, 'return_3d_pct': 1816, 'return_5d_pct': 1314}, 'mode': 'kr_price_limit', 'remaining_rows': 163530, 'removed_rows': 2788}, 'created_at': '2026-06-11T15:14:35.234418+00:00'}`
- evaluation: `{'planned_combinations': 64, 'evaluated_combinations': 64, 'eval_workers': 1, 'elapsed_sec': 257.799, 'combinations_per_sec': 0.248}`
- prepared_rows: `163530`
- evaluated_combinations: `64`
- ok_combinations: `64`
- final_model: `{'saved': False, 'reason': 'not_promotable'}`
- promotion_verdict: `{'promotable': False, 'blocking_reasons': ['active_runs_lt_12', 'active_days_lt_6', 'sample_too_small'], 'risk_gate': {'pass': True, 'risk_score': 0.0, 'blocking_reasons': [], 'components': {'stop5_pct': 100.0, 'bad_path_pct': 100.0, 'stop_before_target_5d_pct': 100.0, 'target_before_stop_5d_pct': 100.0, 'min_1d_pct': -1.960784, 'min_min_low_5d_pct': -9.653092, 'max_fold_stop5_pct': 100.0, 'max_fold_bad_path_pct': 100.0, 'min_fold_min_low_5d_pct': -9.653092, 'min_fold_target_before_stop_5d_pct': 100.0, 'raw_key': 'hit5_5d_pct', 'raw_pct': 100.0, 'guard_key': 'hit5_dd10_5d_pct', 'guard_pct': 100.0, 'guard_raw_ratio': 1.0}}, 'baseline_rows_considered': [{'baseline': 'current_top1', 'topn': 1, 'win_3d_pct': 45.4545, 'win_5d_pct': 45.4545, 'avg_3d_pct': -10.331714, 'avg_5d_pct': -15.078038, 'min_5d_pct': -34.734599}, {'baseline': 'current_top1_exception', 'topn': 1, 'win_3d_pct': 45.4545, 'win_5d_pct': 45.4545, 'avg_3d_pct': -10.331714, 'avg_5d_pct': -15.078038, 'min_5d_pct': -34.734599}, {'baseline': 'decision_score_top1', 'topn': 1, 'win_3d_pct': 41.6667, 'win_5d_pct': 41.6667, 'avg_3d_pct': -9.533797, 'avg_5d_pct': -11.293783, 'min_5d_pct': -26.540665}, {'baseline': 'ml_prob_top1', 'topn': 1, 'win_3d_pct': 41.6667, 'win_5d_pct': 41.6667, 'avg_3d_pct': -7.990635, 'avg_5d_pct': -9.83883, 'min_5d_pct': -23.527494}, {'baseline': 'current_top3', 'topn': 3, 'win_3d_pct': 33.3333, 'win_5d_pct': 39.3939, 'avg_3d_pct': -8.689944, 'avg_5d_pct': -10.274963, 'min_5d_pct': -34.734599}, {'baseline': 'current_top3_exception', 'topn': 3, 'win_3d_pct': 33.3333, 'win_5d_pct': 39.3939, 'avg_3d_pct': -8.689944, 'avg_5d_pct': -10.274963, 'min_5d_pct': -34.734599}, {'baseline': 'decision_score_top3', 'topn': 3, 'win_3d_pct': 40.0, 'win_5d_pct': 45.7143, 'avg_3d_pct': -8.292346, 'avg_5d_pct': -9.609434, 'min_5d_pct': -31.988502}, {'baseline': 'ml_prob_top3', 'topn': 3, 'win_3d_pct': 31.4286, 'win_5d_pct': 40.0, 'avg_3d_pct': -8.76781, 'avg_5d_pct': -7.795623, 'min_5d_pct': -23.527494}]}`

## Best
- market: `KOSDAQ`
- label: `touch5_dd10_5d`
- feature_set: `failure_risk_augmented`
- model: `hist_gb`
- topn: `1`
- selection_rule: `top1_p0.60`
- quality_score: `164.411073`
- n / active_runs / active_days: `3` / `3` / `2`
- win_metric_semantics: `target_touch_mfe_ge_5pct_after_buy_premium`
- close_win_metric_semantics: `defensive_close_return_gt_0_after_buy_premium`
- 1d target-touch win / close defense / close avg/min/max: `33.3333` / `33.3333` / `-0.301659` / `-1.960784` / `3.016591`
- 3d target-touch win / close defense / close avg/min/max: `33.3333` / `100.0` / `3.783308` / `0.395928` / `10.558069`
- 5d target-touch win / close defense / close avg/min/max: `100.0` / `100.0` / `7.445114` / `7.088989` / `7.623177`
- target_before_stop_5d_pct: `100.0`
- hit5/hit10 5d pct: `100.0` / `33.3333`
- guarded hit5/hit10 5d pct: `0.0` / `0.0`
- 5d max-high avg/min/max: `9.217362` / `8.09452` / `11.463047`
- stop5_pct / bad_path_pct: `100.0` / `100.0`

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
1. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top1_p0.60: score=164.411073, n=3, 1d_target=33.3333% close=33.3333%/-0.301659%, 3d_target=33.3333% close=100.0%/3.783308%, 5d_target=100.0% close=100.0%/7.445114%, hit5=100.0%, hit10=33.3333%, mfe5=9.217362%, min5=7.088989%, max5=7.623177%
2. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `hist_gb` top1_p0.60: score=118.671039, n=3, 1d_target=0.0% close=0.0%/-2.013072%, 3d_target=0.0% close=100.0%/0.342383%, 5d_target=100.0% close=100.0%/7.565778%, hit5=100.0%, hit10=0.0%, mfe5=8.03687%, min5=7.45098%, max5=7.623177%
3. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `lightgbm` top1_p0.60: score=652.58427, n=11, 1d_target=45.4545% close=45.4545%/3.681225%, 3d_target=72.7273% close=90.9091%/5.016019%, 5d_target=100.0% close=72.7273%/8.860477%, hit5=100.0%, hit10=63.6364%, mfe5=16.607596%, min5=-7.186225%, max5=21.613002%
4. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top3_p0.60: score=431.346324, n=9, 1d_target=33.3333% close=33.3333%/-0.484754%, 3d_target=66.6667% close=100.0%/7.643354%, 5d_target=100.0% close=100.0%/8.29537%, hit5=100.0%, hit10=66.6667%, mfe5=25.840379%, min5=5.72489%, max5=11.194638%
5. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `hist_gb` top3_p0.60: score=648.607143, n=9, 1d_target=11.1111% close=11.1111%/-2.607334%, 3d_target=66.6667% close=100.0%/6.844517%, 5d_target=100.0% close=100.0%/8.074937%, hit5=100.0%, hit10=66.6667%, mfe5=38.07473%, min5=5.72489%, max5=10.956545%
6. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top1: score=588.979568, n=13, 1d_target=61.5385% close=61.5385%/5.185582%, 3d_target=69.2308% close=69.2308%/12.200735%, 5d_target=84.6154% close=84.6154%/15.838428%, hit5=84.6154%, hit10=69.2308%, mfe5=22.44024%, min5=-11.10333%, max5=70.577897%
7. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `lightgbm` top1: score=388.853477, n=13, 1d_target=38.4615% close=38.4615%/2.36411%, 3d_target=61.5385% close=76.9231%/3.175271%, 5d_target=84.6154% close=61.5385%/6.424331%, hit5=84.6154%, hit10=53.8462%, mfe5=14.261023%, min5=-11.10333%, max5=21.613002%
8. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `lightgbm` top1: score=284.259452, n=13, 1d_target=38.4615% close=38.4615%/-1.057605%, 3d_target=53.8462% close=76.9231%/3.567015%, 5d_target=84.6154% close=69.2308%/4.652014%, hit5=84.6154%, hit10=46.1538%, mfe5=11.283114%, min5=-11.10333%, max5=21.613002%
9. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `lightgbm` top1_p0.60: score=358.798694, n=12, 1d_target=41.6667% close=41.6667%/-0.657902%, 3d_target=58.3333% close=83.3333%/4.307861%, 5d_target=91.6667% close=75.0%/5.276816%, hit5=91.6667%, hit10=50.0%, mfe5=12.401519%, min5=-11.10333%, max5=21.613002%
10. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `hist_gb` top3: score=719.221643, n=38, 1d_target=44.7368% close=39.4737%/1.409145%, 3d_target=71.0526% close=68.4211%/6.308031%, 5d_target=89.4737% close=78.9474%/15.031321%, hit5=89.4737%, hit10=81.5789%, mfe5=28.305271%, min5=-18.399984%, max5=70.577897%
11. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `lightgbm` top3: score=493.873382, n=38, 1d_target=50.0% close=50.0%/1.087297%, 3d_target=76.3158% close=76.3158%/4.767651%, 5d_target=89.4737% close=76.3158%/7.828731%, hit5=89.4737%, hit10=76.3158%, mfe5=17.743628%, min5=-18.399984%, max5=38.031116%
12. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `hist_gb` top1: score=391.979138, n=13, 1d_target=30.7692% close=30.7692%/-0.41888%, 3d_target=38.4615% close=46.1538%/2.922042%, 5d_target=76.9231% close=76.9231%/11.355347%, hit5=76.9231%, hit10=53.8462%, mfe5=16.015898%, min5=-11.10333%, max5=65.347229%
13. `KOSDAQ` `touch5_dd10_5d` `failure_risk_augmented` `lightgbm` top3_p0.60: score=653.293588, n=33, 1d_target=54.5455% close=57.5758%/2.188784%, 3d_target=84.8485% close=87.8788%/7.006055%, 5d_target=100.0% close=87.8788%/10.195214%, hit5=100.0%, hit10=84.8485%, mfe5=20.035669%, min5=-7.186225%, max5=38.031116%
14. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `lightgbm` top3_p0.60: score=704.569829, n=34, 1d_target=52.9412% close=52.9412%/1.036433%, 3d_target=76.4706% close=73.5294%/4.697664%, 5d_target=97.0588% close=91.1765%/14.446763%, hit5=97.0588%, hit10=82.3529%, mfe5=25.245063%, min5=-11.10333%, max5=62.523901%
15. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `hist_gb` top3: score=571.354775, n=38, 1d_target=42.1053% close=36.8421%/0.078387%, 3d_target=63.1579% close=55.2632%/3.755205%, 5d_target=81.5789% close=68.4211%/10.053483%, hit5=81.5789%, hit10=68.4211%, mfe5=23.628496%, min5=-18.399984%, max5=70.577897%
16. `KOSDAQ` `touch5_dd10_5d` `wide_theme` `hist_gb` top1_p0.60: score=-11.3935, n=7, 1d_target=42.8571% close=42.8571%/-0.358757%, 3d_target=42.8571% close=14.2857%/-3.002846%, 5d_target=42.8571% close=28.5714%/-4.864171%, hit5=42.8571%, hit10=28.5714%, mfe5=9.811447%, min5=-16.955017%, max5=17.158897%
17. `KOSDAQ` `touch5_dd10_5d` `flow_no_gate` `hist_gb` top1_p0.60: score=-174.929526, n=5, 1d_target=20.0% close=20.0%/-1.887372%, 3d_target=20.0% close=0.0%/-5.768417%, 5d_target=20.0% close=20.0%/-8.00305%, hit5=20.0%, hit10=20.0%, mfe5=7.812871%, min5=-16.955017%, max5=17.158897%
18. `KOSPI` `touch5_dd10_5d` `flow_no_gate` `lightgbm` top1: score=-64.092984, n=22, 1d_target=13.6364% close=18.1818%/-1.829652%, 3d_target=18.1818% close=9.0909%/-8.922232%, 5d_target=18.1818% close=13.6364%/-9.187176%, hit5=18.1818%, hit10=13.6364%, mfe5=3.146568%, min5=-19.69441%, max5=6.317361%
19. `KOSPI` `touch5_dd10_5d` `flow_no_gate` `lightgbm` top1_p0.60: score=-64.092984, n=22, 1d_target=13.6364% close=18.1818%/-1.829652%, 3d_target=18.1818% close=9.0909%/-8.922232%, 5d_target=18.1818% close=13.6364%/-9.187176%, hit5=18.1818%, hit10=13.6364%, mfe5=3.146568%, min5=-19.69441%, max5=6.317361%
20. `KOSDAQ` `touch5_dd10_5d` `failure_risk_numeric` `lightgbm` top3: score=521.054557, n=38, 1d_target=47.3684% close=47.3684%/0.002057%, 3d_target=68.4211% close=65.7895%/2.835477%, 5d_target=86.8421% close=81.5789%/11.919534%, hit5=86.8421%, hit10=73.6842%, mfe5=22.469284%, min5=-18.399984%, max5=62.523901%

## Top KIS Results
