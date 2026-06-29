# NASDAQ Production Edge Search

- generated_at: `2026-06-29T06:49:16.070723+00:00`
- panel_path: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- rows_eligible: `1480423`
- symbols_eligible: `2312`
- date_range: `2018-06-22` ~ `2026-06-18`
- research_liq_floor: `10000000.0`
- cost_grid_pct: `[0.1, 0.2, 0.35]`

## Best Policies

- `score_alpha3` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.660%` net@0.2 `+1.460%` alpha3 `+0.747%` touch3 `23.80%` dd3 `27.34%` years_net_pos `2/4`
- `score_prod_return_only` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.625%` net@0.2 `+1.425%` alpha3 `+0.689%` touch3 `23.80%` dd3 `27.85%` years_net_pos `3/4`
- `score_alpha5` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.470%` net@0.2 `+1.270%` alpha3 `+0.678%` touch3 `24.56%` dd3 `29.11%` years_net_pos `3/4`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top3 n `890` alpha5 `+1.301%` net@0.2 `+1.101%` alpha3 `+1.218%` touch3 `37.53%` dd3 `34.04%` years_net_pos `4/7`
- `score_prod_path_safe` guard `all` gate `pred_alpha5_ge_0_50` floor `100,000,000` top3 n `340` alpha5 `+1.215%` net@0.2 `+1.015%` alpha3 `+1.274%` touch3 `49.71%` dd3 `42.35%` years_net_pos `2/4`
- `score_prod_combo` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.283%` net@0.2 `+1.083%` alpha3 `+0.456%` touch3 `21.52%` dd3 `28.10%` years_net_pos `4/4`
- `score_alpha5` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top3 n `890` alpha5 `+1.141%` net@0.2 `+0.941%` alpha3 `+0.804%` touch3 `38.20%` dd3 `37.42%` years_net_pos `3/7`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top5 n `1284` alpha5 `+0.972%` net@0.2 `+0.772%` alpha3 `+0.840%` touch3 `37.85%` dd3 `34.03%` years_net_pos `4/7`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top1 n `363` alpha5 `+0.974%` net@0.2 `+0.774%` alpha3 `+0.720%` touch3 `33.33%` dd3 `35.26%` years_net_pos `5/7`
- `score_prod_path_safe` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.103%` net@0.2 `+0.903%` alpha3 `+0.186%` touch3 `20.25%` dd3 `27.85%` years_net_pos `3/4`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top2 n `650` alpha5 `+0.869%` net@0.2 `+0.669%` alpha3 `+0.805%` touch3 `37.08%` dd3 `35.54%` years_net_pos `5/7`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `30,000,000` top10 n `2674` alpha5 `+0.894%` net@0.2 `+0.694%` alpha3 `+0.717%` touch3 `39.38%` dd3 `36.80%` years_net_pos `4/7`
- `score_alpha3` guard `risk_on` gate `pred_pos_ge_0_55` floor `100,000,000` top1 n `519` alpha5 `+0.844%` net@0.2 `+0.644%` alpha3 `+0.736%` touch3 `21.00%` dd3 `14.45%` years_net_pos `5/7`
- `score_prod_path_safe` guard `all` gate `pred_alpha5_ge_0_50` floor `100,000,000` top5 n `504` alpha5 `+0.746%` net@0.2 `+0.546%` alpha3 `+0.978%` touch3 `48.81%` dd3 `42.86%` years_net_pos `3/4`
- `score_prod_combo` guard `all` gate `pred_alpha5_ge_0_25` floor `100,000,000` top1 n `521` alpha5 `+0.863%` net@0.2 `+0.663%` alpha3 `+0.579%` touch3 `31.67%` dd3 `26.49%` years_net_pos `4/6`
- `score_prod_combo` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top5 n `1284` alpha5 `+0.856%` net@0.2 `+0.656%` alpha3 `+0.750%` touch3 `36.06%` dd3 `32.40%` years_net_pos `3/7`
- `score_alpha3` guard `risk_on` gate `pred_pos_ge_0_55` floor `30,000,000` top1 n `580` alpha5 `+0.759%` net@0.2 `+0.559%` alpha3 `+0.873%` touch3 `28.62%` dd3 `19.14%` years_net_pos `4/7`
- `score_prod_combo` guard `all` gate `pred_alpha5_ge_0_50` floor `100,000,000` top3 n `340` alpha5 `+0.756%` net@0.2 `+0.556%` alpha3 `+0.624%` touch3 `49.12%` dd3 `42.65%` years_net_pos `4/4`
- `score_alpha5` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top5 n `1284` alpha5 `+0.873%` net@0.2 `+0.673%` alpha3 `+0.647%` touch3 `38.47%` dd3 `36.92%` years_net_pos `3/7`
- `score_alpha5` guard `all` gate `pred_alpha5_ge_0_50` floor `30,000,000` top5 n `676` alpha5 `+0.783%` net@0.2 `+0.583%` alpha3 `+0.852%` touch3 `53.25%` dd3 `51.48%` years_net_pos `2/4`
- `score_prod_return_only` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top2 n `650` alpha5 `+0.829%` net@0.2 `+0.629%` alpha3 `+0.563%` touch3 `35.54%` dd3 `36.00%` years_net_pos `4/7`
- `score_prod_return_only` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top3 n `890` alpha5 `+0.829%` net@0.2 `+0.629%` alpha3 `+0.613%` touch3 `36.63%` dd3 `35.28%` years_net_pos `3/7`
- `score_alpha5` guard `all` gate `pred_pos_ge_0_60` floor `30,000,000` top10 n `2674` alpha5 `+0.832%` net@0.2 `+0.632%` alpha3 `+0.582%` touch3 `40.35%` dd3 `39.12%` years_net_pos `3/7`
- `score_prod_combo` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top3 n `890` alpha5 `+0.780%` net@0.2 `+0.580%` alpha3 `+0.713%` touch3 `35.28%` dd3 `32.25%` years_net_pos `3/7`
- `score_prod_combo` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top2 n `650` alpha5 `+0.762%` net@0.2 `+0.562%` alpha3 `+0.669%` touch3 `35.69%` dd3 `32.46%` years_net_pos `4/7`

## Fold Summary

- `2020` train `185451` test `152918` alpha5_mean `-0.005289`
- `2021` train `335775` test `201942` alpha5_mean `-0.030896`
- `2022` train `535580` test `183736` alpha5_mean `0.016667`
- `2023` train `721342` test `175899` alpha5_mean `-0.001062`
- `2024` train `897057` test `203730` alpha5_mean `0.013621`
- `2025` train `1098777` test `243737` alpha5_mean `-0.00367`
- `2026` train `1340571` test `126137` alpha5_mean `0.042848`
