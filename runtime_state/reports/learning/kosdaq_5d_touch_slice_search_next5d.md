# KOSDAQ 5D +5% Touch Slice Search

- generated_at: `2026-05-12T12:12:39.026130+00:00`
- rows_loaded: `1947`
- rows_labeled: `1700`
- label: `next 5 trading days High >= entry_reference_price * 1.05`
- include_signal_day: `False`
- target: `touch_5pct_5d >= 70%, avg_mfe_5d_high >= +5%`

## Target-Passing Slices

- tier=⭐T2 AND alpha_score>=90: n=45, touch5=84.444%, avg_mfe=16.8984%, close5_avg=8.2039
- feature_origin=outcome_sync_partial AND priority_rank<=3: n=55, touch5=83.636%, avg_mfe=19.9841%, close5_avg=1.2568
- decision_bucket=ignored AND position=🚀 상승 (Rising): n=35, touch5=82.857%, avg_mfe=14.3412%, close5_avg=4.965
- decision_bucket=ignored AND tier=🏆T1: n=34, touch5=82.353%, avg_mfe=16.9847%, close5_avg=7.4041
- feature_origin=scanner_partial_legacy AND decision_score>=95: n=62, touch5=82.258%, avg_mfe=14.3418%, close5_avg=6.6037
- tier=⭐T2 AND expected_edge_score>=8: n=39, touch5=82.051%, avg_mfe=17.761%, close5_avg=8.7481
- trend=DOWN AND theme_routing_path=core_only: n=72, touch5=81.944%, avg_mfe=17.2214%, close5_avg=10.6612
- feature_origin=outcome_sync_partial AND priority_rank<=2: n=44, touch5=81.818%, avg_mfe=21.4617%, close5_avg=1.6954
- priority_rank<=3 AND whale_score>=70: n=38, touch5=81.579%, avg_mfe=11.8815%, close5_avg=4.3936
- feature_origin=outcome_sync_partial AND kr_universe_role=EXPLOSIVE_LEADER: n=48, touch5=81.25%, avg_mfe=14.3675%, close5_avg=5.7047
- kr_universe_role=EXPLOSIVE_LEADER AND phase25_variant=phase25_kr_swing_xgboost: n=37, touch5=81.081%, avg_mfe=14.4661%, close5_avg=4.2652
- phase25_variant=phase25_kr_swing_xgboost AND alpha_score>=95: n=42, touch5=80.952%, avg_mfe=14.125%, close5_avg=4.9394
- alpha_score>=90 AND volume_ratio>=2: n=31, touch5=80.645%, avg_mfe=21.8008%, close5_avg=13.7053
- decision_bucket=ignored AND ml_prob>=50: n=31, touch5=80.645%, avg_mfe=12.7009%, close5_avg=2.9242
- decision_bucket=ignored AND feature_origin=outcome_sync_partial: n=66, touch5=80.303%, avg_mfe=14.5605%, close5_avg=5.2421
- whale_score>=70 AND volume_ratio>=2: n=30, touch5=80.0%, avg_mfe=21.3068%, close5_avg=8.7244
- phase25_variant=phase25_kr_swing_xgboost AND alpha_score>=90: n=65, touch5=80.0%, avg_mfe=14.0384%, close5_avg=5.2783
- decision_bucket=exception_leader AND trend=UP: n=65, touch5=80.0%, avg_mfe=13.8093%, close5_avg=5.0949
- decision_bucket=ignored AND whale_score>=60: n=59, touch5=79.661%, avg_mfe=15.0322%, close5_avg=5.453
- decision_bucket=ignored AND whale_score>=70: n=49, touch5=79.592%, avg_mfe=15.6036%, close5_avg=4.9251

## Best By Touch

- tier=⭐T2 AND alpha_score>=90: n=45, touch5=84.444%, avg_mfe=16.8984%, close5_avg=8.2039
- feature_origin=outcome_sync_partial AND priority_rank<=3: n=55, touch5=83.636%, avg_mfe=19.9841%, close5_avg=1.2568
- decision_bucket=ignored AND position=🚀 상승 (Rising): n=35, touch5=82.857%, avg_mfe=14.3412%, close5_avg=4.965
- decision_bucket=ignored AND tier=🏆T1: n=34, touch5=82.353%, avg_mfe=16.9847%, close5_avg=7.4041
- feature_origin=scanner_partial_legacy AND decision_score>=95: n=62, touch5=82.258%, avg_mfe=14.3418%, close5_avg=6.6037
- tier=⭐T2 AND expected_edge_score>=8: n=39, touch5=82.051%, avg_mfe=17.761%, close5_avg=8.7481
- trend=DOWN AND theme_routing_path=core_only: n=72, touch5=81.944%, avg_mfe=17.2214%, close5_avg=10.6612
- feature_origin=outcome_sync_partial AND priority_rank<=2: n=44, touch5=81.818%, avg_mfe=21.4617%, close5_avg=1.6954
- priority_rank<=3 AND whale_score>=70: n=38, touch5=81.579%, avg_mfe=11.8815%, close5_avg=4.3936
- feature_origin=outcome_sync_partial AND kr_universe_role=EXPLOSIVE_LEADER: n=48, touch5=81.25%, avg_mfe=14.3675%, close5_avg=5.7047
- kr_universe_role=EXPLOSIVE_LEADER AND phase25_variant=phase25_kr_swing_xgboost: n=37, touch5=81.081%, avg_mfe=14.4661%, close5_avg=4.2652
- phase25_variant=phase25_kr_swing_xgboost AND alpha_score>=95: n=42, touch5=80.952%, avg_mfe=14.125%, close5_avg=4.9394
- alpha_score>=90 AND volume_ratio>=2: n=31, touch5=80.645%, avg_mfe=21.8008%, close5_avg=13.7053
- decision_bucket=ignored AND ml_prob>=50: n=31, touch5=80.645%, avg_mfe=12.7009%, close5_avg=2.9242
- decision_bucket=ignored AND feature_origin=outcome_sync_partial: n=66, touch5=80.303%, avg_mfe=14.5605%, close5_avg=5.2421
- whale_score>=70 AND volume_ratio>=2: n=30, touch5=80.0%, avg_mfe=21.3068%, close5_avg=8.7244
- phase25_variant=phase25_kr_swing_xgboost AND alpha_score>=90: n=65, touch5=80.0%, avg_mfe=14.0384%, close5_avg=5.2783
- decision_bucket=exception_leader AND trend=UP: n=65, touch5=80.0%, avg_mfe=13.8093%, close5_avg=5.0949
- decision_bucket=ignored AND whale_score>=60: n=59, touch5=79.661%, avg_mfe=15.0322%, close5_avg=5.453
- decision_bucket=ignored AND whale_score>=70: n=49, touch5=79.592%, avg_mfe=15.6036%, close5_avg=4.9251