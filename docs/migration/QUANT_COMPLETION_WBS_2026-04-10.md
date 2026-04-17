# Quant Completion WBS

## Goal
- Build a KRX quant program that selects rising names, avoids falling names, and separates explosive movers from continuation setups with traceable evidence and release gates.

## Release Definition
- KOSPI and KOSDAQ must both pass walk-forward validation.
- `picked` bucket must outperform `watchlist` on realized returns for the target horizon.
- KOSDAQ explosive lane and continuation lane must each clear their own release gates.
- Validation must use the same factors the engine actually uses.

## Phase 1. Validation Parity
- Priority: P0
- Objective: make archive validation speak the same language as the live engine.
- Tasks:
- Persist and export scanner factor traces used by ranking.
- Add explicit KR candidate taxonomy: `CORE_TREND`, `EXPLOSIVE_LEADER`, `REJECT_RISK`, `TRANSITIONAL`.
- Add explicit timeframe profile tags for KR scans.
- Rebuild archive export and verify coverage gaps shrink for future runs.
- Exit criteria:
- scanner_handoff contains role/timeframe tags.
- archive export contains `scanner_timeframe_profile` and `kr_universe_role`.
- validation can group by these fields.

## Phase 2. KR Universe Split
- Priority: P1
- Objective: stop forcing all KRX candidates through one logic path.
- Tasks:
- Separate KR into `Core Trend`, `Explosive Leader`, and `Reject Risk`.
- Route KOSDAQ explosive names to 1D-first logic.
- Keep KOSPI mixed lane unless data says otherwise.
- Exit criteria:
- KOSDAQ explosive candidates are tracked separately from 3D continuation names.
- decision and planner traces show the assigned universe role.

## Phase 3. Dual-Timeframe Scanner
- Priority: P1
- Objective: keep daily structure while confirming with hourly flow and breakout evidence.
- Tasks:
- Add hourly confirmation features to KR SWING path.
- Use breakout quality, close-location, turnover acceleration, and flow consensus as confirmation inputs.
- Add release metrics comparing daily-only vs dual-timeframe scoring.
- Exit criteria:
- SWING path is explicitly `daily-primary + 1h confirmation`.
- KOSDAQ hit10 and positive1D improve without degrading KOSPI top10 too heavily.

## Phase 4. Explosive Leader Engine
- Priority: P1
- Objective: capture 10%+ movers without confusing them with late-stage traps.
- Tasks:
- Build explosive leader score from breakout quality, money flow, turnover, close-location, and context tailwind.
- Separate `true leader` from `late chase`.
- Add dedicated release gate for explosive lane.
- Exit criteria:
- explosive lane top-N beats baseline on hit10, positive1D, and avg1D.

## Phase 5. Continuation Engine
- Priority: P2
- Objective: only promote 3D continuation where evidence exists.
- Tasks:
- Keep KOSDAQ continuation on eligible sub-universe only until release gate clears.
- Expand continuation features with flow persistence and theme continuation.
- Exit criteria:
- continuation sub-basket stays positive and primary basket no longer regresses when 3D is enabled.

## Phase 6. Planner and Bucket Semantics
- Priority: P2
- Objective: align `picked`, `watchlist`, and planner decisions with realized edge.
- Tasks:
- Refit picked promotion thresholds.
- Split scanner score, quant priority, and planner action semantics cleanly.
- Exit criteria:
- `picked` outperforms `watchlist` on the intended horizon.

## Phase 7. Walk-Forward Release Gates
- Priority: P0 ongoing
- Objective: block promotion unless changes survive multiple windows.
- Tasks:
- Use 98% confidence validation for KOSPI/KOSDAQ and lane-specific baskets.
- Add release gates for explosive lane, continuation lane, and primary basket.
- Exit criteria:
- promotion decisions are made from release gates, not ad hoc judgment.

## Execution Order
1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7 throughout
