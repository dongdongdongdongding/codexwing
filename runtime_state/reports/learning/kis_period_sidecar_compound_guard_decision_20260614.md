# KIS Period-Sidecar Compound Guard Decision

- generated_at: `2026-06-14T18:59:03+09:00`
- status: `production_not_achieved_current_window`
- data window: `2026-01-01`..`2026-06-10`
- data basis: real KIS period-sidecar prepared caches; no dummy-filled promotion evidence

## Direct Answer

The goal is not impossible, but the current real-data window does not support production promotion.

The strongest paths improve holdout returns materially, but the evidence is not strong enough after sample-size, active-day, active-run, hit-rate, drawdown, and touch-policy economics gates are applied. The recurring pattern is that the best-looking results concentrate in small holdout samples; when the guarded sample is widened, hit rate or min-low control breaks.

## KOSPI Near Miss

- source: `runtime_state/reports/learning/kis_three_stage_guarded_selection_kospi_compound_longfold_20260614.json`
- best config: `prefilter/k10/final2/ev/tail0.85`
- guard: `close_failure_prior_ticker_clean_defense_rate_pct >= 57.575758`
- base: n=`61`, days=`36`, hit5=`52.459`, avg_exit=`-1.108252`, dynamic_exit=`0.688182`, min_low=`-23.793047`
- holdout: n=`11`, days=`7`, hit5=`72.7273`, hit10=`72.7273`, tail=`9.0909`, avg_exit=`2.261713`, dynamic_exit=`5.431454`, min_low=`-10.056783`
- all guarded: n=`31`, days=`20`, hit5=`54.8387`, hit10=`48.3871`, tail=`12.9032`, avg_exit=`0.288528`, dynamic_exit=`2.377343`, min_low=`-15.32357`

Production blockers:

- holdout sample is too small: n=`11` vs production `>=30`, active days=`7` vs `>=15`, active runs=`11` vs `>=20`
- holdout hit5 is just below gate: `72.7273` vs `>=73`
- holdout min-low is just below gate: `-10.056783` vs `>=-10`
- all guarded sample clears n/day minimums better, but hit5 collapses to `54.8387` and min-low worsens to `-15.32357`

Decision: KOSPI is the only meaningful forward-shadow lane, not a production lane.

## KOSDAQ Observation Only

- source: `runtime_state/reports/learning/kis_three_stage_guarded_selection_kosdaq_compound_longfold_20260614.json`
- best config: `day_return/k5/final1/ev_hit10/tail0.75`
- guard: `close_failure_prior_ticker_avg_close_5d_pct >= 11.259848`
- base: n=`24`, days=`24`, hit5=`54.1667`, avg_exit=`-1.420942`, dynamic_exit=`1.277111`, min_low=`-58.95783`
- holdout: n=`4`, days=`4`, hit5=`100.0`, hit10=`100.0`, tail=`0.0`, avg_exit=`4.601458`, dynamic_exit=`9.58248`, min_low=`-7.789335`
- all guarded: n=`11`, days=`11`, hit5=`72.7273`, hit10=`90.9091`, tail=`18.1818`, avg_exit=`1.35008`, dynamic_exit=`4.972641`, min_low=`-15.535445`

Production blockers:

- holdout sample is far too small: n=`4`
- all guarded sample is still too small: n=`11`, active days=`11`
- all guarded hit5 is below gate: `72.7273` vs `>=73`
- all guarded min-low fails risk gate: `-15.535445` vs `>=-10`

Decision: KOSDAQ is not promotable. Keep it observation-only.

## Trace

- Scanner reasons: KOSPI came from prefilter-ranked three-stage selections; KOSDAQ came from day_return-ranked three-stage selections.
- Aggregation notes: selected cases were grouped by market/config, then chronological selected-train and selected-holdout guard validation was applied.
- Backtest diagnostics: compound AND guards improved small holdout slices, but production gates blocked them on sample size and drawdown stability.
- Market/news context: no regime override was applied; sidecar news/date coverage was used only as scan-time features.
- Planner decision: no production promotion; KOSPI forward-shadow only; KOSDAQ observe only.
- Realized outcome: placeholder linked to forward-tracking issue `swing-main-u9sq`.

## Decision

1. Do not promote any candidate to production from the current real-data window.
2. Keep KOSPI compound-guarded three-stage selection as the primary forward-shadow lane.
3. Do not chase more parameter-only searches on this same window unless they add genuinely new data or a stricter out-of-sample design.
4. Next useful research is forward-shadow accumulation plus exit/risk overlays on the KOSPI near-miss path.
