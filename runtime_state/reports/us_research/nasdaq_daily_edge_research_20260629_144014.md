# NASDAQ Daily Edge Research

- generated_at: `2026-06-29T05:40:14.148731+00:00`
- panel_path: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- rows_loaded: `5332611`
- rows_eligible_base: `1480423`
- research_liq_floor: `10000000.0`
- symbols_eligible_base: `2312`
- date_range: `2018-06-22` ~ `2026-06-18`
- caveat: `Current-listed NASDAQ universe; not survivorship-free delisted history.`

## Base Rates

- liq20>=10,000,000: rows `1480423`, symbols `2312`, touch3 `27.93%`, ft55 `33.67%`, ret3 `+0.077%`, ret5 `+0.136%`
- liq20>=30,000,000: rows `885544`, symbols `1700`, touch3 `25.93%`, ft55 `32.03%`, ret3 `+0.120%`, ret5 `+0.202%`
- liq20>=100,000,000: rows `424864`, symbols `867`, touch3 `23.92%`, ft55 `30.23%`, ret3 `+0.181%`, ret5 `+0.297%`

## Top Candidates

- `ml_combo_touch_ft_risk` walk_forward_ml floor `100,000,000` top1 n `1624` touch3 `54.19%` ft55 `51.17%` dd3 `49.82%` ret3_liq_ex `+0.560%` ret5_liq_ex `+0.953%` ft55_liq_ex `+18.77%` years_ret3_pos `6/7`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `100,000,000` top3 n `4872` touch3 `53.45%` ft55 `50.78%` dd3 `50.90%` ret3_liq_ex `+0.344%` ret5_liq_ex `+0.616%` ft55_liq_ex `+18.67%` years_ret3_pos `5/7`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `100,000,000` top2 n `3248` touch3 `53.26%` ft55 `50.31%` dd3 `50.62%` ret3_liq_ex `+0.338%` ret5_liq_ex `+0.591%` ft55_liq_ex `+18.13%` years_ret3_pos `6/7`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `100,000,000` top5 n `8120` touch3 `52.55%` ft55 `50.34%` dd3 `51.26%` ret3_liq_ex `+0.265%` ret5_liq_ex `+0.511%` ft55_liq_ex `+18.28%` years_ret3_pos `5/7`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `100,000,000` top10 n `16240` touch3 `52.33%` ft55 `50.49%` dd3 `50.54%` ret3_liq_ex `+0.252%` ret5_liq_ex `+0.400%` ft55_liq_ex `+18.35%` years_ret3_pos `4/7`
- `formula_trend_momo` formula floor `100,000,000` top1 n `1908` touch3 `44.08%` ft55 `44.97%` dd3 `42.40%` ret3_liq_ex `+0.097%` ret5_liq_ex `+0.565%` ft55_liq_ex `+14.18%` years_ret3_pos `4/9`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `30,000,000` top3 n `4872` touch3 `52.34%` ft55 `49.65%` dd3 `52.13%` ret3_liq_ex `+0.197%` ret5_liq_ex `+0.275%` ft55_liq_ex `+15.77%` years_ret3_pos `5/7`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `30,000,000` top2 n `3248` touch3 `51.91%` ft55 `49.11%` dd3 `52.22%` ret3_liq_ex `+0.202%` ret5_liq_ex `+0.286%` ft55_liq_ex `+15.18%` years_ret3_pos `5/7`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `10,000,000` top1 n `1624` touch3 `53.69%` ft55 `49.20%` dd3 `54.06%` ret3_liq_ex `+0.355%` ret5_liq_ex `+0.203%` ft55_liq_ex `+13.21%` years_ret3_pos `4/7`
- `formula_pullback_uptrend` formula floor `30,000,000` top2 n `3816` touch3 `42.35%` ft55 `45.10%` dd3 `42.06%` ret3_liq_ex `+0.136%` ret5_liq_ex `+0.419%` ft55_liq_ex `+12.90%` years_ret3_pos `5/9`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `30,000,000` top5 n `8120` touch3 `52.56%` ft55 `50.21%` dd3 `51.17%` ret3_liq_ex `+0.211%` ret5_liq_ex `+0.252%` ft55_liq_ex `+16.27%` years_ret3_pos `4/7`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `30,000,000` top10 n `16240` touch3 `51.87%` ft55 `49.75%` dd3 `51.73%` ret3_liq_ex `+0.150%` ret5_liq_ex `+0.185%` ft55_liq_ex `+15.83%` years_ret3_pos `4/7`
- `formula_trend_momo` formula floor `100,000,000` top5 n `9540` touch3 `37.95%` ft55 `41.07%` dd3 `36.31%` ret3_liq_ex `+0.144%` ret5_liq_ex `+0.293%` ft55_liq_ex `+10.52%` years_ret3_pos `4/9`
- `formula_pullback_uptrend` formula floor `10,000,000` top10 n `19080` touch3 `41.48%` ft55 `44.26%` dd3 `41.49%` ret3_liq_ex `+0.078%` ret5_liq_ex `+0.254%` ft55_liq_ex `+10.56%` years_ret3_pos `6/9`
- `formula_pullback_uptrend` formula floor `10,000,000` top5 n `9540` touch3 `42.86%` ft55 `45.44%` dd3 `42.78%` ret3_liq_ex `+0.101%` ret5_liq_ex `+0.223%` ft55_liq_ex `+11.67%` years_ret3_pos `5/9`
- `ml_combo_touch_ft_risk` walk_forward_ml floor `30,000,000` top1 n `1624` touch3 `51.48%` ft55 `48.71%` dd3 `52.46%` ret3_liq_ex `+0.017%` ret5_liq_ex `+0.245%` ft55_liq_ex `+14.80%` years_ret3_pos `4/7`
- `formula_trend_momo` formula floor `10,000,000` top10 n `19080` touch3 `42.63%` ft55 `44.47%` dd3 `41.68%` ret3_liq_ex `+0.132%` ret5_liq_ex `+0.194%` ft55_liq_ex `+11.00%` years_ret3_pos `4/9`
- `formula_pullback_uptrend` formula floor `30,000,000` top3 n `5724` touch3 `42.30%` ft55 `44.53%` dd3 `41.72%` ret3_liq_ex `+0.034%` ret5_liq_ex `+0.219%` ft55_liq_ex `+12.26%` years_ret3_pos `5/9`
- `formula_trend_momo` formula floor `100,000,000` top3 n `5724` touch3 `39.81%` ft55 `42.07%` dd3 `38.45%` ret3_liq_ex `+0.072%` ret5_liq_ex `+0.214%` ft55_liq_ex `+11.47%` years_ret3_pos `4/9`
- `formula_pullback_uptrend` formula floor `30,000,000` top1 n `1908` touch3 `41.30%` ft55 `43.13%` dd3 `43.82%` ret3_liq_ex `+0.066%` ret5_liq_ex `+0.174%` ft55_liq_ex `+10.96%` years_ret3_pos `6/9`

## Fold Summary

- `2020` train `185451` test `152918` touch5_3d:n=120000, dd5_3d:n=120000, ft_5_5:n=120000
- `2021` train `335775` test `201942` touch5_3d:n=120000, dd5_3d:n=120000, ft_5_5:n=120000
- `2022` train `535580` test `183736` touch5_3d:n=120000, dd5_3d:n=120000, ft_5_5:n=120000
- `2023` train `721342` test `175899` touch5_3d:n=120000, dd5_3d:n=120000, ft_5_5:n=120000
- `2024` train `897057` test `203730` touch5_3d:n=120000, dd5_3d:n=120000, ft_5_5:n=120000
- `2025` train `1098777` test `243737` touch5_3d:n=120000, dd5_3d:n=120000, ft_5_5:n=120000
- `2026` train `1340571` test `126137` touch5_3d:n=120000, dd5_3d:n=120000, ft_5_5:n=120000
