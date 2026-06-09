# Close Return Failure Traits

- generated_at: `2026-06-09T09:48:49.349313+00:00`
- report_version: `close_return_failure_traits_v1`
- source_path: `runtime_state/reports/learning/scan_universe_admission_challenger_buy_premium_v2_idscan_20260401_20260528.pkl`
- input_rows: `95822`
- buy_premium_pct: `2.0`
- target_touch_pct: `5.0`

## Overall

- touch5_base_n: `26235`
- close_loss_given_touch5_pct: `53.5163`
- close_defense_given_touch5_pct: `46.4799`
- bad_path_given_touch5_pct: `80.8348`
- touch10_given_touch5_pct: `53.7297`

## Segment Highlights

### ALL

- skipped: `False`
- touch5_base_n: `26235`
- n_failure/n_control: `14040` / `5028`
- close_loss_given_touch5_pct: `53.5163`
- bad_path_given_touch5_pct: `80.8348`

| rank | numeric feature | direction | d | worst bin lift | failure mean | control mean |
|---:|---|---|---:|---:|---:|---:|
| 1 | `priority_rank` | higher_in_failures | `0.644223` | `1.1632` | `25.82266` | `14.597315` |
| 2 | `total_scans` | higher_in_failures | `0.363022` | `1.3306` | `1364.854915` | `1201.77327` |
| 3 | `kis_financial_eps` | lower_in_failures | `-0.39933` | `1.1106` | `526.362419` | `2432.118305` |
| 4 | `kis_daily_ma5` | lower_in_failures | `-0.302217` | `1.1724` | `41774.190897` | `98851.856842` |
| 5 | `kis_daily_ma60` | lower_in_failures | `-0.305917` | `1.1603` | `38602.938263` | `88058.010395` |
| 6 | `kis_daily_bar_count` | higher_in_failures | `0.24421` | `1.2832` | `93.24416` | `93.00716` |
| 7 | `kis_daily_range_20d_low` | lower_in_failures | `-0.299864` | `1.1711` | `35151.2651` | `81569.593079` |
| 8 | `entry_reference_price` | lower_in_failures | `-0.301983` | `1.1623` | `41669.988746` | `98250.580151` |
| 9 | `kis_current_price` | lower_in_failures | `-0.302639` | `1.1596` | `41736.938105` | `98300.206643` |
| 10 | `kis_daily_ma20` | lower_in_failures | `-0.295758` | `1.1718` | `42195.328226` | `97649.598737` |

| rank | category feature | category | n | failure % | lift | avg close | stop5 % |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | `kis_financial_statement_period` | `202601` | `23` | `100.0` | `1.8686` | `-4.349987` | `43.4783` |
| 2 | `kis_theme_news_top_risk_tag` | `policy_risk` | `23` | `95.6522` | `1.7873` | `-8.283225` | `100.0` |
| 3 | `primary_theme` | `산업재/기계` | `26` | `88.4615` | `1.653` | `-7.870179` | `88.4615` |
| 4 | `kis_theme_news_primary_theme` | `산업재/기계` | `26` | `88.4615` | `1.653` | `-7.870179` | `88.4615` |
| 5 | `primary_theme` | `2차전지` | `28` | `82.1429` | `1.5349` | `-7.709544` | `89.2857` |
| 6 | `kis_theme_news_primary_theme` | `2차전지` | `28` | `82.1429` | `1.5349` | `-7.709544` | `89.2857` |
| 7 | `feature_missing_keys` | `['turnover']` | `22` | `72.7273` | `1.359` | `-9.082056` | `95.4545` |
| 8 | `kis_theme_news_top_positive_tag` | `supply` | `38` | `71.0526` | `1.3277` | `-2.192797` | `89.4737` |
| 9 | `primary_theme` | `로봇/자동화` | `60` | `70.0` | `1.308` | `0.850092` | `100.0` |
| 10 | `kis_theme_news_primary_theme` | `로봇/자동화` | `60` | `70.0` | `1.308` | `0.850092` | `100.0` |

| rank | ticker | n | failure % | lift | avg close | avg MFE | avg MAE |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `003280.KS` | `50` | `100.0` | `1.8686` | `-13.085385` | `8.703956` | `-14.699511` |
| 2 | `023960.KS` | `40` | `100.0` | `1.8686` | `-4.281541` | `23.414237` | `-10.013087` |
| 3 | `006360.KS` | `35` | `100.0` | `1.8686` | `-6.4336` | `8.420254` | `-12.967179` |
| 4 | `005820.KS` | `34` | `100.0` | `1.8686` | `-4.856359` | `9.800803` | `-7.196249` |
| 5 | `037270.KS` | `34` | `100.0` | `1.8686` | `-9.63675` | `24.001207` | `-11.133624` |
| 6 | `372910.KS` | `34` | `100.0` | `1.8686` | `-4.482411` | `9.795083` | `-6.769684` |
| 7 | `000540.KS` | `29` | `100.0` | `1.8686` | `-4.02199` | `9.003067` | `-7.045072` |
| 8 | `011930.KS` | `29` | `100.0` | `1.8686` | `-22.929645` | `18.679958` | `-27.909442` |
| 9 | `092790.KS` | `29` | `100.0` | `1.8686` | `-7.413004` | `11.443776` | `-10.075179` |
| 10 | `000040.KS` | `24` | `100.0` | `1.8686` | `-3.97312` | `9.592354` | `-8.484446` |

### KOSDAQ

- skipped: `False`
- touch5_base_n: `14544`
- n_failure/n_control: `8462` / `2325`
- close_loss_given_touch5_pct: `58.1821`
- bad_path_given_touch5_pct: `84.014`

| rank | numeric feature | direction | d | worst bin lift | failure mean | control mean |
|---:|---|---|---:|---:|---:|---:|
| 1 | `kis_daily_bar_count` | higher_in_failures | `0.341996` | `1.4343` | `93.469747` | `93.133763` |
| 2 | `priority_rank` | higher_in_failures | `0.363977` | `1.2788` | `28.997015` | `21.515152` |
| 3 | `total_scans` | higher_in_failures | `0.366211` | `1.2239` | `1714.969038` | `1653.586237` |
| 4 | `alpha_score` | higher_in_failures | `0.392357` | `0.9801` | `44.795656` | `34.932773` |
| 5 | `filtered_count` | higher_in_failures | `0.274005` | `1.1188` | `1674.234342` | `1628.132903` |
| 6 | `kis_daily_pct_from_52w_high` | lower_in_failures | `-0.221928` | `1.1119` | `-32.190431` | `-28.772803` |
| 7 | `kis_day_change_pct` | higher_in_failures | `0.161019` | `1.206` | `1.264394` | `0.218911` |
| 8 | `tech_score` | higher_in_failures | `0.173206` | `0.8836` | `53.138481` | `49.125616` |
| 9 | `prob_clean` | lower_in_failures | `-0.198367` | `0.9437` | `27.274303` | `28.460584` |
| 10 | `kis_daily_range_20d_low` | lower_in_failures | `-0.198983` | `1.0688` | `16560.981919` | `25993.922151` |

| rank | category feature | category | n | failure % | lift | avg close | stop5 % |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | `primary_theme` | `산업재/기계` | `25` | `88.0` | `1.5125` | `-7.902229` | `88.0` |
| 2 | `kis_theme_news_primary_theme` | `산업재/기계` | `25` | `88.0` | `1.5125` | `-7.902229` | `88.0` |
| 3 | `kis_theme_news_top_positive_tag` | `contract_order` | `41` | `85.3659` | `1.4672` | `-11.766338` | `97.561` |
| 4 | `feature_missing_keys` | `['tech_score', 'prob_clean', 'whale_score', 'volume_ratio', 'turnover']` | `244` | `84.0164` | `1.444` | `-10.227054` | `93.0328` |
| 5 | `primary_theme` | `로봇/자동화` | `31` | `83.871` | `1.4415` | `-6.00644` | `100.0` |
| 6 | `kis_theme_news_primary_theme` | `로봇/자동화` | `31` | `83.871` | `1.4415` | `-6.00644` | `100.0` |
| 7 | `primary_theme` | `전자부품/디스플레이` | `29` | `79.3103` | `1.3631` | `-9.012646` | `86.2069` |
| 8 | `kis_theme_news_primary_theme` | `전자부품/디스플레이` | `29` | `79.3103` | `1.3631` | `-9.012646` | `86.2069` |
| 9 | `kis_theme_news_top_positive_tag` | `theme_ai` | `27` | `74.0741` | `1.2731` | `-1.853051` | `100.0` |
| 10 | `kis_theme_news_top_positive_tag` | `market_interest` | `194` | `70.6186` | `1.2138` | `-6.499482` | `91.2371` |

| rank | ticker | n | failure % | lift | avg close | avg MFE | avg MAE |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `051490.KQ` | `22` | `100.0` | `1.7187` | `-8.712419` | `7.97256` | `-10.176653` |
| 2 | `049080.KQ` | `21` | `100.0` | `1.7187` | `-14.49249` | `23.376546` | `-20.701996` |
| 3 | `024060.KQ` | `19` | `100.0` | `1.7187` | `-9.254111` | `15.233031` | `-11.774047` |
| 4 | `335810.KQ` | `19` | `100.0` | `1.7187` | `-3.871761` | `10.403447` | `-6.506301` |
| 5 | `000250.KQ` | `18` | `100.0` | `1.7187` | `-8.559953` | `10.486628` | `-12.620089` |
| 6 | `215100.KQ` | `18` | `100.0` | `1.7187` | `-8.518932` | `16.013941` | `-13.726792` |
| 7 | `129920.KQ` | `17` | `100.0` | `1.7187` | `-18.709623` | `9.134523` | `-20.739835` |
| 8 | `187660.KQ` | `17` | `100.0` | `1.7187` | `-13.433431` | `13.427797` | `-18.763892` |
| 9 | `355150.KQ` | `17` | `100.0` | `1.7187` | `-14.090564` | `14.140982` | `-21.919362` |
| 10 | `407400.KQ` | `17` | `100.0` | `1.7187` | `-16.993953` | `12.841329` | `-18.520383` |

### KOSPI

- skipped: `False`
- touch5_base_n: `11691`
- n_failure/n_control: `5578` / `2703`
- close_loss_given_touch5_pct: `47.7119`
- bad_path_given_touch5_pct: `76.8797`

| rank | numeric feature | direction | d | worst bin lift | failure mean | control mean |
|---:|---|---|---:|---:|---:|---:|
| 1 | `priority_rank` | higher_in_failures | `0.717534` | `1.0109` | `21.941606` | `12.62931` |
| 2 | `kis_financial_eps` | lower_in_failures | `-0.449425` | `1.2109` | `1218.969878` | `4360.675` |
| 3 | `entry_reference_price` | lower_in_failures | `-0.306274` | `1.2525` | `75036.80208` | `157771.705142` |
| 4 | `kis_daily_ma60` | lower_in_failures | `-0.303693` | `1.256` | `67784.616036` | `137827.866624` |
| 5 | `kis_current_price` | lower_in_failures | `-0.306273` | `1.2493` | `75198.937791` | `157713.596374` |
| 6 | `kis_daily_ma5` | lower_in_failures | `-0.304044` | `1.2478` | `75394.534062` | `158224.792231` |
| 7 | `kis_daily_range_20d_low` | lower_in_failures | `-0.29598` | `1.254` | `63353.304589` | `129373.305586` |
| 8 | `kis_daily_high_52w` | lower_in_failures | `-0.294693` | `1.2396` | `95341.399964` | `193254.598594` |
| 9 | `kis_daily_ma20` | lower_in_failures | `-0.29518` | `1.2333` | `75266.955351` | `154992.106733` |
| 10 | `kis_financial_reserve_ratio` | lower_in_failures | `-0.294546` | `1.2021` | `3955.801143` | `9747.162817` |

| rank | category feature | category | n | failure % | lift | avg close | stop5 % |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | `kis_financial_statement_period` | `202601` | `23` | `100.0` | `2.0959` | `-4.349987` | `43.4783` |
| 2 | `kis_stock_trade_stop` | `Y` | `22` | `100.0` | `2.0959` | `-10.178017` | `95.4545` |
| 3 | `primary_theme` | `2차전지` | `20` | `80.0` | `1.6767` | `-5.559212` | `90.0` |
| 4 | `kis_theme_news_primary_theme` | `2차전지` | `20` | `80.0` | `1.6767` | `-5.559212` | `90.0` |
| 5 | `kis_theme_news_top_positive_tag` | `supply` | `32` | `71.875` | `1.5064` | `-2.64216` | `87.5` |
| 6 | `kis_financial_statement_period` | `202509` | `242` | `61.5702` | `1.2905` | `-2.027238` | `64.4628` |
| 7 | `primary_theme` | `자동차` | `78` | `57.6923` | `1.2092` | `2.077591` | `79.4872` |
| 8 | `kis_theme_news_primary_theme` | `자동차` | `78` | `57.6923` | `1.2092` | `2.077591` | `79.4872` |
| 9 | `kis_financial_statement_period` | `UNKNOWN` | `117` | `57.265` | `1.2002` | `-1.553022` | `63.2479` |
| 10 | `primary_theme` | `로봇/자동화` | `29` | `55.1724` | `1.1564` | `8.179489` | `100.0` |

| rank | ticker | n | failure % | lift | avg close | avg MFE | avg MAE |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `003280.KS` | `50` | `100.0` | `2.0959` | `-13.085385` | `8.703956` | `-14.699511` |
| 2 | `023960.KS` | `40` | `100.0` | `2.0959` | `-4.281541` | `23.414237` | `-10.013087` |
| 3 | `006360.KS` | `35` | `100.0` | `2.0959` | `-6.4336` | `8.420254` | `-12.967179` |
| 4 | `005820.KS` | `34` | `100.0` | `2.0959` | `-4.856359` | `9.800803` | `-7.196249` |
| 5 | `037270.KS` | `34` | `100.0` | `2.0959` | `-9.63675` | `24.001207` | `-11.133624` |
| 6 | `372910.KS` | `34` | `100.0` | `2.0959` | `-4.482411` | `9.795083` | `-6.769684` |
| 7 | `000540.KS` | `29` | `100.0` | `2.0959` | `-4.02199` | `9.003067` | `-7.045072` |
| 8 | `011930.KS` | `29` | `100.0` | `2.0959` | `-22.929645` | `18.679958` | `-27.909442` |
| 9 | `092790.KS` | `29` | `100.0` | `2.0959` | `-7.413004` | `11.443776` | `-10.075179` |
| 10 | `000040.KS` | `24` | `100.0` | `2.0959` | `-3.97312` | `9.592354` | `-8.484446` |

## Actionable Hypotheses

- `KOSPI` `category` `kis_financial_statement_period`: lift=`2.0959` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.
- `KOSPI` `category` `kis_stock_trade_stop`: lift=`2.0959` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.
- `ALL` `category` `kis_financial_statement_period`: lift=`1.8686` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.
- `ALL` `category` `kis_theme_news_top_risk_tag`: lift=`1.7873` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.
- `KOSPI` `category` `primary_theme`: lift=`1.6767` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.
- `KOSPI` `category` `kis_theme_news_primary_theme`: lift=`1.6767` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.
- `ALL` `category` `primary_theme`: lift=`1.653` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.
- `ALL` `category` `kis_theme_news_primary_theme`: lift=`1.653` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.
- `ALL` `category` `primary_theme`: lift=`1.5349` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.
- `KOSDAQ` `category` `primary_theme`: lift=`1.5125` d=`None` implication=Treat this category as a separate exit regime before allowing +10% hold targets.

## Notes

- Primary failure cohort is touch5_close_loss: +5% MFE after buy premium, then 5D close < 0%.
- Control cohort is clean_touch5_close_defense: +5% MFE, 5D close > 0%, no -5% stop proxy and no 1D <-3% early weakness.
- Numeric/categorical traits exclude realized outcome columns so they can feed future admission and TP/SL profiles.
- Ticker traits are evidence for watch/profile routing, not standalone promotion rules when support is small.
