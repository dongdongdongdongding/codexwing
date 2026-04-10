# Project Context Analysis (2026-04-10)

## Snapshot
- Workspace: `swing-main`
- Analysis date: `2026-04-10`
- Basis:
  - project rules in `AGENTS.md`
  - migration docs under `docs/migration/`
  - multi-agent runtime under `multi_agent/`
  - recent local artifacts under `runtime_state/shared_working/`
  - recent operational rows in Supabase (`agent_run_summaries`, `agent_postmortems`, `agent_improvement_tickets`, `agent_profile_diagnostics`, `agent_outcome_health`)

## 1. Project Context
This project is no longer just a stock scanner. It is being reshaped into a quant research and execution-support system that must satisfy two audiences at once:

- engineers who need reusable engine modules
- a PM/operator who needs to inspect why the system recommended, rejected, or missed something

The repository started from an Antigravity-style monolith and is now in an additive migration stage toward a 5-agent architecture:

1. Scanner Agent
2. Aggregation Agent
3. Backtest & Learning Agent
4. Market & News Context Agent
5. PM Planner Agent

The intended end state is not "LLM chatter." The intended end state is:

- structured handoffs
- explicit evidence and warnings
- reproducible artifacts
- separated memory layers
- postmortem and improvement-ticket loops

This direction is consistent across `AGENTS.md`, `docs/migration/ARCHITECTURE_ANALYSIS.md`, and `multi_agent/README.md`.

## 2. Current State
The project has already built a meaningful multi-agent trace layer, but production behavior is still primarily legacy-driven.

### What is already real
- `multi_agent/` contains contracts, schemas, storage layout, agent runtimes, orchestration bridge, and operations tools.
- Every run can emit:
  - `scanner_handoff.json`
  - `aggregation_handoff.json`
  - `backtest_handoff.json`
  - `market_context_handoff.json`
  - `planner_handoff.json`
  - `postmortem_report.json`
  - `improvement_tickets.json`
  - `profile_diagnostics.json`
  - `outcome_health.json`
  - `realized_outcomes.json`
- Supabase persistence is working for PM-facing operational tables.
- Daily summary and outcome updater tooling exist.

### What is still true in practice
- Recent Supabase runs are still recorded as:
  - `strategy_version=legacy-ui-v1`
  - `model_version=legacy`
  - `code_version=bridge-v1`
- This means the system is still mainly:
  - running legacy scan logic first
  - then bridging that output into the multi-agent trace pipeline

In other words, the multi-agent layer is already valuable, but it is still mostly an observability and decision-overlay layer on top of legacy execution.

## 3. What Is Working Well

### Traceability is materially better than before
The repository now has a real run record, not just a UI result screen.

- recent runs are persisted in Supabase
- postmortems are auto-generated
- improvement tickets are auto-generated
- outcome-health snapshots exist
- profile diagnostics exist

This is a major architectural improvement because it turns the system into something that can actually be audited and iterated on.

### Memory layers are structurally separated
The current filesystem layout matches the intended memory model:

- local short-term memory: `runtime_state/local_short_term/`
- shared working memory: `runtime_state/shared_working/`
- long-term memory: `runtime_state/long_term/`
- artifact store: `runtime_state/artifacts/`

That separation is simple but correct, and it aligns with the project rules.

### PM-facing operational tooling exists
The project already has useful PM/ops reporting hooks:

- outcome health reports
- profile diagnostics reports
- fallback watchlist tracking
- daily summaries
- dashboard SQL templates for Supabase

This is a strong base for explainability and postmortem workflows.

## 4. Core Problems

### A. The architecture is still dominated by giant legacy modules
The main structural problem is not missing scaffolding. It is that the core execution logic is still concentrated in oversized files.

Current file sizes:

- `modules/quant_analysis.py`: 3856 lines
- `modules/scanner_services.py`: 2733 lines
- `app.py`: 2514 lines
- `modules/scanner_runtime.py`: 450 lines
- `multi_agent/agents/planner_runtime.py`: 521 lines

Implication:

- engine logic is still not cleanly bounded by responsibility
- UI risk is still too high because `app.py` remains operationally important
- scanner, scoring, ranking, and decision semantics are still harder to test in isolation than the target architecture requires

This is the main reason the migration is not "done" even though many artifacts already exist.

### B. Production is still using the bridge, not the new orchestrator as the primary execution path
Recent runs in Supabase show `legacy-ui-v1` and `bridge-v1`, not an orchestrator-native version.

Implication:

- the new architecture is not yet the real source of execution authority
- the system still depends on legacy scan semantics first, structured orchestration second
- drift risk remains between legacy logic and newer planner/runtime layers

This is acceptable as a migration stage, but it is still a gap.

### C. Machine-readable outputs are not always strict JSON
`runtime_state/shared_working/RUN-6E60F98F/market_context_handoff.json` contains `NaN` in `raw_context.krw_change_1d`.

That breaks one of the most important project goals:

- outputs must be machine-readable
- trace artifacts should be safe for downstream automation

Python's default `json.dump(...)` allows non-standard `NaN`, so the repository is currently writing files that look like JSON but are not strict interoperable JSON.

This is a real auditability problem, not a cosmetic one.

### D. Decision semantics are internally inconsistent
In `RUN-6E60F98F`:

- `planner_handoff.json` contains 82 decisions
- all 82 are `OBSERVE`
- decision scores range from `60.3` to `100.0`

The planner is demoting decisions through several guards:

- market-mode probation
- priority guards
- expected-edge guards

But the exported `decision_score` remains the original scanner-side score.

Implication:

- a human can read a row with `decision=OBSERVE` and `decision_score=100.0`
- downstream systems may over-trust the raw score
- "what the system thinks is actionable" and "what the score says" are no longer aligned

This is exactly the kind of ambiguity that creates PM/operator confusion.

### E. Confidence is still too easy to overstate relative to evidence quality
`planner_runtime.py` computes confidence mainly from scanner score and weak-candidate ratio. Recent postmortem tickets already show this issue:

- `Strengthen small-sample safeguards`
- requested change: attach sample-size penalty to planner confidence and show warning banner

The concern is valid. In the latest KOSPI run:

- confidence is as high as `0.95`
- sampled real backtest coverage ratio is only `0.061`
- total sampled trades sum is `22`
- regime sensitivity status is `low_sample`

Implication:

- confidence can look stronger than the actual evidence base
- the system is partially aware of this problem
- the mitigation exists as ticketing, but not yet as a fully enforced decision contract

### F. Backtest diagnostics are useful but still shallow relative to the target architecture
The project has improved beyond pure placeholders, but the current backtest layer is still only partially authoritative.

Latest KOSPI backtest handoff shows:

- `mode=quantstrategy_backtest_sampled`
- real backtests sampled on only 5 tickers
- regime sensitivity tested in only 1 regime slice
- warning: `REGIME_BACKTEST_LOW_SAMPLE`

Implication:

- diagnostics are directionally useful
- but still too thin to serve as a strong planner foundation
- planner decisions are still relying heavily on scanner score and hand-coded guards rather than rich learned diagnostics

### G. Operational backlog is still large
Recent Supabase outcome-health totals over 20 rows show:

- `outcomes_total=9038`
- `pending=3678`
- `resolved=5256`
- `expired=104`
- `fallback_total=84`
- `fallback_pending=84`

This means the system is producing trace records well, but closure is still incomplete.

Implication:

- realized-outcome feedback exists, but not tightly enough
- fallback watchlist tracking is present, but not yet fully closing the loop
- PM review can still be biased by incomplete outcome closure

### H. Filter starvation and fallback behavior are still active symptoms
Recent profile diagnostics show repeated heavy reject pressure:

- `INTRADAY_MIN_PRICE_VOLUME_FAIL`
- `LIQUIDITY_FILTER_FAIL`
- `PRECISION_GATE_T3_LOW_ML_SUPPORT`

There are also runs where:

- `prod_zero_streak_alert=true`
- fallback watchlist was applied from a prior source run

Implication:

- the scanner is still periodically too restrictive in production conditions
- fallback policy is useful as a safety net
- but fallback should remain exceptional, not a normal mode of operation

### I. PM Planner is still partly acting as a rules engine, not only as a planning authority
The project rule says the PM Planner should:

- review outputs from other agents
- analyze failures
- generate improvement tickets
- request targeted changes

That part is happening.

But in practice, `planner_runtime.py` also contains a large amount of hard-coded market-mode gating and decision demotion logic.

Implication:

- PM semantics and rule-engine semantics are still mixed
- planner logic is becoming another policy monolith
- responsibilities are cleaner than before, but still not clean enough

## 5. Main Strategic Interpretation
The project is not failing because it lacks ideas or instrumentation.
It is succeeding in instrumentation, but it is now entering the harder phase:

- turning observability into execution authority
- turning traces into reliable decision semantics
- turning a bridge architecture into a bounded engine architecture

The current state is best described as:

> "A strong migration scaffolding and observability layer wrapped around a still-dominant legacy engine."

That is a healthy midpoint, but not the target architecture yet.

## 6. Priority Order From Here

### Priority 1. Enforce strict artifact validity
Immediate fix area:

- sanitize `NaN` / `inf` / non-JSON-safe values before writing artifacts
- make all handoff outputs strict JSON

Reason:

- traceability and automation both depend on artifact trustworthiness

### Priority 2. Separate raw scanner score from effective planner action score
Introduce distinct fields such as:

- `scanner_score_raw`
- `planner_action_score`
- `decision_after_gates`
- `confidence_reason`

Reason:

- current outputs can tell two different stories at once
- PM/operator needs one coherent action interpretation

### Priority 3. Make sample-size and regime-depth penalties first-class decision inputs
Do not leave this only as a ticket.

Reason:

- the repository already detected the issue correctly
- confidence and final decision severity should be directly shaped by evidence depth

### Priority 4. Move production authority away from legacy bridge paths
The non-UI/orchestrated path should become the primary runtime, with UI acting as presentation/control rather than business-logic owner.

Reason:

- this is the cleanest way to reduce drift and hidden UI coupling

### Priority 5. Split the remaining monoliths by bounded context
Highest-value extraction targets:

1. feature generation and signal detection from `modules/quant_analysis.py`
2. candidate gating/ranking utilities from `modules/scanner_services.py`
3. orchestration remnants from `app.py`

Reason:

- this is the biggest long-term lever for testability and safe iteration speed

### Priority 6. Tighten outcome closure loops
Focus on:

- pending backlog reduction
- stale fallback aging
- clearer closure metrics per market/profile/run type

Reason:

- the system cannot learn well if too much of the recommendation surface remains operationally unresolved

## 7. Bottom Line
This repository already has the bones of a serious multi-agent trading decision system.

The strongest parts today are:

- trace collection
- operational observability
- postmortem/ticket loops
- additive migration discipline

The weakest parts today are:

- oversized legacy engine ownership
- non-strict machine-readable outputs
- planner score/action ambiguity
- shallow evidence depth behind high confidence
- incomplete closure of realized outcomes

The next phase should not be "add more features first."
The next phase should be:

- make artifacts trustworthy
- make decision semantics unambiguous
- make evidence depth matter more
- make the new architecture the real runtime path

