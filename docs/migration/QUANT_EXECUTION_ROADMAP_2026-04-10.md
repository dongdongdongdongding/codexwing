# Quant Execution Roadmap

## Objective
- Maximize basket return, upside hit rate, and loser avoidance for KOSPI/KOSDAQ.
- Rank stocks that actually rise.
- Avoid mixing short-lived event bursts with multi-day continuation names in the same basket.
- Require 98% confidence interval validation before promotion.

## Program Stages
1. Scorecard lock
- Fix 1D / 3D / 5D metrics.
- Fix release gates for KOSPI and KOSDAQ.
- Treat upside capture and downside avoidance as first-class metrics.

2. Lane separation
- Split KR candidates into `1d` and `3d` lanes.
- Carry lane metadata through planner, watchlist, realized outcomes, and archive export.
- Prevent KOSDAQ baskets from mixing incompatible holding profiles.

3. Factor redesign
- `1d` lane:
  - news catalyst
  - disclosure / beneficiary context
  - turnover acceleration
  - strong close location
  - flow-leader confirmation
- `3d` lane:
  - trend persistence
  - multi-day flow support
  - theme continuation
  - clean-prob / expected-return persistence
  - anti-fade guard

4. Market-specific policy
- KOSPI:
  - institutional / foreign flow continuity
  - cleaner continuation bias
- KOSDAQ:
  - theme expansion vs event burst explicitly separated
  - persistence filters stronger than current intraday breakout bias

5. Validation and release gating
- Walk-forward archive validation.
- 98% confidence interval on:
  - avg 1D return
  - avg 3D return
  - positive 1D / 3D hit rate
  - avoid-down 1D / 3D rate
  - 10% mover precision
- Promote only when the target lane improves without unacceptable regression in its intended holding horizon.

## Current Status
- Scorecard and archive validation exist.
- KR context, theme, and flow-leader signals are now embedded in ranking.
- KR quant reranker exists.
- Planner now supports lane-aware KR prioritization.
- Remaining gap: KOSDAQ 3D persistence is still weak in archive validation.

## Immediate Next Steps
1. Carry `selection_lane`, `target_horizon_days`, and quant priority scores end-to-end.
2. Tighten KOSDAQ `3d` persistence guard.
3. Re-run archive validation.
4. Only then decide whether to promote the new ranking path further into production.

## Release Gate
- KOSPI:
  - top10 1D positive-rate improvement
  - no material collapse in 3D continuation
- KOSDAQ:
  - chosen active lane must improve its intended horizon
  - if `3d` lane stays weak, default market basket to `1d` lane instead of mixing
- Any regression in loser-avoidance beyond tolerance blocks promotion.
