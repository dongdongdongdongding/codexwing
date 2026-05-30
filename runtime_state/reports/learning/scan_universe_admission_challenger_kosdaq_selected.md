# Scan Universe Admission Challenger

- generated_at: `2026-05-30T18:28:04.682102+00:00`
- source: `scan_universe_snapshots`
- prepared_rows: `47234`
- evaluated_combinations: `2`
- ok_combinations: `2`
- final_model: `{'saved': True, 'model_path': '/Users/dongdong/Projects/codex_swing/swing-main/models/scan_universe_challengers/kosdaq__pos_5d__wide_no_theme__hist_gb__top1_p0p55.pkl', 'train_rows': 31385, 'positive_rate_pct': 25.5791}`
- promotion_verdict: `{'promotable': True, 'blocking_reasons': [], 'baseline_rows_considered': [{'baseline': 'current_top1', 'topn': 1, 'win_3d_pct': 31.5789, 'win_5d_pct': 15.7895, 'avg_3d_pct': -2.39611, 'avg_5d_pct': -6.875204, 'min_5d_pct': -21.787709}, {'baseline': 'current_top1_exception', 'topn': 1, 'win_3d_pct': 31.5789, 'win_5d_pct': 15.7895, 'avg_3d_pct': -2.39611, 'avg_5d_pct': -6.875204, 'min_5d_pct': -21.787709}, {'baseline': 'decision_score_top1', 'topn': 1, 'win_3d_pct': 31.5789, 'win_5d_pct': 21.0526, 'avg_3d_pct': -5.736885, 'avg_5d_pct': -8.983073, 'min_5d_pct': -27.225131}, {'baseline': 'ml_prob_top1', 'topn': 1, 'win_3d_pct': 47.3684, 'win_5d_pct': 47.3684, 'avg_3d_pct': -2.397758, 'avg_5d_pct': -1.907139, 'min_5d_pct': -36.839729}]}`

## Best
- market: `KOSDAQ`
- label: `pos_5d`
- feature_set: `wide_no_theme`
- model: `hist_gb`
- topn: `1`
- selection_rule: `top1_p0.55`
- quality_score: `566.928956`
- n / active_runs / active_days: `18` / `15` / `8`
- 1d win/avg/min/max: `77.7778` / `6.391591` / `-1.282051` / `19.56912`
- 3d win/avg/min/max: `100.0` / `10.630242` / `0.17138` / `23.35845`
- 5d win/avg/min/max: `94.4444` / `10.427779` / `-3.941731` / `21.723519`
- target_before_stop_5d_pct: `94.4444`
- stop5_pct / bad_path_pct: `11.1111` / `11.1111`

## Baselines
- `current_top1` top1: n=19, 1d=52.6316%/0.273893%, 3d=31.5789%/-2.39611%, 5d=15.7895%/-6.875204%, min5=-21.787709%, max5=12.783505%
- `current_top1_exception` top1: n=19, 1d=52.6316%/0.273893%, 3d=31.5789%/-2.39611%, 5d=15.7895%/-6.875204%, min5=-21.787709%, max5=12.783505%
- `decision_score_top1` top1: n=19, 1d=42.1053%/-2.423814%, 3d=31.5789%/-5.736885%, 5d=21.0526%/-8.983073%, min5=-27.225131%, max5=12.783505%
- `ml_prob_top1` top1: n=19, 1d=42.1053%/-1.431505%, 3d=47.3684%/-2.397758%, 5d=47.3684%/-1.907139%, min5=-36.839729%, max5=21.108179%

## Top Results
1. `KOSDAQ` `pos_5d` `wide_no_theme` `hist_gb` top1_p0.55: score=566.928956, n=18, 1d=77.7778%/6.391591%, 3d=100.0%/10.630242%, 5d=94.4444%/10.427779%, min5=-3.941731%, max5=21.723519%
2. `KOSDAQ` `pos_5d` `wide_no_theme` `hist_gb` top1: score=492.311889, n=24, 1d=79.1667%/5.985225%, 3d=79.1667%/9.821666%, 5d=79.1667%/9.977656%, min5=-13.614104%, max5=35.463918%
