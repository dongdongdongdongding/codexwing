# KOSDAQ Ordered Candidate Search

- market: `KOSDAQ`
- generated_at: `2026-05-27T02:41:25.433800+00:00`
- rows_labeled: `9260`
- ordered_label_ready_rows: `8568`
- unique_ticker_dates: `2315`
- split_day: `2026-05-05`

## Baseline

- `5D_ordered_5v5`: all n=2184 win=38.5531%, test n=1171 win=29.2058%, test_stop=70.7088%
- `5D_ordered_8v5`: all n=2148 win=29.6555%, test n=1135 win=22.9075%, test_stop=77.0044%
- `5D_ordered_10v5`: all n=2131 win=25.0117%, test n=1118 win=19.0519%, test_stop=80.7692%
- `5D_ordered_12v5`: all n=2105 win=20.8551%, test n=1092 win=15.3846%, test_stop=84.1575%

## Flow Feature Coverage

- unique_ticker_dates: `2315`
- `foreigner`: non_empty=779 coverage=33.6501%
- `foreign_flow`: non_empty=779 coverage=33.6501%
- `foreigner_1d`: non_empty=553 coverage=23.8877%
- `foreigner_3d`: non_empty=553 coverage=23.8877%
- `foreigner_10d`: non_empty=553 coverage=23.8877%
- `institution`: non_empty=779 coverage=33.6501%
- `institution_flow`: non_empty=779 coverage=33.6501%
- `institution_1d`: non_empty=553 coverage=23.8877%
- `institution_3d`: non_empty=553 coverage=23.8877%
- `institution_10d`: non_empty=553 coverage=23.8877%
- `retail`: non_empty=779 coverage=33.6501%
- `retail_flow`: non_empty=779 coverage=33.6501%
- `retail_1d`: non_empty=553 coverage=23.8877%
- `retail_3d`: non_empty=553 coverage=23.8877%
- `retail_10d`: non_empty=553 coverage=23.8877%
- `whale_flow_1d`: non_empty=553 coverage=23.8877%
- `whale_flow_3d`: non_empty=553 coverage=23.8877%
- `whale_flow_10d`: non_empty=553 coverage=23.8877%
- `dominant`: non_empty=779 coverage=33.6501%
- `whale_trend`: non_empty=779 coverage=33.6501%
- `flow_consensus_buying`: non_empty=779 coverage=33.6501%
- `retail_dominant`: non_empty=779 coverage=33.6501%
- `flow_window`: non_empty=553 coverage=23.8877%
- `flow_asof`: non_empty=553 coverage=23.8877%

## Theme Refresh

- refreshed_rows: `1464` / `9260`
- refreshed_pct: `15.8099`
- unclassified_rows_after_refresh: `280`
- primary_source_distribution: `{'stock_master': 5908, 'not_refreshed': 3352}`

## Practical Watch 75pct Non-Theme

- `5D_ordered_5v5` ['decision_score>=96', 'theme_day_avg_alpha_score<=61.5714', 'theme_day_strength_rank<=6', 'theme_day_strength_pct<=87.5']: all n=20 win=75.0%, train n=11 win=54.5455%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=100.0%, min_fold=100.0%, avg_mfe=9.5599%, avg_mae=-1.9077%, min_mae=-14.8999%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 8/50.0% test 9/100.0%]
- `5D_ordered_5v5` ['decision_score>=96', 'theme_day_avg_alpha_score<=61.5714', 'theme_day_strength_rank<=6', 'theme_day_strength_pct<=93.3333']: all n=20 win=75.0%, train n=11 win=54.5455%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=100.0%, min_fold=100.0%, avg_mfe=9.5599%, avg_mae=-1.9077%, min_mae=-14.8999%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 8/50.0% test 9/100.0%]
- `5D_ordered_5v5` ['decision_score>=96', 'theme_day_avg_alpha_score<=61.5714', 'theme_day_strength_rank<=6', 'theme_day_avg_volume_ratio>=1.05']: all n=17 win=70.5882%, train n=8 win=37.5%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=100.0%, min_fold=100.0%, avg_mfe=9.0268%, avg_mae=-1.7445%, min_mae=-10.1382%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 6/33.3333% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_avg_alpha_score<=69.5321']: all n=21 win=95.2381%, train n=8 win=87.5%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=95.2381%, min_fold=87.5%, avg_mfe=11.5589%, avg_mae=-0.8535%, min_mae=-6.3098%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/87.5% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_avg_alpha_score<=73.1111']: all n=21 win=95.2381%, train n=8 win=87.5%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=95.2381%, min_fold=87.5%, avg_mfe=11.5589%, avg_mae=-0.8535%, min_mae=-6.3098%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/87.5% test 13/100.0%]
- `5D_ordered_5v5` ['ml_prob<=40', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'theme_day_avg_alpha_score<=73.1111']: all n=17 win=94.1176%, train n=8 win=87.5%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=94.1176%, min_fold=87.5%, avg_mfe=9.8146%, avg_mae=-0.9286%, min_mae=-5.035%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 6/83.3333% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_strength_score>=4.1706']: all n=21 win=90.4762%, train n=8 win=75.0%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=90.4762%, min_fold=75.0%, avg_mfe=10.588%, avg_mae=-1.0845%, min_mae=-6.6092%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/75.0% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.9476', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_strength_score>=4.1706']: all n=21 win=90.4762%, train n=8 win=75.0%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=90.4762%, min_fold=75.0%, avg_mfe=10.588%, avg_mae=-1.0845%, min_mae=-6.6092%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/75.0% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=75', 'alpha_score<=66']: all n=21 win=85.7143%, train n=9 win=66.6667%, test n=12 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=89.4737%, min_fold=71.4286%, avg_mfe=9.4968%, avg_mae=-1.2743%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 12/100.0%; trend=UP train 9/66.6667% test 12/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=96', 'theme_day_strength_pct<=87.5']: all n=19 win=84.2105%, train n=8 win=62.5%, test n=11 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=71.4286%, avg_mfe=9.9215%, avg_mae=-1.7608%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 11/100.0%; trend=UP train 7/57.1429% test 11/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=96', 'theme_day_strength_pct<=93.3333']: all n=19 win=84.2105%, train n=8 win=62.5%, test n=11 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=71.4286%, avg_mfe=9.9215%, avg_mae=-1.7608%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 11/100.0%; trend=UP train 7/57.1429% test 11/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=96', 'theme_day_avg_volume_ratio>=1.35']: all n=19 win=84.2105%, train n=9 win=66.6667%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=75.0%, avg_mfe=9.6654%, avg_mae=-1.9377%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 7/57.1429% test 10/100.0%]
- `5D_ordered_5v5` ['ml_prob=[20.4,40]', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'alpha_score<=87']: all n=18 win=88.8889%, train n=9 win=77.7778%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=77.7778%, avg_mfe=9.3734%, avg_mae=-1.3732%, min_mae=-5.6393%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/77.7778% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=92', 'theme_day_avg_volume_ratio>=1.45']: all n=18 win=83.3333%, train n=8 win=62.5%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.2353%, min_fold=71.4286%, avg_mfe=9.9663%, avg_mae=-1.659%, min_mae=-6.6151%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 5/60.0% test 10/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.4', 'theme_day_avg_alpha_score<=69.5321', 'decision_score>=90', 'theme_day_avg_volume_ratio>=1.35']: all n=16 win=81.25%, train n=8 win=62.5%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=86.6667%, min_fold=71.4286%, avg_mfe=10.7502%, avg_mae=-2.0545%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 7/57.1429% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=96', 'theme_day_avg_volume_ratio>=1.05']: all n=22 win=81.8182%, train n=11 win=63.6364%, test n=11 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.7143%, min_fold=70.0%, avg_mfe=9.3621%, avg_mae=-1.8738%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 11/100.0%; trend=UP train 9/55.5556% test 11/100.0%]
- `5D_ordered_5v5` ['ml_prob=[20.4,40]', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'theme_day_avg_volume_ratio>=1.05']: all n=21 win=85.7143%, train n=12 win=75.0%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.7143%, min_fold=75.0%, avg_mfe=9.1195%, avg_mae=-1.5686%, min_mae=-5.6393%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 12/75.0% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=92', 'theme_day_strength_pct<=87.5']: all n=21 win=80.9524%, train n=10 win=60.0%, test n=11 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.0%, min_fold=66.6667%, avg_mfe=9.5503%, avg_mae=-1.8862%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 11/100.0%; trend=UP train 9/55.5556% test 11/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=92', 'theme_day_strength_pct<=93.3333']: all n=21 win=80.9524%, train n=10 win=60.0%, test n=11 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.0%, min_fold=66.6667%, avg_mfe=9.5503%, avg_mae=-1.8862%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 11/100.0%; trend=UP train 9/55.5556% test 11/100.0%]
- `5D_ordered_5v5` ['tech_score<=75', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'alpha_score<=66', 'theme_day_strength_score>=4.1706']: all n=20 win=85.0%, train n=8 win=62.5%, test n=12 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.0%, min_fold=62.5%, avg_mfe=8.8517%, avg_mae=-1.3004%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 12/100.0%; trend=UP train 8/62.5% test 12/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.4', 'theme_day_avg_alpha_score<=69.5321', 'decision_score>=90', 'theme_day_avg_volume_ratio>=1.05']: all n=20 win=80.0%, train n=11 win=63.6364%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=84.2105%, min_fold=70.0%, avg_mfe=10.2264%, avg_mae=-1.9859%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/55.5556% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=67.3333', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_symbol_count>=6']: all n=19 win=84.2105%, train n=9 win=66.6667%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=84.2105%, min_fold=66.6667%, avg_mfe=9.9894%, avg_mae=-1.5733%, min_mae=-8.8683%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 9/66.6667% test 10/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=92', 'theme_day_avg_volume_ratio>=1.35']: all n=20 win=80.0%, train n=10 win=60.0%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=84.2105%, min_fold=66.6667%, avg_mfe=9.1821%, avg_mae=-2.1391%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 7/57.1429% test 10/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.4', 'theme_day_avg_alpha_score<=67.3333', 'conviction_score<=73.4', 'theme_day_avg_volume_ratio>=1.05']: all n=18 win=83.3333%, train n=9 win=66.6667%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=66.6667%, avg_mfe=11.0185%, avg_mae=-0.9107%, min_mae=-8.078%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 8/62.5% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=1.05', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'alpha_score<=74']: all n=23 win=82.6087%, train n=10 win=60.0%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=82.6087%, min_fold=25.0%, avg_mfe=9.8441%, avg_mae=-1.4282%, min_mae=-7.2695%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 10/60.0% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=67.3333', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=75', 'theme_day_strength_rank<=8']: all n=17 win=82.3529%, train n=9 win=66.6667%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=82.353%, min_fold=66.6667%, avg_mfe=8.484%, avg_mae=-2.0607%, min_mae=-8.8683%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 9/66.6667% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=67.3333', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=80', 'theme_day_strength_rank<=8']: all n=17 win=82.3529%, train n=9 win=66.6667%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=82.353%, min_fold=66.6667%, avg_mfe=8.484%, avg_mae=-2.0607%, min_mae=-8.8683%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 9/66.6667% test 8/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.4', 'theme_day_avg_alpha_score<=69.5321', 'decision_score>=90', 'theme_day_strength_pct<=87.5']: all n=18 win=77.7778%, train n=9 win=55.5556%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=82.3529%, min_fold=62.5%, avg_mfe=10.6673%, avg_mae=-2.0404%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 8/50.0% test 9/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.4', 'theme_day_avg_alpha_score<=69.5321', 'decision_score>=90', 'theme_day_strength_pct<=93.3333']: all n=18 win=77.7778%, train n=9 win=55.5556%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=82.3529%, min_fold=62.5%, avg_mfe=10.6673%, avg_mae=-2.0404%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 8/50.0% test 9/100.0%]
- `5D_ordered_5v5` ['ml_prob<=40', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'theme_day_strength_pct<=87.5']: all n=17 win=82.3529%, train n=8 win=62.5%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=82.3529%, min_fold=62.5%, avg_mfe=8.8136%, avg_mae=-1.8326%, min_mae=-8.5519%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 5/40.0% test 9/100.0%]

## Practical Candidates 75pct Non-Theme

- none

## Strong Practical 80pct Non-Theme

- none

## Recent-Regime 75pct Non-Theme Diagnostics

- none

## Promotion-Ready Non-Theme Candidates

- none

## Release-Like Non-Theme Candidates

- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_avg_alpha_score<=69.5321']: all n=21 win=95.2381%, train n=8 win=87.5%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=95.2381%, min_fold=87.5%, avg_mfe=11.5589%, avg_mae=-0.8535%, min_mae=-6.3098%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/87.5% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_avg_alpha_score<=73.1111']: all n=21 win=95.2381%, train n=8 win=87.5%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=95.2381%, min_fold=87.5%, avg_mfe=11.5589%, avg_mae=-0.8535%, min_mae=-6.3098%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/87.5% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_strength_score>=4.1706']: all n=21 win=90.4762%, train n=8 win=75.0%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=90.4762%, min_fold=75.0%, avg_mfe=10.588%, avg_mae=-1.0845%, min_mae=-6.6092%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/75.0% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.9476', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_strength_score>=4.1706']: all n=21 win=90.4762%, train n=8 win=75.0%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=90.4762%, min_fold=75.0%, avg_mfe=10.588%, avg_mae=-1.0845%, min_mae=-6.6092%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/75.0% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=75', 'alpha_score<=66']: all n=21 win=85.7143%, train n=9 win=66.6667%, test n=12 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=89.4737%, min_fold=71.4286%, avg_mfe=9.4968%, avg_mae=-1.2743%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 12/100.0%; trend=UP train 9/66.6667% test 12/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=96', 'theme_day_avg_volume_ratio>=1.35']: all n=19 win=84.2105%, train n=9 win=66.6667%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=75.0%, avg_mfe=9.6654%, avg_mae=-1.9377%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 7/57.1429% test 10/100.0%]
- `5D_ordered_5v5` ['ml_prob=[20.4,40]', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'alpha_score<=87']: all n=18 win=88.8889%, train n=9 win=77.7778%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=77.7778%, avg_mfe=9.3734%, avg_mae=-1.3732%, min_mae=-5.6393%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/77.7778% test 9/100.0%]
- `5D_ordered_5v5` ['ml_prob=[20.4,40]', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'theme_day_avg_volume_ratio>=1.05']: all n=21 win=85.7143%, train n=12 win=75.0%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.7143%, min_fold=75.0%, avg_mfe=9.1195%, avg_mae=-1.5686%, min_mae=-5.6393%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 12/75.0% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=67.3333', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_symbol_count>=6']: all n=19 win=84.2105%, train n=9 win=66.6667%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=84.2105%, min_fold=66.6667%, avg_mfe=9.9894%, avg_mae=-1.5733%, min_mae=-8.8683%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 9/66.6667% test 10/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.4', 'theme_day_avg_alpha_score<=67.3333', 'conviction_score<=73.4', 'theme_day_avg_volume_ratio>=1.05']: all n=18 win=83.3333%, train n=9 win=66.6667%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=66.6667%, avg_mfe=11.0185%, avg_mae=-0.9107%, min_mae=-8.078%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 8/62.5% test 9/100.0%]
- `5D_ordered_5v5` ['ml_prob<=40', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'theme_day_avg_volume_ratio>=1.05']: all n=28 win=82.1429%, train n=19 win=73.6842%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=82.1428%, min_fold=73.6842%, avg_mfe=9.0869%, avg_mae=-1.9956%, min_mae=-9.6838%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 16/75.0% test 9/100.0%]
- `5D_ordered_5v5` ['ml_prob=[20.4,40]', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6']: all n=22 win=81.8182%, train n=13 win=69.2308%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=69.2308%, avg_mfe=8.7984%, avg_mae=-1.7922%, min_mae=-6.4873%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 13/69.2308% test 9/100.0%]
- `5D_ordered_5v5` ['ml_prob=[20.4,40]', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'theme_day_avg_expected_return_3d_pct>=-0.1806']: all n=22 win=81.8182%, train n=13 win=69.2308%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=69.2308%, avg_mfe=8.7984%, avg_mae=-1.7922%, min_mae=-6.4873%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 13/69.2308% test 9/100.0%]
- `5D_ordered_5v5` ['ml_prob=[20.4,40]', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'theme_day_avg_volume_ratio>=0.9476']: all n=22 win=81.8182%, train n=13 win=69.2308%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=69.2308%, avg_mfe=8.7984%, avg_mae=-1.7922%, min_mae=-6.4873%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 13/69.2308% test 9/100.0%]
- `5D_ordered_5v5` ['ml_prob=[20.4,40]', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'theme_day_strength_score>=4.1706']: all n=22 win=81.8182%, train n=13 win=69.2308%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=81.8182%, min_fold=69.2308%, avg_mfe=8.7984%, avg_mae=-1.7922%, min_mae=-6.4873%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 13/69.2308% test 9/100.0%]

## Current Cohort Baseline

### 5D_ordered_5v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 79 | 43.038 | 53.1646 | -1.5171 | -46.3097 | 30.9707 | 32.7869 | 5.3773 | -17.0874 |
| Top3 | 184 | 45.6522 | 50.5435 | -0.2489 | -46.3097 | 50.3643 | 34.4595 | 6.3884 | -27.957 |
| Top5 | 275 | 41.8182 | 55.2727 | -0.2123 | -46.3097 | 56.9153 | 34.5291 | 5.9531 | -27.957 |
| Exception Leader | 215 | 50.2326 | 46.5116 | 0.9769 | -34.8118 | 65.653 | 21.6418 | 5.7668 | -19.2557 |
| Top5+Exception | 490 | 45.5102 | 51.4286 | 0.4895 | -46.3097 | 65.653 | 29.6919 | 5.8714 | -27.957 |

### 5D_ordered_8v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 79 | 27.8481 | 64.557 | -1.5171 | -46.3097 | 30.9707 | 32.7869 | 5.995 | -17.0874 |
| Top3 | 184 | 34.2391 | 57.6087 | -0.2489 | -46.3097 | 50.3643 | 34.4595 | 6.9697 | -27.957 |
| Top5 | 275 | 30.1818 | 62.5455 | -0.2123 | -46.3097 | 56.9153 | 34.5291 | 6.5299 | -27.957 |
| Exception Leader | 210 | 38.5714 | 51.9048 | 0.9769 | -34.8118 | 65.653 | 21.6418 | 6.9238 | -26.8063 |
| Top5+Exception | 485 | 33.8144 | 57.9381 | 0.4895 | -46.3097 | 65.653 | 29.6919 | 6.7005 | -27.957 |

### 5D_ordered_10v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 79 | 26.5823 | 64.557 | -1.5171 | -46.3097 | 30.9707 | 32.7869 | 6.1302 | -17.0874 |
| Top3 | 184 | 30.9783 | 59.2391 | -0.2489 | -46.3097 | 50.3643 | 34.4595 | 7.1597 | -27.957 |
| Top5 | 275 | 27.2727 | 63.6364 | -0.2123 | -46.3097 | 56.9153 | 34.5291 | 6.8316 | -27.957 |
| Exception Leader | 209 | 31.5789 | 54.5455 | 0.9769 | -34.8118 | 65.653 | 21.6418 | 7.4033 | -26.8063 |
| Top5+Exception | 484 | 29.1322 | 59.7107 | 0.4895 | -46.3097 | 65.653 | 29.6919 | 7.0785 | -27.957 |

### 5D_ordered_12v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 78 | 20.5128 | 67.9487 | -1.5171 | -46.3097 | 30.9707 | 32.7869 | 6.3717 | -17.0874 |
| Top3 | 183 | 25.1366 | 62.8415 | -0.2489 | -46.3097 | 50.3643 | 34.4595 | 7.4094 | -27.957 |
| Top5 | 274 | 22.2628 | 66.4234 | -0.2123 | -46.3097 | 56.9153 | 34.5291 | 7.2371 | -27.957 |
| Exception Leader | 207 | 25.6039 | 57.0048 | 0.9769 | -34.8118 | 65.653 | 21.6418 | 7.4876 | -26.8063 |
| Top5+Exception | 481 | 23.7006 | 62.3701 | 0.4895 | -46.3097 | 65.653 | 29.6919 | 7.3449 | -27.957 |


## Curated Ordered Candidates

- `kosdaq_low_model_1d_rebound_5v5` `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'selection_lane=1d', 'prob_clean<=31.8']: all n=22 win=77.2727%, train n=20 win=80.0%, test n=2 win=50.0%, test_stop=50.0%, test_med_close=-12.9114%, test_min_close=-12.9114%, test_loss5=100.0%, fold_win=80.0%, min_fold=75.0%, avg_mfe=9.4125%, avg_mae=-2.9842%, min_mae=-12.4594%, same_regime=[market_gate=GREEN train 0/None% test 2/50.0%; trend=UP train 19/78.9474% test 2/50.0%]
- `kosdaq_low_loss_theme_rebound_5v5` `5D_ordered_5v5` ['tech_score<=80', 'theme_day_avg_decision_score<=63.0879', 'theme_day_symbol_count>=7', 'trend=UP']: all n=36 win=55.5556%, train n=15 win=80.0%, test n=21 win=38.0952%, test_stop=61.9048%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=55.5555%, min_fold=38.0952%, avg_mfe=6.6742%, avg_mae=-5.1418%, min_mae=-13.7153%, same_regime=[market_gate=GREEN train 0/None% test 18/38.8889%; trend=UP train 15/80.0% test 21/38.0952%]

## High-Win Small-N Non-Theme Candidates

- `5D_ordered_5v5` ['decision_score>=96', 'theme_day_avg_alpha_score<=61.5714', 'theme_day_strength_rank<=6', 'theme_day_strength_pct<=87.5']: all n=20 win=75.0%, train n=11 win=54.5455%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=100.0%, min_fold=100.0%, avg_mfe=9.5599%, avg_mae=-1.9077%, min_mae=-14.8999%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 8/50.0% test 9/100.0%]
- `5D_ordered_5v5` ['decision_score>=96', 'theme_day_avg_alpha_score<=61.5714', 'theme_day_strength_rank<=6', 'theme_day_strength_pct<=93.3333']: all n=20 win=75.0%, train n=11 win=54.5455%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=100.0%, min_fold=100.0%, avg_mfe=9.5599%, avg_mae=-1.9077%, min_mae=-14.8999%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 8/50.0% test 9/100.0%]
- `5D_ordered_5v5` ['decision_score>=96', 'theme_day_avg_alpha_score<=61.5714', 'theme_day_strength_rank<=6', 'theme_day_avg_volume_ratio>=1.05']: all n=17 win=70.5882%, train n=8 win=37.5%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=100.0%, min_fold=100.0%, avg_mfe=9.0268%, avg_mae=-1.7445%, min_mae=-10.1382%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 6/33.3333% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_avg_alpha_score<=69.5321']: all n=21 win=95.2381%, train n=8 win=87.5%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=95.2381%, min_fold=87.5%, avg_mfe=11.5589%, avg_mae=-0.8535%, min_mae=-6.3098%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/87.5% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_avg_alpha_score<=73.1111']: all n=21 win=95.2381%, train n=8 win=87.5%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=95.2381%, min_fold=87.5%, avg_mfe=11.5589%, avg_mae=-0.8535%, min_mae=-6.3098%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/87.5% test 13/100.0%]
- `5D_ordered_5v5` ['ml_prob<=40', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'theme_day_avg_alpha_score<=73.1111']: all n=17 win=94.1176%, train n=8 win=87.5%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=94.1176%, min_fold=87.5%, avg_mfe=9.8146%, avg_mae=-0.9286%, min_mae=-5.035%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 6/83.3333% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_strength_score>=4.1706']: all n=21 win=90.4762%, train n=8 win=75.0%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=90.4762%, min_fold=75.0%, avg_mfe=10.588%, avg_mae=-1.0845%, min_mae=-6.6092%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/75.0% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.9476', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=65', 'theme_day_strength_score>=4.1706']: all n=21 win=90.4762%, train n=8 win=75.0%, test n=13 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=90.4762%, min_fold=75.0%, avg_mfe=10.588%, avg_mae=-1.0845%, min_mae=-6.6092%, same_regime=[market_gate=GREEN train 0/None% test 13/100.0%; trend=UP train 8/75.0% test 13/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_volume_ratio>=0.8633', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'tech_score<=75', 'alpha_score<=66']: all n=21 win=85.7143%, train n=9 win=66.6667%, test n=12 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=89.4737%, min_fold=71.4286%, avg_mfe=9.4968%, avg_mae=-1.2743%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 12/100.0%; trend=UP train 9/66.6667% test 12/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=96', 'theme_day_strength_pct<=87.5']: all n=19 win=84.2105%, train n=8 win=62.5%, test n=11 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=71.4286%, avg_mfe=9.9215%, avg_mae=-1.7608%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 11/100.0%; trend=UP train 7/57.1429% test 11/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=96', 'theme_day_strength_pct<=93.3333']: all n=19 win=84.2105%, train n=8 win=62.5%, test n=11 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=71.4286%, avg_mfe=9.9215%, avg_mae=-1.7608%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 11/100.0%; trend=UP train 7/57.1429% test 11/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=96', 'theme_day_avg_volume_ratio>=1.35']: all n=19 win=84.2105%, train n=9 win=66.6667%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=75.0%, avg_mfe=9.6654%, avg_mae=-1.9377%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 7/57.1429% test 10/100.0%]
- `5D_ordered_5v5` ['ml_prob=[20.4,40]', 'theme_day_avg_expected_return_1d_pct>=0.1514', 'theme_day_symbol_count>=6', 'alpha_score<=87']: all n=18 win=88.8889%, train n=9 win=77.7778%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.8889%, min_fold=77.7778%, avg_mfe=9.3734%, avg_mae=-1.3732%, min_mae=-5.6393%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/77.7778% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5321', 'theme_day_avg_expected_return_3d_pct>=-0.1806', 'decision_score>=92', 'theme_day_avg_volume_ratio>=1.45']: all n=18 win=83.3333%, train n=8 win=62.5%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=88.2353%, min_fold=71.4286%, avg_mfe=9.9663%, avg_mae=-1.659%, min_mae=-6.6151%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 5/60.0% test 10/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.4', 'theme_day_avg_alpha_score<=69.5321', 'decision_score>=90', 'theme_day_avg_volume_ratio>=1.35']: all n=16 win=81.25%, train n=8 win=62.5%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=86.6667%, min_fold=71.4286%, avg_mfe=10.7502%, avg_mae=-2.0545%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 7/57.1429% test 8/100.0%]

## Theme-Dependent Diagnostics

- none

## Notes

- Production scanner ranking is unchanged.
- Practical watch starts at ordered test win >=75%.
- Practical candidates require ordered test win >=75%, all win >=60%, train win >=55%, and stop/loss-tail/fold safeguards.
- Recent-regime candidates pass the latest test window but fail the all/train stability floor, so they are not promotion candidates.
- Strong practical candidates use ordered test win >=80%; promotion-ready remains stricter and requires larger samples.
- feature_quality is excluded from searched categorical conditions because it is a data completeness marker, not a trading signal.
- theme_day_* features are dynamic same-day peer aggregates, not fixed theme-name filters.
- same_regime_diagnostics show train/test behavior inside the candidate's dominant test regime dimensions.
- Release-like candidates exclude static primary_theme conditions to avoid hard-coded theme overfit.
- Rows with immature no-touch labels are excluded from win-rate denominators.
- Daily OHLCV same-bar target/stop order is conservative stop-first via the imported labeler.
