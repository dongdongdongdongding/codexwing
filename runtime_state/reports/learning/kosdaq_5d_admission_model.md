# KOSDAQ 5D Admission Model

- generated_at: `2026-05-12T12:02:21.764273+00:00`
- rows: `1376`
- days: `26`
- target: `win_5d >= 70%, avg_5d >= +5%`
- saved_model_path: ``

## Best Target-Passing Slice

- none

## Experiments

### logistic + extra_trees_reg
- bucket_exception_leader: n=99, win5=65.657%, avg5=6.0109%, hit5=44.444%
- pred_return_5d_q950: n=64, win5=64.062%, avg5=8.1837%, hit5=51.562%
- p_win_q925: n=95, win5=58.947%, avg5=5.0961%, hit5=41.053%
- p_win_q900: n=127, win5=58.268%, avg5=4.6278%, hit5=38.583%
- p_hit5_q950: n=64, win5=57.812%, avg5=2.7219%, hit5=31.25%

### logistic + hist_gb_reg
- bucket_exception_leader: n=99, win5=65.657%, avg5=6.0109%, hit5=44.444%
- p_win_q925: n=95, win5=58.947%, avg5=5.0961%, hit5=41.053%
- p_win_q900: n=127, win5=58.268%, avg5=4.6278%, hit5=38.583%
- p_hit5_q950: n=64, win5=57.812%, avg5=2.7219%, hit5=31.25%
- p_win_q850: n=190, win5=57.368%, avg5=4.0883%, hit5=38.947%

### extra_trees + extra_trees_reg
- bucket_exception_leader: n=99, win5=65.657%, avg5=6.0109%, hit5=44.444%
- admission_score_q950: n=64, win5=65.625%, avg5=7.0953%, hit5=50.0%
- admission_score_q925: n=95, win5=65.263%, avg5=7.5289%, hit5=49.474%
- p_win_q850: n=190, win5=64.211%, avg5=5.0524%, hit5=46.316%
- pred_return_5d_q950: n=64, win5=64.062%, avg5=8.1837%, hit5=51.562%

### extra_trees + hist_gb_reg
- bucket_exception_leader: n=99, win5=65.657%, avg5=6.0109%, hit5=44.444%
- admission_score_q950: n=64, win5=65.625%, avg5=7.3858%, hit5=53.125%
- p_win_q850: n=190, win5=64.211%, avg5=5.0524%, hit5=46.316%
- p_win_q900: n=127, win5=62.992%, avg5=4.7267%, hit5=45.669%
- p_win_q800: n=253, win5=62.846%, avg5=4.9786%, hit5=43.478%

### hist_gb + extra_trees_reg
- bucket_exception_leader: n=99, win5=65.657%, avg5=6.0109%, hit5=44.444%
- pred_return_5d_q950: n=64, win5=64.062%, avg5=8.1837%, hit5=51.562%
- admission_score_q925: n=95, win5=62.105%, avg5=4.0517%, hit5=46.316%
- admission_score_q950: n=64, win5=60.938%, avg5=4.5617%, hit5=43.75%
- admission_score_q900: n=127, win5=60.63%, avg5=4.6644%, hit5=45.669%

### hist_gb + hist_gb_reg
- bucket_exception_leader: n=99, win5=65.657%, avg5=6.0109%, hit5=44.444%
- p_win_q900: n=127, win5=60.63%, avg5=4.4578%, hit5=41.732%
- p_win_q800: n=253, win5=60.079%, avg5=4.492%, hit5=41.502%
- p_win_q700: n=380, win5=59.474%, avg5=4.0057%, hit5=40.789%
- admission_score_q950: n=64, win5=59.375%, avg5=4.5279%, hit5=45.312%
