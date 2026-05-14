# Admission Cycle 70pct Shadow Search

- generated_at: `2026-05-14T05:25:45.461732+00:00`
- mode: `shadow_only_not_production`
- input_rows: `4335`
- config: `{'max_depth': 2, 'beam_width': 80, 'min_train': 20, 'min_test': 8, 'max_conditions': 100, 'train_ratio': 0.7, 'run_ml': False}`

## Holdout Champions

| rank | market | cohort | profile | test_n | test_win | test_avg_5d | test_stop5 | train_n | train_win | conditions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | KOSPI | All | 5D_clean_10v5 | 11 | 90.909 | 9.836 | 0.0 | 55 | 38.182 | ml_prob<=24.9<br>prob_clean>=32.4 |
| 2 | KOSPI | Top3 | 5D_clean_10v5 | 9 | 77.778 | 8.8081 | 11.111 | 28 | 50.0 | prob_clean<=31.8<br>kr_universe_role=CORE_TREND |
| 3 | KOSDAQ | Exception Leader | 5D_clean_10v5 | 8 | 75.0 | 12.4332 | 25.0 | 56 | 41.071 | ml_prob>=21.3<br>priority_rank>=4 |
| 4 | KOSDAQ | Exception Leader | 5D_clean_10v5 | 8 | 75.0 | 10.9271 | 12.5 | 36 | 41.667 | volume_ratio<=0.96<br>priority_rank>=4 |
| 5 | KOSDAQ | Top3 | 5D_clean_10v5 | 8 | 75.0 | 10.0226 | 12.5 | 22 | 36.364 | ml_prob<=39.95<br>prob_clean<=31.3 |
| 6 | KOSDAQ | Top3 | 5D_clean_10v5 | 12 | 75.0 | 9.1643 | 8.333 | 24 | 41.667 | ml_prob<=50<br>prob_clean<=31.3 |
| 7 | KOSDAQ | Top5+Exception | 5D_clean_10v5 | 8 | 75.0 | 8.9239 | 25.0 | 22 | 45.455 | ml_prob>=22.8<br>volume_ratio<=0.87 |
| 8 | KOSDAQ | Exception Leader | 5D_clean_10v5 | 8 | 75.0 | 7.3918 | 25.0 | 50 | 42.0 | decision_score<=72.8<br>priority_rank>=4 |
| 9 | KOSDAQ | Exception Leader | 5D_clean_10v5 | 8 | 75.0 | 7.1909 | 25.0 | 44 | 47.727 | prob_clean<=26.48<br>trend=UP |
| 10 | KOSPI | Top3 | 5D_clean_10v5 | 12 | 75.0 | 6.8209 | 8.333 | 39 | 41.026 | ml_prob<=34.65<br>kr_universe_role=CORE_TREND |
| 11 | KOSDAQ | All | 5D_clean_10v5 | 8 | 75.0 | 6.6054 | 25.0 | 94 | 38.298 | alpha_score<=51<br>prob_clean<=28.8 |
| 12 | KOSPI | Top5+Exception | 5D_clean_10v5 | 8 | 75.0 | 6.083 | 0.0 | 52 | 42.308 | ml_prob<=32.38<br>prob_clean>=30.8 |
| 13 | KOSDAQ | Top5+Exception | 5D_clean_10v5 | 11 | 72.727 | 14.0766 | 18.182 | 40 | 45.0 | decision_score<=98.122<br>volume_ratio<=0.87 |
| 14 | KOSDAQ | Top5+Exception | 5D_clean_10v5 | 11 | 72.727 | 8.8603 | 18.182 | 34 | 41.176 | ml_prob>=22.8<br>volume_ratio<=1.01 |
| 15 | KOSPI | Top3 | 5D_clean_10v5 | 11 | 72.727 | 6.132 | 9.091 | 38 | 39.474 | priority_rank>=2<br>kr_universe_role=CORE_TREND |
| 16 | KOSDAQ | Top5+Exception | 5D_clean_10v5 | 10 | 70.0 | 8.3622 | 20.0 | 49 | 48.98 | ml_prob>=16.8<br>prob_clean<=22.26 |
| 17 | KOSDAQ | Top5+Exception | 5D_clean_10v5 | 10 | 70.0 | 8.3048 | 20.0 | 24 | 33.333 | prob_clean>=30.78<br>volume_ratio<=1.01 |
| 18 | KOSPI | All | 5D_clean_10v5 | 9 | 66.667 | 21.4857 | 22.222 | 43 | 53.488 | whale_score>=80<br>priority_rank<=37 |
| 19 | KOSPI | All | 5D_clean_10v5 | 9 | 66.667 | 21.4857 | 22.222 | 45 | 53.333 | whale_score>=78<br>priority_rank<=37 |
| 20 | KOSPI | All | 5D_clean_15v5 | 9 | 66.667 | 21.4857 | 22.222 | 43 | 32.558 | whale_score>=80<br>priority_rank<=37 |
| 21 | KOSPI | All | 5D_clean_15v5 | 9 | 66.667 | 21.4857 | 22.222 | 45 | 33.333 | whale_score>=78<br>priority_rank<=37 |
| 22 | KOSPI | All | 5D_clean_10v5 | 9 | 66.667 | 18.6852 | 22.222 | 68 | 54.412 | decision_score>=52.2<br>whale_score>=70 |
| 23 | KOSPI | All | 5D_clean_10v5 | 9 | 66.667 | 16.7028 | 22.222 | 53 | 50.943 | alpha_score<=99<br>whale_score>=80 |
| 24 | KOSPI | All | 5D_clean_15v5 | 9 | 66.667 | 16.7028 | 22.222 | 53 | 32.075 | alpha_score<=99<br>whale_score>=80 |
| 25 | KOSDAQ | Top5+Exception | 5D_clean_10v5 | 9 | 66.667 | 16.171 | 22.222 | 38 | 44.737 | alpha_score<=86<br>volume_ratio<=0.87 |
| 26 | KOSDAQ | Top5+Exception | 5D_clean_15v5 | 9 | 66.667 | 16.171 | 22.222 | 38 | 21.053 | alpha_score<=86<br>volume_ratio<=0.87 |
| 27 | KOSDAQ | Top5+Exception | 5D_clean_10v5 | 9 | 66.667 | 12.1431 | 22.222 | 23 | 39.13 | alpha_score<=86<br>prob_clean>=33.62 |
| 28 | KOSDAQ | Top5+Exception | 5D_clean_15v5 | 9 | 66.667 | 12.1431 | 22.222 | 23 | 26.087 | alpha_score<=86<br>prob_clean>=33.62 |
| 29 | KOSDAQ | Exception Leader | 5D_clean_10v5 | 9 | 66.667 | 10.9024 | 33.333 | 64 | 39.062 | ml_prob>=21.3<br>priority_rank>=3 |
| 30 | KOSDAQ | Top5 | 5D_clean_10v5 | 12 | 66.667 | 10.2821 | 0.0 | 31 | 51.613 | alpha_score<=87.1<br>prob_clean<=30.6 |

## 70pct+ Holdout Candidates

- `KOSPI` / `All` / `5D_clean_10v5`: test win `90.909`% n=`11`, train win `38.182`% n=`55`; conditions=['ml_prob<=24.9', 'prob_clean>=32.4']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `77.778`% n=`9`, train win `50.0`% n=`28`; conditions=['prob_clean<=31.8', 'kr_universe_role=CORE_TREND']
- `KOSDAQ` / `Exception Leader` / `5D_clean_10v5`: test win `75.0`% n=`8`, train win `41.071`% n=`56`; conditions=['ml_prob>=21.3', 'priority_rank>=4']
- `KOSDAQ` / `Exception Leader` / `5D_clean_10v5`: test win `75.0`% n=`8`, train win `41.667`% n=`36`; conditions=['volume_ratio<=0.96', 'priority_rank>=4']
- `KOSDAQ` / `Top3` / `5D_clean_10v5`: test win `75.0`% n=`8`, train win `36.364`% n=`22`; conditions=['ml_prob<=39.95', 'prob_clean<=31.3']
- `KOSDAQ` / `Top3` / `5D_clean_10v5`: test win `75.0`% n=`12`, train win `41.667`% n=`24`; conditions=['ml_prob<=50', 'prob_clean<=31.3']
- `KOSDAQ` / `Top5+Exception` / `5D_clean_10v5`: test win `75.0`% n=`8`, train win `45.455`% n=`22`; conditions=['ml_prob>=22.8', 'volume_ratio<=0.87']
- `KOSDAQ` / `Exception Leader` / `5D_clean_10v5`: test win `75.0`% n=`8`, train win `42.0`% n=`50`; conditions=['decision_score<=72.8', 'priority_rank>=4']
- `KOSDAQ` / `Exception Leader` / `5D_clean_10v5`: test win `75.0`% n=`8`, train win `47.727`% n=`44`; conditions=['prob_clean<=26.48', 'trend=UP']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `75.0`% n=`12`, train win `41.026`% n=`39`; conditions=['ml_prob<=34.65', 'kr_universe_role=CORE_TREND']
- `KOSDAQ` / `All` / `5D_clean_10v5`: test win `75.0`% n=`8`, train win `38.298`% n=`94`; conditions=['alpha_score<=51', 'prob_clean<=28.8']
- `KOSPI` / `Top5+Exception` / `5D_clean_10v5`: test win `75.0`% n=`8`, train win `42.308`% n=`52`; conditions=['ml_prob<=32.38', 'prob_clean>=30.8']
- `KOSDAQ` / `Top5+Exception` / `5D_clean_10v5`: test win `72.727`% n=`11`, train win `45.0`% n=`40`; conditions=['decision_score<=98.122', 'volume_ratio<=0.87']
- `KOSDAQ` / `Top5+Exception` / `5D_clean_10v5`: test win `72.727`% n=`11`, train win `41.176`% n=`34`; conditions=['ml_prob>=22.8', 'volume_ratio<=1.01']
- `KOSPI` / `Top3` / `5D_clean_10v5`: test win `72.727`% n=`11`, train win `39.474`% n=`38`; conditions=['priority_rank>=2', 'kr_universe_role=CORE_TREND']
- `KOSDAQ` / `Top5+Exception` / `5D_clean_10v5`: test win `70.0`% n=`10`, train win `48.98`% n=`49`; conditions=['ml_prob>=16.8', 'prob_clean<=22.26']
- `KOSDAQ` / `Top5+Exception` / `5D_clean_10v5`: test win `70.0`% n=`10`, train win `33.333`% n=`24`; conditions=['prob_clean>=30.78', 'volume_ratio<=1.01']

## Notes
- This is an internal admission cycle only; production scanner logic is unchanged.
- 5D clean labels use archive high/low proxy: target MFE reached and stop MAE not breached.
- 1D/3D labels use close-return target plus no 5D stop breach, so they are conservative but not exact intraday order labels.
- Primary theme values are intentionally excluded from rule features because themes rotate and fixed-theme rules overfit.
