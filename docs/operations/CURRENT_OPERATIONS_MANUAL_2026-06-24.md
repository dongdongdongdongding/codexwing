# Current Operations Manual - 2026-06-24

This document is the operator-facing map of the current system. It records what the code actually runs today, which model lanes are live, which lanes are observation-only, how to use the scanner, and where the evidence is stored.

## Evidence Files Read

- `AGENTS.md` instructions supplied in the session.
- Beads: `bd list --json`, `bd comments swing-main-0to`, `scripts/issue log`, `bd show swing-main-hbt8 --json`.
- Daily execution: `multi_agent/tools/run_daily_ops.sh`, `multi_agent/tools/run_kr_daily_auto_scans.py`, `multi_agent/tools/run_kis_operational_kr_scan.py`.
- Scan pipeline: `multi_agent/workflows/non_ui_scan_pipeline.py`, `modules/scanner_runtime.py`, `modules/scanner_services.py`.
- Live model producers: `multi_agent/tools/report_swing_ensemble.py`, `multi_agent/tools/report_kospi_intraday_swing.py`, `multi_agent/tools/report_kosdaq_intraday_vwap_guard.py`, `multi_agent/tools/report_kospi_normal_pead_shadow.py`, `multi_agent/tools/report_firsttouch_down_shadow.py`.
- Intraday registry and KOSDAQ model: `modules/intraday_candidate_registry.py`, `modules/kosdaq_intraday_vwap_guard.py`.
- Consumer surfaces: `app.py`, `ui/*`, `modules/discord_integration/*`, `modules/candidate_interpretation.py`, `modules/operational_candidate_scoring.py`.
- Storage and ledgers: `modules/db_schema.py`, `modules/db_manager.py`, `modules/scan_persistence.py`, `modules/runtime_artifact_store.py`, `modules/post_scan_outcome_ledger.py`.
- Current research evidence: `runtime_state/reports/learning/intraday_claude_codex_synthesis_latest.md`, `runtime_state/reports/learning/intraday_3d_t5_model_training_latest.md`, `runtime_state/reports/learning/intraday_3d_t5_monthly_failure_diagnosis_latest.md`, `runtime_state/reports/learning/intraday_3d_t5_return_optimized_latest.md`, `docs/research/RESEARCH_JOURNEY_2026-06.md`.

## Operating Purpose

The system is a Korean and US quant research plus execution-support system. The current KR production focus is not generic "high score means buy". The current production direction is:

- Keep the legacy scanner/planner visible for audit and learning.
- Use validated model lanes only when their own forward-touch contract is explicit.
- Separate `SWING` and `INTRADAY` scan modes in storage, UI, Discord, and research ledgers.
- Treat intraday minute-bar models as the main frontier for the operator target: high probability of +5% within a short horizon, with enough liquidity and forward validation.
- Keep every recommendation traceable through scanner reasons, aggregation notes, backtest diagnostics, market/news context, planner decision, and realized outcome placeholders.

The system is not an autonomous brokerage execution engine. It produces candidate signals, trade contracts, validation ledgers, and operator surfaces.

## Current Live Model Lanes

| Lane | Market | Mode | Producer | Default | Main contract | Status |
|---|---|---|---|---|---|---|
| `swing_ensemble` | KOSPI, KOSDAQ | `SWING` | `report_swing_ensemble.py` | ON, production ON | Price-only LGBM/XGB/ExtraTrees ensemble predicts `ft_5_5`; top ~1%; `>=100억`; 5 trading day hold; +5% first-touch target; no tight stop. | Live forward validation. Does not meet 75% goal; validated around 66-67% hit in research note. |
| `kospi_intraday` | KOSPI | `INTRADAY` producer lane, routed with SWING-style helper | `report_kospi_intraday_swing.py` | ON, production ON | Intraday path plus daily-context ensemble predicts 3-day +5% touch; `>=100억`; `close_vwap>=0`; `idx_vol20>=8`; top2; 3D close hold. | Live to validate. KOSPI monthly floor required a volatility guard. |
| `kosdaq_intraday_3d_t5_vwap_guard` | KOSDAQ | `INTRADAY` | `report_kosdaq_intraday_vwap_guard.py` | ON, production ON | Stored LGBM + previous-month isotonic model; 15:00 minute-confirmed entry; `p_cal>=0.80`; `pre_vwap_dist_pct>=0`; top2; `>=30억` main lane and `>=100억` tradeability lane; 3D close hold; target +5% touch. | Current KOSDAQ intraday deployment. Forward ledger is mandatory. |

## Observation And Disabled Lanes

| Lane | Market | Mode | Default | Reason |
|---|---|---|---|---|
| KOSPI NORMAL PEAD shadow | KOSPI | `SWING` | Shadow ON, production OFF | Reclassified as falsification ledger, not an edge claim. The previous KS11/external benchmark narrative was corrected. |
| First-touch down shadow | KR | `SWING` | OFF | Down-regime edge was judged beta/fragile and is not active unless explicitly enabled. |
| KOSPI intraday 09:05 5D candidate | KOSPI | `INTRADAY` | Registry only | Beads `swing-main-ho2w` remains open to wire live forward ledger. |
| KOSDAQ tail guard 5D research | KOSDAQ | `INTRADAY` | Research only | Net/excess positive but win/day-win near 50%, so not an operating promotion candidate. |
| KOSPI cohort Practical/Exception promotion | KOSPI | `SWING` | Beads state stale/in-progress | Older Beads notes mention wired promotion, but later Claude/Codex validation corrected the edge narrative. Do not treat as current production edge without rechecking flags and code. |

## Daily Operations Flow

The operational script is:

```bash
multi_agent/tools/run_daily_ops.sh
```

Current important steps in order:

1. Update realized outcomes.
2. Update outcome return metrics.
3. Backfill scanner full returns.
4. Export scan archive learning dataset.
5. Report outcome conversion and contaminated runs.
6. For each KR market and scan mode, generate daily summaries, outcome health, fallback health, prediction validation, paper-trade ledger, walk-forward release gate, cohort release gate, and stale fallback alert.
7. Generate dynamic theme entry profiles and scan cohort performance.
8. Run operational admission optimizers and exit-policy watch reports.
9. Run regime signal shadow and observation reports.
10. Run KOSPI NORMAL PEAD falsification shadow when enabled.
11. Run live SWING ensemble producer.
12. Run live KOSPI intraday producer.
13. Run live KOSDAQ intraday VWAP-guard producer.
14. Run drift alert and daily model foundation gate.

The current default daily producers are model-lane appenders. They write ledgers and also route live picks to Supabase surfaces when their `*_PRODUCTION` env var is enabled.

## Automatic KR Scan Flow

The automatic scan entrypoint is:

```bash
python3 multi_agent/tools/run_kr_daily_auto_scans.py
```

Default targets:

- `KOSPI/SWING`
- `KOSDAQ/SWING`
- `KOSPI/INTRADAY`
- `KOSDAQ/INTRADAY`

Operational timing:

- `premarket` phase: 08:20 KST. Builds pre-market theme prior only.
- `confirmed` scan phase: after 09:30 KST, normally 09:35. Runs KOSPI/KOSDAQ SWING and INTRADAY scans.

The default scan engine is KIS operational primary with legacy fallback:

- KIS primary env overrides: `AG_KIS_OPERATIONAL_PREFILTER=1`, `AG_KR_MARKET_DATA_PROVIDER=kis_only`, `AG_ENABLE_KIS_MARKET_DATA=1`, `AG_ENABLE_KIS_SIDECAR=1`, `KIS_ENABLE_LIVE_CALLS=1`.
- Legacy fallback can run if KIS primary fails and `AG_KR_DAILY_LEGACY_FALLBACK=1`.
- Legacy shadow can run if `AG_KR_DAILY_LEGACY_SHADOW=1`.

## Manual Commands

Run KIS operational scan for a market:

```bash
python3 -m multi_agent.tools.run_kis_operational_kr_scan --market KOSDAQ --scan-mode INTRADAY
```

Run the KOSDAQ intraday live producer directly:

```bash
KIS_ENABLE_LIVE_CALLS=1 python3 multi_agent/tools/report_kosdaq_intraday_vwap_guard.py --min-liq 30 --tradeability-liq 100 --daily-context-source cache
```

Run SWING ensemble producer:

```bash
python3 multi_agent/tools/report_swing_ensemble.py --top-pct 1.0 --min-liq 100
```

Run KOSPI intraday producer:

```bash
KIS_ENABLE_LIVE_CALLS=1 python3 multi_agent/tools/report_kospi_intraday_swing.py --min-liq 100
```

Launch Streamlit UI:

```bash
streamlit run app.py
```

Discord bot entrypoint:

```bash
python3 multi_agent/tools/discord_bot.py
```

Register Discord slash commands:

```bash
python3 multi_agent/tools/discord_register_commands.py
```

## Important Environment Flags

| Variable | Current operational meaning |
|---|---|
| `AG_SWING_ENSEMBLE_ENABLE` | Enables daily SWING ensemble report step. Default in daily ops is ON. |
| `AG_SWING_ENSEMBLE_PRODUCTION` | Routes SWING ensemble picks to live surfaces. Current producer default is ON. |
| `AG_KOSPI_INTRADAY_ENABLE` | Enables KOSPI intraday producer step. Daily ops default is ON. |
| `AG_KOSPI_INTRADAY_PRODUCTION` | Routes KOSPI intraday picks live. Producer default is ON. |
| `AG_KOSDAQ_INTRADAY_ENABLE` | Enables KOSDAQ intraday VWAP guard step. Daily ops default is ON. |
| `AG_KOSDAQ_INTRADAY_PRODUCTION` | Routes KOSDAQ intraday picks live. Producer default is ON. |
| `AG_KOSDAQ_INTRADAY_MIN_LIQ` | Main KOSDAQ intraday liquidity floor in eok. Daily ops default is `30`. |
| `AG_KOSDAQ_INTRADAY_TRADEABILITY_LIQ` | Tradeability lane floor in eok. Daily ops default is `100`. |
| `AG_KOSDAQ_INTRADAY_DAILY_CONTEXT_SOURCE` | `cache` or `kis`; producer default follows env and daily ops uses cache unless overridden. |
| `AG_KOSPI_NORMAL_PEAD_SHADOW_ENABLE` | Enables PEAD falsification ledger. Default in daily ops is ON. |
| `AG_KOSPI_NORMAL_PEAD_PRODUCTION` | Must remain OFF unless a new validation explicitly changes it. |
| `AG_FIRSTTOUCH_DOWN_SHADOW_ENABLE` | First-touch down observation lane. Default is OFF. |
| `AG_UI_ADVANCED` | Shows advanced Streamlit tabs and tools. Default OFF means only Scanner, Top Analysis, Archive. |
| `AG_SCAN_ARCHIVE_SUPABASE_ENABLED` | Enables archive UI Supabase reads. Default in `app.py` is OFF, with local artifact fallback ON. |
| `AG_RUNTIME_ARTIFACT_WRITE_DB` | Persists run artifacts to Supabase `runtime_artifacts`. Default ON. |
| `KIS_ENABLE_LIVE_CALLS` | Required for real KIS network calls. KIS adapters are safe to import without it. |

## Operator Workflow

1. Let daily ops run and verify the generated reports under `runtime_state/reports/experimental` and `runtime_state/reports/learning`.
2. Use Streamlit Scanner for ad hoc scans. Choose market and `스윙` or `장중`.
3. Use Streamlit Top Analysis for the current Top Deep candidates.
4. Use Archive to replay a run, inspect measured returns, and compare scan-time order with realized outcomes.
5. Use Discord `/signals` for model-lane quick lookup, with the caveat below.
6. Use Discord `/top_deep`, `/archive`, and `/runs` for broader run inspection.
7. Review ledgers before trusting a lane as production-quality. Live routing is not the same as full validated production maturity.

## Current Consumer-Surface Caveat

`modules/operational_candidate_scoring.py` currently defines:

```python
MODEL_VALIDATED_LANES = {"swing_ensemble", "kospi_intraday"}
```

`modules/discord_integration/renderers.py::build_model_signals_embed` filters `/signals` by that whitelist. The KOSDAQ intraday VWAP guard producer routes live with `decision_bucket="kosdaq_intraday_3d_t5_vwap_guard"`, so generic Top Deep/Archive surfaces can receive it, but `/signals` and dedicated model-lane interpretation may not include it until the consumer whitelist/profile is extended.

This is a current documentation and consumer integration gap, not a research conclusion. It should be handled as follow-up if `/signals` is expected to show the KOSDAQ intraday lane.

## Beads State Relevant To Operations

Open or in-progress items that matter operationally:

- `swing-main-hbt8`: this documentation task.
- `swing-main-ho2w`: wire KR_INTRADAY_5D shadow candidate to live forward ledger.
- `swing-main-bxcd`: KOSPI cohort-level release gate, but notes are stale relative to later validation corrections.
- `swing-main-n6u3`, `swing-main-xuy1`, `swing-main-u9sq`, `swing-main-yf9n`: KIS touch5/dd10 and sidecar backfill/research stream.
- `swing-main-yk25`: Supabase authenticated PostgREST timeout can block DB backfill paths.
- `swing-main-30s`: old INTRADAY learning pipeline recovery. It predates the new 3D T5 intraday lane and should not be confused with the current KOSDAQ VWAP guard producer.

Closed recent items that changed current state:

- `swing-main-ardq`: KOSDAQ `KR_INTRADAY_3D_T5` VWAP-guard live scoring ledger.
- `swing-main-g6g8`: KOSDAQ intraday liquidity floor comparison.
- `swing-main-gs7v`: low-month failure diagnosis.
- `swing-main-jhpq`: model-lane consumer surface consistency, but current KOSDAQ lane still needs the caveat above.

## What Counts As Promotion

The current project standard is not "a backtest headline passed". A lane should be considered promotable only when it has:

- Explicit candidate ID and strategy family.
- A fixed entry policy.
- A fixed target/holding/exit contract.
- Liquidity floor and cost assumptions.
- Same-day or liquidity-matched control where applicable.
- Walk-forward or OOS validation.
- Forward ledger with enough picks, enough days, and enough months.
- Consumer-surface parity: web, archive, Discord, DB, and local artifact all show the same decision semantics.
- No unresolved data-routing gap for the lane.

## Immediate Operating Direction

The current operating direction is:

- Keep KOSDAQ intraday 15:00 VWAP guard live-forward and measure it hard.
- Keep KOSPI intraday live-forward but recognize its volatility guard is based on a repaired weak-month diagnosis.
- Keep SWING ensemble live-forward for modest daily price-ML evidence, not for the 75% target.
- Do not resurrect old daily PEAD/regime/Practical/Exception narratives as production edges without the corrected benchmark and cost assumptions.
- Treat new intraday work as `scan_mode=INTRADAY` from source to storage to UI. Do not mix it into SWING gates.
