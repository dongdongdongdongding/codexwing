# Code Audit (2026-04-10)

## Scope
- Repository-wide Python syntax sweep
- High-risk logic review on scanner, planner, persistence, and market-intelligence paths
- Validation context anchored to KOSPI/KOSDAQ upward-selection objective

## Automated Sweep
- Python files checked: 101
- Syntax/compile errors: 0
- Broad `except Exception` occurrences: 346
- Largest Python files:
  - `modules/quant_analysis.py` (3856)
  - `modules/scanner_services.py` (2733)
  - `app.py` (2514)
  - `multi_agent/workflows/legacy_orchestration.py` (1857)
- Non-standard JSON numeric values observed in persisted artifacts:
  - `runtime_state/shared_working/RUN-6E60F98F/market_context_handoff.json`
  - `runtime_state/shared_working/RUN-42B98BAA/market_context_handoff.json`
  - `runtime_state/reports/validation/contaminated_runs_all.json`
  - many additional `scanner_handoff.json` / `market_context_handoff.json` files

## Fixed In This Turn

### 1. Strict JSON serialization
- File: `multi_agent/contracts/serialization.py`
- Change:
  - sanitize `NaN` / `inf` / `-inf` to `null`
  - enforce `allow_nan=False`
- Reason:
  - machine-readable artifacts must be strict JSON for audits and downstream tooling

### 2. Scanner DB client reuse
- File: `modules/scanner_runtime.py`
- Change:
  - introduced shared cached `DBManager`
  - removed repeated per-symbol client construction in scan path
- Reason:
  - KRX bulk scans should not reconnect/create a DB client for each symbol

### 3. Safer DB upsert dedupe
- File: `modules/db_manager.py`
- Change:
  - when `run_id` exists, delete only `(ticker, run_id)` rows before insert
  - same-day ticker-wide delete now only happens as fallback
- Reason:
  - previous logic could erase same-day history from other runs and contaminate validation archives

## Findings

### P0. Persisted JSON artifacts were not standards-compliant
- File: `multi_agent/contracts/serialization.py:8-11`
- Symptom:
  - `json.dump(...)` used default `allow_nan=True`
- Evidence:
  - persisted artifacts include raw `NaN` values in runtime and validation JSON
- Impact:
  - breaks strict machine readability
  - creates parser incompatibility across tools/languages
  - weakens auditability and model/ops pipelines

### P0. Same-day scan archives could be overwritten across runs
- File: `modules/db_manager.py:311-321`
- Symptom:
  - delete-then-insert used `(ticker + created_at >= today_start)` instead of run-scoped dedupe
- Impact:
  - same-day repeated runs for the same ticker could silently erase earlier scan rows
  - historical validation and learning datasets become biased or incomplete

### P1. Planner action and exported score semantics diverge
- File: `multi_agent/agents/planner_runtime.py:347-366`
- File: `multi_agent/agents/planner_runtime.py:400-456`
- Symptom:
  - planner demotes `decision` through multiple gates
  - exported `decision_score` remains scanner-side score
- Observed effect:
  - latest runs can show `decision=OBSERVE` with very high `decision_score`
- Impact:
  - PM/operator sees contradictory recommendation state
  - ranking validation can over-trust a score that no longer matches the final action

### P1. Intraday candidate path hard-rejects liquidity before market leadership is fully considered
- File: `modules/scanner_services.py:297-329`
- Symptom:
  - intraday candidates are rejected on absolute price/volume/turnover thresholds before leadership, theme-route, or flow persistence can rescue them
- Impact:
  - early-stage movers and smaller but accelerating names are lost before contextual evaluation
  - system becomes over-biased toward conservative filtering rather than upward-move capture

### P1. KRX market-leader bypass is far too narrow
- File: `modules/scanner_services.py:1475-1486`
- File: `modules/scanner_services.py:1490-1497`
- Symptom:
  - market leader detection requires only:
    - `ml_prob >= 65`
    - volume ratio >= 1.5
    - green candle
  - baseline filter then bypasses only this narrowly defined subset
- Impact:
  - genuine money-flow leaders without high model probability are still rejected
  - system ties "leadership" too tightly to existing model confidence, which is exactly what needs to be challenged when the model is missing movers

### P1. Precision gate is structurally tuned for suppression, not profit maximization
- File: `modules/scanner_services.py:1044-1057`
- File: `modules/scanner_services.py:1190-1248`
- Symptom:
  - gate defaults are framed as precision-first hard thresholds
  - `T3_LOW_ML_SUPPORT`, `TREND_MISMATCH`, and low-clean-prob rejections trigger before broader upward-selection logic
- Impact:
  - scanner optimizes for lower candidate count and cleaner-looking output
  - upward movers with imperfect early-model support are systematically removed

### P1. KR swing path layers too many serial hard gates before final ranking
- File: `modules/scanner_services.py:2356-2618`
- Symptom:
  - one symbol may be eliminated by:
    - baseline filter
    - market policy
    - hard filter
    - sector gate
    - precision gate
    - only then reach final score composition
- Impact:
  - true positives are lost before final ranking has a chance to compare them
  - debugging why a winner was missed becomes difficult because suppression is distributed across many gates

### P1. Market intelligence "leader" selection is not actually selecting leaders
- File: `modules/market_intelligence.py:650-691`
- Symptom:
  - `_dynamic_kr_market_leaders(...)` returns the first tickers from the market universe list
  - there is no ranking by turnover, flow, relative strength, or theme breadth in that function
- Impact:
  - market/news context may be built from arbitrary universe head items rather than actual session leaders
  - downstream context intelligence can become directionally wrong or diluted

### P1. Broad exception swallowing is excessive in core engine paths
- Examples:
  - `modules/quant_analysis.py` (54 occurrences)
  - `modules/scanner_services.py` (28)
  - `modules/db_manager.py` (24)
  - `modules/market_intelligence.py` (21)
  - `app.py` (17)
- Impact:
  - failures can silently degrade scores or candidate coverage instead of surfacing as structured warnings
  - hard to distinguish "no signal" from "evaluation broke"

### P2. DB client creation inside hot scan path was wasteful
- File: `modules/scanner_runtime.py:103-107`
- File: `modules/scanner_runtime.py:185-188`
- File: `modules/scanner_runtime.py:211-214`
- Symptom:
  - scanner instantiated `DBManager()` per symbol path
- Impact:
  - unnecessary connection/client overhead during large scans
  - higher latency and greater chance of intermittent DB failure under load
- Status:
  - fixed in this turn via cached singleton reuse

### P2. DB column discovery is unreliable on empty tables
- File: `modules/db_manager.py:25-47`
- Symptom:
  - `_get_table_columns(...)` infers schema from `select('*').limit(1)`
  - empty table returns no columns and disables filtering
- Impact:
  - payload filtering becomes inconsistent depending on table state
  - schema drift or typos can slip through silently in new environments

### P2. Review and validation datasets still show current ranking underperforming for upward capture
- Files:
  - `runtime_state/reports/validation/kr_top_mover_capture_kospi.md`
  - `runtime_state/reports/validation/kr_top_mover_capture_kosdaq.md`
- Evidence:
  - KOSPI daily top5 precision for 10% movers: `0.00%`
  - KOSDAQ daily top5/top10/top20 precision for 10% movers: `0.00%`
  - stronger segments are often `SWING + picked/watchlist`, not current top intraday ranking
- Impact:
  - current top-rank order is not aligned with the objective of selecting rising names and avoiding losers

## Strategic Interpretation
The repository has solid observability and growing validation depth, but the active selection engine is still too suppression-heavy.

The dominant pattern is:
- hard filters fire early
- leadership is defined too narrowly
- planner/action semantics drift from raw scores
- artifacts/history can be corrupted by serialization or dedupe behavior

## Recommended Next Moves
1. Split `scanner_score_raw` from `planner_action_score` and rank on the action-aware score.
2. Replace static intraday liquidity hard fails with staged leader/flow exceptions.
3. Redefine KRX leader detection around turnover acceleration, theme breadth, and foreign/institutional flow, not just `ml_prob`.
4. Audit broad `except Exception` paths and convert the most important ones into structured warnings.
5. Rebuild market-intelligence leader selection from ranked session leaders instead of universe order.
6. Expand validation to include:
   - close/1d/3d positive-hit rate
   - loser-avoidance rate
   - top-N positive selection precision
   - basket return with 98% confidence intervals
