# Scan Universe Admission Challenger

- generated_at: `2026-06-08T08:13:18.080212+00:00`
- source: `scan_universe_snapshots`
- grid_preset: `kis_operational_fast`
- fetch_strategy: `{'mode': 'id_chunks', 'chunks': [{'type': 'id', 'min_id': 1, 'max_id': 5000, 'rows': 3348}, {'type': 'id', 'min_id': 5001, 'max_id': 10000, 'rows': 2911}], 'requested_limit': 0, 'fetch_chunk_days': 0, 'fetch_id_chunk_size': 5000, 'fetch_timeout_sec': 5.0, 'max_fetch_chunks': 2, 'truncated_by_max_fetch_chunks': False, 'elapsed_sec': 47.4, 'rows': 6259}`
- prepared_cache: `{'enabled': True, 'mode': 'write', 'path': '/private/tmp/kis_operational_fast_smoke.prepared.pkl', 'meta_path': '/private/tmp/kis_operational_fast_smoke.prepared.pkl.meta.json', 'prepared_rows': 5968, 'raw_rows': 6259, 'prepare_elapsed_sec': 0.699}`
- evaluation: `{'planned_combinations': 432, 'evaluated_combinations': 432, 'eval_workers': 2, 'elapsed_sec': 2.202, 'combinations_per_sec': 196.141}`
- prepared_rows: `5968`
- evaluated_combinations: `432`
- ok_combinations: `0`
- final_model: `{'saved': False, 'reason': 'no_best'}`
- promotion_verdict: `{'promotable': False, 'reason': 'no_valid_challenger'}`

## Best
- market: `None`
- label: `None`
- feature_set: `None`
- model: `None`
- topn: `None`
- selection_rule: `None`
- quality_score: `None`
- n / active_runs / active_days: `None` / `None` / `None`
- 1d win/avg/min/max: `None` / `None` / `None` / `None`
- 3d win/avg/min/max: `None` / `None` / `None` / `None`
- 5d win/avg/min/max: `None` / `None` / `None` / `None`
- target_before_stop_5d_pct: `None`
- hit5/hit10 5d pct: `None` / `None`
- guarded hit5/hit10 5d pct: `None` / `None`
- 5d max-high avg/min/max: `None` / `None` / `None`
- stop5_pct / bad_path_pct: `None` / `None`

## Best KIS
- market: `None`
- label: `None`
- feature_set: `None`
- model: `None`
- selection_rule: `None`
- quality_score: `None`
- n / active_runs / active_days: `None` / `None` / `None`
- 1d win/avg/min/max: `None` / `None` / `None` / `None`
- 3d win/avg/min/max: `None` / `None` / `None` / `None`
- 5d win/avg/min/max: `None` / `None` / `None` / `None`
- hit5/hit10 5d pct: `None` / `None`
- promotion_verdict: `{'promotable': False, 'reason': 'no_valid_challenger'}`

## KIS Feature Readiness
- status: `ok`
- required_rows / required_days: `120` / `2`
- families: `{'sidecar': {'rows': 5967, 'outcome_label_rows': 5967, 'unique_runs': 6, 'unique_days': 2, 'mature_for_training': True, 'date_coverage': {'2026-05-27': {'rows': 2772, 'outcome_label_rows': 2772, 'unique_runs': 3, 'rows_by_market': {'KOSDAQ': 1593, 'KOSPI': 1179}}, '2026-05-28': {'rows': 3195, 'outcome_label_rows': 3195, 'unique_runs': 3, 'rows_by_market': {'KOSPI': 1599, 'KOSDAQ': 1596}}}}, 'prefilter': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'theme_news': {'rows': 5967, 'outcome_label_rows': 5967, 'unique_runs': 6, 'unique_days': 2, 'mature_for_training': True, 'date_coverage': {'2026-05-27': {'rows': 2772, 'outcome_label_rows': 2772, 'unique_runs': 3, 'rows_by_market': {'KOSDAQ': 1593, 'KOSPI': 1179}}, '2026-05-28': {'rows': 3195, 'outcome_label_rows': 3195, 'unique_runs': 3, 'rows_by_market': {'KOSPI': 1599, 'KOSDAQ': 1596}}}}, 'any_kis': {'rows': 5967, 'outcome_label_rows': 5967, 'unique_runs': 6, 'unique_days': 2, 'mature_for_training': True, 'date_coverage': {'2026-05-27': {'rows': 2772, 'outcome_label_rows': 2772, 'unique_runs': 3, 'rows_by_market': {'KOSDAQ': 1593, 'KOSPI': 1179}}, '2026-05-28': {'rows': 3195, 'outcome_label_rows': 3195, 'unique_runs': 3, 'rows_by_market': {'KOSPI': 1599, 'KOSDAQ': 1596}}}}}`
- by_market: `{'KOSDAQ': {'sidecar': {'rows': 3189, 'outcome_label_rows': 3189, 'unique_runs': 2, 'unique_days': 2, 'mature_for_training': True, 'date_coverage': {'2026-05-27': {'rows': 1593, 'outcome_label_rows': 1593, 'unique_runs': 1, 'rows_by_market': {'KOSDAQ': 1593}}, '2026-05-28': {'rows': 1596, 'outcome_label_rows': 1596, 'unique_runs': 1, 'rows_by_market': {'KOSDAQ': 1596}}}}, 'prefilter': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'theme_news': {'rows': 3189, 'outcome_label_rows': 3189, 'unique_runs': 2, 'unique_days': 2, 'mature_for_training': True, 'date_coverage': {'2026-05-27': {'rows': 1593, 'outcome_label_rows': 1593, 'unique_runs': 1, 'rows_by_market': {'KOSDAQ': 1593}}, '2026-05-28': {'rows': 1596, 'outcome_label_rows': 1596, 'unique_runs': 1, 'rows_by_market': {'KOSDAQ': 1596}}}}, 'any_kis': {'rows': 3189, 'outcome_label_rows': 3189, 'unique_runs': 2, 'unique_days': 2, 'mature_for_training': True, 'date_coverage': {'2026-05-27': {'rows': 1593, 'outcome_label_rows': 1593, 'unique_runs': 1, 'rows_by_market': {'KOSDAQ': 1593}}, '2026-05-28': {'rows': 1596, 'outcome_label_rows': 1596, 'unique_runs': 1, 'rows_by_market': {'KOSDAQ': 1596}}}}}, 'KOSPI': {'sidecar': {'rows': 2778, 'outcome_label_rows': 2778, 'unique_runs': 4, 'unique_days': 2, 'mature_for_training': True, 'date_coverage': {'2026-05-27': {'rows': 1179, 'outcome_label_rows': 1179, 'unique_runs': 2, 'rows_by_market': {'KOSPI': 1179}}, '2026-05-28': {'rows': 1599, 'outcome_label_rows': 1599, 'unique_runs': 2, 'rows_by_market': {'KOSPI': 1599}}}}, 'prefilter': {'rows': 0, 'outcome_label_rows': 0, 'unique_runs': 0, 'unique_days': 0, 'mature_for_training': False, 'date_coverage': {}}, 'theme_news': {'rows': 2778, 'outcome_label_rows': 2778, 'unique_runs': 4, 'unique_days': 2, 'mature_for_training': True, 'date_coverage': {'2026-05-27': {'rows': 1179, 'outcome_label_rows': 1179, 'unique_runs': 2, 'rows_by_market': {'KOSPI': 1179}}, '2026-05-28': {'rows': 1599, 'outcome_label_rows': 1599, 'unique_runs': 2, 'rows_by_market': {'KOSPI': 1599}}}}, 'any_kis': {'rows': 2778, 'outcome_label_rows': 2778, 'unique_runs': 4, 'unique_days': 2, 'mature_for_training': True, 'date_coverage': {'2026-05-27': {'rows': 1179, 'outcome_label_rows': 1179, 'unique_runs': 2, 'rows_by_market': {'KOSPI': 1179}}, '2026-05-28': {'rows': 1599, 'outcome_label_rows': 1599, 'unique_runs': 2, 'rows_by_market': {'KOSPI': 1599}}}}}}`
- theme_news_feature_fill: `{'kis_theme_news_available': 100.0, 'kis_theme_news_kis_backed': 100.0, 'kis_theme_news_evidence_score': 100.0, 'kis_theme_news_news_checked': 100.0, 'kis_theme_news_news_count': 100.0, 'kis_theme_news_headline_count': 100.0, 'kis_theme_news_positive_tag_count': 100.0, 'kis_theme_news_risk_tag_count': 100.0, 'kis_theme_news_vi_triggered': 1.441, 'kis_theme_news_level': 100.0, 'kis_theme_news_primary_theme': 1.491, 'kis_theme_news_kis_sector_name': 99.665, 'kis_theme_news_standard_industry_code': 99.983, 'kis_theme_news_top_positive_tag': 1.491, 'kis_theme_news_top_risk_tag': 1.257}`

## Baselines

## Top Results

## Top KIS Results
