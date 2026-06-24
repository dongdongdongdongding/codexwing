# Intraday Claude/Codex Research Synthesis

- Report version: `intraday_claude_codex_synthesis_v1`
- Scope: `KR_INTRADAY_3D_T5`
- Data source reviewed: `/Users/dongdong/research_cache`
- Status: research synthesis, not production approval

## Source Mapping

Claude scripts are reproducible under `/Users/dongdong/research_cache`:

- `intraday_backfill.py`: 1-minute raw bar collection.
- `intraday_panel.py`, `intraday_autonomous.py`: first intraday probes and strict walk-forward validation.
- `goal_search.py`, `meta_ensemble.py`: daily-goal search and meta-ensemble ceiling checks.
- `intraday_3d_panel.py`, `intraday_3d_model.py`, `intraday_3d_enhanced.py`, `intraday_3d_returns.py`, `intraday_holding_study.py`: 3-day +5% model, enhanced daily-context model, return and holding-period studies.

## Key Method Difference

Claude's `intraday_3d_*` family uses full intraday-day features and sets entry to the scan-day close.

Codex's current KOSDAQ model uses a live 15:00 entry and only pre-entry state, with `pre_vwap_dist_pct >= 0` as the entry-quality guard.

These are compatible but not identical:

- Claude lane: close-buy / market-on-close style candidate.
- Codex lane: live 15:00 intraday candidate.

## Claude Enhanced Model Recheck

Reproduced the enhanced intraday+daily-context walk-forward model and applied a close-VWAP guard, which is the close-buy analogue of Codex's 15:00 VWAP guard.

| Market | Policy | n | Hit | CI low | 3D net | Month min hit | Months >=70 |
|---|---:|---:|---:|---:|---:|---:|---:|
| KOSDAQ | top2 + close_vwap>=0 | 320 | 85.00% | 80.67% | +7.76% | 75.00% | 8/8 |
| KOSDAQ | top5 + close_vwap>=2 | 399 | 84.21% | 80.31% | +6.13% | 78.46% | 8/8 |
| KOSDAQ | top5 | 1584 | 81.44% | 79.45% | +4.22% | 71.43% | 8/8 |
| KOSPI | top2 + close_vwap>=0 | 332 | 84.04% | 79.71% | +5.80% | 61.11% | 6/7 |
| KOSPI | top5 | 1670 | 77.84% | 75.79% | +4.01% | 54.36% | 6/8 |

## Codex Current Best Candidate

| Market | Policy | n | Hit | CI low | 3D net | Month min hit | Months >=70 |
|---|---:|---:|---:|---:|---:|---:|---:|
| KOSDAQ | 15:00 p>=0.80 + pre_vwap_dist>=0 top2 | 81 | 90.12% | 81.70% | +10.27% | 80.00% | 7/7 |

## Synthesis

Best common family:

`KR_INTRADAY_3D_T5_CONTEXT_VWAP_GUARD`

The shared edge is not just classifier confidence. The strongest common pattern is:

1. 3-day +5% touch classifier.
2. Daily context merged with intraday path features.
3. VWAP-positive entry-quality guard.
4. 3-day close-hold return contract.
5. No tight stop as the primary return contract; stops reduce expectancy in both studies.

## Candidate Ranking

1. KOSDAQ live 15:00 VWAP-guard candidate: strongest return and hit, but smaller n.
2. KOSDAQ close-buy enhanced top2 + close_vwap>=0: larger n, 8/8 monthly >=70, strong close-buy production-lane candidate.
3. KOSDAQ close-buy enhanced top5 + close_vwap>=2: lower return than top2, but more samples and stronger monthly floor.
4. KOSPI enhanced top2 + close_vwap>=0: strong aggregate hit, but monthly floor fails; forward/research only until a KOSPI regime guard is found.

## Production Direction

Immediate shared direction:

- Keep KOSDAQ live 15:00 VWAP-guard model as the first forward ledger candidate.
- Add a separate KOSDAQ close-buy lane from Claude's enhanced model, with close_vwap guard.
- Do not promote KOSPI yet despite high aggregate hit; monthly instability remains.

Promotion should require forward evidence:

- At least 60 forward picks, 30 days, 2 months for micro-production.
- Target touch >=75%, day hit >=80%, net 3D return >0, liquidity-matched excess >0.
- No month with n>=5 below 65% hit.
- Full production only after 120 forward picks and 4 forward months.

