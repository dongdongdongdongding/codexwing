# Operational Status

- Date: 2026-03-31
- Status: usable now

## What is operational
- US avoid buckets downgrade to watchlist-only at planner stage.
- KOSDAQ and KOSPI use separate liquidity-aware universes.
- KOSDAQ zero-result runs now keep a current-run near-miss watchlist instead of returning nothing.
- reject diagnostics, planner warnings, realized outcome placeholders, and postmortem traces are all written.

## Example artifacts
- US watchlist-only validation:
  - [RUN-08CDC5E4 planner_handoff.json](/Users/dongdong/Desktop/codex_swing/swing-main/runtime_state/shared_working/RUN-08CDC5E4/planner_handoff.json)
- KOSDAQ liquid universe validation:
  - [RUN-758DCA86 planner_handoff.json](/Users/dongdong/Desktop/codex_swing/swing-main/runtime_state/shared_working/RUN-758DCA86/planner_handoff.json)
  - [RUN-758DCA86 realized_outcomes.json](/Users/dongdong/Desktop/codex_swing/swing-main/runtime_state/shared_working/RUN-758DCA86/realized_outcomes.json)

## Remaining gap
- win-rate 70% / return 15% is not yet proven with live realized outcomes.
- current remaining KOSDAQ bottleneck is mostly `KR_HARD_FILTER_FAIL` in RED market.

## Recommended production path
- use current prod profile defaults
- treat `WATCHLIST_ONLY` outputs as monitored opportunities, not active buys
- continue accumulating realized outcomes for weekly policy recalibration
