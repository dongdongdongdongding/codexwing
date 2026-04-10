# PM Planner Report

## Scope
- scanner prediction accuracy review
- KOSDAQ zero-result diagnosis
- operational stability hardening plan

## Constraint
Perfect prediction accuracy and perfect operational stability cannot be guaranteed in live markets.
The system can, however, be made materially safer, more auditable, and more robust against known failure modes.

## Findings
1. Model stack health improved after restoring Phase18.2 + Phase25 + universal fallback.
2. Backtest signal ranking improved versus legacy decision score, but live 70%+ win-rate is not yet proven.
3. KOSDAQ zero-result was not primarily a prod-threshold issue.
4. The main failure was malformed scanner input universe: newly listed names, SPAC-like names, non-standard codes, and insufficient-history symbols dominated the first scan tranche.
5. After universe hygiene was added, the top reject reason shifted from `MISSING_ANTIGRAV_SCORE` to strategy-level reasons (`KR_HARD_FILTER_FAIL`, `KR_SIGNAL_WINDOW_FAIL`, `PRECISION_GATE_RED_MARKET`).
6. This means the system has moved from upstream data-quality failure toward intentional strategy filtering.

## Evidence
- Phase25 retrain: AUC 0.5690
- Legacy Decision Score Top-20: avg -2.16%, win>0 35.0%
- Phase25 Top-20: avg +3.53%, win>0 60.0%
- KOSDAQ run before universe hygiene:
  - prod/dev both 0 results
  - top reject = `MISSING_ANTIGRAV_SCORE`
- KOSDAQ run after universe hygiene:
  - 0 results remained in RED market
  - top reject = `KR_HARD_FILTER_FAIL`
  - liquidity failures dropped sharply

## Planner Decision
- Treat the KOSDAQ 0-result issue as partially resolved.
- Root cause A (broken input universe) is mitigated.
- Root cause B (bear-market hard filtering) remains active by design and should not be bypassed blindly.

## Plan
1. Stabilize scanner input universe for KOSPI/KOSDAQ.
2. Keep bear-market hard filters intact unless evidence supports selective relaxation.
3. Accumulate realized outcomes and re-run Phase25 on stronger labels.
4. Promote blended model probability and clean-hit probability into ranking/audit outputs.
5. Add a dedicated scanner diagnostics report for KR reject-reason shifts.

## Tickets
- TKT-PM-KRX-UNIVERSE: completed in this turn
- TKT-PM-KR-DIAGNOSTICS: pending
- TKT-PM-LIVE-LABELS: pending
