# Architecture Analysis and Safe Migration Plan

## Scope
This document maps the current Antigravity-derived codebase and proposes a staged migration into a 5-agent architecture while preserving working trading logic.

## 1. Current Architecture Summary
- Main UI and orchestration live in `app.py` (large Streamlit monolith).
- Core engine logic is centralized in `modules/quant_analysis.py` (`QuantStrategy`), including data fetch, indicators, signal generation, backtest, scoring, ML inference, and verdict logic.
- Automation path exists in `auto_bot.py` with overlapping scanner logic.
- Persistence is handled by `modules/db_manager.py` (Supabase).
- Macro/news context logic exists in `modules/macro_scheduler.py`, `modules/market_intelligence.py`, and `modules/news_analysis.py`.
- Training/evaluation scripts are separate (`train_global_brain.py`, `train_ml_targets.py`, `retrain_ml.py`, `backtest_framework.py`, `train_model.py`).

## 2. Reusable Modules Map
### High-confidence reusable
- `modules/macro_scheduler.py`: market regime overlay context.
- `modules/market_intelligence.py`: structured market/news intelligence.
- `modules/news_analysis.py`: ticker-level sentiment extraction.
- `backtest_framework.py`: walk-forward parameter optimization.
- `retrain_ml.py`: realized-outcome learning loop.

### Reusable with adapter/wrapper
- `QuantStrategy.fetch_data`, `calculate_indicators`, `check_signals`.
- `QuantStrategy.backtest`, `detect_pre_surge_signals`.
- `QuantStrategy.get_investor_flows`, `get_real_trend`, `get_price_position`.
- `DBManager` save/fetch methods.

## 3. Files That Are Too Tightly Coupled
- `app.py`: UI, scanner orchestration, ranking logic, runtime state, and DB writes are mixed.
- `modules/quant_analysis.py`: too many responsibilities in one class.
- `auto_bot.py`: duplicated scoring/scanning behavior and drift risk versus UI path.

## 4. Logic That Should Stay Engine-Level
- Signal generation and technical feature computation.
- Backtest and diagnostics logic.
- Market regime and macro/news overlay calculations.
- Scoring functions and candidate ranking inputs.
- Model inference and calibration outputs.

## 5. Logic That Should Be Removed From UI Files
- Threaded scanner worker business rules.
- Candidate pass/fail gating.
- Decision-score composition.
- Direct DB upserts for scanner outcomes.
- Market-context side effects that depend on UI session state.

## 6. Proposed 5-Agent Migration Plan
### Scanner Agent
- Own candidate generation and scanner traces.
- Emit machine-readable candidate list and pass reasons.

### Aggregation Agent
- Analyze candidate concentration (sector/style/theme).
- Emit diversity and cluster diagnostics.

### Backtest & Learning Agent
- Run realistic, regime-aware diagnostics.
- Emit expectancy, win rate, PF, calibration, sample-size warnings.

### Market & News Context Agent
- Compute market regime, macro pressure, sector flow, and news impacts.
- Emit support/suppression overlay scores and warnings.

### PM Planner Agent
- Read all structured handoffs.
- Produce final ranking, rationale, warnings, postmortem, and improvement tickets.

## 7. Proposed Storage Layers
- `local short-term memory`: per-agent run-local temp state.
- `shared working memory`: current run/day handoff artifacts.
- `long-term memory`: historical outcomes, postmortems, ticket history, regime performance.
- `artifact store`: reproducible outputs (json/csv/parquet/md/charts/models).

## 8. Proposed DB Tables and JSON Handoff Schemas
### DB tables (proposed)
- `agent_runs`: run metadata (run_id, versions, timestamps, status).
- `scanner_candidates`: normalized scanner outputs.
- `aggregation_reports`: candidate quality diagnostics.
- `backtest_diagnostics`: backtest/calibration/sample-size diagnostics.
- `market_context_snapshots`: macro/news/regime overlays.
- `planner_decisions`: final ranked recommendations with rationale.
- `realized_outcomes`: post-recommendation outcomes.
- `postmortems`: structured failure analyses.
- `improvement_tickets`: ticket lifecycle by responsible agent/module.

### Handoff schemas
- scanner handoff
- aggregation handoff
- backtest handoff
- market context handoff
- planner decision
- postmortem report
- improvement ticket

Draft schemas are provided under `multi_agent/schemas/`.

## 9. Refactor Risks Likely to Break Current Behavior
- Rule drift between UI scanner and bot scanner if duplicated logic remains.
- Silent failure due to broad exception handling in scan loops.
- Runtime behavior changes from naming mismatches (`MACD_signal` vs `MACD_Signal`, missing method references).
- Hidden dependence on Streamlit session state in non-UI execution paths.
- Data/API rate-limit sensitivities when moving orchestration.

## 10. First Minimal Safe Refactor Steps
1. Add non-destructive scaffolding (contracts, schemas, memory layers, agent interfaces).
2. Preserve existing runtime paths and keep scanners working as-is.
3. Extract scanner business logic into a reusable service module (no formula changes).
4. Route UI and bot to shared scanner service to reduce drift.
5. Add structured handoff writes without replacing current DB tables yet.
6. Add PM postmortem and ticket contracts, then wire planner read-only synthesis.
7. Migrate persistence incrementally table-by-table with backfill scripts.

## Safety Guardrails
- Do not delete core engine/model files.
- Do not rewrite `QuantStrategy` wholesale.
- Prefer additive changes and adapter layers.
- Keep behavior-equivalent wrappers before any logic movement.
