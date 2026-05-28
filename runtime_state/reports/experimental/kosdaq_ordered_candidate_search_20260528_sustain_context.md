# KOSDAQ Ordered Candidate Search

- market: `KOSDAQ`
- generated_at: `2026-05-28T08:11:57.477803+00:00`
- rows_labeled: `9416`
- ordered_label_ready_rows: `8568`
- unique_ticker_dates: `2354`
- split_day: `2026-05-06`

## Baseline

- `5D_ordered_5v5`: all n=2184 win=38.5531%, test n=1118 win=29.3381%, test_stop=70.5725%
- `5D_ordered_8v5`: all n=2148 win=29.6555%, test n=1082 win=22.8281%, test_stop=77.0795%
- `5D_ordered_10v5`: all n=2131 win=25.0117%, test n=1065 win=19.2488%, test_stop=80.5634%
- `5D_ordered_12v5`: all n=2105 win=20.8551%, test n=1039 win=15.6882%, test_stop=83.9269%

## Flow Feature Coverage

- unique_ticker_dates: `2354`
- `foreigner`: non_empty=782 coverage=33.2201%
- `foreign_flow`: non_empty=782 coverage=33.2201%
- `foreigner_1d`: non_empty=556 coverage=23.6194%
- `foreigner_3d`: non_empty=556 coverage=23.6194%
- `foreigner_10d`: non_empty=556 coverage=23.6194%
- `institution`: non_empty=782 coverage=33.2201%
- `institution_flow`: non_empty=782 coverage=33.2201%
- `institution_1d`: non_empty=556 coverage=23.6194%
- `institution_3d`: non_empty=556 coverage=23.6194%
- `institution_10d`: non_empty=556 coverage=23.6194%
- `retail`: non_empty=782 coverage=33.2201%
- `retail_flow`: non_empty=782 coverage=33.2201%
- `retail_1d`: non_empty=556 coverage=23.6194%
- `retail_3d`: non_empty=556 coverage=23.6194%
- `retail_10d`: non_empty=556 coverage=23.6194%
- `whale_flow_1d`: non_empty=556 coverage=23.6194%
- `whale_flow_3d`: non_empty=556 coverage=23.6194%
- `whale_flow_10d`: non_empty=556 coverage=23.6194%
- `dominant`: non_empty=782 coverage=33.2201%
- `whale_trend`: non_empty=782 coverage=33.2201%
- `flow_consensus_buying`: non_empty=782 coverage=33.2201%
- `retail_dominant`: non_empty=782 coverage=33.2201%
- `flow_window`: non_empty=556 coverage=23.6194%
- `flow_asof`: non_empty=556 coverage=23.6194%

## Theme Refresh

- refreshed_rows: `32` / `9416`
- refreshed_pct: `0.3398`
- unclassified_rows_after_refresh: `280`
- primary_source_distribution: `{'stock_master': 8076, 'not_refreshed': 1340}`

## Practical Watch 75pct Non-Theme

- `5D_ordered_5v5` ['whale_score<=78', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'theme_day_avg_decision_score>=65.265']: all n=27 win=85.1852%, train n=13 win=69.2308%, test n=14 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.1852%, min_fold=69.2308%, avg_mfe=12.4907%, avg_mae=-2.8498%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 14/100.0%; trend=UP train 12/75.0% test 14/100.0%]
- `5D_ordered_5v5` ['whale_score<=78', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'theme_day_strength_rank>=2']: all n=27 win=85.1852%, train n=13 win=69.2308%, test n=14 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.1852%, min_fold=69.2308%, avg_mfe=12.4907%, avg_mae=-2.8498%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 14/100.0%; trend=UP train 12/75.0% test 14/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.39', 'theme_day_avg_alpha_score<=69.5714', 'decision_score>=90', 'theme_day_avg_volume_ratio>=1.05']: all n=20 win=80.0%, train n=11 win=63.6364%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=84.2105%, min_fold=70.0%, avg_mfe=10.2264%, avg_mae=-1.9859%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/55.5556% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5714', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'decision_score>=95.375', 'theme_day_avg_volume_ratio>=1.05']: all n=20 win=80.0%, train n=11 win=63.6364%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=84.2105%, min_fold=70.0%, avg_mfe=9.1409%, avg_mae=-2.0482%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/55.5556% test 9/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8731%, avg_mae=-3.2684%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8731%, avg_mae=-3.2684%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8561%, avg_mae=-2.9998%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8561%, avg_mae=-2.9998%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_rank<=4']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.0408%, avg_mae=-3.2465%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_pct>=77.7778']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.0408%, avg_mae=-3.2465%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_rank<=4']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.0408%, avg_mae=-3.2465%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_pct>=77.7778']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.0408%, avg_mae=-3.2465%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_avg_alpha_score<=73.3333']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=11.7046%, avg_mae=-3.0339%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 5/60.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_avg_alpha_score<=73.3333']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=11.7046%, avg_mae=-3.0339%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 5/60.0% test 8/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.39', 'theme_day_avg_alpha_score<=69.5714', 'decision_score>=90', 'theme_day_strength_pct<=87.5']: all n=19 win=78.9474%, train n=10 win=60.0%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=66.6667%, avg_mfe=10.837%, avg_mae=-2.0581%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/55.5556% test 9/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.39', 'theme_day_avg_alpha_score<=69.5714', 'decision_score>=90', 'theme_day_strength_pct<=93.3333']: all n=19 win=78.9474%, train n=10 win=60.0%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=66.6667%, avg_mfe=10.837%, avg_mae=-2.0581%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/55.5556% test 9/100.0%]
- `5D_ordered_5v5` ['whale_score<=78', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'tech_score<=80']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=10.7281%, avg_mae=-3.3288%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 10/70.0% test 8/100.0%]
- `5D_ordered_5v5` ['expected_edge_score>=6.73', 'theme_day_avg_alpha_score<=69.5714', 'decision_score>=90', 'theme_day_avg_volume_ratio>=1.05']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=10.3977%, avg_mae=-2.0044%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 9/55.5556% test 8/100.0%]
- `5D_ordered_5v5` ['expected_edge_score>=1.77', 'theme_day_avg_alpha_score<=67.6667', 'alpha_score<=49', 'theme_day_strength_pct<=87.5']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=10.0145%, avg_mae=-0.9254%, min_mae=-6.6519%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 10/70.0% test 8/100.0%]
- `5D_ordered_5v5` ['expected_edge_score>=1.77', 'theme_day_avg_alpha_score<=67.6667', 'alpha_score<=49', 'theme_day_strength_pct<=93.3333']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=10.0145%, avg_mae=-0.9254%, min_mae=-6.6519%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 10/70.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.9724%, avg_mae=-3.0686%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.9724%, avg_mae=-3.0686%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.9554%, avg_mae=-2.7999%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.9554%, avg_mae=-2.7999%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_avg_alpha_score<=73.3333']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.4596%, avg_mae=-2.8446%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 5/60.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_avg_alpha_score<=73.3333']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.4596%, avg_mae=-2.8446%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 5/60.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_rank<=4']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.3453%, avg_mae=-3.0572%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_pct>=77.7778']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.3453%, avg_mae=-3.0572%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_rank<=4']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.3453%, avg_mae=-3.0572%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_pct>=77.7778']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.3453%, avg_mae=-3.0572%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]

## Practical Candidates 75pct Non-Theme

- none

## Strong Practical 80pct Non-Theme

- none

## Recent-Regime 75pct Non-Theme Diagnostics

- none

## Promotion-Ready Non-Theme Candidates

- none

## Release-Like Non-Theme Candidates

- `5D_ordered_5v5` ['whale_score<=78', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'theme_day_avg_decision_score>=65.265']: all n=27 win=85.1852%, train n=13 win=69.2308%, test n=14 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.1852%, min_fold=69.2308%, avg_mfe=12.4907%, avg_mae=-2.8498%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 14/100.0%; trend=UP train 12/75.0% test 14/100.0%]
- `5D_ordered_5v5` ['whale_score<=78', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'theme_day_strength_rank>=2']: all n=27 win=85.1852%, train n=13 win=69.2308%, test n=14 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.1852%, min_fold=69.2308%, avg_mfe=12.4907%, avg_mae=-2.8498%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 14/100.0%; trend=UP train 12/75.0% test 14/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8731%, avg_mae=-3.2684%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8731%, avg_mae=-3.2684%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8561%, avg_mae=-2.9998%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8561%, avg_mae=-2.9998%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['whale_score<=78', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'tech_score<=80']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=10.7281%, avg_mae=-3.3288%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 10/70.0% test 8/100.0%]
- `5D_ordered_5v5` ['expected_edge_score>=1.77', 'theme_day_avg_alpha_score<=67.6667', 'alpha_score<=49', 'theme_day_strength_pct<=87.5']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=10.0145%, avg_mae=-0.9254%, min_mae=-6.6519%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 10/70.0% test 8/100.0%]
- `5D_ordered_5v5` ['expected_edge_score>=1.77', 'theme_day_avg_alpha_score<=67.6667', 'alpha_score<=49', 'theme_day_strength_pct<=93.3333']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=10.0145%, avg_mae=-0.9254%, min_mae=-6.6519%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 10/70.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.9724%, avg_mae=-3.0686%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.9724%, avg_mae=-3.0686%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.9554%, avg_mae=-2.7999%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=9.9554%, avg_mae=-2.7999%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_5v5` ['whale_score<=70', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'theme_day_avg_decision_score>=65.265']: all n=23 win=82.6087%, train n=13 win=69.2308%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=82.6087%, min_fold=69.2308%, avg_mfe=12.1105%, avg_mae=-3.1549%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 12/75.0% test 10/100.0%]
- `5D_ordered_5v5` ['whale_score<=70', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'theme_day_strength_rank>=2']: all n=23 win=82.6087%, train n=13 win=69.2308%, test n=10 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=82.6087%, min_fold=69.2308%, avg_mfe=12.1105%, avg_mae=-3.1549%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 10/100.0%; trend=UP train 12/75.0% test 10/100.0%]

## Current Cohort Baseline

### 5D_ordered_5v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 78 | 43.5897 | 53.8462 | -1.6266 | -46.3097 | 30.9707 | 33.3333 | 5.3976 | -17.0874 |
| Top3 | 183 | 45.9016 | 50.8197 | -0.2854 | -46.3097 | 50.3643 | 34.6939 | 6.4025 | -27.957 |
| Top5 | 274 | 41.9708 | 55.4745 | -0.2489 | -46.3097 | 56.9153 | 34.6847 | 5.961 | -27.957 |
| Exception Leader | 216 | 50.0 | 46.2963 | 0.9772 | -34.8118 | 65.653 | 21.4815 | 5.7576 | -19.2557 |
| Top5+Exception | 490 | 45.5102 | 51.4286 | 0.4895 | -46.3097 | 65.653 | 29.6919 | 5.8714 | -27.957 |

### 5D_ordered_8v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 78 | 28.2051 | 65.3846 | -1.6266 | -46.3097 | 30.9707 | 33.3333 | 6.0233 | -17.0874 |
| Top3 | 183 | 34.4262 | 57.9235 | -0.2854 | -46.3097 | 50.3643 | 34.6939 | 6.987 | -27.957 |
| Top5 | 274 | 30.292 | 62.7737 | -0.2489 | -46.3097 | 56.9153 | 34.6847 | 6.5399 | -27.957 |
| Exception Leader | 211 | 38.3886 | 51.6588 | 0.9772 | -34.8118 | 65.653 | 21.4815 | 6.909 | -26.8063 |
| Top5+Exception | 485 | 33.8144 | 57.9381 | 0.4895 | -46.3097 | 65.653 | 29.6919 | 6.7005 | -27.957 |

### 5D_ordered_10v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 78 | 26.9231 | 65.3846 | -1.6266 | -46.3097 | 30.9707 | 33.3333 | 6.1601 | -17.0874 |
| Top3 | 183 | 31.1475 | 59.5628 | -0.2854 | -46.3097 | 50.3643 | 34.6939 | 7.1781 | -27.957 |
| Top5 | 274 | 27.3723 | 63.8686 | -0.2489 | -46.3097 | 56.9153 | 34.6847 | 6.8427 | -27.957 |
| Exception Leader | 210 | 31.4286 | 54.2857 | 0.9772 | -34.8118 | 65.653 | 21.4815 | 7.3861 | -26.8063 |
| Top5+Exception | 484 | 29.1322 | 59.7107 | 0.4895 | -46.3097 | 65.653 | 29.6919 | 7.0785 | -27.957 |

### 5D_ordered_12v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 77 | 20.7792 | 68.8312 | -1.6266 | -46.3097 | 30.9707 | 33.3333 | 6.4052 | -17.0874 |
| Top3 | 182 | 25.2747 | 63.1868 | -0.2854 | -46.3097 | 50.3643 | 34.6939 | 7.4292 | -27.957 |
| Top5 | 273 | 22.3443 | 66.6667 | -0.2489 | -46.3097 | 56.9153 | 34.6847 | 7.2497 | -27.957 |
| Exception Leader | 208 | 25.4808 | 56.7308 | 0.9772 | -34.8118 | 65.653 | 21.4815 | 7.4699 | -26.8063 |
| Top5+Exception | 481 | 23.7006 | 62.3701 | 0.4895 | -46.3097 | 65.653 | 29.6919 | 7.3449 | -27.957 |


## Curated Ordered Candidates

- `kosdaq_low_model_1d_rebound_5v5` `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'selection_lane=1d', 'prob_clean<=31.8']: all n=22 win=77.2727%, train n=20 win=80.0%, test n=2 win=50.0%, test_stop=50.0%, test_med_close=-12.9114%, test_min_close=-12.9114%, test_loss5=100.0%, fold_win=80.0%, min_fold=76.4706%, avg_mfe=9.4125%, avg_mae=-2.9842%, min_mae=-12.4594%, same_regime=[market_gate=GREEN train 0/None% test 2/50.0%; trend=UP train 19/78.9474% test 2/50.0%]
- `kosdaq_low_loss_theme_rebound_5v5` `5D_ordered_5v5` ['tech_score<=80', 'theme_day_avg_decision_score<=63.0879', 'theme_day_symbol_count>=7', 'trend=UP']: all n=36 win=55.5556%, train n=15 win=80.0%, test n=21 win=38.0952%, test_stop=61.9048%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=55.5555%, min_fold=38.0952%, avg_mfe=6.6742%, avg_mae=-5.1418%, min_mae=-13.7153%, same_regime=[market_gate=GREEN train 0/None% test 18/38.8889%; trend=UP train 15/80.0% test 21/38.0952%]

## High-Win Small-N Non-Theme Candidates

- `5D_ordered_5v5` ['whale_score<=78', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'theme_day_avg_decision_score>=65.265']: all n=27 win=85.1852%, train n=13 win=69.2308%, test n=14 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.1852%, min_fold=69.2308%, avg_mfe=12.4907%, avg_mae=-2.8498%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 14/100.0%; trend=UP train 12/75.0% test 14/100.0%]
- `5D_ordered_5v5` ['whale_score<=78', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'theme_day_symbol_count>=17', 'theme_day_strength_rank>=2']: all n=27 win=85.1852%, train n=13 win=69.2308%, test n=14 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=85.1852%, min_fold=69.2308%, avg_mfe=12.4907%, avg_mae=-2.8498%, min_mae=-10.0418%, same_regime=[market_gate=GREEN train 0/None% test 14/100.0%; trend=UP train 12/75.0% test 14/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.39', 'theme_day_avg_alpha_score<=69.5714', 'decision_score>=90', 'theme_day_avg_volume_ratio>=1.05']: all n=20 win=80.0%, train n=11 win=63.6364%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=84.2105%, min_fold=70.0%, avg_mfe=10.2264%, avg_mae=-1.9859%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/55.5556% test 9/100.0%]
- `5D_ordered_5v5` ['theme_day_avg_alpha_score<=69.5714', 'theme_day_avg_expected_return_1d_pct>=0.0475', 'decision_score>=95.375', 'theme_day_avg_volume_ratio>=1.05']: all n=20 win=80.0%, train n=11 win=63.6364%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=84.2105%, min_fold=70.0%, avg_mfe=9.1409%, avg_mae=-2.0482%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/55.5556% test 9/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8731%, avg_mae=-3.2684%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_symbol_count>=9']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8731%, avg_mae=-3.2684%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8561%, avg_mae=-2.9998%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_score>=4.9642']: all n=18 win=83.3333%, train n=10 win=70.0%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.8561%, avg_mae=-2.9998%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_rank<=4']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.0408%, avg_mae=-3.2465%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_strength_pct>=77.7778']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.0408%, avg_mae=-3.2465%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_rank<=4']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.0408%, avg_mae=-3.2465%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_strength_pct>=77.7778']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=13.0408%, avg_mae=-3.2465%, min_mae=-7.8454%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 4/75.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'kr_universe_role=EXPLOSIVE_LEADER', 'conviction_score<=65.03', 'theme_day_avg_alpha_score<=73.3333']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=11.7046%, avg_mae=-3.0339%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 5/60.0% test 8/100.0%]
- `5D_ordered_8v5` ['theme_day_avg_expected_return_1d_pct>=0.0475', 'explosive_leader_flag=1', 'conviction_score<=65.03', 'theme_day_avg_alpha_score<=73.3333']: all n=19 win=78.9474%, train n=11 win=63.6364%, test n=8 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=70.0%, avg_mfe=11.7046%, avg_mae=-3.0339%, min_mae=-10.1971%, same_regime=[market_gate=GREEN train 0/None% test 8/100.0%; trend=UP train 5/60.0% test 8/100.0%]
- `5D_ordered_5v5` ['expected_return_1d_pct>=0.39', 'theme_day_avg_alpha_score<=69.5714', 'decision_score>=90', 'theme_day_strength_pct<=87.5']: all n=19 win=78.9474%, train n=10 win=60.0%, test n=9 win=100.0%, test_stop=0.0%, test_med_close=None%, test_min_close=None%, test_loss5=None%, fold_win=83.3333%, min_fold=66.6667%, avg_mfe=10.837%, avg_mae=-2.0581%, min_mae=-10.8604%, same_regime=[market_gate=GREEN train 0/None% test 9/100.0%; trend=UP train 9/55.5556% test 9/100.0%]

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
