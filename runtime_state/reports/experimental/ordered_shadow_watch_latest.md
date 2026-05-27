# Ordered Shadow Watch

- generated_at: `2026-05-27T05:16:21.132122+00:00`
- production_scanner_changed: `False`

## KOSPI

- split_day: `2026-05-06`
- cache: loaded=6705 fresh=6705 missing_labeled=0 ready=5870

| Rule | Status | All | Train | Test | Conditions |
|---|---|---:|---:|---:|---|
| ordered_prob_band_top3_10v5 | watch_small_sample | n=21 win=66.6667% stop=23.8095% | n=15 win=73.3333% | n=6 win=50.0% stop=50.0% loss5=100.0% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0 |
| ordered_prob_band_top3_ml_cap_10v5 | watch_small_sample | n=16 win=75.0% stop=12.5% | n=13 win=69.2308% | n=3 win=100.0% stop=0.0% loss5=None% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0; ml_prob<=38.6 |
| ordered_prob_band_top3_core_route_10v5 | watch_small_sample | n=13 win=76.9231% stop=15.3846% | n=11 win=72.7273% | n=2 win=100.0% stop=0.0% loss5=None% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0; theme_routing_path=core_only |
| ordered_prob_band_top3_edge_cap_10v5 | watch_small_sample | n=13 win=76.9231% stop=15.3846% | n=10 win=70.0% | n=3 win=100.0% stop=0.0% loss5=None% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0; expected_return_3d_pct<=0.458 |
| ordered_prob_band_top3_phase_low_10v5 | watch_small_sample | n=10 win=80.0% stop=20.0% | n=9 win=77.7778% | n=1 win=100.0% stop=0.0% loss5=None% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0; phase25_prob<=40.6 |
| kospi_refreshed_theme_core_prob_alpha_10v5 | shadow_only | n=26 win=69.2308% stop=15.3846% | n=18 win=66.6667% | n=8 win=75.0% stop=25.0% loss5=0.0% | prob_clean>=35.5; theme_day_avg_alpha_score<=81; kr_universe_role=CORE_TREND; alpha_score>=67 |
| kospi_stable_top1_expected_edge_8v4 | shadow_only | n=30 win=43.3333% stop=46.6667% | n=13 win=76.9231% | n=17 win=17.6471% stop=70.5882% loss5=30.0% | cohort=Top1; expected_edge_score>=2.23 |
| kospi_stable_top1_expected_return_8v4 | shadow_only | n=30 win=43.3333% stop=46.6667% | n=13 win=76.9231% | n=17 win=17.6471% stop=70.5882% loss5=30.0% | cohort=Top1; expected_return_1d_pct>=0.18 |
| kospi_dynamic_phase_theme_watch_10v5 | shadow_only | n=22 win=77.2727% stop=18.1818% | n=14 win=71.4286% | n=8 win=87.5% stop=12.5% loss5=0.0% | cohort=Top3; phase25_prob<=38.3; theme_day_strength_rank<=8; theme_day_strength_score>=2.0908 |

## KOSDAQ

- split_day: `2026-05-05`
- cache: loaded=9260 fresh=9260 missing_labeled=0 ready=8568

| Rule | Status | All | Train | Test | Conditions |
|---|---|---:|---:|---:|---|
| kosdaq_validated_touch_exception_5v5 | watch_small_sample | n=7 win=28.5714% stop=71.4286% | n=3 win=66.6667% | n=4 win=0.0% stop=100.0% loss5=100.0% | cohort=Top5; trend=UP; alpha_score>=90; volume_ratio>=2 |
| kosdaq_low_loss_theme_rebound_5v5 | shadow_only | n=36 win=55.5556% stop=44.4444% | n=15 win=80.0% | n=21 win=38.0952% stop=61.9048% loss5=None% | tech_score<=80; theme_day_avg_decision_score<=63.0879; theme_day_symbol_count>=7; trend=UP |
| kosdaq_low_model_1d_rebound_5v5 | watch_small_sample | n=22 win=77.2727% stop=22.7273% | n=20 win=80.0% | n=2 win=50.0% stop=50.0% loss5=100.0% | ml_prob=[10,20.84]; volume_ratio<=1.23; selection_lane=1d; prob_clean<=31.8 |
| kosdaq_dynamic_theme_tech_watch_5v5 | shadow_only | n=21 win=95.2381% stop=4.7619% | n=8 win=87.5% | n=13 win=100.0% stop=0.0% loss5=None% | theme_day_avg_volume_ratio>=0.8633; theme_day_avg_expected_return_1d_pct>=0.1514; tech_score<=65; theme_day_avg_alpha_score<=69.5321 |

## Notes

- This report only evaluates pre-registered ordered shadow/watch rules.
- It refreshes ordered label caches from the current archive before evaluating metrics.
- review_candidate is not automatic promotion; manual release gates still apply.
