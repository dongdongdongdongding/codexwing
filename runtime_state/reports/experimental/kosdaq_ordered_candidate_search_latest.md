# KOSDAQ Ordered Candidate Search

- market: `KOSDAQ`
- generated_at: `2026-05-16T16:10:07.829935+00:00`
- rows_labeled: `6272`
- ordered_label_ready_rows: `5838`
- unique_ticker_dates: `1568`
- split_day: `2026-04-22`

## Baseline

- `5D_ordered_5v5`: all n=1480 win=41.9595%, test n=806 win=35.1117%, test_stop=63.5236%
- `5D_ordered_8v5`: all n=1460 win=31.9178%, test n=786 win=27.0992%, test_stop=69.8473%
- `5D_ordered_10v5`: all n=1451 win=26.6023%, test n=777 win=21.6216%, test_stop=73.7452%
- `5D_ordered_12v5`: all n=1447 win=22.322%, test n=773 win=18.37%, test_stop=75.5498%

## Practical Watch 75pct Non-Theme

- `5D_ordered_8v5` ['ml_prob>=50', 'volume_ratio>=0.901', 'expected_edge_score<=2.92', 'alpha_score>=77']: all n=35 win=42.8571%, train n=26 win=26.9231%, test n=9 win=88.8889%, test_stop=11.1111%, test_med_close=13.7392%, test_min_close=-8.881%, test_loss5=25.0%, fold_win=41.1765%, min_fold=26.9231%, avg_mfe=8.4753%, avg_mae=-4.0794%, min_mae=-10.1971%
- `5D_ordered_8v5` ['ml_prob>=50', 'volume_ratio>=0.901', 'expected_edge_score<=2.92', 'alpha_score>=83']: all n=32 win=43.75%, train n=24 win=29.1667%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=13.7392%, test_min_close=-8.881%, test_loss5=25.0%, fold_win=43.75%, min_fold=29.1667%, avg_mfe=8.8739%, avg_mae=-4.003%, min_mae=-10.1971%
- `5D_ordered_5v5` ['ml_prob>=50', 'whale_score>=79', 'alpha_score>=77', 'decision_score<=90.5']: all n=21 win=71.4286%, train n=8 win=50.0%, test n=13 win=84.6154%, test_stop=15.3846%, test_med_close=-0.287%, test_min_close=-26.8634%, test_loss5=33.3333%, fold_win=70.0%, min_fold=50.0%, avg_mfe=9.6867%, avg_mae=-4.3322%, min_mae=-15.3727%
- `5D_ordered_8v5` ['ml_prob>=50', 'volume_ratio>=0.825', 'expected_edge_score<=2.92', 'alpha_score>=77']: all n=38 win=44.7368%, train n=26 win=26.9231%, test n=12 win=83.3333%, test_stop=16.6667%, test_med_close=9.7838%, test_min_close=-9.5521%, test_loss5=27.2727%, fold_win=43.2433%, min_fold=26.9231%, avg_mfe=8.6406%, avg_mae=-4.0905%, min_mae=-10.1971%
- `5D_ordered_8v5` ['ml_prob>=50', 'volume_ratio>=0.825', 'expected_edge_score<=2.92', 'alpha_score>=83']: all n=35 win=45.7143%, train n=24 win=29.1667%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=9.7838%, test_min_close=-9.5521%, test_loss5=27.2727%, fold_win=45.7143%, min_fold=29.1667%, avg_mfe=9.0191%, avg_mae=-4.0216%, min_mae=-10.1971%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'decision_score<=90.5']: all n=18 win=72.2222%, train n=8 win=62.5%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=75.0%, min_fold=63.6364%, avg_mfe=9.9538%, avg_mae=-2.2185%, min_mae=-7.888%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=59']: all n=29 win=68.9655%, train n=19 win=63.1579%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=70.3704%, min_fold=66.6667%, avg_mfe=8.3706%, avg_mae=-3.127%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=59']: all n=29 win=68.9655%, train n=19 win=63.1579%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=70.3704%, min_fold=66.6667%, avg_mfe=8.3706%, avg_mae=-3.127%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'decision_score<=90.5']: all n=31 win=64.5161%, train n=21 win=57.1429%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=68.4211%, min_fold=63.6364%, avg_mfe=7.643%, avg_mae=-2.8835%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob>=50', 'whale_score>=79', 'alpha_score>=77', 'decision_score<=97.5']: all n=24 win=66.6667%, train n=10 win=50.0%, test n=14 win=78.5714%, test_stop=21.4286%, test_med_close=-2.4362%, test_min_close=-26.8634%, test_loss5=38.4615%, fold_win=65.2174%, min_fold=50.0%, avg_mfe=8.7112%, avg_mae=-4.5334%, min_mae=-15.3727%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=69.005']: all n=25 win=64.0%, train n=16 win=56.25%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=73.3333%, min_fold=71.4286%, avg_mfe=7.9239%, avg_mae=-2.6363%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=69.005', 'prob_clean<=35.225']: all n=25 win=64.0%, train n=16 win=56.25%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=73.3333%, min_fold=71.4286%, avg_mfe=7.9239%, avg_mae=-2.6363%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=69.005', 'alpha_score<=89.1']: all n=24 win=62.5%, train n=15 win=53.3333%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=7.9795%, avg_mae=-2.5814%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=68']: all n=24 win=70.8333%, train n=15 win=66.6667%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=7.6521%, test_min_close=-3.8413%, test_loss5=0.0%, fold_win=69.5652%, min_fold=63.6364%, avg_mfe=8.6836%, avg_mae=-3.4056%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=68']: all n=24 win=70.8333%, train n=15 win=66.6667%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=7.6521%, test_min_close=-3.8413%, test_loss5=0.0%, fold_win=69.5652%, min_fold=63.6364%, avg_mfe=8.6836%, avg_mae=-3.4056%, min_mae=-12.4594%
- `5D_ordered_5v5` ['whale_score>=73', 'ml_prob>=50', 'alpha_score>=77', 'decision_score<=90.5']: all n=32 win=68.75%, train n=14 win=57.1429%, test n=18 win=77.7778%, test_stop=22.2222%, test_med_close=1.6556%, test_min_close=-26.8634%, test_loss5=35.2941%, fold_win=67.742%, min_fold=57.1429%, avg_mfe=8.6672%, avg_mae=-4.2443%, min_mae=-15.3727%
- `5D_ordered_5v5` ['ml_prob>=50', 'whale_score>=85', 'decision_score<=90.5', 'alpha_score>=59']: all n=21 win=61.9048%, train n=8 win=37.5%, test n=13 win=76.9231%, test_stop=23.0769%, test_med_close=-4.8766%, test_min_close=-26.8634%, test_loss5=50.0%, fold_win=61.9048%, min_fold=37.5%, avg_mfe=7.222%, avg_mae=-4.8347%, min_mae=-19.457%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59', 'decision_score<=97.5']: all n=22 win=81.8182%, train n=14 win=85.7143%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=84.2105%, min_fold=70.0%, avg_mfe=8.4091%, avg_mae=-2.8353%, min_mae=-11.354%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59', 'prob_clean<=35.225']: all n=24 win=75.0%, train n=16 win=75.0%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=75.0%, min_fold=70.0%, avg_mfe=7.915%, avg_mae=-3.1958%, min_mae=-12.4594%
- `5D_ordered_5v5` ['alpha_score<=68', 'ml_prob=[19.285,22.475]', 'prob_clean=[25.535,40.505]']: all n=20 win=65.0%, train n=12 win=58.3333%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=-2.678%, test_min_close=-6.7388%, test_loss5=14.2857%, fold_win=75.0%, min_fold=71.4286%, avg_mfe=7.7873%, avg_mae=-2.6421%, min_mae=-8.3439%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59', 'prob_clean<=31.8']: all n=22 win=72.7273%, train n=14 win=71.4286%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=72.7273%, min_fold=70.0%, avg_mfe=8.1425%, avg_mae=-3.3065%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59']: all n=28 win=71.4286%, train n=20 win=70.0%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=72.0%, min_fold=70.0%, avg_mfe=7.6814%, avg_mae=-3.5951%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=64.775']: all n=22 win=63.6364%, train n=14 win=57.1429%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=7.4491%, avg_mae=-2.7872%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=64.775', 'alpha_score<=89.1']: all n=22 win=63.6364%, train n=14 win=57.1429%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=7.4491%, avg_mae=-2.7872%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=64.775', 'prob_clean<=35.225']: all n=22 win=63.6364%, train n=14 win=57.1429%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=7.4491%, avg_mae=-2.7872%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.05', 'decision_score<=90.5', 'alpha_score>=59']: all n=16 win=75.0%, train n=8 win=75.0%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=3.1178%, test_min_close=-8.3012%, test_loss5=14.2857%, fold_win=71.4286%, min_fold=60.0%, avg_mfe=11.5053%, avg_mae=-1.9757%, min_mae=-5.7737%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.05', 'decision_score<=90.5']: all n=17 win=70.5882%, train n=9 win=66.6667%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=3.1178%, test_min_close=-8.3012%, test_loss5=14.2857%, fold_win=71.4286%, min_fold=60.0%, avg_mfe=10.9644%, avg_mae=-2.1798%, min_mae=-5.7737%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.05', 'decision_score<=90.5', 'alpha_score>=59']: all n=17 win=70.5882%, train n=9 win=66.6667%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=3.1178%, test_min_close=-8.3012%, test_loss5=14.2857%, fold_win=71.4286%, min_fold=60.0%, avg_mfe=10.9239%, avg_mae=-2.5274%, min_mae=-11.354%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'decision_score<=90.5', 'prob_clean<=31.8']: all n=27 win=66.6667%, train n=19 win=63.1579%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=70.5883%, min_fold=66.6667%, avg_mfe=6.845%, avg_mae=-3.0002%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'decision_score<=90.5', 'prob_clean<=35.225']: all n=27 win=66.6667%, train n=19 win=63.1579%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=70.5883%, min_fold=66.6667%, avg_mfe=6.845%, avg_mae=-3.0002%, min_mae=-9.5495%

## Practical Candidates 75pct Non-Theme

- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'decision_score<=90.5']: all n=18 win=72.2222%, train n=8 win=62.5%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=75.0%, min_fold=63.6364%, avg_mfe=9.9538%, avg_mae=-2.2185%, min_mae=-7.888%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=59']: all n=29 win=68.9655%, train n=19 win=63.1579%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=70.3704%, min_fold=66.6667%, avg_mfe=8.3706%, avg_mae=-3.127%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=59']: all n=29 win=68.9655%, train n=19 win=63.1579%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=70.3704%, min_fold=66.6667%, avg_mfe=8.3706%, avg_mae=-3.127%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'decision_score<=90.5']: all n=31 win=64.5161%, train n=21 win=57.1429%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=68.4211%, min_fold=63.6364%, avg_mfe=7.643%, avg_mae=-2.8835%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=69.005']: all n=25 win=64.0%, train n=16 win=56.25%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=73.3333%, min_fold=71.4286%, avg_mfe=7.9239%, avg_mae=-2.6363%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=69.005', 'prob_clean<=35.225']: all n=25 win=64.0%, train n=16 win=56.25%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=73.3333%, min_fold=71.4286%, avg_mfe=7.9239%, avg_mae=-2.6363%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=68']: all n=24 win=70.8333%, train n=15 win=66.6667%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=7.6521%, test_min_close=-3.8413%, test_loss5=0.0%, fold_win=69.5652%, min_fold=63.6364%, avg_mfe=8.6836%, avg_mae=-3.4056%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=68']: all n=24 win=70.8333%, train n=15 win=66.6667%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=7.6521%, test_min_close=-3.8413%, test_loss5=0.0%, fold_win=69.5652%, min_fold=63.6364%, avg_mfe=8.6836%, avg_mae=-3.4056%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59', 'decision_score<=97.5']: all n=22 win=81.8182%, train n=14 win=85.7143%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=84.2105%, min_fold=70.0%, avg_mfe=8.4091%, avg_mae=-2.8353%, min_mae=-11.354%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59', 'prob_clean<=35.225']: all n=24 win=75.0%, train n=16 win=75.0%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=75.0%, min_fold=70.0%, avg_mfe=7.915%, avg_mae=-3.1958%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59', 'prob_clean<=31.8']: all n=22 win=72.7273%, train n=14 win=71.4286%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=72.7273%, min_fold=70.0%, avg_mfe=8.1425%, avg_mae=-3.3065%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59']: all n=28 win=71.4286%, train n=20 win=70.0%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=72.0%, min_fold=70.0%, avg_mfe=7.6814%, avg_mae=-3.5951%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=64.775']: all n=22 win=63.6364%, train n=14 win=57.1429%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=7.4491%, avg_mae=-2.7872%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=64.775', 'alpha_score<=89.1']: all n=22 win=63.6364%, train n=14 win=57.1429%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=7.4491%, avg_mae=-2.7872%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=64.775', 'prob_clean<=35.225']: all n=22 win=63.6364%, train n=14 win=57.1429%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=7.4491%, avg_mae=-2.7872%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'decision_score<=90.5', 'prob_clean<=31.8']: all n=27 win=66.6667%, train n=19 win=63.1579%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=70.5883%, min_fold=66.6667%, avg_mfe=6.845%, avg_mae=-3.0002%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'decision_score<=90.5', 'prob_clean<=35.225']: all n=27 win=66.6667%, train n=19 win=63.1579%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=70.5883%, min_fold=66.6667%, avg_mfe=6.845%, avg_mae=-3.0002%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'decision_score<=90.5']: all n=29 win=65.5172%, train n=21 win=61.9048%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=70.5883%, min_fold=66.6667%, avg_mfe=6.6054%, avg_mae=-3.3109%, min_mae=-11.354%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'decision_score<=90.5', 'alpha_score<=89.1']: all n=28 win=64.2857%, train n=20 win=60.0%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=68.75%, min_fold=66.6667%, avg_mfe=6.606%, avg_mae=-3.2879%, min_mae=-11.354%

## Strong Practical 80pct Non-Theme

- none

## Recent-Regime 75pct Non-Theme Diagnostics

- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=69.005', 'alpha_score<=89.1']: all n=24 win=62.5%, train n=15 win=53.3333%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=4.2194%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=71.4286%, min_fold=66.6667%, avg_mfe=7.9795%, avg_mae=-2.5814%, min_mae=-9.5495%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'decision_score<=69.005', 'alpha_score<=83']: all n=23 win=60.8696%, train n=15 win=53.3333%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=3.1178%, test_min_close=-8.3012%, test_loss5=14.2857%, fold_win=69.2308%, min_fold=66.6667%, avg_mfe=7.9807%, avg_mae=-2.5208%, min_mae=-9.5495%

## Promotion-Ready Non-Theme Candidates

- none

## Release-Like Non-Theme Candidates

- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=68']: all n=24 win=70.8333%, train n=15 win=66.6667%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=7.6521%, test_min_close=-3.8413%, test_loss5=0.0%, fold_win=69.5652%, min_fold=63.6364%, avg_mfe=8.6836%, avg_mae=-3.4056%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=68']: all n=24 win=70.8333%, train n=15 win=66.6667%, test n=9 win=77.7778%, test_stop=22.2222%, test_med_close=7.6521%, test_min_close=-3.8413%, test_loss5=0.0%, fold_win=69.5652%, min_fold=63.6364%, avg_mfe=8.6836%, avg_mae=-3.4056%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59', 'decision_score<=97.5']: all n=22 win=81.8182%, train n=14 win=85.7143%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=84.2105%, min_fold=70.0%, avg_mfe=8.4091%, avg_mae=-2.8353%, min_mae=-11.354%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59', 'prob_clean<=35.225']: all n=24 win=75.0%, train n=16 win=75.0%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=75.0%, min_fold=70.0%, avg_mfe=7.915%, avg_mae=-3.1958%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59', 'prob_clean<=31.8']: all n=22 win=72.7273%, train n=14 win=71.4286%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=72.7273%, min_fold=70.0%, avg_mfe=8.1425%, avg_mae=-3.3065%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=19.285', 'volume_ratio<=1.23', 'alpha_score>=59']: all n=28 win=71.4286%, train n=20 win=70.0%, test n=8 win=75.0%, test_stop=25.0%, test_med_close=7.6521%, test_min_close=-8.3012%, test_loss5=12.5%, fold_win=72.0%, min_fold=70.0%, avg_mfe=7.6814%, avg_mae=-3.5951%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'decision_score<=97.5']: all n=25 win=76.0%, train n=14 win=78.5714%, test n=11 win=72.7273%, test_stop=27.2727%, test_med_close=4.2401%, test_min_close=-8.3012%, test_loss5=10.0%, fold_win=78.2609%, min_fold=64.2857%, avg_mfe=9.4663%, avg_mae=-2.4019%, min_mae=-7.888%
- `5D_ordered_5v5` ['prob_clean=[28.1,31.8]', 'expected_edge_score>=2.92']: all n=20 win=70.0%, train n=9 win=66.6667%, test n=11 win=72.7273%, test_stop=27.2727%, test_med_close=0.5682%, test_min_close=-33.2955%, test_loss5=45.4545%, fold_win=70.0%, min_fold=70.0%, avg_mfe=7.9148%, avg_mae=-3.0521%, min_mae=-15.3727%
- `5D_ordered_5v5` ['prob_clean=[28.1,31.8]', 'expected_edge_score>=2.92', 'alpha_score>=59']: all n=20 win=70.0%, train n=9 win=66.6667%, test n=11 win=72.7273%, test_stop=27.2727%, test_med_close=0.5682%, test_min_close=-33.2955%, test_loss5=45.4545%, fold_win=70.0%, min_fold=70.0%, avg_mfe=7.9148%, avg_mae=-3.0521%, min_mae=-15.3727%

## Current Cohort Baseline

### 5D_ordered_5v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 61 | 47.541 | 47.541 | -0.9342 | -23.3281 | 30.9707 | 26.7857 | 5.5914 | -17.0874 |
| Top3 | 151 | 50.3311 | 45.0331 | 0.8442 | -33.2955 | 50.3643 | 28.0303 | 6.8051 | -27.957 |
| Top5 | 227 | 45.815 | 50.6608 | 1.5182 | -33.2955 | 56.9153 | 27.7778 | 6.2821 | -27.957 |
| Exception Leader | 141 | 56.0284 | 39.0071 | 3.0733 | -34.8118 | 65.653 | 13.4454 | 5.9367 | -19.2557 |
| Top5+Exception | 368 | 49.7283 | 46.1957 | 1.8622 | -34.8118 | 65.653 | 22.3975 | 6.1498 | -27.957 |

### 5D_ordered_8v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 61 | 27.8689 | 62.2951 | -0.9342 | -23.3281 | 30.9707 | 26.7857 | 6.3914 | -17.0874 |
| Top3 | 151 | 36.4238 | 53.6424 | 0.8442 | -33.2955 | 50.3643 | 28.0303 | 7.5135 | -27.957 |
| Top5 | 227 | 32.1586 | 59.0308 | 1.5182 | -33.2955 | 56.9153 | 27.7778 | 6.9808 | -27.957 |
| Exception Leader | 139 | 42.446 | 43.1655 | 3.0733 | -34.8118 | 65.653 | 13.4454 | 7.2043 | -26.8063 |
| Top5+Exception | 366 | 36.0656 | 53.0055 | 1.8622 | -34.8118 | 65.653 | 22.3975 | 7.0657 | -27.957 |

### 5D_ordered_10v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 61 | 26.2295 | 62.2951 | -0.9342 | -23.3281 | 30.9707 | 26.7857 | 6.5665 | -17.0874 |
| Top3 | 151 | 32.4503 | 55.6291 | 0.8442 | -33.2955 | 50.3643 | 28.0303 | 7.745 | -27.957 |
| Top5 | 227 | 28.6344 | 60.3524 | 1.5182 | -33.2955 | 56.9153 | 27.7778 | 7.3464 | -27.957 |
| Exception Leader | 137 | 34.3066 | 44.5255 | 3.0733 | -34.8118 | 65.653 | 13.4454 | 7.8161 | -26.8063 |
| Top5+Exception | 364 | 30.7692 | 54.3956 | 1.8622 | -34.8118 | 65.653 | 22.3975 | 7.5232 | -27.957 |

### 5D_ordered_12v5
| cohort | n | win | stop | med_close5 | min_close5 | max_close5 | close_loss5 | avg_mfe | min_mae |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 | 61 | 21.3115 | 63.9344 | -0.9342 | -23.3281 | 30.9707 | 26.7857 | 6.9549 | -17.0874 |
| Top3 | 151 | 26.4901 | 58.9404 | 0.8442 | -33.2955 | 50.3643 | 28.0303 | 8.073 | -27.957 |
| Top5 | 227 | 23.348 | 62.9956 | 1.5182 | -33.2955 | 56.9153 | 27.7778 | 7.8099 | -27.957 |
| Exception Leader | 137 | 27.0073 | 46.7153 | 3.0733 | -34.8118 | 65.653 | 13.4454 | 7.968 | -26.8063 |
| Top5+Exception | 364 | 24.7253 | 56.8681 | 1.8622 | -34.8118 | 65.653 | 22.3975 | 7.8694 | -27.957 |


## Curated Ordered Candidates

- none

## High-Win Small-N Non-Theme Candidates

- `5D_ordered_8v5` ['ml_prob>=50', 'volume_ratio>=0.901', 'expected_edge_score<=2.92', 'alpha_score>=77']: all n=35 win=42.8571%, train n=26 win=26.9231%, test n=9 win=88.8889%, test_stop=11.1111%, test_med_close=13.7392%, test_min_close=-8.881%, test_loss5=25.0%, fold_win=41.1765%, min_fold=26.9231%, avg_mfe=8.4753%, avg_mae=-4.0794%, min_mae=-10.1971%
- `5D_ordered_8v5` ['ml_prob>=50', 'volume_ratio>=0.901', 'expected_edge_score<=2.92', 'alpha_score>=83']: all n=32 win=43.75%, train n=24 win=29.1667%, test n=8 win=87.5%, test_stop=12.5%, test_med_close=13.7392%, test_min_close=-8.881%, test_loss5=25.0%, fold_win=43.75%, min_fold=29.1667%, avg_mfe=8.8739%, avg_mae=-4.003%, min_mae=-10.1971%
- `5D_ordered_5v5` ['ml_prob>=50', 'whale_score>=79', 'alpha_score>=77', 'decision_score<=90.5']: all n=21 win=71.4286%, train n=8 win=50.0%, test n=13 win=84.6154%, test_stop=15.3846%, test_med_close=-0.287%, test_min_close=-26.8634%, test_loss5=33.3333%, fold_win=70.0%, min_fold=50.0%, avg_mfe=9.6867%, avg_mae=-4.3322%, min_mae=-15.3727%
- `5D_ordered_8v5` ['ml_prob>=50', 'volume_ratio>=0.825', 'expected_edge_score<=2.92', 'alpha_score>=77']: all n=38 win=44.7368%, train n=26 win=26.9231%, test n=12 win=83.3333%, test_stop=16.6667%, test_med_close=9.7838%, test_min_close=-9.5521%, test_loss5=27.2727%, fold_win=43.2433%, min_fold=26.9231%, avg_mfe=8.6406%, avg_mae=-4.0905%, min_mae=-10.1971%
- `5D_ordered_8v5` ['ml_prob>=50', 'volume_ratio>=0.825', 'expected_edge_score<=2.92', 'alpha_score>=83']: all n=35 win=45.7143%, train n=24 win=29.1667%, test n=11 win=81.8182%, test_stop=18.1818%, test_med_close=9.7838%, test_min_close=-9.5521%, test_loss5=27.2727%, fold_win=45.7143%, min_fold=29.1667%, avg_mfe=9.0191%, avg_mae=-4.0216%, min_mae=-10.1971%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'decision_score<=90.5']: all n=18 win=72.2222%, train n=8 win=62.5%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=75.0%, min_fold=63.6364%, avg_mfe=9.9538%, avg_mae=-2.2185%, min_mae=-7.888%
- `5D_ordered_5v5` ['ml_prob=[10,20.84]', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=59']: all n=29 win=68.9655%, train n=19 win=63.1579%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=70.3704%, min_fold=66.6667%, avg_mfe=8.3706%, avg_mae=-3.127%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'alpha_score>=59']: all n=29 win=68.9655%, train n=19 win=63.1579%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=70.3704%, min_fold=66.6667%, avg_mfe=8.3706%, avg_mae=-3.127%, min_mae=-12.4594%
- `5D_ordered_5v5` ['ml_prob<=20.84', 'volume_ratio<=1.23', 'prob_clean<=31.8', 'decision_score<=90.5']: all n=31 win=64.5161%, train n=21 win=57.1429%, test n=10 win=80.0%, test_stop=20.0%, test_med_close=5.3211%, test_min_close=-8.3012%, test_loss5=11.1111%, fold_win=68.4211%, min_fold=63.6364%, avg_mfe=7.643%, avg_mae=-2.8835%, min_mae=-9.5495%

## Theme-Dependent Diagnostics

- none

## Notes

- Production scanner ranking is unchanged.
- Practical watch starts at ordered test win >=75%.
- Practical candidates require ordered test win >=75%, all win >=60%, train win >=55%, and stop/loss-tail/fold safeguards.
- Recent-regime candidates pass the latest test window but fail the all/train stability floor, so they are not promotion candidates.
- Strong practical candidates use ordered test win >=80%; promotion-ready remains stricter and requires larger samples.
- feature_quality is excluded from searched categorical conditions because it is a data completeness marker, not a trading signal.
- Release-like candidates exclude static primary_theme conditions to avoid hard-coded theme overfit.
- Rows with immature no-touch labels are excluded from win-rate denominators.
- Daily OHLCV same-bar target/stop order is conservative stop-first via the imported labeler.
