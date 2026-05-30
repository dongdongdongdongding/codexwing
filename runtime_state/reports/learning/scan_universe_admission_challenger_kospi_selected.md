# Scan Universe Admission Challenger

- generated_at: `2026-05-30T18:29:50.266291+00:00`
- source: `scan_universe_snapshots`
- prepared_rows: `48654`
- evaluated_combinations: `2`
- ok_combinations: `2`
- final_model: `{'saved': True, 'model_path': '/Users/dongdong/Projects/codex_swing/swing-main/models/scan_universe_challengers/kospi__clean_5d__wide_no_theme__xgboost__top1_p0p60.pkl', 'train_rows': 36666, 'positive_rate_pct': 16.2167}`
- promotion_verdict: `{'promotable': True, 'blocking_reasons': [], 'baseline_rows_considered': [{'baseline': 'current_top1', 'topn': 1, 'win_3d_pct': 33.3333, 'win_5d_pct': 42.8571, 'avg_3d_pct': -4.802161, 'avg_5d_pct': 0.399651, 'min_5d_pct': -28.214732}, {'baseline': 'current_top1_exception', 'topn': 1, 'win_3d_pct': 33.3333, 'win_5d_pct': 42.8571, 'avg_3d_pct': -4.802161, 'avg_5d_pct': 0.399651, 'min_5d_pct': -28.214732}, {'baseline': 'decision_score_top1', 'topn': 1, 'win_3d_pct': 26.6667, 'win_5d_pct': 28.8889, 'avg_3d_pct': -5.277648, 'avg_5d_pct': -1.116457, 'min_5d_pct': -20.118343}, {'baseline': 'ml_prob_top1', 'topn': 1, 'win_3d_pct': 20.0, 'win_5d_pct': 42.2222, 'avg_3d_pct': -4.170032, 'avg_5d_pct': -3.266814, 'min_5d_pct': -20.093897}]}`

## Best
- market: `KOSPI`
- label: `clean_5d`
- feature_set: `wide_no_theme`
- model: `xgboost`
- topn: `1`
- selection_rule: `top1_p0.60`
- quality_score: `506.105083`
- n / active_runs / active_days: `24` / `24` / `6`
- 1d win/avg/min/max: `100.0` / `12.932358` / `0.504202` / `30.607287`
- 3d win/avg/min/max: `79.1667` / `7.771095` / `-2.184874` / `24.714829`
- 5d win/avg/min/max: `79.1667` / `7.110499` / `-2.521008` / `26.235741`
- target_before_stop_5d_pct: `79.1667`
- stop5_pct / bad_path_pct: `0.0` / `20.8333`

## Baselines
- `current_top1` top1: n=42, 1d=35.7143%/-1.274459%, 3d=33.3333%/-4.802161%, 5d=42.8571%/0.399651%, min5=-28.214732%, max5=52.473327%
- `current_top1_exception` top1: n=42, 1d=35.7143%/-1.274459%, 3d=33.3333%/-4.802161%, 5d=42.8571%/0.399651%, min5=-28.214732%, max5=52.473327%
- `decision_score_top1` top1: n=45, 1d=44.4444%/0.019452%, 3d=26.6667%/-5.277648%, 5d=28.8889%/-1.116457%, min5=-20.118343%, max5=112.16%
- `ml_prob_top1` top1: n=45, 1d=42.2222%/-1.067049%, 3d=20.0%/-4.170032%, 5d=42.2222%/-3.266814%, min5=-20.093897%, max5=13.170732%

## Top Results
1. `KOSPI` `clean_5d` `wide_no_theme` `xgboost` top1_p0.60: score=506.105083, n=24, 1d=100.0%/12.932358%, 3d=79.1667%/7.771095%, 5d=79.1667%/7.110499%, min5=-2.521008%, max5=26.235741%
2. `KOSPI` `clean_5d` `wide_no_theme` `xgboost` top1: score=-2.761246, n=56, 1d=55.3571%/2.777522%, 3d=51.7857%/-1.075765%, 5d=57.1429%/0.120094%, min5=-33.279483%, max5=26.235741%
