# Codex Swing Quant Scanner

KR/US swing and intraday scanner with multi-agent execution support, scan archive learning, realized-outcome tracking, and Streamlit operator UI.

## Current Status

Updated: 2026-05-13

- Primary repository: `git@github-codexwing:dongdongdongdongding/codexwing.git`
- Issue database: beads through `scripts/issue`
- Beads remote: `git+ssh://git@github-dolt-beads/dongdongdongdongding/dolt.git`
- Streamlit UI: `python3 -m streamlit run app.py --server.port 8501`
- Runtime artifact policy is active: generated run trees and large archives are ignored; curated learning, validation, and trading reports are tracked intentionally.

Recent stabilization work:

- Scan archive writes are run-scoped so repeated same-day ticker scans do not corrupt top-rank parity.
- Scanner archive rows now carry 5-day high-touch labels such as `max_high_return_5d_pct` and `hit_5pct_within_5d`.
- KR swing context includes US lead and macro/derivative signals for planner-facing diagnostics.
- UI cards expose planner action trace fields without changing the core scoring engine.
- `runtime_state` was pruned from the Git index: generated `artifacts`, `shared_working`, context caches, and large archive datasets remain local artifacts rather than source-controlled files.

## Core Capabilities

- KR/US market scanning with legacy-safe production defaults and relaxed development profiles.
- Streamlit operator cockpit for scan review, report inspection, and planner traces.
- Multi-agent workflow contracts for scanner, aggregation, backtest/learning, market/news context, and PM planner stages.
- Learning and validation tools for KR swing slices, live policy performance, paper-trade ledgers, and scan archive consistency.
- Realized outcome tracking and postmortem artifacts for recommendation auditability.

## Setup

```bash
git clone git@github-codexwing:dongdongdongdongding/codexwing.git
cd codexwing
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with local API keys and database credentials. Do not commit secrets.

## Run The UI

```bash
python3 -m streamlit run app.py --server.port 8501
```

Current local URL:

```text
http://localhost:8501
```

## Model And Learning Jobs

Large model binaries are ignored under `models/*.pkl`. Regenerate them locally when needed:

```bash
python3 train_ml_targets.py
python3 train_global_brain.py
python3 retrain_ml.py
```

Useful learning/reporting commands:

```bash
python3 multi_agent/tools/update_outcome_return_metrics.py
python3 multi_agent/tools/export_scan_archive_learning_dataset.py --market ALL
python3 multi_agent/tools/verify_scan_archive_top_consistency.py
python3 multi_agent/tools/report_live_policy_performance.py
python3 multi_agent/tools/build_paper_trade_ledger.py
```

## Non-UI Scan Pipeline

```bash
python3 -m multi_agent.workflows.non_ui_scan_pipeline --market KOSDAQ --profile prod --max-scan 100 --max-workers 4
python3 -m multi_agent.workflows.non_ui_scan_pipeline --market KOSPI --profile prod --max-scan 100 --max-workers 4
python3 -m multi_agent.workflows.non_ui_scan_pipeline --market NASDAQ --profile dev --tickers AAPL,NVDA,MSFT --max-scan 3 --max-workers 1
```

Recommended KR universe hygiene:

```bash
AG_KRX_MIN_LISTING_DAYS=330
AG_KRX_EXCLUDE_SPACS=1
AG_KRX_EXCLUDE_NON_NUMERIC_CODES=1
```

## Report Policy

Tracked reports are curated evidence, not raw runtime dumps. Keep compact JSON/Markdown summaries that explain model quality, validation, or trading outcomes. Do not commit whole run directories, context caches, large archive datasets, or per-run scanner artifacts.

Primary tracked report areas:

- `runtime_state/reports/learning/`
- `runtime_state/reports/validation/`
- `runtime_state/reports/trading/`
- selected long-term summary JSONL files under `runtime_state/long_term/`

See `docs/migration/RUNTIME_ARTIFACT_POLICY.md` for exact rules.

## Issue Workflow

Use beads for all work tracking:

```bash
scripts/issue
scripts/issue start <issue-id>
scripts/issue end <issue-id> "reason"
bd dolt push
```

Before ending a coding session:

```bash
git pull --rebase
bd dolt push
git push
git status --short --branch
```

## Key Docs

- `AGENTS.md`: project rules and session completion workflow
- `multi_agent/README.md`: multi-agent workflow and tool commands
- `docs/operations/CODEX_TAKEOVER.md`: Codex operating handoff
- `docs/migration/RUNTIME_ARTIFACT_POLICY.md`: runtime artifact tracking policy
