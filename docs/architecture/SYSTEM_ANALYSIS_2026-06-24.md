# System Analysis - 2026-06-24

This is the integrated current-state analysis after the daily-edge corrections, intraday research, and KOSDAQ intraday deployment.

## Evidence Files Read

This analysis is based on Beads state, collaboration comments, current source files, daily ops scripts, live producers, UI/Discord consumers, storage contracts, and current learning reports listed in:

- `docs/operations/CURRENT_OPERATIONS_MANUAL_2026-06-24.md`
- `docs/architecture/BACKEND_DATA_ARCHITECTURE_2026-06-24.md`
- `docs/architecture/FRONTEND_OPERATOR_UI_2026-06-24.md`

## Current Objective

The operator target discussed in the current research stream is:

- Find operating candidates that can reach +5% within a short horizon.
- For the intraday target, the stated goal is about 70-75% probability of +5% within 3 days.
- Keep losses controlled enough for an 8:2 style operating profile.
- Use enough liquidity for actual trading, not only micro-cap statistical artifacts.
- Use forward ledgers before declaring full production maturity.

The current system is closest to that target in the KOSDAQ intraday 15:00 VWAP-guard lane.

## Key Research Corrections

### 1. Daily benchmark correction

Older daily "edge" claims were affected by benchmark choice:

- external KS11 benchmark could create artifacts
- cap-weighted internal benchmark could create size bias
- same-day size-matched controls are more appropriate when judging stock-picker skill

Result:

- regime conditional daily model: no durable edge
- NORMAL PEAD: no durable edge
- Practical-80: not validated as clean production edge
- score/rerank edge: at best market-neutralization or weak filter, not clean buy edge
- Exception Leader: positive in a short window, but not durable enough

### 2. Daily price-ML correction

The daily price-only ML top slice had real statistical signal under corrected validation, but cost/liquidity assumptions changed interpretation:

- It is not a 75% target model.
- It is a modest `ft_5_5` signal.
- With realistic lower costs, it can survive at some liquidity floors in research.
- Operationally it is still best treated as live-forward validation, not the main path to the 75%/3D target.

### 3. Intraday synthesis

The intraday research conclusion is stronger:

- Minute-bar context plus daily context matters.
- A 3-day +5% touch target is more aligned with the operator goal than daily 5D direction.
- VWAP-positive entry quality is the common stabilizer.
- Tight stops reduce expectancy in the tested intraday return studies.
- 3D close hold is the current best return contract for the KOSDAQ model.

## Current Best Model Family

The current best shared intraday family is:

```text
KR_INTRADAY_3D_T5_CONTEXT_VWAP_GUARD
```

Core elements:

1. Target: high touches +5% within 3 trading days.
2. Entry quality: price above VWAP before/at entry.
3. Intraday path features.
4. Previous daily context features.
5. Liquidity floor split.
6. Forward ledger.
7. 3D close-hold return policy.

## Production Status By Area

### SWING daily scanner/planner

Status: operational and visible, but not the main edge frontier.

Strengths:

- mature scanner/planner trace pipeline
- strong artifact and archive system
- web/Discord parity for normal surfaces
- realized outcome backfill machinery

Weaknesses:

- many old daily edge narratives were corrected or retracted
- legacy chart/flow/theme axes can demote price-only model lanes unless whitelisted
- daily selection does not satisfy the 75% target

### SWING ensemble lane

Status: live forward validation.

It should be used as:

- modest daily price-ML signal
- live evidence accumulation
- secondary operating lane

It should not be used as:

- proof that 75% daily target is solved
- replacement for intraday target research

### KOSPI intraday lane

Status: live forward validation.

Pros:

- high aggregate backtest hit after `close_vwap>=0` and `idx_vol20>=8`
- liquidity floor `>=100억`
- routes through existing model-lane consumer helper

Risks:

- volatility guard repairs a weak month and rests on limited weak-month evidence
- in-script training makes the production artifact less stable than the KOSDAQ stored bundle
- route uses SWING-style helper while conceptually intraday; docs and consumer surfaces must preserve semantics

### KOSDAQ intraday lane

Status: current best deployment candidate.

Pros:

- stored model bundle
- explicit candidate ID and strategy family
- live 15:00 entry uses only pre-entry data
- strong guarded OOS report
- `>=30억` and `>=100억` liquidity lanes both recorded
- direct ledger with `touch3d_t5`, `ret3d`, `mfe3`, `mae3`

Risks:

- sample is still small relative to full production
- data window is about one year
- `/signals` whitelist does not currently include its bucket
- drawdown is large; no tight stop is currently favored by expectancy, so sizing and operator discipline matter

## Structural Strengths

1. The project now has explicit scan modes.
2. KIS live data is integrated through adapters, not ad hoc scraping.
3. Runtime artifacts are persisted locally and optionally to Supabase.
4. Top Deep and Archive can recover from local artifacts.
5. Beads tracks follow-up work and research issues.
6. Candidate interpretation is centralized enough to avoid pure UI-only semantics.
7. Model-lane producers have explicit ledgers.
8. The research process now records benchmark and cost corrections instead of hiding them.

## Structural Weaknesses

1. `app.py` remains a large composition file.
2. Some docs and Beads notes are stale relative to the latest corrections.
3. KOSDAQ intraday consumer integration is not fully aligned with the existing model-lane whitelist.
4. KOSPI intraday retrains inside the producer rather than loading a versioned artifact.
5. Supabase timeout can block historical/backfill workflows.
6. Research cache dependencies live outside the repo and must be present.
7. Old model artifacts remain present even when retired.
8. Full intraday validation is limited by KIS minute-bar history length.

## What Should Not Be Done

- Do not promote old PEAD, regime, Practical-80, or Exception Leader narratives as production edges without the corrected benchmark and forward gates.
- Do not mix intraday candidates into SWING gates because their target, entry, and holding contract differ.
- Do not use win rate alone. Always read return, drawdown, liquidity, sample, active days, and monthly floor.
- Do not treat a local model file as live status. Live status comes from daily ops flags and producer routing.
- Do not hide candidates in the UI because action labels are cautious; visibility and buyability are separate.

## What Should Be Done Next

### Highest priority

Complete KOSDAQ intraday consumer parity:

- add `kosdaq_intraday_3d_t5_vwap_guard` to model-lane profile or create a dedicated KOSDAQ profile
- ensure `/signals` shows latest KOSDAQ intraday picks
- ensure Top Deep/Archive/Discord cards show entry=15:00, target +5%, hold 3D, no tight stop, liquidity lane, and probability

### Next

Stabilize KOSDAQ intraday live-forward monitoring:

- minimum forward picks: 60
- minimum days: 30
- minimum months: 2
- target touch minimum: 75%
- day hit minimum: 80%
- net 3D close return > 0
- liquidity-decile excess > 0
- no month with n>=5 below 65%
- realized slippage <= 0.50%

### Then

Version the KOSPI intraday model artifact:

- move training out of live producer or cache the trained bundle
- record feature list, data window, hyperparameters, validation, and checksum
- keep the volatility guard but track whether it remains necessary forward

### Continue

Keep SWING ensemble ledger running, but classify it as a modest daily signal.

## Final Analysis

The system has moved from daily stock picking toward intraday path/entry quality because the corrected daily research mostly capped out below the operator goal. The current best common model is the KOSDAQ 15:00 VWAP-guard `KR_INTRADAY_3D_T5` lane, supported by Claude/Codex synthesis and now deployed as a live-forward candidate.

The main unresolved issue is no longer "is there any promising model?" The main issue is operational maturation:

- consumer parity
- forward sample accumulation
- slippage and liquidity tracking
- drawdown-aware sizing
- strict separation of INTRADAY from SWING

If the KOSDAQ intraday lane holds in forward data, it is the clearest path toward the 3-day +5% target. If it does not, the project should keep accumulating minute data and avoid forcing daily models into a target they have not met.
