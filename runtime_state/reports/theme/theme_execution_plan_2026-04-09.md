# Theme Execution Plan (2026-04-09)

## Objective Assessment
- The theme-driven plan is likely to improve recall and return capture in RED/YELLOW or mixed markets by preserving true theme leaders that the baseline scanner often filters out.
- It does not automatically improve precision. Precision can fall if theme states are noisy, leader ranking is weak, or theme exceptions bypass hard filters too early.
- The safest rollout is shadow-first, additive-score second, exception-routing last.

## Success Metrics
- RED/YELLOW market candidate coverage increases versus baseline.
- Picked average return does not deteriorate versus baseline.
- Theme-routed candidates outperform generic watchlist candidates on 1D/3D returns.
- Theme leader top1 candidates outperform the average member of the same theme.

## Risks
- Noisy theme mapping causing false positives.
- Generic disclosure/news events over-inflating unrelated themes.
- Planner explanations becoming richer before ranking quality is proven.
- Hard-filter exceptions weakening the baseline system.

## Rollout Stages
1. Theme catalog and theme signal engine in shadow mode.
2. Theme leader ranker and theme clusters in scanner/aggregation/planner handoffs.
3. Additive theme score injection only.
4. Validation report review.
5. Limited theme exception routing in poor market regimes only after evidence.

## Implemented In This Slice
- KR theme catalog with multi-membership confidence.
- Theme signal engine from news/disclosure/macro drivers.
- Theme leader ranker and per-candidate leader metrics.
- Theme router in shadow/additive mode.
- market_context_handoff carries theme_states/beneficiary_themes/headwind_themes.
- scanner_handoff carries theme_context/leader_metrics/routing_path.
- aggregation_handoff now includes theme clusters and theme leaderboard.
- planner_handoff now carries theme_rationale/theme_risk.

## Next Validation Focus
- Compare theme-shadow routed candidates versus baseline watchlist on recent KOSDAQ/KOSPI runs.
- Verify no precision collapse in GREEN markets.
- Only then allow theme exception routing to influence hard filter bypass.
