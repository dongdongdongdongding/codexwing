# Objective Lock (2026-04-10)

## Non-Negotiable Goal
The scanner must optimize for profitable long selection in KOSPI/KOSDAQ.

This means all future analysis, ranking, validation, and tuning must prioritize:

1. correctly selecting stocks that go up
2. capturing explosive winners as well as solid upward movers
3. avoiding stocks that go down after selection
4. improving total return and positive-hit reliability, not just raw candidate filtering

## What Must Be Measured
The system must not be evaluated only on "top movers" or only on "win rate".
It must be evaluated on all of the following together:

- 10%+ mover capture rate
- positive return hit rate (`return_close_pct > 0`, `return_1d_pct > 0`, `return_3d_pct > 0`)
- top-N ranking precision for upward movers
- loser-avoidance rate
- average return of selected baskets
- confidence intervals for all major claims

## Explicit Anti-Goal
Do not optimize the scanner into a conservative filter that merely rejects many names.
Do not optimize for downward names being surfaced.
Do not treat "strictness" as success unless it improves actual upward-selection performance.

## Working Interpretation
The desired engine is:

- a money-flow and leadership detector
- a market-context aware ranking system
- a positive-expectancy selector

It is not merely:

- a cautious anomaly rejector
- a score beautifier
- a UI-friendly ranking layer

## Persistence Note
If context is compressed later, preserve this objective as the primary reference for future work.
