# Swing Main - Current Operating System

Last updated: 2026-06-24

This repository is a quant trading research and execution-support system for KR/US swing and intraday candidate generation. It contains scanners, model-lane producers, multi-agent traces, Streamlit and Discord operator surfaces, Supabase/local persistence, and forward-validation ledgers.

The current KR research direction has shifted from daily stock picking toward intraday path and entry-quality models. The strongest current deployment candidate is the KOSDAQ 15:00 VWAP-guard `KR_INTRADAY_3D_T5` lane.

## Start Here

- [Current Operations Manual](docs/operations/CURRENT_OPERATIONS_MANUAL_2026-06-24.md)
- [Backend And Data Architecture](docs/architecture/BACKEND_DATA_ARCHITECTURE_2026-06-24.md)
- [Frontend, Discord, And Design Structure](docs/architecture/FRONTEND_OPERATOR_UI_2026-06-24.md)
- [System Analysis](docs/architecture/SYSTEM_ANALYSIS_2026-06-24.md)
- [Model Trading Strategies](docs/research/MODEL_TRADING_STRATEGIES_2026-06-24.md)

Older docs remain useful as history, but some contain retracted daily-edge conclusions. Use the current docs above as the operating baseline.

## Current Live Lanes

| Lane | Market | Mode | Entry | Target | Status |
|---|---|---|---|---|---|
| SWING ensemble | KOSPI/KOSDAQ | `SWING` | latest/next session daily contract | `ft_5_5`, 5D | live-forward, modest daily edge |
| KOSPI intraday | KOSPI | intraday model lane | close-buy/full-session minute context | 3D +5% touch | live-forward |
| KOSDAQ intraday VWAP guard | KOSDAQ | `INTRADAY` | 15:00 minute-confirmed | 3D +5% touch | live-forward, current best intraday lane |

Observation or disabled lanes include KOSPI NORMAL PEAD shadow, first-touch down shadow, KOSPI 09:05 5D intraday shadow, KOSDAQ tail guard research, and KIS touch5/dd10 research.

## Main Commands

Daily operations:

```bash
multi_agent/tools/run_daily_ops.sh
```

Automatic KR scans:

```bash
python3 multi_agent/tools/run_kr_daily_auto_scans.py
```

KIS operational scan:

```bash
python3 -m multi_agent.tools.run_kis_operational_kr_scan --market KOSDAQ --scan-mode INTRADAY
```

KOSDAQ intraday VWAP guard producer:

```bash
KIS_ENABLE_LIVE_CALLS=1 python3 multi_agent/tools/report_kosdaq_intraday_vwap_guard.py --min-liq 30 --tradeability-liq 100 --daily-context-source cache
```

Streamlit UI:

```bash
streamlit run app.py
```

Discord bot:

```bash
python3 multi_agent/tools/discord_bot.py
```

## Core Architecture

The scanner pipeline:

1. Acquires market data through KIS/FDR/fallback sources.
2. Builds scanner candidates with explicit `scan_mode`.
3. Writes scanner handoff into local short-term memory.
4. Runs aggregation, backtest diagnostics, market/news context, planner, and postmortem traces.
5. Generates Top Deep reports.
6. Persists local artifacts, Supabase rows, runtime artifacts, scan-universe snapshots, and post-scan outcome ledgers.

The model-lane producer path:

1. Scores a fixed validated model lane.
2. Writes its own JSON/MD report and JSONL ledger.
3. Resolves pending forward outcomes after the horizon passes.
4. Optionally routes picks directly to `market_scan_results` and `scan_deep_reports`.

These two paths coexist. Do not assume every live pick went through the same planner gate.

## Data Locations

Repo-local operational state:

- `runtime_state/artifacts/RUN-*`
- `runtime_state/shared_working/RUN-*`
- `runtime_state/reports/*`
- `runtime_state/long_term/*`

External research cache:

- `~/research_cache/px_long.parquet`
- `~/research_cache/intraday/{code}.parquet`
- `~/research_cache/intraday_3d_panel.parquet`
- other research stores: flow, DART, fund, PEAD, shares

Supabase tables used by the app:

- `market_scan_results`
- `scan_deep_reports`
- `post_scan_outcome_ledger`
- `runtime_artifacts`
- `scan_universe_snapshots`
- `agent_realized_outcomes`

## Current Important Caveat

KOSDAQ intraday VWAP guard is deployed through its producer and direct Supabase routing, but the existing model-lane consumer whitelist currently contains only:

```python
{"swing_ensemble", "kospi_intraday"}
```

That means `/signals` and dedicated model-lane interpretation may omit or generically render the KOSDAQ intraday bucket until the consumer whitelist/profile is extended. Top Deep and Archive can still display the direct rows.

## Development Rules

- Keep scanner, backend, UI, and planner logic separated.
- Do not bury engine logic in Streamlit-only files.
- Use Beads for task tracking.
- Preserve run artifacts and structured traces for every recommendation-worthy candidate.
- Treat missing data as missing; do not fabricate prices, flow, or stop values.
- Keep `SWING` and `INTRADAY` separate from source to storage to UI.
- Do not treat old model files as live status. Live status comes from producer flags, daily ops, and route code.

## Issue Tracking

Use the project shortcut:

```bash
scripts/issue status
scripts/issue start <id>
scripts/issue end <id> "reason"
scripts/issue sync
scripts/issue log
```

Shared Claude/Codex coordination thread:

```bash
bd comments swing-main-0to
bd comment swing-main-0to "[Codex] ..."
```

## Validation Discipline

A model is not production-mature because a headline win rate is high. It needs:

- fixed entry and exit contract
- explicit cost and liquidity assumptions
- corrected same-day or liquidity/size-matched control
- walk-forward/OOS evidence
- forward ledger
- enough picks, days, and months
- web/archive/Discord/DB consumer parity

Current priority is forward-validating and operationally hardening the KOSDAQ intraday `KR_INTRADAY_3D_T5` lane.
