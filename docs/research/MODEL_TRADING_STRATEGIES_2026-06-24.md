# Model Trading Strategies - 2026-06-24

This document records the current model-by-model trading strategy contracts. It is not a guarantee of future returns. It is a practical map of what each model is trying to trade, how it enters, how it exits, and whether it is live, shadow, or research-only.

## Evidence Files Read

- `multi_agent/tools/report_swing_ensemble.py`
- `multi_agent/tools/report_kospi_intraday_swing.py`
- `multi_agent/tools/report_kosdaq_intraday_vwap_guard.py`
- `modules/kosdaq_intraday_vwap_guard.py`
- `modules/intraday_candidate_registry.py`
- `multi_agent/tools/report_kospi_normal_pead_shadow.py`
- `multi_agent/tools/report_firsttouch_down_shadow.py`
- `modules/scanner_services.py`
- `multi_agent/agents/planner_runtime.py`
- `docs/research/RESEARCH_JOURNEY_2026-06.md`
- `runtime_state/reports/learning/intraday_claude_codex_synthesis_latest.md`
- `runtime_state/reports/learning/intraday_3d_t5_monthly_failure_diagnosis_latest.md`
- Beads open/closed issues from `bd list --json`.

## Strategy Summary

| Strategy | Market | Mode | Live routing | Primary target | Current use |
|---|---|---:|---:|---|---|
| SWING price-ML ensemble | KOSPI/KOSDAQ | SWING | Yes | `ft_5_5` | Modest daily forward lane |
| KOSPI intraday 3D +5% | KOSPI | INTRADAY concept | Yes | 3D +5% MFE touch | Live-forward lane |
| KOSDAQ intraday 15:00 VWAP guard | KOSDAQ | INTRADAY | Yes | 3D +5% touch | Current best intraday deployment |
| KOSPI intraday 09:05 5D | KOSPI | INTRADAY | No | 5D `t10_s5` path | Shadow registry, needs ledger |
| KOSDAQ tail guard | KOSDAQ | INTRADAY | No | 5D path | Research only |
| KOSPI NORMAL PEAD | KOSPI | SWING | No | 5D first-touch | Falsification shadow only |
| First-touch down | KR | SWING | No | Down-regime first-touch | Disabled shadow |
| Exception Leader | KR | SWING | Planner/legacy observation | Momentum exception | Short-window positive, not durable production |
| Practical-80 | KOSPI | SWING | Promotion disabled/stale | Practical cohort | Not validated as current production edge |
| Phase25 KOSDAQ intraday | KOSDAQ | INTRADAY | Retired | Old phase25 intraday | Avoid/retired |
| KIS touch5/dd10 | KOSPI/KOSDAQ | SWING | Shadow/research | 5D touch and drawdown | Open Beads research stream |

## 1. SWING Price-ML Ensemble

Files:

- `multi_agent/tools/report_swing_ensemble.py`

Model:

- LGBM
- XGBoost
- ExtraTrees
- trained on trailing daily `px_long.parquet`
- price-only feature set

Target:

- `ft_5_5`: price touches +5% before -5% within 5 sessions.

Universe:

- KOSPI and KOSDAQ.
- Current default liquidity floor `>=100억` daily trading value.

Selection:

- Top ~1% by ensemble probability per market.
- Current command default: `--top-pct 1.0 --min-liq 100`.

Entry:

- Stored producer route uses entry reference from latest close.
- Ledger resolution uses next-day open as the first-touch entry in `resolve_pending`.

Exit:

- 5 trading days.
- +5% first-touch target.
- -5% first-touch failure label for `ft_5_5`.
- No tight live stop in the model-lane trade plan.

Current interpretation:

- Live forward validation lane.
- Research note says it is durable/modest, around 66-67% `ft_5_5` hit in corrected validation, not a 75% target solver.
- Useful as a secondary daily model, not the main intraday objective.

Operational outputs:

- `runtime_state/reports/experimental/swing_ensemble_latest.json`
- `runtime_state/reports/experimental/swing_ensemble_latest.md`
- `runtime_state/reports/experimental/swing_ensemble_ledger.jsonl`
- Supabase `market_scan_results`
- Supabase `scan_deep_reports`

## 2. KOSPI Intraday 3D +5% Context VWAP Guard

Files:

- `multi_agent/tools/report_kospi_intraday_swing.py`

Model:

- LGBM
- XGBoost
- ExtraTrees
- trained in-script from `~/research_cache/intraday_3d_panel.parquet` and daily context.

Target:

- 3-day +5% MFE touch (`y3` in the script comment).

Universe:

- KOSPI.
- Default liquidity floor `>=100억`.

Selection:

- top2 by ensemble probability.
- `close_vwap>=0`.
- `idx_vol20>=8`.
- liquidity must pass at emission.

Entry:

- Close-buy entry after full-session minute bars.
- This is not a mid-session on-demand scan.

Exit:

- 3-day close hold.
- +5% target is the touch diagnostic.
- No tight stop in the primary return contract.

Research basis recorded in script:

- Top2 + `close_vwap>=0` + `idx_vol20>=8`.
- Backtest hit about 85%, monthly floor about 71%, 3D close return about +6.2%.
- The volatility guard was introduced because one low-volatility weak month made +5% structurally rare.

Current interpretation:

- Live-forward lane.
- Good candidate, but weaker operational artifact discipline than KOSDAQ because model is trained inside producer.
- Needs forward validation to prove the repaired volatility guard is not overfit.

Operational outputs:

- `runtime_state/reports/experimental/kospi_intraday_swing_latest.json`
- `runtime_state/reports/experimental/kospi_intraday_swing_latest.md`
- `runtime_state/reports/experimental/kospi_intraday_swing_ledger.jsonl`
- Supabase route via `_route_live` with bucket `kospi_intraday`.

## 3. KOSDAQ Intraday 15:00 VWAP Guard

Files:

- `modules/kosdaq_intraday_vwap_guard.py`
- `multi_agent/tools/report_kosdaq_intraday_vwap_guard.py`

Candidate ID:

```text
kosdaq_intraday_1500_3d_t5_vwap_guard_shadow_v1
```

Strategy family:

```text
KR_INTRADAY_3D_T5
```

Model artifact:

```text
models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl
```

Model:

- LightGBM classifier.
- Previous-month isotonic calibration.
- Stored joblib bundle with feature list and selection policy.

Target:

- `target_touch3d_t5`: high touches +5% within 3 trading days from 15:00 entry price.

Universe:

- KOSDAQ only.
- Universe selected from `~/research_cache/px_long.parquet`.
- Recent 90-day median liquidity.

Liquidity lanes:

- `>=30억`: main edge lane.
- `>=100억`: tradeability lane.

Entry:

- 15:00 minute-confirmed entry.
- KIS minute bars are fetched at 15:00 and fallback earlier snapshots if needed.
- Feature computation uses bars from 09:00 through 15:00 only, avoiding post-entry leakage.

Selection:

- `p_cal>=0.80`.
- `pre_vwap_dist_pct>=0`.
- daily top2.
- `liq_prev_eok>=min_liq`.

Exit:

- 3D close hold is the primary return policy.
- +5% touch is the diagnostic target.
- Stop is not part of the current primary return contract.

Cost:

- `ROUNDTRIP_COST_PCT = 0.33`.

Current validation from registry/report:

- `>=30억`: n=81, hit 90.12%, CI low 81.70%, close3 net@0.33 +10.27%, month hit min 80%.
- `>=100억`: n=40, hit 85.00%, CI low 70.93%, close3 net@0.33 +5.11%, month hit min 75%.

Current interpretation:

- Current best KOSDAQ intraday deployment.
- Live-forward validation is active.
- Full promotion still requires forward micro-production gate.

Forward gate from registry:

- minimum forward picks 60
- minimum forward days 30
- minimum forward months 2
- target touch3d_t5 >=75%
- day hit >=80%
- net 3D close return >0
- liquidity-decile excess >0
- no month with n>=5 below 65%
- realized slippage <=0.50%

Operational outputs:

- `runtime_state/reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_latest.json`
- `runtime_state/reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_latest.md`
- `runtime_state/reports/experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl`
- Supabase `market_scan_results`
- Supabase `scan_deep_reports`

Known consumer caveat:

- The bucket is not currently in `MODEL_VALIDATED_LANES`, so `/signals` may omit it.

## 4. KOSPI Intraday 09:05 5D Shadow

File:

- `modules/intraday_candidate_registry.py`

Candidate ID:

```text
kospi_intraday_0905_5d_t10s5_shadow_v1
```

Strategy family:

```text
KR_INTRADAY_5D
```

Entry:

- 09:05 minute-confirmed entry.

Target and exit:

- target +10%
- stop -5%
- hold 5D
- primary return column `exit5d_ret_t10_s5`

Validation recorded in registry:

- KOSPI `>=100억`
- n=421
- days=101
- months=10
- net avg +2.299%
- excess avg +1.272%
- win 62.71%
- day win 78.22%
- target-first 21.6%
- stop-first 15.2%

Current interpretation:

- Shadow candidate only.
- Per-pick win is below 75% and stop-first is near guard.
- Beads `swing-main-ho2w` tracks wiring this candidate to live forward ledger.

## 5. KOSDAQ Intraday Tail Guard Research

File:

- `modules/intraday_candidate_registry.py`

Candidate ID:

```text
kosdaq_intraday_tail_guard_research_v1
```

Strategy family:

```text
KR_INTRADAY_5D
```

Entry:

- 11:30 minute-confirmed entry with no-stop/MAE guard.

Target and exit:

- target +10%
- stop -5%
- hold 5D

Validation recorded:

- KOSDAQ `>=30억`
- n=174
- net avg +1.08%
- excess avg +1.19%
- win 49.4%
- day win 50.5%
- target-first 17.2%
- stop-first 17.8%

Current interpretation:

- Research only.
- Tail guard lowers some risk, but hit rate and day-win stay near 50%.
- Not an operating promotion candidate.

## 6. KOSPI NORMAL PEAD Shadow

File:

- `multi_agent/tools/report_kospi_normal_pead_shadow.py`

Current role:

- Falsification ledger.
- Production OFF.

Reason:

- Previous "survived edge" narrative was corrected.
- Panel/internal benchmark and equal/size controls did not support a robust production edge.

Entry/exit:

- Former candidate used KOSPI NORMAL, price/flow/coarse PEAD, ensemble, `>=100억`, top5, label `ft_5_5`.
- Current shadow should not be read as buy recommendation.

Operational use:

- Keep ledger to collect contradictory evidence.
- Do not route to production unless a new validation explicitly reopens it.

## 7. First-Touch Down Shadow

File:

- `multi_agent/tools/report_firsttouch_down_shadow.py`

Current role:

- Disabled by default.
- Observation-only if enabled.

Reason:

- Down-edge was judged beta/artifact in later validation.

Operational use:

- Not part of current production direction.

## 8. Exception Leader

Files:

- legacy planner/orchestration paths
- `multi_agent/workflows/legacy_orchestration.py`
- `multi_agent/agents/planner_runtime.py`

Current interpretation:

- Momentum exception stream.
- Short-window positive signal was found under size-matched validation, but sample was about 4 months and concentrated in one month.
- Not durable production edge.
- Can remain visible for observation and forward evidence.

Strategy if observed:

- Treat as high-volatility watch stream.
- Do not size or promote based on old `77%` headline alone.
- Require forward ledger with corrected controls.

## 9. Practical-80

Files:

- `modules/practical_entry_gate.py`
- `multi_agent/agents/planner_runtime.py`

Current interpretation:

- Older 90%+ win narrative was corrected.
- Cap-weighted negative result was also corrected as size-biased, but clean size-matched result was not production-significant.
- Disable/promotion-off state is conservative and acceptable unless a new forward gate proves otherwise.

Strategy if encountered:

- Use as diagnostic/profile evidence, not automatic buy.
- Do not restore promotion on stale 2026-April-only evidence.

## 10. Phase25 Legacy Models

Files:

- `retrain_ml.py`
- `modules/quant_analysis.py`
- `multi_agent/agents/planner_runtime.py`
- model files under `models/phase25_*`

Important current facts:

- `phase25_kosdaq_intraday` is explicitly retired/avoided in tests and planner reliability gates.
- File existence does not mean production use.
- Planner has reliability gates for uncertain, below-random, weak OOS, and retired variants.

Strategy:

- Do not trade retired/inverted Phase25 intraday variants.
- Use current model-lane producers instead.

## 11. KIS touch5/dd10 Shadow Stream

Relevant Beads:

- `swing-main-n6u3`
- `swing-main-xuy1`
- `swing-main-u9sq`
- `swing-main-yf9n`

Current role:

- Research and shadow-forward stream.
- Aims to use KIS sidecar/prefilter/flow/history to build touch5/dd10 or expected-value rankers.

Current blocker:

- feature parity and historical sidecar coverage
- sample gates
- Supabase/PostgREST timeout risk

Strategy:

- Do not confuse this stream with the live KOSDAQ intraday model.
- Keep it as a separate daily/SWING research lane until promotion gates clear.

## Practical Trading Interpretation

For current operating decisions:

1. KOSDAQ intraday VWAP guard is the primary candidate for the operator's 3D +5% target.
2. KOSPI intraday is a live-forward sibling, but its guard and training artifact need more production hardening.
3. SWING ensemble is a modest daily model and useful for forward data, not the 75% target.
4. Old daily cohort/PEAD/regime stories are not production edges today.
5. Any model-lane pick must show entry, target, hold, liquidity lane, probability, and ledger status before being treated as actionable.
