# Loss Exclusion Guard Mining

- generated_at: `2026-08-14T00:56:56.563978+00:00`
- report_version: `loss_exclusion_guard_mining_v1`
- input_rows: `10335`
- quality_scope: `all`
- guard_count: `11202`
- production_candidate_count: `0`
- shadow_candidate_count: `283`
- guard_levels: `{'coverage_fail': 6924, 'diagnostic': 3986, 'shadow_candidate': 283, 'sample_fail': 9}`

## Top Exclusion Guards

| Rank | Level | Market | Scope | Horizon | Terms | Retain | Base Win | Kept Win | ΔWin | Base Avg | Kept Avg | ΔAvg | Kept Min | Bad ↓ | Stop ↓ | Exclude Conditions |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3892 | 52.695 | 66.154 | 13.459 | -0.8029 | 4.4715 | 5.2744 | -28.4733 | 12.612 | 5.399 | conviction_score >= 68.845<br>expected_return_1d_pct >= 0.97 |
| 2 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3713 | 52.695 | 67.742 | 15.047 | -0.8029 | 4.2887 | 5.0916 | -43.5507 | 13.754 | 8.104 | decision == OBSERVE<br>loss_risk_score <= 15.86 |
| 3 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3713 | 52.695 | 67.742 | 15.047 | -0.8029 | 4.2887 | 5.0916 | -43.5507 | 13.754 | 8.104 | decision == OBSERVE<br>loss_risk_score <= 15.86 |
| 4 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 65.574 | 12.879 | -0.8029 | 3.8918 | 4.6947 | -35.4483 | 14.705 | 7.971 | decision == OBSERVE<br>expected_return_1d_pct >= 0.97 |
| 5 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 65.574 | 12.879 | -0.8029 | 3.8918 | 4.6947 | -35.4483 | 14.705 | 7.971 | decision == OBSERVE<br>expected_return_3d_pct >= 1.41 |
| 6 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3653 | 52.695 | 65.574 | 12.879 | -0.8029 | 3.8918 | 4.6947 | -35.4483 | 14.705 | 7.971 | decision == OBSERVE<br>expected_return_1d_pct >= 0.97 |
| 7 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3653 | 52.695 | 65.574 | 12.879 | -0.8029 | 3.8918 | 4.6947 | -35.4483 | 14.705 | 7.971 | decision == OBSERVE<br>expected_return_3d_pct >= 1.41 |
| 8 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3593 | 52.695 | 65.0 | 12.305 | -0.8029 | 3.9257 | 4.7286 | -35.4483 | 14.022 | 7.835 | expected_return_1d_pct >= 0.97<br>market_gate == GREEN |
| 9 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3593 | 52.695 | 65.0 | 12.305 | -0.8029 | 3.9257 | 4.7286 | -35.4483 | 14.022 | 7.835 | expected_return_3d_pct >= 1.41<br>market_gate == GREEN |
| 10 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3593 | 52.695 | 65.0 | 12.305 | -0.8029 | 3.9257 | 4.7286 | -35.4483 | 14.022 | 7.835 | expected_return_1d_pct >= 0.97<br>market_gate == GREEN |
| 11 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3593 | 52.695 | 65.0 | 12.305 | -0.8029 | 3.9257 | 4.7286 | -35.4483 | 14.022 | 7.835 | expected_return_3d_pct >= 1.41<br>market_gate == GREEN |
| 12 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3892 | 52.695 | 66.154 | 13.459 | -0.8029 | 4.1438 | 4.9467 | -43.5507 | 12.612 | 8.476 | loss_risk_score <= 15.86<br>market_gate == GREEN |
| 13 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3892 | 52.695 | 66.154 | 13.459 | -0.8029 | 4.1438 | 4.9467 | -43.5507 | 12.612 | 8.476 | loss_risk_score <= 15.86<br>market_gate == GREEN |
| 14 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3713 | 52.695 | 64.516 | 11.821 | -0.8029 | 3.817 | 4.6199 | -35.4483 | 13.754 | 8.104 | decision == OBSERVE<br>expected_edge_score >= 10.785 |
| 15 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3713 | 52.695 | 64.516 | 11.821 | -0.8029 | 3.817 | 4.6199 | -35.4483 | 13.754 | 8.104 | decision == OBSERVE<br>expected_edge_score >= 10.785 |
| 16 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.4611 | 52.695 | 64.935 | 12.24 | -0.8029 | 3.6743 | 4.4772 | -43.5507 | 12.832 | 9.674 | decision_score >= 90.3<br>decision == OBSERVE |
| 17 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 63.934 | 11.239 | -0.8029 | 3.8492 | 4.6521 | -35.4483 | 13.066 | 7.971 | expected_edge_score >= 10.785<br>market_gate == GREEN |
| 18 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.3653 | 52.695 | 63.934 | 11.239 | -0.8029 | 3.8492 | 4.6521 | -35.4483 | 13.066 | 7.971 | expected_edge_score >= 10.785<br>market_gate == GREEN |
| 19 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.479 | 52.695 | 63.75 | 11.055 | -0.8029 | 3.5796 | 4.3825 | -43.5507 | 11.939 | 9.918 | decision_score >= 90.3<br>market_gate == GREEN |
| 20 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3654 | 49.519 | 61.842 | 12.323 | -1.803 | 2.3677 | 4.1707 | -43.5507 | 10.628 | 7.844 | conviction_score >= 71<br>decision == OBSERVE |
| 21 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3726 | 49.519 | 61.29 | 11.771 | -1.803 | 2.3441 | 4.1471 | -43.5507 | 10.267 | 7.971 | conviction_score >= 71<br>market_gate == GREEN |
| 22 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3774 | 49.519 | 61.147 | 11.628 | -1.803 | 2.2654 | 4.0684 | -43.5507 | 10.246 | 7.417 | conviction_score >= 71.7<br>decision == OBSERVE |
| 23 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3846 | 49.519 | 60.625 | 11.106 | -1.803 | 2.2445 | 4.0475 | -43.5507 | 9.904 | 7.548 | conviction_score >= 71.7<br>market_gate == GREEN |
| 24 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.491 | 52.695 | 63.415 | 10.72 | -0.8029 | 2.7737 | 3.5766 | -43.5507 | 10.567 | 6.412 | decision == OBSERVE<br>expected_return_1d_pct >= 1.09 |
| 25 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.485 | 52.695 | 62.963 | 10.268 | -0.8029 | 2.785 | 3.5879 | -43.5507 | 10.01 | 6.291 | expected_return_1d_pct >= 1.09<br>market_gate == GREEN |
| 26 | shadow_candidate | KOSPI | ranked_top20 | 5d | 1 | 0.3942 | 49.519 | 60.366 | 10.847 | -1.803 | 1.9383 | 3.7413 | -43.5507 | 9.264 | 6.496 | decision == OBSERVE |
| 27 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3942 | 49.519 | 60.366 | 10.847 | -1.803 | 1.9383 | 3.7413 | -43.5507 | 9.264 | 6.496 | decision == OBSERVE<br>prob_clean >= 53.55 |
| 28 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3942 | 49.519 | 60.366 | 10.847 | -1.803 | 1.9383 | 3.7413 | -43.5507 | 9.264 | 6.496 | decision == OBSERVE<br>prob_clean >= 55.4 |
| 29 | shadow_candidate | KOSPI | ranked_top20 | 5d | 1 | 0.4038 | 49.519 | 60.119 | 10.6 | -1.803 | 1.9133 | 3.7163 | -43.5507 | 9.249 | 6.685 | market_gate == GREEN |
| 30 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.4038 | 49.519 | 60.119 | 10.6 | -1.803 | 1.9133 | 3.7163 | -43.5507 | 9.249 | 6.685 | market_gate == GREEN<br>prob_clean >= 53.55 |
| 31 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.4038 | 49.519 | 60.119 | 10.6 | -1.803 | 1.9133 | 3.7163 | -43.5507 | 9.249 | 6.685 | market_gate == GREEN<br>prob_clean >= 55.4 |
| 32 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.497 | 52.695 | 62.651 | 9.956 | -0.8029 | 2.6424 | 3.4453 | -43.5507 | 9.906 | 6.529 | decision == OBSERVE<br>expected_edge_score >= 12.12 |
| 33 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.497 | 52.695 | 62.651 | 9.956 | -0.8029 | 2.6424 | 3.4453 | -43.5507 | 9.906 | 6.529 | decision == OBSERVE<br>expected_return_3d_pct >= 1.58 |
| 34 | shadow_candidate | KOSPI | ranked_top20 | 5d | 2 | 0.3918 | 49.519 | 60.123 | 10.604 | -1.803 | 1.9388 | 3.7418 | -43.5507 | 8.961 | 6.447 | decision == OBSERVE<br>market_gate == GREEN |
| 35 | shadow_candidate | KOSPI | top5 | 5d | 1 | 0.5449 | 52.695 | 61.538 | 8.843 | -0.8029 | 2.4896 | 3.2925 | -43.5507 | 9.535 | 7.377 | decision == OBSERVE |
| 36 | shadow_candidate | KOSPI | top5_exception | 5d | 1 | 0.5449 | 52.695 | 61.538 | 8.843 | -0.8029 | 2.4896 | 3.2925 | -43.5507 | 9.535 | 7.377 | decision == OBSERVE |
| 37 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.491 | 52.695 | 62.195 | 9.5 | -0.8029 | 2.6519 | 3.4548 | -43.5507 | 9.347 | 6.412 | expected_edge_score >= 12.12<br>market_gate == GREEN |
| 38 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.491 | 52.695 | 62.195 | 9.5 | -0.8029 | 2.6519 | 3.4548 | -43.5507 | 9.347 | 6.412 | expected_return_3d_pct >= 1.58<br>market_gate == GREEN |
| 39 | shadow_candidate | KOSPI | top5 | 5d | 1 | 0.5689 | 52.695 | 61.053 | 8.358 | -0.8029 | 2.4223 | 3.2252 | -43.5507 | 9.373 | 7.747 | market_gate == GREEN |
| 40 | shadow_candidate | KOSPI | top5_exception | 5d | 1 | 0.5689 | 52.695 | 61.053 | 8.358 | -0.8029 | 2.4223 | 3.2252 | -43.5507 | 9.373 | 7.747 | market_gate == GREEN |
| 41 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.5389 | 52.695 | 61.111 | 8.416 | -0.8029 | 2.4967 | 3.2996 | -43.5507 | 9.022 | 7.279 | decision == OBSERVE<br>market_gate == GREEN |
| 42 | shadow_candidate | KOSPI | top5_exception | 5d | 2 | 0.5389 | 52.695 | 61.111 | 8.416 | -0.8029 | 2.4967 | 3.2996 | -43.5507 | 9.022 | 7.279 | decision == OBSERVE<br>market_gate == GREEN |
| 43 | shadow_candidate | KOSPI | top5_exception | 3d | 2 | 0.4093 | 49.741 | 60.76 | 11.019 | 0.1862 | 2.6589 | 2.4727 | -27.5556 | 12.344 | 3.116 | conviction_score >= 69.5<br>expected_return_1d_pct >= 0.97 |
| 44 | shadow_candidate | KOSPI | top5_exception | 3d | 2 | 0.4093 | 49.741 | 60.76 | 11.019 | 0.1862 | 2.6589 | 2.4727 | -27.5556 | 12.344 | 3.116 | conviction_score >= 69.5<br>expected_return_3d_pct >= 1.41 |
| 45 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.41 | 52.0 | 65.854 | 13.854 | 0.178 | 2.5914 | 2.4134 | -28.4071 | 7.458 | 0.893 | institution_10d >= 32831<br>prob_clean >= 50.4 |
| 46 | shadow_candidate | KOSPI | top5 | 3d | 2 | 0.3627 | 49.741 | 60.0 | 10.259 | 0.1862 | 2.5735 | 2.3873 | -27.5556 | 11.421 | 4.508 | conviction_score >= 68.845<br>expected_return_1d_pct >= 0.97 |
| 47 | shadow_candidate | KOSPI | top5 | 3d | 2 | 0.3627 | 49.741 | 60.0 | 10.259 | 0.1862 | 2.5735 | 2.3873 | -27.5556 | 11.421 | 4.508 | conviction_score >= 68.845<br>expected_return_3d_pct >= 1.41 |
| 48 | shadow_candidate | KOSPI | top5_exception | 3d | 2 | 0.3627 | 49.741 | 60.0 | 10.259 | 0.1862 | 2.5735 | 2.3873 | -27.5556 | 11.421 | 4.508 | conviction_score >= 68.845<br>expected_return_1d_pct >= 0.97 |
| 49 | shadow_candidate | KOSPI | top5_exception | 3d | 2 | 0.3627 | 49.741 | 60.0 | 10.259 | 0.1862 | 2.5735 | 2.3873 | -27.5556 | 11.421 | 4.508 | conviction_score >= 68.845<br>expected_return_3d_pct >= 1.41 |
| 50 | shadow_candidate | KOSPI | top5 | 5d | 1 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_edge_score >= 9.001 |
| 51 | shadow_candidate | KOSPI | top5 | 5d | 1 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_return_3d_pct >= 1.18 |
| 52 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_edge_score >= 9.001<br>expected_return_3d_pct >= 1.18 |
| 53 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_edge_score >= 9.001<br>expected_return_1d_pct >= 0.97 |
| 54 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_edge_score >= 9.001<br>expected_return_3d_pct >= 1.41 |
| 55 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_edge_score >= 9.001<br>expected_return_1d_pct >= 1.09 |
| 56 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_edge_score >= 9.001<br>expected_return_3d_pct >= 1.58 |
| 57 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_return_1d_pct >= 0.97<br>expected_return_3d_pct >= 1.18 |
| 58 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_edge_score >= 10.785<br>expected_return_3d_pct >= 1.18 |
| 59 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_return_1d_pct >= 1.09<br>expected_return_3d_pct >= 1.18 |
| 60 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_edge_score >= 12.12<br>expected_return_3d_pct >= 1.18 |
| 61 | shadow_candidate | KOSPI | top5_exception | 5d | 1 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_edge_score >= 9.001 |
| 62 | shadow_candidate | KOSPI | top5_exception | 5d | 1 | 0.3653 | 52.695 | 60.656 | 7.961 | -0.8029 | 2.9839 | 3.7868 | -28.4733 | 6.509 | 1.414 | expected_return_3d_pct >= 1.18 |
| 63 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.5 | 52.0 | 64.4 | 12.4 | 0.178 | 2.2574 | 2.0794 | -36.1594 | 8.6 | 3.8 | conviction_score >= 71<br>institution_10d >= 32831 |
| 64 | shadow_candidate | KOSPI | top5 | 5d | 1 | 0.3533 | 52.695 | 61.017 | 8.322 | -0.8029 | 2.6653 | 3.4682 | -28.4733 | 6.537 | 0.914 | conviction_score >= 66.8 |
| 65 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3533 | 52.695 | 61.017 | 8.322 | -0.8029 | 2.6653 | 3.4682 | -28.4733 | 6.537 | 0.914 | conviction_score >= 66.8<br>expected_edge_score >= 12.12 |
| 66 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3533 | 52.695 | 61.017 | 8.322 | -0.8029 | 2.6653 | 3.4682 | -28.4733 | 6.537 | 0.914 | conviction_score >= 66.8<br>expected_return_3d_pct >= 1.58 |
| 67 | shadow_candidate | KOSPI | top5_exception | 5d | 1 | 0.3533 | 52.695 | 61.017 | 8.322 | -0.8029 | 2.6653 | 3.4682 | -28.4733 | 6.537 | 0.914 | conviction_score >= 66.8 |
| 68 | shadow_candidate | KOSPI | top5 | 5d | 1 | 0.5569 | 52.695 | 60.215 | 7.52 | -0.8029 | 2.2588 | 3.0617 | -35.4483 | 8.377 | 1.114 | expected_return_1d_pct >= 0.97 |
| 69 | shadow_candidate | KOSPI | top5 | 5d | 1 | 0.5569 | 52.695 | 60.215 | 7.52 | -0.8029 | 2.2588 | 3.0617 | -35.4483 | 8.377 | 1.114 | expected_return_3d_pct >= 1.41 |
| 70 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.5569 | 52.695 | 60.215 | 7.52 | -0.8029 | 2.2588 | 3.0617 | -35.4483 | 8.377 | 1.114 | expected_return_1d_pct >= 0.97<br>expected_return_3d_pct >= 1.41 |
| 71 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.5569 | 52.695 | 60.215 | 7.52 | -0.8029 | 2.2588 | 3.0617 | -35.4483 | 8.377 | 1.114 | expected_edge_score >= 10.785<br>expected_return_1d_pct >= 0.97 |
| 72 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.5569 | 52.695 | 60.215 | 7.52 | -0.8029 | 2.2588 | 3.0617 | -35.4483 | 8.377 | 1.114 | expected_edge_score >= 12.12<br>expected_return_1d_pct >= 0.97 |
| 73 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.5569 | 52.695 | 60.215 | 7.52 | -0.8029 | 2.2588 | 3.0617 | -35.4483 | 8.377 | 1.114 | expected_return_1d_pct >= 0.97<br>expected_return_3d_pct >= 1.58 |
| 74 | shadow_candidate | KOSPI | top5_exception | 5d | 1 | 0.5569 | 52.695 | 60.215 | 7.52 | -0.8029 | 2.2588 | 3.0617 | -35.4483 | 8.377 | 1.114 | expected_return_1d_pct >= 0.97 |
| 75 | shadow_candidate | KOSPI | top5_exception | 5d | 1 | 0.5569 | 52.695 | 60.215 | 7.52 | -0.8029 | 2.2588 | 3.0617 | -35.4483 | 8.377 | 1.114 | expected_return_3d_pct >= 1.41 |
| 76 | shadow_candidate | KOSPI | ranked_top20 | 3d | 2 | 0.404 | 52.0 | 64.356 | 12.356 | 0.178 | 2.1843 | 2.0063 | -39.3293 | 8.751 | 4.184 | conviction_score >= 71<br>retail_10d <= -22629.9 |
| 77 | shadow_candidate | KOSPI | top5 | 5d | 1 | 0.5629 | 52.695 | 59.575 | 6.88 | -0.8029 | 2.2269 | 3.0298 | -35.4483 | 7.817 | 1.274 | expected_edge_score >= 10.785 |
| 78 | shadow_candidate | KOSPI | top5_exception | 5d | 1 | 0.5629 | 52.695 | 59.575 | 6.88 | -0.8029 | 2.2269 | 3.0298 | -35.4483 | 7.817 | 1.274 | expected_edge_score >= 10.785 |
| 79 | shadow_candidate | KOSPI | top5 | 5d | 1 | 0.3593 | 52.695 | 60.0 | 7.305 | -0.8029 | 2.7986 | 3.6015 | -28.4733 | 5.689 | 1.168 | expected_return_1d_pct >= 0.81 |
| 80 | shadow_candidate | KOSPI | top5 | 5d | 2 | 0.3593 | 52.695 | 60.0 | 7.305 | -0.8029 | 2.7986 | 3.6015 | -28.4733 | 5.689 | 1.168 | expected_edge_score >= 9.001<br>expected_return_1d_pct >= 0.81 |

## Production Candidates

- None found under current holdout gate.

## Shadow Candidates

- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.3892 win_delta=13.459 avg_delta=5.2744 :: conviction_score >= 68.845 / expected_return_1d_pct >= 0.97
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.3713 win_delta=15.047 avg_delta=5.0916 :: decision == OBSERVE / loss_risk_score <= 15.86
- `KOSPI` `top5_exception` `5d` level=shadow_candidate retain=0.3713 win_delta=15.047 avg_delta=5.0916 :: decision == OBSERVE / loss_risk_score <= 15.86
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.3653 win_delta=12.879 avg_delta=4.6947 :: decision == OBSERVE / expected_return_1d_pct >= 0.97
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.3653 win_delta=12.879 avg_delta=4.6947 :: decision == OBSERVE / expected_return_3d_pct >= 1.41
- `KOSPI` `top5_exception` `5d` level=shadow_candidate retain=0.3653 win_delta=12.879 avg_delta=4.6947 :: decision == OBSERVE / expected_return_1d_pct >= 0.97
- `KOSPI` `top5_exception` `5d` level=shadow_candidate retain=0.3653 win_delta=12.879 avg_delta=4.6947 :: decision == OBSERVE / expected_return_3d_pct >= 1.41
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.3593 win_delta=12.305 avg_delta=4.7286 :: expected_return_1d_pct >= 0.97 / market_gate == GREEN
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.3593 win_delta=12.305 avg_delta=4.7286 :: expected_return_3d_pct >= 1.41 / market_gate == GREEN
- `KOSPI` `top5_exception` `5d` level=shadow_candidate retain=0.3593 win_delta=12.305 avg_delta=4.7286 :: expected_return_1d_pct >= 0.97 / market_gate == GREEN
- `KOSPI` `top5_exception` `5d` level=shadow_candidate retain=0.3593 win_delta=12.305 avg_delta=4.7286 :: expected_return_3d_pct >= 1.41 / market_gate == GREEN
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.3892 win_delta=13.459 avg_delta=4.9467 :: loss_risk_score <= 15.86 / market_gate == GREEN
- `KOSPI` `top5_exception` `5d` level=shadow_candidate retain=0.3892 win_delta=13.459 avg_delta=4.9467 :: loss_risk_score <= 15.86 / market_gate == GREEN
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.3713 win_delta=11.821 avg_delta=4.6199 :: decision == OBSERVE / expected_edge_score >= 10.785
- `KOSPI` `top5_exception` `5d` level=shadow_candidate retain=0.3713 win_delta=11.821 avg_delta=4.6199 :: decision == OBSERVE / expected_edge_score >= 10.785
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.4611 win_delta=12.24 avg_delta=4.4772 :: decision_score >= 90.3 / decision == OBSERVE
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.3653 win_delta=11.239 avg_delta=4.6521 :: expected_edge_score >= 10.785 / market_gate == GREEN
- `KOSPI` `top5_exception` `5d` level=shadow_candidate retain=0.3653 win_delta=11.239 avg_delta=4.6521 :: expected_edge_score >= 10.785 / market_gate == GREEN
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.479 win_delta=11.055 avg_delta=4.3825 :: decision_score >= 90.3 / market_gate == GREEN
- `KOSPI` `ranked_top20` `5d` level=shadow_candidate retain=0.3654 win_delta=12.323 avg_delta=4.1707 :: conviction_score >= 71 / decision == OBSERVE
- `KOSPI` `ranked_top20` `5d` level=shadow_candidate retain=0.3726 win_delta=11.771 avg_delta=4.1471 :: conviction_score >= 71 / market_gate == GREEN
- `KOSPI` `ranked_top20` `5d` level=shadow_candidate retain=0.3774 win_delta=11.628 avg_delta=4.0684 :: conviction_score >= 71.7 / decision == OBSERVE
- `KOSPI` `ranked_top20` `5d` level=shadow_candidate retain=0.3846 win_delta=11.106 avg_delta=4.0475 :: conviction_score >= 71.7 / market_gate == GREEN
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.491 win_delta=10.72 avg_delta=3.5766 :: decision == OBSERVE / expected_return_1d_pct >= 1.09
- `KOSPI` `top5` `5d` level=shadow_candidate retain=0.485 win_delta=10.268 avg_delta=3.5879 :: expected_return_1d_pct >= 1.09 / market_gate == GREEN
- `KOSPI` `ranked_top20` `5d` level=shadow_candidate retain=0.3942 win_delta=10.847 avg_delta=3.7413 :: decision == OBSERVE
- `KOSPI` `ranked_top20` `5d` level=shadow_candidate retain=0.3942 win_delta=10.847 avg_delta=3.7413 :: decision == OBSERVE / prob_clean >= 53.55
- `KOSPI` `ranked_top20` `5d` level=shadow_candidate retain=0.3942 win_delta=10.847 avg_delta=3.7413 :: decision == OBSERVE / prob_clean >= 55.4
- `KOSPI` `ranked_top20` `5d` level=shadow_candidate retain=0.4038 win_delta=10.6 avg_delta=3.7163 :: market_gate == GREEN
- `KOSPI` `ranked_top20` `5d` level=shadow_candidate retain=0.4038 win_delta=10.6 avg_delta=3.7163 :: market_gate == GREEN / prob_clean >= 53.55

## Diagnostics

- `KOSPI` `top5` rows=688 days=68 cut=2026-07-16 predicates=334 levels={'coverage_fail': 1128, 'diagnostic': 723, 'shadow_candidate': 94}
- `KOSPI` `top5_exception` rows=700 days=68 cut=2026-07-16 predicates=337 levels={'coverage_fail': 1163, 'diagnostic': 692, 'shadow_candidate': 67}
- `KOSPI` `ranked_top20` rows=1914 days=68 cut=2026-07-16 predicates=338 levels={'coverage_fail': 1185, 'diagnostic': 735, 'shadow_candidate': 102}
- `KOSDAQ` `top5` rows=636 days=66 cut=2026-07-20 predicates=292 levels={'coverage_fail': 1103, 'diagnostic': 601, 'shadow_candidate': 4, 'sample_fail': 1}
- `KOSDAQ` `top5_exception` rows=658 days=66 cut=2026-07-20 predicates=302 levels={'coverage_fail': 1082, 'diagnostic': 596, 'shadow_candidate': 8, 'sample_fail': 1}
- `KOSDAQ` `ranked_top20` rows=1942 days=66 cut=2026-07-20 predicates=314 levels={'coverage_fail': 1263, 'diagnostic': 639, 'shadow_candidate': 8, 'sample_fail': 7}

## Notes
- Internal research only; production scanner/model artifacts are unchanged.
- Rules are exclusion/demotion candidates: matching rows are removed from the evaluated cohort, then the remaining cohort is scored on holdout.
- Predicate thresholds and categorical levels are learned from the train split only, then applied to holdout.
- Primary theme identity is excluded by default because fixed-theme rules can overfit rotating market themes.
- Production candidates require train/test uplift, retained support, positive average return, controlled bad-path/stop risk, and tail loss no worse than -12%.
- By default only 3D/5D guards can be production candidates; 1D-only improvements remain shadow candidates for swing use.
