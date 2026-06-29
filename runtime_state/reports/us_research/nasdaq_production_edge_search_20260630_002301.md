# NASDAQ Promotion-Gated Edge Search

- generated_at: `2026-06-29T15:23:01.239758+00:00`
- panel_path: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- rows_eligible: `1480423`
- symbols_eligible: `2312`
- date_range: `2018-06-22` ~ `2026-06-18`
- research_liq_floor: `10000000.0`
- cost_grid_pct: `[0.1, 0.2, 0.35]`

## Best Policies

- `score_alpha3` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.660%` net@0.2 `+1.460%` ret5_pos `46.84%` net_pos `57.72%` alpha3 `+0.747%` touch3 `23.80%` ft55 `26.08%` dd3 `27.34%` years_net_pos `2/4` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:395<1000, days_below_min:60<250, ret5_below_min:0.566361<1, ret5_pos_rate_below_min:0.468354<0.55, touch3_below_min:0.237975<0.55, ft55_below_min:0.260759<0.55, years_alpha5_net_0_2_pos_below_min:2<5`
- `score_prod_return_only` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.625%` net@0.2 `+1.425%` ret5_pos `46.33%` net_pos `58.23%` alpha3 `+0.689%` touch3 `23.80%` ft55 `25.06%` dd3 `27.85%` years_net_pos `3/4` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:395<1000, days_below_min:60<250, ret5_below_min:0.47651<1, ret5_pos_rate_below_min:0.463291<0.55, touch3_below_min:0.237975<0.55, ft55_below_min:0.250633<0.55, years_alpha5_net_0_2_pos_below_min:3<5`
- `score_alpha5` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.470%` net@0.2 `+1.270%` ret5_pos `47.09%` net_pos `58.73%` alpha3 `+0.678%` touch3 `24.56%` ft55 `26.84%` dd3 `29.11%` years_net_pos `3/4` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:395<1000, days_below_min:60<250, ret5_below_min:0.274813<1, alpha5_net_cost_0_2_ci95_lo_below_min:-0.147342<0, ret5_pos_rate_below_min:0.470886<0.55, touch3_below_min:0.24557<0.55, ft55_below_min:0.268354<0.55, years_alpha5_net_0_2_pos_below_min:3<5`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top3 n `890` alpha5 `+1.301%` net@0.2 `+1.101%` ret5_pos `52.81%` net_pos `47.87%` alpha3 `+1.218%` touch3 `37.53%` ft55 `37.53%` dd3 `34.04%` years_net_pos `4/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:890<1000, ret5_pos_rate_below_min:0.52809<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.478652<0.55, touch3_below_min:0.375281<0.55, ft55_below_min:0.375281<0.55, years_alpha5_net_0_2_pos_below_min:4<5`
- `score_prod_path_safe` guard `all` gate `pred_alpha5_ge_0_50` floor `100,000,000` top3 n `340` alpha5 `+1.215%` net@0.2 `+1.015%` ret5_pos `51.76%` net_pos `52.65%` alpha3 `+1.274%` touch3 `49.71%` ft55 `47.65%` dd3 `42.35%` years_net_pos `2/4` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:340<1000, days_below_min:139<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.247112<0, ret5_pos_rate_below_min:0.517647<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.526471<0.55, touch3_below_min:0.497059<0.55, ft55_below_min:0.476471<0.55, dd3_above_max:0.423529>0.35`
- `score_prod_combo` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.283%` net@0.2 `+1.083%` ret5_pos `43.80%` net_pos `56.96%` alpha3 `+0.456%` touch3 `21.52%` ft55 `22.28%` dd3 `28.10%` years_net_pos `4/4` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:395<1000, days_below_min:60<250, ret5_below_min:0.132764<1, alpha5_net_cost_0_2_ci95_lo_below_min:-0.134209<0, ret5_pos_rate_below_min:0.437975<0.55, touch3_below_min:0.21519<0.55, ft55_below_min:0.222785<0.55, years_alpha5_net_0_2_pos_below_min:4<5`
- `score_alpha5` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top3 n `890` alpha5 `+1.141%` net@0.2 `+0.941%` ret5_pos `52.58%` net_pos `47.98%` alpha3 `+0.804%` touch3 `38.20%` ft55 `37.08%` dd3 `37.42%` years_net_pos `3/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:890<1000, ret5_pos_rate_below_min:0.525843<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.479775<0.55, touch3_below_min:0.382022<0.55, ft55_below_min:0.370787<0.55, dd3_above_max:0.374157>0.35, years_alpha5_net_0_2_pos_below_min:3<5`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top5 n `1284` alpha5 `+0.972%` net@0.2 `+0.772%` ret5_pos `53.58%` net_pos `48.21%` alpha3 `+0.840%` touch3 `37.85%` ft55 `37.69%` dd3 `34.03%` years_net_pos `4/7` gate `BLOCK`
  - promotion_blocking_reasons: `ret5_pos_rate_below_min:0.535826<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.482087<0.55, touch3_below_min:0.378505<0.55, ft55_below_min:0.376947<0.55, years_alpha5_net_0_2_pos_below_min:4<5`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top1 n `363` alpha5 `+0.974%` net@0.2 `+0.774%` ret5_pos `52.89%` net_pos `46.28%` alpha3 `+0.720%` touch3 `33.33%` ft55 `31.96%` dd3 `35.26%` years_net_pos `5/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:363<1000, alpha5_net_cost_0_2_ci95_lo_below_min:-0.601017<0, ret5_pos_rate_below_min:0.528926<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.46281<0.55, touch3_below_min:0.333333<0.55, ft55_below_min:0.319559<0.55, dd3_above_max:0.352617>0.35`
- `score_prod_path_safe` guard `all` gate `pred_alpha5_ge_0_50_dd_le_0_45` floor `30,000,000` top10 n `395` alpha5 `+1.103%` net@0.2 `+0.903%` ret5_pos `43.54%` net_pos `57.22%` alpha3 `+0.186%` touch3 `20.25%` ft55 `21.77%` dd3 `27.85%` years_net_pos `3/4` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:395<1000, days_below_min:60<250, ret5_below_min:-0.022806<1, alpha5_net_cost_0_2_ci95_lo_below_min:-0.266805<0, ret5_pos_rate_below_min:0.435443<0.55, touch3_below_min:0.202532<0.55, ft55_below_min:0.217722<0.55, years_alpha5_net_0_2_pos_below_min:3<5`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top2 n `650` alpha5 `+0.869%` net@0.2 `+0.669%` ret5_pos `52.31%` net_pos `47.23%` alpha3 `+0.805%` touch3 `37.08%` ft55 `36.77%` dd3 `35.54%` years_net_pos `5/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:650<1000, alpha5_net_cost_0_2_ci95_lo_below_min:-0.359955<0, ret5_pos_rate_below_min:0.523077<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.472308<0.55, touch3_below_min:0.370769<0.55, ft55_below_min:0.367692<0.55, dd3_above_max:0.355385>0.35`
- `score_alpha3` guard `all` gate `pred_pos_ge_0_60` floor `30,000,000` top10 n `2674` alpha5 `+0.894%` net@0.2 `+0.694%` ret5_pos `52.66%` net_pos `49.33%` alpha3 `+0.717%` touch3 `39.38%` ft55 `38.03%` dd3 `36.80%` years_net_pos `4/7` gate `BLOCK`
  - promotion_blocking_reasons: `ret5_pos_rate_below_min:0.526552<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.493269<0.55, touch3_below_min:0.393792<0.55, ft55_below_min:0.380329<0.55, dd3_above_max:0.367988>0.35, years_alpha5_net_0_2_pos_below_min:4<5`
- `score_alpha3` guard `risk_on` gate `pred_pos_ge_0_55` floor `100,000,000` top1 n `519` alpha5 `+0.844%` net@0.2 `+0.644%` ret5_pos `50.87%` net_pos `49.90%` alpha3 `+0.736%` touch3 `21.00%` ft55 `24.28%` dd3 `14.45%` years_net_pos `5/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:519<1000, alpha5_net_cost_0_2_ci95_lo_below_min:-0.041212<0, ret5_pos_rate_below_min:0.508671<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.499037<0.55, touch3_below_min:0.210019<0.55, ft55_below_min:0.242775<0.55`
- `score_prod_path_safe` guard `all` gate `pred_alpha5_ge_0_50` floor `100,000,000` top5 n `504` alpha5 `+0.746%` net@0.2 `+0.546%` ret5_pos `50.99%` net_pos `51.59%` alpha3 `+0.978%` touch3 `48.81%` ft55 `47.42%` dd3 `42.86%` years_net_pos `3/4` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:504<1000, days_below_min:139<250, ret5_below_min:0.811369<1, alpha5_net_cost_0_2_ci95_lo_below_min:-0.571529<0, ret5_pos_rate_below_min:0.509921<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.515873<0.55, touch3_below_min:0.488095<0.55, ft55_below_min:0.474206<0.55`
- `score_prod_combo` guard `all` gate `pred_alpha5_ge_0_25` floor `100,000,000` top1 n `521` alpha5 `+0.863%` net@0.2 `+0.663%` ret5_pos `56.62%` net_pos `47.60%` alpha3 `+0.579%` touch3 `31.67%` ft55 `33.21%` dd3 `26.49%` years_net_pos `4/6` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:521<1000, alpha5_net_cost_0_2_ci95_lo_below_min:-0.002645<0, alpha5_net_cost_0_2_pos_rate_below_min:0.476008<0.55, touch3_below_min:0.316699<0.55, ft55_below_min:0.332054<0.55, years_alpha5_net_0_2_pos_below_min:4<5`
- `score_prod_combo` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top5 n `1284` alpha5 `+0.856%` net@0.2 `+0.656%` ret5_pos `53.35%` net_pos `48.36%` alpha3 `+0.750%` touch3 `36.06%` ft55 `35.98%` dd3 `32.40%` years_net_pos `3/7` gate `BLOCK`
  - promotion_blocking_reasons: `ret5_pos_rate_below_min:0.533489<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.483645<0.55, touch3_below_min:0.360592<0.55, ft55_below_min:0.359813<0.55, years_alpha5_net_0_2_pos_below_min:3<5`
- `score_alpha3` guard `risk_on` gate `pred_pos_ge_0_55` floor `30,000,000` top1 n `580` alpha5 `+0.759%` net@0.2 `+0.559%` ret5_pos `51.03%` net_pos `47.76%` alpha3 `+0.873%` touch3 `28.62%` ft55 `31.55%` dd3 `19.14%` years_net_pos `4/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:580<1000, ret5_below_min:0.987665<1, alpha5_net_cost_0_2_ci95_lo_below_min:-0.121395<0, ret5_pos_rate_below_min:0.510345<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.477586<0.55, touch3_below_min:0.286207<0.55, ft55_below_min:0.315517<0.55, years_alpha5_net_0_2_pos_below_min:4<5`
- `score_prod_combo` guard `all` gate `pred_alpha5_ge_0_50` floor `100,000,000` top3 n `340` alpha5 `+0.756%` net@0.2 `+0.556%` ret5_pos `51.76%` net_pos `52.65%` alpha3 `+0.624%` touch3 `49.12%` ft55 `47.35%` dd3 `42.65%` years_net_pos `4/4` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:340<1000, days_below_min:139<250, ret5_below_min:0.913975<1, alpha5_net_cost_0_2_ci95_lo_below_min:-0.739024<0, ret5_pos_rate_below_min:0.517647<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.526471<0.55, touch3_below_min:0.491176<0.55, ft55_below_min:0.473529<0.55`
- `score_alpha5` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top5 n `1284` alpha5 `+0.873%` net@0.2 `+0.673%` ret5_pos `51.48%` net_pos `47.04%` alpha3 `+0.647%` touch3 `38.47%` ft55 `37.07%` dd3 `36.92%` years_net_pos `3/7` gate `BLOCK`
  - promotion_blocking_reasons: `ret5_pos_rate_below_min:0.514798<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.470405<0.55, touch3_below_min:0.384735<0.55, ft55_below_min:0.370717<0.55, dd3_above_max:0.369159>0.35, years_alpha5_net_0_2_pos_below_min:3<5`
- `score_alpha5` guard `all` gate `pred_alpha5_ge_0_50` floor `30,000,000` top5 n `676` alpha5 `+0.783%` net@0.2 `+0.583%` ret5_pos `48.52%` net_pos `47.78%` alpha3 `+0.852%` touch3 `53.25%` ft55 `48.22%` dd3 `51.48%` years_net_pos `2/4` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:676<1000, days_below_min:166<250, alpha5_net_cost_0_2_ci95_lo_below_min:-0.521531<0, ret5_pos_rate_below_min:0.485207<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.477811<0.55, touch3_below_min:0.532544<0.55, ft55_below_min:0.482249<0.55, dd3_above_max:0.514793>0.35`
- `score_prod_return_only` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top2 n `650` alpha5 `+0.829%` net@0.2 `+0.629%` ret5_pos `52.00%` net_pos `46.62%` alpha3 `+0.563%` touch3 `35.54%` ft55 `34.77%` dd3 `36.00%` years_net_pos `4/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:650<1000, alpha5_net_cost_0_2_ci95_lo_below_min:-0.336736<0, ret5_pos_rate_below_min:0.52<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.466154<0.55, touch3_below_min:0.355385<0.55, ft55_below_min:0.347692<0.55, dd3_above_max:0.36>0.35, years_alpha5_net_0_2_pos_below_min:4<5`
- `score_prod_return_only` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top3 n `890` alpha5 `+0.829%` net@0.2 `+0.629%` ret5_pos `52.13%` net_pos `46.74%` alpha3 `+0.613%` touch3 `36.63%` ft55 `36.18%` dd3 `35.28%` years_net_pos `3/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:890<1000, alpha5_net_cost_0_2_ci95_lo_below_min:-0.178757<0, ret5_pos_rate_below_min:0.521348<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.467416<0.55, touch3_below_min:0.366292<0.55, ft55_below_min:0.361798<0.55, dd3_above_max:0.352809>0.35, years_alpha5_net_0_2_pos_below_min:3<5`
- `score_alpha5` guard `all` gate `pred_pos_ge_0_60` floor `30,000,000` top10 n `2674` alpha5 `+0.832%` net@0.2 `+0.632%` ret5_pos `51.65%` net_pos `48.92%` alpha3 `+0.582%` touch3 `40.35%` ft55 `38.22%` dd3 `39.12%` years_net_pos `3/7` gate `BLOCK`
  - promotion_blocking_reasons: `ret5_pos_rate_below_min:0.516455<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.489155<0.55, touch3_below_min:0.403515<0.55, ft55_below_min:0.382199<0.55, dd3_above_max:0.391174>0.35, years_alpha5_net_0_2_pos_below_min:3<5`
- `score_prod_combo` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top3 n `890` alpha5 `+0.780%` net@0.2 `+0.580%` ret5_pos `53.37%` net_pos `48.76%` alpha3 `+0.713%` touch3 `35.28%` ft55 `35.96%` dd3 `32.25%` years_net_pos `3/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:890<1000, alpha5_net_cost_0_2_ci95_lo_below_min:-0.089154<0, ret5_pos_rate_below_min:0.533708<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.48764<0.55, touch3_below_min:0.352809<0.55, ft55_below_min:0.359551<0.55, years_alpha5_net_0_2_pos_below_min:3<5`
- `score_prod_combo` guard `all` gate `pred_pos_ge_0_60` floor `100,000,000` top2 n `650` alpha5 `+0.762%` net@0.2 `+0.562%` ret5_pos `52.31%` net_pos `47.54%` alpha3 `+0.669%` touch3 `35.69%` ft55 `35.69%` dd3 `32.46%` years_net_pos `4/7` gate `BLOCK`
  - promotion_blocking_reasons: `n_below_min:650<1000, alpha5_net_cost_0_2_ci95_lo_below_min:-0.232315<0, ret5_pos_rate_below_min:0.523077<0.55, alpha5_net_cost_0_2_pos_rate_below_min:0.475385<0.55, touch3_below_min:0.356923<0.55, ft55_below_min:0.356923<0.55, years_alpha5_net_0_2_pos_below_min:4<5`

## Fold Summary

- `2020` train `185451` test `152918` alpha5_mean `-0.005289`
- `2021` train `335775` test `201942` alpha5_mean `-0.030896`
- `2022` train `535580` test `183736` alpha5_mean `0.016667`
- `2023` train `721342` test `175899` alpha5_mean `-0.001062`
- `2024` train `897057` test `203730` alpha5_mean `0.013621`
- `2025` train `1098777` test `243737` alpha5_mean `-0.00367`
- `2026` train `1340571` test `126137` alpha5_mean `0.042848`
