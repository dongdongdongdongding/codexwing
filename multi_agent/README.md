# Multi-Agent Scaffolding (Additive)

This directory provides a safe, additive foundation for a 5-agent architecture:
- Orchestrator Agent
- Scanner Agent
- Aggregation Agent
- Backtest & Learning Agent
- Market & News Context Agent
- PM Planner Agent

## What this stage does
- Adds typed contracts for handoffs and PM workflows.
- Adds JSON schema drafts for machine-readable exchange.
- Adds memory-layer path contracts (local/shared/long-term/artifact).
- Adds agent runtime builders (`aggregation/backtest/market/planner`) reused by both agent classes and legacy orchestration.
- Adds legacy orchestration bridge that emits downstream handoffs and appends run/postmortem/ticket logs into `runtime_state/long_term/*.jsonl`.
- Scanner Agent can now ingest legacy scanner rows JSON and emit non-placeholder `scanner_handoff.json`.

## What this stage does not do
- It does not replace existing scanner/runtime behavior in `app.py` or `auto_bot.py`.
- It does not delete or rewrite core logic in `modules/quant_analysis.py`.
- It does not modify model files under `models/`.

## Next safe wiring step
Wire a non-UI scan runner that calls shared scanner runtime directly, then feeds
Scanner Agent input without touching `app.py` execution semantics.

## Scaffold pipeline run
- Placeholder (no scanner input):
  - `python3 multi_agent/workflows/scaffold_run.py --market KR`
- With legacy scanner rows JSON:
  - `python3 multi_agent/workflows/scaffold_run.py --market KR --scanner-input /abs/path/results.json`
- Output:
  - scanner + aggregation + backtest + market + planner handoffs
  - `profile_diagnostics.json` (profile gap / zero-streak diagnostics)
  - `run_manifest.json`
  - `postmortem_report.json`
  - `improvement_tickets.json`
  - `realized_outcomes.json`

## Top-Level Orchestrator Run
- Uses a top-level orchestrator to:
  - interpret the user request
  - assign the task to the right agent sequence
  - execute each agent in order
  - validate that required artifacts exist
  - emit one completion report
- Example:
  - `python3 -m multi_agent.workflows.orchestrated_task --market KOSDAQ --request "Analyze current scanner accuracy and generate planner-ready diagnostics."`
  - `python3 -m multi_agent.workflows.orchestrated_task --market KOSDAQ --request "Run full scan pipeline from scanner input." --scanner-input /abs/path/results.json`
- Outputs:
  - `orchestrator_request.json`
  - `orchestrator_report.json`
  - downstream 5-agent handoffs under `runtime_state/shared_working/RUN-*`

## Non-UI scan pipeline run
- Uses shared scanner runtime (`run_parallel_scan`) and then routes to Scanner Agent + orchestration.
- Market data retrieval uses fallback provider chain: `yfinance` -> `FinanceDataReader`.
- Supports execution profiles (`--profile prod|dev`) for gate defaults.
  - `prod`: legacy-safe defaults
  - `dev`: relaxed thresholds for diagnosis/smoke checks
  - explicit `AG_US_*` env vars override profile defaults
  - optional regime-slice knobs:
    - `AG_REAL_BACKTEST_REGIME_PERIOD` (default `2y`)
    - `AG_REAL_BACKTEST_REGIME_MIN_DAYS` (default `20`)
- Example:
  - `python3 -m multi_agent.workflows.non_ui_scan_pipeline --market KOSPI --profile prod --max-scan 100 --max-workers 2`
- Manual ticker subset (skip universe fetch):
  - `python3 -m multi_agent.workflows.non_ui_scan_pipeline --market NASDAQ --profile dev --tickers META,AAPL,MSFT --max-scan 50`
- Outputs:
  - local short-term scanner input: `runtime_state/local_short_term/scanner_agent/RUN-*/legacy_scan_results.json`
  - shared handoffs and PM artifacts: `runtime_state/shared_working/RUN-*/*.json`
  - artifact bundle: `runtime_state/artifacts/RUN-*/`
  - includes filter diagnostics: `reject_reason_counts` (why symbols were dropped)
  - includes profile trace: `execution_profile`, `applied_profile_defaults`, `gate_config`
  - PM postmortem auto-checks profile divergence:
    - when `prod` run is zero-result and recent `dev` baseline is strong, profile-gap tickets are auto-issued
    - when `prod` zero-result streak reaches threshold, planner auto-applies fallback watchlist from recent `dev` run
    - fallback entries include `watchlist_meta` (`risk_label`, `generated_at`, `expires_at`, `horizon_days`, `source_run_id`)
    - fallback recommendations are also written to `realized_outcomes.json` as `decision=FALLBACK_WATCHLIST` for post-run tracking
  - backtest handoff includes sampled real diagnostics + regime-sliced metrics (`regime_sensitivity.slices`)
    - low trade-depth runs are explicitly marked (`status=low_sample|low_sample_no_trades`, warning=`REGIME_BACKTEST_LOW_SAMPLE`)
  - market context uses cache fallback on fetch failures (`runtime_state/long_term/context_cache/*.json`)

## Utility jobs
- Backfill long-term JSONL to DB (safe dry-run):
  - `python3 multi_agent/tools/backfill_agent_memory_to_db.py --dry-run --limit 50`
  - includes profile diagnostics backfill (`runtime_state/long_term/profile_diagnostics/profile_diagnostics.jsonl`)
  - includes outcome health backfill (`runtime_state/long_term/outcome_health/outcome_health.jsonl`)
  - staged backfill(`--limit`) 시 FK 안전을 위해 누락 run summary stub를 자동 보강
- Resolve realized outcomes from `signals.result_3d`:
  - `python3 multi_agent/tools/update_realized_outcomes.py --dry-run --limit-runs 20 --resolve-all`
  - DB lookup health check succeeds when resolution/expiry runs; unresolved pending rows past horizon are marked `EXPIRED`
  - optional override: `--allow-expire-without-db` (use only when DB lookup is intentionally unavailable)
- Report conversion metrics:
  - `python3 multi_agent/tools/report_outcome_conversion.py --limit-runs 200`
  - includes `expired_outcomes` and `closure_rate_pct` (resolved + expired)
- Report scan profile diagnostics (`prod/dev` pass/filter and reject reasons):
  - `python3 multi_agent/tools/report_scan_profile_metrics.py --limit-runs 200 --market NASDAQ`
- Report realized Top-N validation by segment (`market × scan_mode`):
  - `python3 multi_agent/tools/report_segment_topn_validation.py --topn 5 --recent-days 20`
- Report segment-specific rerank overlays against actual Supabase outcomes plus rich local bridge artifacts:
  - `python3 multi_agent/tools/report_segment_overlay_proxy_validation.py --segments KOSPI:INTRADAY,KOSDAQ:SWING --topn 5 --recent-days 20`
- Backfill missing `market_scan_results` feature columns from `shared_working/scanner_handoff` using `run_id+ticker`:
  - `python3 multi_agent/tools/backfill_market_scan_features.py --market KOSDAQ --scan-mode SWING`
- Report profile diagnostics from DB (`agent_profile_diagnostics`):
  - `python3 multi_agent/tools/report_profile_diagnostics_db.py --limit 50 --market NASDAQ`
- Report outcome health from DB (`agent_outcome_health`):
  - `python3 multi_agent/tools/report_outcome_health_db.py --limit 50 --market NASDAQ`
  - DNS/DB failure 시 `runtime_state/long_term/outcome_health/outcome_health.jsonl` fallback 사용
- Report fallback outcome health from DB (`agent_profile_diagnostics` + `agent_realized_outcomes`):
  - `python3 multi_agent/tools/report_fallback_outcome_health_db.py --limit-runs 100 --market NASDAQ`
  - DNS/DB failure 시 자동으로 `runtime_state/shared_working` 기반 local fallback 리포트로 전환
- Build daily summary artifacts (`JSON + Markdown`):
  - `python3 multi_agent/tools/build_daily_agent_summary.py --date 2026-03-31 --market NASDAQ`
  - output: `runtime_state/reports/daily/daily_summary_YYYY-MM-DD.json|md`
  - when previous-day summary exists, `delta_vs_prev_day` is auto-populated
- Build official classification and theme membership artifacts:
  - `python3 multi_agent/tools/build_theme_data_pipeline.py --market ALL`
  - output:
    - `runtime_state/long_term/instrument_master/{KR,US}.json`
    - `runtime_state/long_term/theme_membership/{KR,US}.json`
    - `runtime_state/reports/theme_validation/theme_data_pipeline_{kr,us}.json|md`
- Check stale fallback pending and send webhook alert (optional):
  - `python3 multi_agent/tools/check_stale_fallback_alert.py --market NASDAQ --threshold 3 --dry-run`
  - webhook: `--webhook-url https://...` (or env var below)
- Cron wrapper:
  - `bash multi_agent/tools/run_outcome_updater.sh --dry-run --resolve-all`
  - full daily ops: `bash multi_agent/tools/run_daily_ops.sh`
- Learning automation:
  - nightly refresh: `python3 multi_agent/tools/run_learning_cycle.py --mode nightly`
  - weekly retrain: `python3 multi_agent/tools/run_learning_cycle.py --mode weekly`
  - install launchd schedules: `bash multi_agent/tools/install_learning_launchd.sh`

## Daily Summary Auto-Emit
- non-UI scan pipeline now attempts daily summary generation after each run.
- default enabled via `AG_EMIT_DAILY_SUMMARY=1` (set `0` to disable).
- stale fallback alert hook is also available in pipeline:
  - `AG_STALE_FALLBACK_ALERT_ENABLE=1`
  - `AG_STALE_FALLBACK_ALERT_MIN=3`
  - `AG_STALE_FALLBACK_ALERT_LIMIT_RUNS=200`
  - `AG_STALE_FALLBACK_ALERT_WEBHOOK_URL=<url>` (optional)
  - `AG_STALE_FALLBACK_ALERT_DRY_RUN=1` (payload-only test)

## SQL Templates
- Supabase dashboard query templates:
  - `docs/migration/agent_dashboard_queries.sql`

## Ops Runbook
- outcome updater only: `docs/migration/OUTCOME_UPDATER_CRON.md`
- full daily ops: `docs/migration/DAILY_OPS_CRON.md`
