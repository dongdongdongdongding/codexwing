# KOSDAQ 5D +5% Touch Slice Search

- generated_at: `2026-05-12T17:51:04.838841+00:00`
- rows_loaded: `2204`
- rows_labeled: `1952`
- label: `next 5 trading days High >= entry_reference_price * 1.05`
- include_signal_day: `False`
- target: `touch_5pct_5d >= 70%, avg_mfe_5d_high >= +5%`

## Target-Passing Slices

- feature_origin=outcome_sync_partial AND priority_rank<=3: n=70, touch5=85.714%, avg_mfe=18.7313%, close5_avg=2.3594
- tier=⭐T2 AND alpha_score>=90: n=45, touch5=84.444%, avg_mfe=16.8671%, close5_avg=8.302
- feature_origin=outcome_sync_partial AND priority_rank<=2: n=55, touch5=83.636%, avg_mfe=19.8152%, close5_avg=1.8995
- decision_bucket=ignored AND position=🚀 상승 (Rising): n=36, touch5=83.333%, avg_mfe=14.4896%, close5_avg=5.1825
- decision_bucket=ignored AND tier=🏆T1: n=35, touch5=82.857%, avg_mfe=17.0618%, close5_avg=7.5519
- tier=⭐T2 AND expected_edge_score>=8: n=39, touch5=82.051%, avg_mfe=17.766%, close5_avg=8.8766
- priority_rank<=3 AND whale_score>=70: n=39, touch5=82.051%, avg_mfe=11.8496%, close5_avg=4.1314
- phase25_variant=phase25_kr_swing_xgboost AND alpha_score>=95: n=43, touch5=81.395%, avg_mfe=14.3924%, close5_avg=5.5494
- alpha_score>=90 AND volume_ratio>=2: n=31, touch5=80.645%, avg_mfe=21.8008%, close5_avg=13.7053
- decision_bucket=picked AND priority_rank<=10: n=36, touch5=80.556%, avg_mfe=11.9552%, close5_avg=2.0989
- kr_universe_role=EXPLOSIVE_LEADER AND phase25_variant=phase25_kr_swing_xgboost: n=41, touch5=80.488%, avg_mfe=13.7524%, close5_avg=4.5215
- decision_bucket=ignored AND ml_prob>=50: n=41, touch5=80.488%, avg_mfe=12.1982%, close5_avg=3.5165
- feature_origin=scanner_partial_legacy AND decision_score>=95: n=61, touch5=80.328%, avg_mfe=14.1911%, close5_avg=6.446
- decision_bucket=ignored AND feature_origin=outcome_sync_partial: n=71, touch5=80.282%, avg_mfe=14.4651%, close5_avg=5.279
- whale_score>=70 AND volume_ratio>=2: n=30, touch5=80.0%, avg_mfe=21.3068%, close5_avg=8.7244
- kr_universe_role=EXPLOSIVE_LEADER AND whale_score>=80: n=30, touch5=80.0%, avg_mfe=11.8306%, close5_avg=1.4494
- priority_rank<=2 AND whale_score>=70: n=30, touch5=80.0%, avg_mfe=11.7218%, close5_avg=3.7985
- kr_universe_role=EXPLOSIVE_LEADER AND alpha_score>=95: n=84, touch5=79.762%, avg_mfe=15.4509%, close5_avg=5.2321
- decision_bucket=ignored AND whale_score>=40: n=64, touch5=79.688%, avg_mfe=14.9744%, close5_avg=5.2774
- decision_bucket=ignored AND whale_score>=60: n=59, touch5=79.661%, avg_mfe=15.0322%, close5_avg=5.453

## Best By Touch

- feature_origin=outcome_sync_partial AND priority_rank<=3: n=70, touch5=85.714%, avg_mfe=18.7313%, close5_avg=2.3594
- tier=⭐T2 AND alpha_score>=90: n=45, touch5=84.444%, avg_mfe=16.8671%, close5_avg=8.302
- feature_origin=outcome_sync_partial AND priority_rank<=2: n=55, touch5=83.636%, avg_mfe=19.8152%, close5_avg=1.8995
- decision_bucket=ignored AND position=🚀 상승 (Rising): n=36, touch5=83.333%, avg_mfe=14.4896%, close5_avg=5.1825
- decision_bucket=ignored AND tier=🏆T1: n=35, touch5=82.857%, avg_mfe=17.0618%, close5_avg=7.5519
- tier=⭐T2 AND expected_edge_score>=8: n=39, touch5=82.051%, avg_mfe=17.766%, close5_avg=8.8766
- priority_rank<=3 AND whale_score>=70: n=39, touch5=82.051%, avg_mfe=11.8496%, close5_avg=4.1314
- phase25_variant=phase25_kr_swing_xgboost AND alpha_score>=95: n=43, touch5=81.395%, avg_mfe=14.3924%, close5_avg=5.5494
- alpha_score>=90 AND volume_ratio>=2: n=31, touch5=80.645%, avg_mfe=21.8008%, close5_avg=13.7053
- decision_bucket=picked AND priority_rank<=10: n=36, touch5=80.556%, avg_mfe=11.9552%, close5_avg=2.0989
- kr_universe_role=EXPLOSIVE_LEADER AND phase25_variant=phase25_kr_swing_xgboost: n=41, touch5=80.488%, avg_mfe=13.7524%, close5_avg=4.5215
- decision_bucket=ignored AND ml_prob>=50: n=41, touch5=80.488%, avg_mfe=12.1982%, close5_avg=3.5165
- feature_origin=scanner_partial_legacy AND decision_score>=95: n=61, touch5=80.328%, avg_mfe=14.1911%, close5_avg=6.446
- decision_bucket=ignored AND feature_origin=outcome_sync_partial: n=71, touch5=80.282%, avg_mfe=14.4651%, close5_avg=5.279
- whale_score>=70 AND volume_ratio>=2: n=30, touch5=80.0%, avg_mfe=21.3068%, close5_avg=8.7244
- kr_universe_role=EXPLOSIVE_LEADER AND whale_score>=80: n=30, touch5=80.0%, avg_mfe=11.8306%, close5_avg=1.4494
- priority_rank<=2 AND whale_score>=70: n=30, touch5=80.0%, avg_mfe=11.7218%, close5_avg=3.7985
- kr_universe_role=EXPLOSIVE_LEADER AND alpha_score>=95: n=84, touch5=79.762%, avg_mfe=15.4509%, close5_avg=5.2321
- decision_bucket=ignored AND whale_score>=40: n=64, touch5=79.688%, avg_mfe=14.9744%, close5_avg=5.2774
- decision_bucket=ignored AND whale_score>=60: n=59, touch5=79.661%, avg_mfe=15.0322%, close5_avg=5.453