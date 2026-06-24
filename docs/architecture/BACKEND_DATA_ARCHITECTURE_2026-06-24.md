# Backend And Data Architecture - 2026-06-24

This document maps what the backend does, what data it uses, how data is collected and normalized, where it is stored, and how it is used by models, scans, UI, Discord, and validation.

## Evidence Files Read

- Execution: `multi_agent/tools/run_daily_ops.sh`, `multi_agent/tools/run_kr_daily_auto_scans.py`, `multi_agent/tools/run_kis_operational_kr_scan.py`.
- Pipeline: `multi_agent/workflows/non_ui_scan_pipeline.py`, `multi_agent/workflows/legacy_export.py`, `multi_agent/workflows/legacy_orchestration.py`.
- Scanner: `modules/scanner_runtime.py`, `modules/scanner_services.py`, `modules/scan_policy.py`, `modules/strategy_family_policy.py`.
- KIS and market data: `modules/kis_openapi.py`, `modules/kis_operational_adapter.py`, `modules/kis_operational_prefilter.py`, `modules/market_data.py`, `docs/operations/KR_INTRADAY_DATA_ADAPTERS.md`.
- Model producers: `multi_agent/tools/report_swing_ensemble.py`, `multi_agent/tools/report_kospi_intraday_swing.py`, `multi_agent/tools/report_kosdaq_intraday_vwap_guard.py`.
- Intraday model code: `modules/kosdaq_intraday_vwap_guard.py`, `modules/intraday_candidate_registry.py`.
- Persistence: `modules/db_schema.py`, `modules/db_manager.py`, `modules/scan_persistence.py`, `modules/runtime_artifact_store.py`, `modules/post_scan_outcome_ledger.py`, `modules/top_deep_report.py`.
- Memory/artifacts: `multi_agent/storage/memory_layers.py` by usage in scan pipeline, `docs/migration/RUNTIME_ARTIFACT_POLICY.md`.
- Current research artifacts under `runtime_state/reports/learning`.

## High-Level Backend Shape

The backend has five overlapping responsibilities:

1. Market data acquisition and normalization.
2. Scanner candidate generation.
3. Multi-agent trace generation and planner decisioning.
4. Model-lane production and forward ledgers.
5. Persistence, archive, and validation refresh.

The system has two main execution styles:

- Full scanner pipeline: KIS or legacy market scan, then scanner/aggregation/backtest/market/planner handoffs, Top Deep reports, archive persistence, runtime artifacts.
- Model-lane producer: a focused report script scores a validated model lane, writes its own ledger/report, and can directly route picks to `market_scan_results` plus `scan_deep_reports`.

These two styles coexist. The docs and UI must not pretend every live pick came through the same planner pipeline.

## Data Sources

### KIS Open API

KIS is the preferred KR live source. `modules/kis_openapi.py` defines endpoints for:

- OAuth token and websocket approval.
- Domestic quote.
- Daily bars.
- Same-day minute bars.
- Historical daily minute bars.
- Asking price and conclusion tape.
- Current and daily investor flow.
- Foreign/institution ranking and market investor time series.
- Volume, fluctuation, volume-power, expected up/down rankings.
- VI status.
- News title.
- Industry current and daily bars.

KIS live calls are guarded by `KIS_ENABLE_LIVE_CALLS=1`. The adapters can be imported without making real network calls.

### FinanceDataReader

FDR is used for:

- Daily stock history in `report_swing_ensemble.py`.
- KOSPI/KOSDAQ index context in producer scripts.
- KOSPI intraday producer daily context and pending-resolution reads.
- Research cache generation outside the repo.

FDR is useful but not treated as the only benchmark source after the benchmark-artifact corrections.

### Research Cache

The current research cache lives outside the repo at:

```text
~/research_cache
```

Important files and directories:

- `px_long.parquet`: daily long panel with code, date, market, price features, labels, and liquidity.
- `flow`, `dart_ann`, `dart_events`, `fund`, `pead_surprise`, `shares`: research-side factor stores mentioned in the Claude/Codex handoff.
- `intraday/{code}.parquet`: raw 1-minute OHLCV store.
- `intraday_3d_panel.parquet`: 3D intraday panel used by KOSPI intraday training path.

Current verified intraday raw store from the collaboration brief:

- 2,594 tickers.
- 150,038,731 one-minute bars.
- Date window: 2025-07-01 to 2026-06-19.
- Median 237 trading days per ticker.
- Out-of-hours leakage 0.
- Size about 2.40GB.
- KIS minute-bar retention is about one year, so deeper history must accumulate from now.

This raw store is separate from scan-DB intraday readiness rows. Do not mix the two when interpreting coverage metrics.

### Supabase

Supabase is the primary shared DB surface when credentials are configured. Core tables used in code:

- `market_scan_results`: archive-level scan and model-lane rows.
- `scan_deep_reports`: detailed Top Deep rows consumed by web/Discord.
- `post_scan_outcome_ledger`: run/ticker outcome ledger.
- `runtime_artifacts`: JSON/text artifacts by `run_id` and `artifact_key`.
- `scan_universe_snapshots`: emitted and rejected universe rows for future learning.
- `agent_realized_outcomes`: realized outcome store referenced in DB manager.

The DB layer is schema-drift tolerant. `modules/db_manager.py` filters payloads to existing columns and has local extension column lists for newer fields.

## Data Normalization

### Market Data Normalization

`modules/market_data.py` maps symbols and normalizes OHLCV frames:

- KR suffix `.KS` and `.KQ` are converted to bare FDR/KIS codes where needed.
- Index aliases map to KIS/FDR index codes, including KS11 and KQ11.
- OHLCV columns are normalized to `Open`, `High`, `Low`, `Close`, `Volume`.
- Timezone-aware indexes are made naive for downstream pandas compatibility.

### KIS Normalization

`modules/kis_operational_adapter.py` converts KIS payloads into internal contracts:

- `normalize_kis_daily_bars`
- `normalize_kis_minute_bars`
- rank membership normalization
- VI status normalization
- news title normalization with symbol-scope filtering
- stock info normalization
- quote fields and investor-flow fields for scanner sidecars

`kis_intraday_input_hour()` chooses a KIS minute input hour based on KST time, or `AG_KIS_INTRADAY_INPUT_HOUR` when overridden.

### KIS Operational Prefilter

`modules/kis_operational_prefilter.py` builds a live KR candidate universe from KIS rankings and quote signals:

- volume rank
- fluctuation rank
- volume power rank
- VI status
- quote activity
- optional investor flow

It scores candidates using rank points, quote score components, and flow score components. It can exclude management/risk/warning/halt/overheated names depending on config.

## Scanner Pipeline

The non-UI pipeline entrypoint is:

```python
multi_agent.workflows.non_ui_scan_pipeline.run_non_ui_scan_pipeline()
```

Major steps:

1. Resolve market, scan mode, profile defaults, and ticker universe.
2. Build run context with a `RUN-*` id.
3. Load macro context and market gate.
4. Resolve market intelligence and news adjustment.
5. Run parallel scanner workers through `scan_symbol_with_retry`.
6. Sort passed rows by `Decision Score` and `Antigrav`.
7. Write `legacy_scan_results.json` into local short-term memory.
8. Run `OrchestratorAgent`.
9. Run legacy orchestration to generate scanner, aggregation, backtest, market context, planner, diagnostics, and postmortem artifacts.
10. Generate Top Deep reports.
11. Write post-scan outcome ledger.
12. Write raw scan results and CSV into artifact store.
13. Write scan integrity artifacts.
14. Write daily summary and stale fallback alert.
15. Persist `scan_universe_snapshots`.
16. Persist standard runtime artifacts to Supabase.

The scan mode is explicit and must remain explicit:

- `SWING`: daily swing scanner and SWING model lanes.
- `INTRADAY`: intraday scanner candidates and intraday model lanes.

## Scanner Candidate Logic

### `evaluate_app_kr_candidate`

This is the KR SWING scanner candidate evaluator. It requires:

- Signal column exists and recent signal hits pass.
- ML inference is real and not a fallback dummy.
- Baseline WR/PF filter.
- KR market policy and hard filters.
- Precision gate.
- Sector gate.
- ML probability and surge tag computation.
- Profile, rank, theme, context, segment, continuation, and quant overlays.
- KIS sidecar fields where available.

It emits both UI rows and DB payloads with scanner timeframe profile, KR universe role, flow fields, theme context, leader metrics, expected edge fields, target/stop/hold, and model trace fields.

### `evaluate_intraday_candidate`

This is the generic scanner `INTRADAY` evaluator. It uses recent OHLCV bars from `QuantStrategy` and computes:

- liquidity and price filters
- EMA trend
- 3-bar breakout
- session open, previous close, intraday return, day return
- ATR-based target/stop
- news adjustment
- ML probability when available
- market gate penalty
- theme overlay
- expected edge profile
- KR universe role
- KIS sidecar fields for KR

For KR intraday scanner candidates, current default filters include:

- minimum KR price `1000`
- `AG_INTRADAY_KR_MIN_VOLUME` default `20000`
- KOSPI min turnover default `700,000,000`
- KOSDAQ/KR min turnover default `300,000,000`

This generic scanner is not the same as the new KOSDAQ `KR_INTRADAY_3D_T5` live model producer.

## Model-Lane Producers

### SWING Ensemble

File: `multi_agent/tools/report_swing_ensemble.py`

Backend behavior:

- Trains LGBM, XGB, and ExtraTrees on trailing `px_long.parquet`.
- Uses price-only features.
- Labels `ft_5_5`.
- Scores both KOSPI and KOSDAQ.
- Requires recent 20D value traded `>= min_liq * 1e8`.
- Emits top probability percentile per market.
- Writes `runtime_state/reports/experimental/swing_ensemble_ledger.jsonl`.
- Writes latest JSON/MD report.
- If production is enabled, writes market scan rows and direct Top Deep rows via `_route_live`.

### KOSPI Intraday

File: `multi_agent/tools/report_kospi_intraday_swing.py`

Backend behavior:

- Trains a 3-model ensemble on `~/research_cache/intraday_3d_panel.parquet` and daily context from `px_long.parquet`.
- Fetches current/full-session KIS minute bars.
- Builds intraday features such as day return, open-range return, morning/afternoon return, late 30-minute return, day range, close location, close VWAP distance, up-minute fraction, intraday volatility, acceleration, gap, and volume z-score.
- Uses daily features such as returns, moving-average distances/slopes, RSI, distance to highs/lows, Bollinger percent, ATR, volume ratio, turn z-score, OBV slope, CMF, index momentum and volatility.
- Filters `liq>=100억`, `close_vwap>=0`, and `idx_vol20>=8`.
- Emits top2.
- Writes `kospi_intraday_swing_ledger.jsonl`.
- Routes live through the SWING `_route_live` helper with bucket `kospi_intraday`.

### KOSDAQ Intraday VWAP Guard

Files:

- `modules/kosdaq_intraday_vwap_guard.py`
- `multi_agent/tools/report_kosdaq_intraday_vwap_guard.py`

Backend behavior:

- Loads stored model bundle `models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl`.
- Uses `MODEL_FEATURES = INTRADAY_FEATURES + DAILY_PREV_FEATURES`.
- Intraday features stop at 15:00: open gap, pre-entry return/high/low/range, close location, VWAP distance, pre-entry traded value versus previous liquidity.
- Daily previous features include returns, moving-average distances, RSI, acceleration, consecutive up days, distance to highs, Bollinger fields, ATR, volatility, volume ratio/trend, turn z, OBV slope, CMF, index momentum, and index volatility.
- Universe comes from `px_long.parquet` KOSDAQ recent median liquidity.
- Daily context can come from research cache or KIS.
- Minute bars come from KIS same-day or historical daily minute endpoints.
- Selection policy from model bundle defaults to `p_cal>=0.80`, `pre_vwap_dist_pct>=0`, top2.
- Minimum liquidity floor default is `30억`; tradeability lane is `100억`.
- Writes `kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl`.
- Resolves pending rows with KIS daily bars after enough days pass.
- Routes live by direct writes to `market_scan_results` and `scan_deep_reports`.

## Persistence Architecture

### `market_scan_results`

Single source mapping is `modules/db_schema.py::SCAN_RESULT_COLUMNS`. New scanner fields should be added there once. This prevents silent column drops.

Important persisted fields:

- identity: ticker, stock name, market, market type, scan mode
- scanner scores: alpha, tech, ML, prob clean, whale, decision, conviction
- flow windows and investor flow fields
- strategy: strategy family, run ID, priority rank, decision, bucket, selection lane, source ref
- return/outcome fields across 10m, 30m, 1h, close, 1D, 3D, 5D, 7D, 14D, 30D
- path labels: target before stop, stop before target, ordered entry, MFE/MAE fields
- model trace: phase25 variants/probs/AUC/OOS metrics, inference errors
- expected edge fields
- regime fields
- theme context and leader metrics
- feature snapshot and routing path

DB upsert behavior:

- If `run_id+ticker` exists, merge into the authoritative same-run row.
- Delete shadow duplicates.
- If no same-run row exists, delete same-day duplicate for same ticker when run_id absent.
- Incomplete feature rows can be quarantined unless explicitly allowed.

### `scan_deep_reports`

Generated by `modules/top_deep_report.py` or model-lane direct routers. It is the detailed candidate surface for web and Discord.

Fields include:

- report identity and version
- ticker, stock name, market, run id
- scan mode and strategy family
- rank, decision, decision bucket, signal label
- analysis section and rank
- entry/target/stop/hold trade plan
- selection thesis and selection alignment
- candidate interpretation
- realized expectancy admission
- policy metadata and readiness contracts

### `runtime_artifacts`

`modules/runtime_artifact_store.py` persists local JSON/MD/TXT/CSV artifacts by:

- `run_id`
- `artifact_key`
- `artifact_type`
- market
- scan mode
- source
- source path
- payload or content text
- checksum
- metadata

Standard artifact keys include:

- `scan_pipeline_summary`
- `raw_scan_results`
- `observed_factor_snapshots`
- `scan_integrity_report`
- `scanner_handoff`
- `aggregation_handoff`
- `backtest_handoff`
- `market_context_handoff`
- `planner_handoff`
- `profile_diagnostics`
- `realized_outcomes`
- `post_scan_outcome_ledger`
- `top_deep_reports`

### `scan_universe_snapshots`

`modules/scan_persistence.py::_persist_scan_universe_snapshot` builds emitted and rejected run rows for KR scans. Forward returns are intentionally NULL at scan time. They are filled later by outcome backfills.

### Local `runtime_state`

`runtime_state/` is operational state, not source code. Per `docs/migration/RUNTIME_ARTIFACT_POLICY.md`, generated run directories, caches, daily reports, archive datasets, and large generated artifacts should not be treated as normal source files. Curated small summaries may be tracked when they are release evidence.

## Multi-Agent Memory Layers

The conceptual layers required by project instructions are implemented through filesystem memory use:

- Local short-term memory: per-agent/run temporary input such as `legacy_scan_results.json`.
- Shared working memory: `runtime_state/shared_working/RUN-*`, containing handoffs and planner outputs.
- Long-term memory: `runtime_state/long_term`, used for persistent caches and value-chain/theme/profile state.
- Artifact store: `runtime_state/artifacts/RUN-*`, containing raw scan results, summaries, CSVs, and integrity reports.

The non-UI pipeline and web scan persistence both write the same minimum artifact contract so Archive can recover even if Supabase is unavailable.

## Outcome And Validation Pipeline

Daily ops refreshes:

- realized outcomes
- outcome return metrics
- scanner full returns
- archive learning datasets
- outcome conversion reports
- contaminated run tags
- post-scan validation reports
- paper-trade ledgers
- release gates
- drift alerts
- model foundation gate

Model-lane producers also keep their own ledgers:

- `swing_ensemble_ledger.jsonl`
- `kospi_intraday_swing_ledger.jsonl`
- `kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl`
- `kospi_normal_pead_shadow_ledger` via report script
- `firsttouch_down_shadow` ledger when enabled

These ledgers are not interchangeable. Each has its own label, entry price, horizon, and cost semantics.

## Known Backend Risks

1. Supabase PostgREST timeout is tracked in `swing-main-yk25`; DB backfills can hang or fail.
2. KOSDAQ intraday is live-routed but not included in the current `MODEL_VALIDATED_LANES` whitelist. That affects `/signals` and dedicated model-lane interpretation.
3. KOSPI intraday producer trains in-script on each run. That is reproducible but operationally heavier and less artifact-stable than the KOSDAQ stored bundle.
4. Several older model artifacts remain in `models/`, including retired/inverted phase25 intraday variants. Do not infer live status from file existence.
5. Research cache lives outside repo. It is necessary for current producers. Operational docs must always state that dependency.
6. Intraday raw store covers about one year and one dominant recent regime. Strong intraday evidence still needs forward accumulation.
