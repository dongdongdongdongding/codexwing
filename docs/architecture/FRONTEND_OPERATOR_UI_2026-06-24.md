# Frontend, Discord, And Design Structure - 2026-06-24

This document maps the operator-facing surfaces: Streamlit UI, Discord commands, design system, data-loading paths, and known consumer gaps.

## Evidence Files Read

- `app.py`
- `ui/theme.py`
- `ui/components.py`
- `ui/scan_cockpit.py`
- `ui/top_deep_view.py`
- `ui/archive_data.py`
- `ui/performance_view.py`
- `ui/scan_integrity_view.py`
- `ui/kis_theme_network_view.py`
- `ui/intelligence_view.py`
- `ui/view_chrome.py`
- `modules/ui_helpers.py`
- `modules/operational_readiness_ui.py`
- `modules/candidate_interpretation.py`
- `modules/operational_candidate_scoring.py`
- `modules/discord_integration/commands.py`
- `modules/discord_integration/renderers.py`
- `modules/discord_integration/scan_executor.py`
- `multi_agent/tools/discord_bot.py`
- `multi_agent/tools/discord_register_commands.py`

## Streamlit Role

`app.py` is still the main page composition entrypoint. The current architecture has moved many reusable surfaces into `ui/*`, but `app.py` remains large and includes scanner launch logic, global status panels, deep-dive logic, and archive composition.

The UI is not the source of model truth. It reads:

- local runtime artifacts
- Supabase `market_scan_results`
- Supabase `scan_deep_reports`
- Supabase/local runtime artifacts
- current report JSON under `runtime_state/reports`

The UI should present stored evidence and contracts, not invent missing values.

## Default Tabs

When `AG_UI_ADVANCED` is unset or false, the UI shows:

- `스캐너`
- `Top 분석`
- `아카이브`

When `AG_UI_ADVANCED=1`, it shows:

- `스캐너`
- `Top 분석`
- `인텔리전스`
- `테마 네트워크`
- `성과`
- `아카이브`
- `정밀분석`

This split is deliberate. The default operator surface is kept focused on actual operating decisions.

## Global Status Layer

At app startup, the UI builds a compact status bar from:

- selected market
- macro context from `modules.macro_scheduler.get_macro_context`
- market gate from `compute_market_gate`
- daily model foundation gate from `runtime_state/reports/learning/daily_model_foundation_gate.json`
- segment accuracy snapshot from `modules.segment_accuracy`

The "운영 판정 상세" expander uses `modules/operational_readiness_ui.py` to show blockers and next actions. This keeps Korean-first operational copy outside Streamlit-only code.

## Scanner Tab

The scanner tab lets the operator choose:

- market: KOSPI, KOSDAQ, NASDAQ, S&P500, AMEX
- scan mode: `스윙` or `장중`
- max scan count

The scan button starts a background job through app-side state helpers. That job calls scanner runtime and persists run artifacts through the same artifact contract used by non-UI scans.

Important behavior:

- The scan continues while the user moves tabs.
- The scan continuity banner remains visible.
- Top Deep reports are generated after scan completion.
- Local and DB artifacts are written for Archive recovery.

Advanced-only file upload scanner remains in the advanced UI path.

## Top Analysis Tab

The Top Analysis tab is implemented by `ui/top_deep_view.py`.

Data sources:

- Supabase `scan_deep_reports`
- local JSON files under `runtime_state/reports/top_deep`

Merge behavior:

- DB rows are loaded first.
- Local rows are merged.
- Certain local fields are authoritative when present, including analysis section/rank, decision, bucket, selection alignment, display contract, and candidate interpretation.

Top Deep displays:

- candidate interpretation
- trade plan
- buy-premium execution gate for legacy planner candidates
- flow captions
- policy metadata
- realized expectancy admission
- portfolio exposure context
- scan integrity panel where available

## Archive Tab

The Archive tab is implemented in `app.py` with data access helpers from `ui/archive_data.py`.

Default behavior:

- Supabase archive is disabled unless `AG_SCAN_ARCHIVE_SUPABASE_ENABLED=1`.
- Local fallback is enabled by default.
- Local artifacts are merged with DB rows when both exist.

Archive can filter by:

- date
- KR/US
- decision bucket
- scan mode: `SWING` or `INTRADAY`
- validation status
- run id

For a selected run, Archive loads:

- planner handoff from `runtime_artifacts` or local shared working directory
- profile diagnostics
- raw scan results
- scan integrity context

It then enriches rows with planner trace and rebuilds scan-universe admission display for KR markets.

Important Archive rule:

- Archive Top must mirror scan-time/planner order for the selected `run_id`.
- It must not mix multiple same-day runs or silently re-rank by decision score.

## Performance, Intelligence, Theme Network, Deep Dive

Advanced-only pages:

- Performance: `ui/performance_view.py`, daily ops overview.
- Intelligence: `ui/intelligence_view.py`, market intelligence and theme momentum.
- Theme Network: `ui/kis_theme_network_view.py`.
- Deep Dive: large app-side single-ticker analysis path using `QuantStrategy`, macro, news, Prophet-like prediction, technical levels, flow, and chart/image support.

The advanced pages contain useful diagnostics but should not be treated as the default execution surface.

## Design System

`ui/theme.py` injects the design tokens and CSS:

- background and surface tokens
- Toss-like card surfaces
- status banners
- compact cards
- segmented tabs
- dataframes and metrics
- Pretendard font import

Current UI style:

- Korean-first labels.
- Wide layout.
- Card containers for repeated candidate rows.
- Compact L0 status bar, L1 summary cards, L2 detailed grids.
- Main tabs use `st.segmented_control`.

Design debt:

- `app.py` still has large non-modular sections, especially deep-dive and archive composition.
- Existing issue `swing-main-usd` tracks further Streamlit view extraction.

## Candidate Interpretation

`modules/candidate_interpretation.py` is the main bridge between stored rows and operator-facing meaning.

Two interpretation modes exist:

1. Model-validated lane interpretation.
2. Legacy operational candidate interpretation.

Current model-validated whitelist:

```python
MODEL_VALIDATED_LANES = {"swing_ensemble", "kospi_intraday"}
```

For these buckets, `build_model_lane_interpretation` returns:

- `MODEL_BUY`
- entry reference price
- +5% target
- no tight stop
- fixed hold days
- probability label
- selection thesis

All other buckets use the legacy operational scoring axes and buy-premium execution gate.

## Current KOSDAQ Intraday Consumer Gap

The KOSDAQ intraday VWAP guard producer writes:

- `decision_bucket="kosdaq_intraday_3d_t5_vwap_guard"`
- `decision="KOSDAQ_INTRADAY_3D_T5_BUY"`
- `scan_mode="INTRADAY"`
- `strategy_family="KR_INTRADAY_3D_T5"`

Because that bucket is not in `MODEL_VALIDATED_LANES`, some surfaces may render it through generic interpretation instead of the concise model-lane card.

Affected path confirmed in code:

- `/signals` uses `build_model_signals_embed`.
- `build_model_signals_embed` filters rows where `decision_bucket in MODEL_VALIDATED_LANES`.
- Therefore `/signals` currently surfaces SWING ensemble and KOSPI intraday, not necessarily KOSDAQ intraday, unless the whitelist is extended.

Generic Top Deep, Archive, and direct `scan_deep_reports` reads can still show the KOSDAQ lane because the producer writes those rows directly.

## Discord Commands

Defined in `modules/discord_integration/commands.py`:

- `/kospi_scan`: starts KOSPI scan.
- `/kosdaq_scan`: starts KOSDAQ scan.
- `/macro_refresh`: refreshes macro context.
- `/top_deep`: Top Deep lookup.
- `/signals`: model signals lookup.
- `/archive`: archive lookup.
- `/runs`: run lookup.
- `/status`: bot/server/status lookup.

Scan execution uses `modules/discord_integration/scan_executor.py`:

- Creates a `DiscordScanJob`.
- Builds command `python -m multi_agent.tools.run_kis_operational_kr_scan`.
- Uses a lock to prevent conflicting scan jobs.
- Reads recent artifact summary after job completion.

Rendering uses `modules/discord_integration/renderers.py`:

- Loads Top Deep rows from Supabase or local fallback.
- Splits embeds under Discord field/character limits.
- Builds status, run, archive, top-deep, and scan result embeds.
- Has a concise model-lane card for whitelisted model lanes.

## Web And Discord Alignment Rules

Current product contract requires web and Discord to preserve:

- section identity
- final action and reason codes
- entry condition and stop/exclusion condition
- quality/upside/timing grades
- chase/exclusion risk
- flow windows and missing-data warnings
- run ID and outcome status

When a model-lane producer bypasses normal planner generation and writes direct Top Deep rows, it must still populate enough fields for both web and Discord. KOSPI intraday reuses `_route_live`; KOSDAQ intraday has its own router.

## UI/Design Follow-Ups

1. Add KOSDAQ intraday bucket/profile to model-lane consumer interpretation if `/signals` and concise cards are required for that lane.
2. Keep `scan_mode=INTRADAY` visible on KOSDAQ intraday rows; do not render it as SWING.
3. Continue extracting `app.py` into focused modules per `swing-main-usd`.
4. Keep advanced research tools behind `AG_UI_ADVANCED=1`.
5. Do not display raw probability as guaranteed win rate; always show sample, horizon, and contract when available.
