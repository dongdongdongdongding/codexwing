# KOSDAQ 5D Admission Model

- generated_at: `2026-05-12T11:32:41.809693+00:00`
- rows: `176`
- days: `12`
- target: `win_5d >= 70%, avg_5d >= +5%`
- saved_model_path: ``

## Best Target-Passing Slice

- none

## Experiments

### logistic + extra_trees_reg
- p_win_q850: n=24, win5=54.167%, avg5=7.3321%, hit5=45.833%
- p_win_q700: n=48, win5=54.167%, avg5=4.7965%, hit5=41.667%
- p_win_q750: n=40, win5=52.5%, avg5=5.4908%, hit5=45.0%
- pred_return_5d_q700: n=57, win5=50.877%, avg5=5.1216%, hit5=38.596%
- pred_return_5d_q750: n=57, win5=50.877%, avg5=5.1216%, hit5=38.596%

### logistic + hist_gb_reg
- pred_return_5d_q750: n=40, win5=62.5%, avg5=6.4056%, hit5=45.0%
- pred_return_5d_q800: n=36, win5=61.111%, avg5=6.2254%, hit5=44.444%
- pred_return_5d_q850: n=25, win5=60.0%, avg5=5.503%, hit5=40.0%
- pred_return_5d_q700: n=51, win5=54.902%, avg5=4.6451%, hit5=41.176%
- p_win_q850: n=24, win5=54.167%, avg5=7.3321%, hit5=45.833%

### extra_trees + extra_trees_reg
- admission_score_q700: n=48, win5=52.083%, avg5=5.8545%, hit5=39.583%
- p_hit5_q700: n=48, win5=52.083%, avg5=4.8804%, hit5=35.417%
- p_win_q700: n=49, win5=51.02%, avg5=3.6399%, hit5=34.694%
- pred_return_5d_q700: n=57, win5=50.877%, avg5=5.1216%, hit5=38.596%
- pred_return_5d_q750: n=57, win5=50.877%, avg5=5.1216%, hit5=38.596%

### extra_trees + hist_gb_reg
- pred_return_5d_q750: n=40, win5=62.5%, avg5=6.4056%, hit5=45.0%
- pred_return_5d_q800: n=36, win5=61.111%, avg5=6.2254%, hit5=44.444%
- pred_return_5d_q850: n=25, win5=60.0%, avg5=5.503%, hit5=40.0%
- admission_score_q850: n=24, win5=58.333%, avg5=7.0771%, hit5=41.667%
- pred_return_5d_q700: n=51, win5=54.902%, avg5=4.6451%, hit5=41.176%

### hist_gb + extra_trees_reg
- p_win_q850: n=24, win5=66.667%, avg5=7.7414%, hit5=41.667%
- p_win_q800: n=34, win5=58.824%, avg5=4.535%, hit5=32.353%
- admission_score_q700: n=65, win5=58.462%, avg5=6.4909%, hit5=40.0%
- admission_score_q750: n=65, win5=58.462%, avg5=6.4909%, hit5=40.0%
- p_win_q700: n=76, win5=57.895%, avg5=5.6445%, hit5=35.526%

### hist_gb + hist_gb_reg
- p_win_q850: n=24, win5=66.667%, avg5=7.7414%, hit5=41.667%
- admission_score_q800: n=32, win5=62.5%, avg5=8.7022%, hit5=43.75%
- pred_return_5d_q750: n=40, win5=62.5%, avg5=6.4056%, hit5=45.0%
- pred_return_5d_q800: n=36, win5=61.111%, avg5=6.2254%, hit5=44.444%
- pred_return_5d_q850: n=25, win5=60.0%, avg5=5.503%, hit5=40.0%
