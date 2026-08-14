# Ordered Shadow Watch

- generated_at: `2026-08-14T00:52:30.279739+00:00`
- production_scanner_changed: `False`

## KOSPI

- split_day: `2026-06-21`
- cache: loaded=10887 fresh=10761 missing_labeled=27 ready=7119

| Rule | Status | All | Train | Test | Conditions |
|---|---|---:|---:|---:|---|
| ordered_prob_band_top3_10v5 | watch_small_sample | n=24 win=70.8333% stop=20.8333% | n=24 win=70.8333% | n=0 win=None% stop=None% loss5=None% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0 |
| ordered_prob_band_top3_ml_cap_10v5 | watch_small_sample | n=18 win=77.7778% stop=11.1111% | n=18 win=77.7778% | n=0 win=None% stop=None% loss5=None% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0; ml_prob<=38.6 |
| ordered_prob_band_top3_core_route_10v5 | watch_small_sample | n=14 win=78.5714% stop=14.2857% | n=14 win=78.5714% | n=0 win=None% stop=None% loss5=None% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0; theme_routing_path=core_only |
| ordered_prob_band_top3_edge_cap_10v5 | watch_small_sample | n=15 win=80.0% stop=13.3333% | n=15 win=80.0% | n=0 win=None% stop=None% loss5=None% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0; expected_return_3d_pct<=0.458 |
| ordered_prob_band_top3_phase_low_10v5 | watch_small_sample | n=12 win=75.0% stop=16.6667% | n=12 win=75.0% | n=0 win=None% stop=None% loss5=None% | cohort=Top3; prob_clean=[28.1,31.8]; decision_score>=100; explosive_leader_flag=0; phase25_prob<=40.6 |
| kospi_refreshed_theme_core_prob_alpha_10v5 | watch_small_sample | n=28 win=64.2857% stop=21.4286% | n=28 win=64.2857% | n=0 win=None% stop=None% loss5=None% | prob_clean>=35.5; theme_day_avg_alpha_score<=81; kr_universe_role=CORE_TREND; alpha_score>=67 |
| kospi_stable_top1_expected_edge_8v4 | watch_small_sample | n=36 win=44.4444% stop=47.2222% | n=36 win=44.4444% | n=0 win=None% stop=None% loss5=None% | cohort=Top1; expected_edge_score>=2.23 |
| kospi_stable_top1_expected_return_8v4 | watch_small_sample | n=35 win=42.8571% stop=48.5714% | n=35 win=42.8571% | n=0 win=None% stop=None% loss5=None% | cohort=Top1; expected_return_1d_pct>=0.18 |
| kospi_dynamic_phase_theme_watch_10v5 | watch_small_sample | n=27 win=62.963% stop=22.2222% | n=27 win=62.963% | n=0 win=None% stop=None% loss5=None% | cohort=Top3; phase25_prob<=38.3; theme_day_strength_rank<=8; theme_day_strength_score>=2.0908 |

## KOSDAQ

- split_day: `2026-06-22`
- cache: loaded=13000 fresh=12856 missing_labeled=16 ready=9761

| Rule | Status | All | Train | Test | Conditions |
|---|---|---:|---:|---:|---|
| kosdaq_validated_touch_exception_5v5 | watch_small_sample | n=7 win=28.5714% stop=71.4286% | n=7 win=28.5714% | n=0 win=None% stop=None% loss5=None% | cohort=Top5; trend=UP; alpha_score>=90; volume_ratio>=2 |
| kosdaq_low_loss_theme_rebound_5v5 | watch_small_sample | n=61 win=32.7869% stop=67.2131% | n=61 win=32.7869% | n=0 win=None% stop=None% loss5=None% | tech_score<=80; theme_day_avg_decision_score<=63.0879; theme_day_symbol_count>=7; trend=UP |
| kosdaq_low_model_1d_rebound_5v5 | watch_small_sample | n=22 win=77.2727% stop=22.7273% | n=22 win=77.2727% | n=0 win=None% stop=None% loss5=None% | ml_prob=[10,20.84]; volume_ratio<=1.23; selection_lane=1d; prob_clean<=31.8 |
| kosdaq_dynamic_theme_tech_watch_5v5 | watch_small_sample | n=31 win=64.5161% stop=35.4839% | n=31 win=64.5161% | n=0 win=None% stop=None% loss5=None% | theme_day_avg_volume_ratio>=0.8633; theme_day_avg_expected_return_1d_pct>=0.1514; tech_score<=65; theme_day_avg_alpha_score<=69.5321 |

## Notes

- This report only evaluates pre-registered ordered shadow/watch rules.
- It refreshes ordered label caches from the current archive before evaluating metrics.
- review_candidate is not automatic promotion; manual release gates still apply.
