# US / AMEX Expansion Plan

## Objective
Build a US-market expansion in two separated tracks:
- NASDAQ / large-cap US scan: general swing + intraday continuation logic
- AMEX moonshot scan: separate high-volatility breakout algorithm focused on 100%+ movers

The system must validate win rate / return before model finalization, and must use full-universe scans rather than small ticker samples when building the research dataset.

## Current State

### What already exists
- UI supports `NASDAQ`, `S&P500`, `AMEX` market selection.
- Scanner runtime supports `SWING` and `INTRADAY` scan modes.
- US rows are stored in `market_scan_results` with `scan_mode`, decision buckets, and realized return fields.
- Daily / archive / realized-outcome plumbing is already connected to Supabase and local run artifacts.

### Current limitations
1. `max_scan` truncates the universe.
- `modules/scanner_runtime.py` slices `ticker_list[:max_scan]`.
- This is fine for operations, but not enough for full-universe research.

2. AMEX is not a true separate strategy yet.
- AMEX currently shares the US scanner path.
- The main differences are only threshold tweaks like `AG_US_HARD_AMEX_RS_MIN` and smaller liquidity floors.
- That is not enough for 100%+ breakout hunting.

3. Current US backtest path is sampled, not full-universe.
- `multi_agent/agents/backtest_runtime.py` uses sampled diagnostics.
- Useful for runtime sanity, insufficient for model definition.

4. Current training path is not split by US regime / AMEX moonshot objective.
- Existing training scripts mainly assume legacy scan archive or KR-oriented regime structures.
- There is no dedicated AMEX target such as `same_day >= +30%`, `T+3D max >= +100%`, or `gap-followthrough survival`.

5. Current US universe fetch is broad but not research-normalized.
- `modules/quant_analysis.py` fetches NASDAQ/S&P500 via `FinanceDataReader.StockListing`.
- AMEX filtering excludes obvious junk, but still needs more precise research filters for warrants/ETNs/leveraged products/reverse split artifacts.

## Required Split

### 1. NASDAQ / US Main Strategy
Purpose:
- More stable US swing / intraday continuation setup.

Candidate traits:
- trend continuation
- relative strength vs SPY / QQQ
- volume expansion
- earnings-risk aware
- regime-aware filtering

Primary evaluation:
- 1D / 3D / 5D forward return
- intraday: 30m / 1h / close
- win rate, expectancy, PF, sample size

### 2. AMEX Moonshot Strategy
Purpose:
- Find explosive names that can move 30% / 50% / 100%+ quickly.

Candidate traits:
- abnormal volume multiple
- float / size proxy if available
- first-breakout after compression or halt-style expansion
- intraday range expansion
- gap-and-go / reclaim / parabolic continuation patterns
- looser alpha logic, stricter liquidity / structure logic

Primary evaluation:
- same-day close return
- T+1 open / close return
- max excursion within 1D / 3D
- hit rate for +20%, +50%, +100%
- failure severity (gap fade / close below VWAP-like proxy / reversal depth)

## Research Before Model Finalization

### Mandatory validation stage
Before training the final AMEX or NASDAQ model:
1. full-universe scan archive generation
2. forward return enrichment
3. regime split analysis
4. bucketed baseline rules evaluation
5. only then model training

### Minimum validation outputs
- sample size by market / regime / bucket
- avg return
- median return
- win rate (>0)
- hit rate (>5%, >10%, >20%, >50%, >100%)
- max adverse excursion proxy
- max favorable excursion proxy
- coverage ratio
- missed-winner analysis

## Agent Responsibilities

### Scanner Agent
- Build full-universe US and AMEX scan datasets.
- Separate `US_MAIN` and `AMEX_MOONSHOT` scan policies.
- Record rejection reasons and structural traces.

### Aggregation Agent
- Cluster results by market, regime, setup type, and bucket.
- Identify concentration in biotech / mining / low-float / theme baskets.
- Compare survivorship of AMEX explosive candidates.

### Backtest & Learning Agent
- Build full-universe forward-return dataset.
- Evaluate baseline rules before any model fitting.
- Train only after target quality / sample quality checks pass.

### Market & News Context Agent
- Separate US broad-market regime from speculative-microcap risk appetite.
- Track risk-on/risk-off signals relevant to AMEX moonshots.

### PM Planner Agent
- Keep NASDAQ recommendations and AMEX moonshots separate in planner output.
- Require explicit warnings for low-sample or hype-driven AMEX picks.
- Issue tickets if AMEX rules become too noisy or too sparse.

## Staged Implementation

### Stage 1: Research foundation
- Add US full-universe research runner that ignores small `max_scan` sample behavior.
- Build separate archive tags:
  - `strategy_family = US_MAIN`
  - `strategy_family = AMEX_MOONSHOT`
- Add forward-return enrichment for US and AMEX.

### Stage 2: Baseline validation
- NASDAQ full-universe baseline report:
  - regime x setup x horizon
- AMEX moonshot baseline report:
  - hit rates for >20 / >50 / >100
  - risk of catastrophic fade

### Stage 3: Strategy split
- NASDAQ policy remains more conservative.
- AMEX policy becomes separate algorithm with its own filters, scoring, and planner bucket.

### Stage 4: Model training
- Train NASDAQ model only after baseline validation passes.
- Train AMEX moonshot model only after target distribution and sample quality are acceptable.
- Keep these model artifacts separate.

### Stage 5: Operationalization
- Separate UI views / planner buckets:
  - US Main Picks
  - AMEX Moonshots
- Separate archive filters and performance cards.

## First Safe Refactor Steps
1. Add a dedicated `research_mode` or full-universe runner for US/AMEX.
2. Stop treating AMEX as merely a threshold variant of the US scanner.
3. Add AMEX-specific archive labels and forward-return targets.
4. Produce validation reports before touching the final model.

## Important Risks
- AMEX data quality and symbol hygiene can heavily distort backtests.
- 100% movers are extremely sparse and noisy; sample-size illusion risk is high.
- Full-universe US scans may be slow; batching and artifact caching are required.
- If we train before validating base hit-rate structure, model quality will be misleading.

## Recommendation
Proceed in this order:
1. full-universe US / AMEX research runner
2. validation reports
3. AMEX-specific algorithm design
4. model training only after evidence is strong enough
