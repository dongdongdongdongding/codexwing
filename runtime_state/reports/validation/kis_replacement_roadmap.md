# KIS Replacement Roadmap

## Summary
- operator_answer: KIS can stay as the KR daily operational source path with legacy fallback. KIS model candidates must remain in the top Shadow/Risk Review lane until the market-specific promotion gates pass, and final production replacement must report existing Top1/Top3/Top5 versus KIS metrics side by side.
- current_replacement_level: production-primary source default with legacy fallback; KIS model promotion remains shadow/risk-review
- source_only_change: The promotion changes the daily operational execution path, archives KIS prefilter/sidecar/theme-news features, and exposes those real KIS fields to challenger training with maturity gates; scanner/planner scoring contracts remain compatible.
- endpoint_ok_count: 25
- endpoint_failed_count: 0
- emitted_theme_news_backfill_rows: 3029
- emitted_theme_news_news_checked_rows: 3029
- emitted_theme_news_no_dummy_data: True
- model_comparison_report: runtime_state/reports/learning/kis_model_market_comparison.json

## Implemented Now
- market_data_toggle: AG_KR_MARKET_DATA_PROVIDER=kis_first or kis_only
- investor_flow_toggle: AG_KR_INVESTOR_FLOW_PROVIDER=kis_first or kis_only
- scanner_sidecar_toggle: AG_ENABLE_KIS_SIDECAR=1
- sidecar_adapter: modules.kis_operational_adapter
- top_deep_kis_source_timing: scan_as_of/deep_analysis_as_of/source_timing persisted in scan_deep_reports
- kis_challenger_feature_pipeline: scan_universe_snapshots.feature_snapshot KIS sidecar/prefilter payload is flattened into KIS-only and KIS-augmented challenger feature sets
- kis_challenger_maturity_gate: KIS feature sets train only on real KIS payload rows and require configured rows/days; no dummy rows are accepted
- candidate_only_deep_analysis: Top Deep consumes scan_universe_admission + Exception Leader candidates, not all tickers
- daily_scan_engine_default: AG_KR_DAILY_SCAN_ENGINE=kis_operational
- production_default_changed: True
- legacy_fallback_preserved: True
- legacy_fallback_toggle: AG_KR_DAILY_LEGACY_FALLBACK=1

## 100 Percent Replacement Gates
| Gate | Target | Current Status |
|---|---|---|
| source_contract | KIS payloads map to existing OHLCV, quote, and whale-flow fields | implemented_and_unit_tested |
| quote_universe | 100% effective KR quote coverage with retry/cache | {"effective_quote_success_rate_pct": 100.0, "source": "prior live KIS readiness sweep"} |
| ohlcv_history | >=99% KOSPI/KOSDAQ daily OHLCV availability for scanner candidates and archive replay | adapter_added; live dual-run not complete |
| intraday_bars | same-day minute bars support intraday refresh without stale yfinance dependency | adapter_added; production replay not complete |
| investor_flow | KIS stock investor flow works after the exchange time gate and falls back explicitly when unavailable | KIS-first toggle added; prior live check saw time-gated failures |
| rank_vi_news_financial | rank membership, VI status, news-title count, and financial ratios persist as model sidecar fields | {"emitted_kis_backed_rows": 3029, "emitted_news_checked_rows": 3029, "emitted_strength_levels": {"medium": 2611, "strong": 418}, "emitted_theme_news_rows": 3029, "kis_news_api_calls": 1425, "latency_policy": "candidate-only existing-sidecar news enrichment with ticker/date de-duplication; not full-universe news calls during live scan", "no_dummy_data": true, "status": "KIS operational prefilter rank/VI/quote/flow payload is archived per run; emitted candidate theme/news evidence is backfilled from real KIS news-title API results"} |
| consumer_parity | scanner, Discord, archive, top-deep, Supabase, and learning outputs consume the same normalized contract | daily KR autoscan defaults to KIS operational primary with explicit legacy fallback; Supabase compatibility was verified on live KIS rows; Top Deep now records KIS source timing when sidecar evidence is present |
| candidate_only_deep_analysis | Deep analysis runs only on emitted Top/Admission/Exception candidates, never on the whole raw universe | implemented_and_unit_tested |
| deep_analysis_source_timing | scan_as_of and deep_analysis_as_of are stored separately with price/flow/news source snapshots | implemented_and_unit_tested |
| nightly_full_universe_validation | Full-universe KIS validation is checkpointed per item and remains a validation lane, not the operational scan path | implemented_and_unit_tested |
| model_lift | KIS-augmented challenger beats current segment gates without worse tail loss | {"challenger_report": "runtime_state/reports/learning/kis_model_market_comparison.json", "prefilter_outcome_label_rows": 0, "prefilter_rows": 36, "readiness_status": "ok", "required_days": 10, "required_rows": 1200, "sidecar_outcome_label_rows": 105299, "sidecar_rows": 105299, "theme_news_outcome_label_rows": null, "theme_news_rows": null} |

## Model Upgrade Plan
- sidecar_persistence: Persist KIS quote, OHLCV summary, flow, rank, VI, news-title, and financial fields next to KR scanner rows. Success: No recommendation order change; complete KIS sidecar for eligible KR candidates.
- source_timing_contract: Separate scan snapshot time from Top Deep generation time and record source snapshots for price, flow, and news. Success: Every Top Deep row explains whether KIS sidecar, scan proxy, or fallback fetch supplied each field.
- dual_run_quality_report: Compare KIS-first and legacy outputs for scanner rows, archive rows, Discord lookup, and top-deep reports. Success: No silent missing-field drift; all consumer payloads carry source warnings.
- challenger_training: Run KIS sidecar-only, prefilter-only, sidecar-augmented, prefilter-augmented, and full KIS-augmented challengers after the maturity gate passes. Success: Segment Top5 positive-rate, average 5D return, bad-path rate, and stop-first rate improve on real resolved KIS rows.
- promotion: Promote KIS primary with explicit fallback after gates pass. Success: Production KR scanner uses KIS primary without lowering current release gates.

## Scan Logic Maximization Plan
- prefilter: Use KIS rank, quote activity, VI, trade value, and flow availability to bound the candidate universe before expensive scanner work. Guardrail: Prefilter must store selected and rejected evidence; no dummy rows and no silent empty candidate success.
- admission: Score only KIS-prefiltered candidates with current scan_universe_admission lanes, preserving Top5/Exception/Shadow section traces. Guardrail: Promotion requires live outcome gates by market/section/horizon, including bad-path and stop-first risk.
- deep_analysis: Use KIS sidecar as the primary Top Deep evidence source and keep fallback sources visible in source_timing. Guardrail: scan_as_of and deep_analysis_as_of must differ when data is refreshed after scan time.
- learning: Use flattened KIS sidecar and prefilter features in explicit feature-group ablations. Guardrail: Only train/promote a KIS-augmented challenger on real KIS payload rows with enough resolved outcomes; no dummy or missing-only KIS rows.
- operations: Keep operational scan KIS-prefiltered and reserve 3-way full-universe KIS scans for checkpointed nightly validation. Guardrail: Full-universe validation failure cannot block candidate-only operational persistence unless source contract gates fail.

## Final Operational Reflection Plan
- performance_source: runtime_state/reports/learning/kis_model_market_comparison.json
- metric_contract: 2d is intentionally excluded; report uses completed 1d/3d/5d scan_universe outcome labels only.
- comparison_contract: For each market, show existing production Top1/Top3/Top5 versus the current KIS challenger on n, active_days, active_runs, win_1d/3d/5d, avg_1d/3d/5d, min_1d/5d, max_5d, min_low_5d, bad_path, and promotion-gate blockers.

### Current KIS Market Reflection
| Market | Action | Gate | Production Ready | n | Active Days | Win 5D | Avg 5D | Min Low 5D |
|---|---|---|---:|---:|---:|---:|---:|---:|
| KOSDAQ | shadow_top_section_only_until_gate_passes | shadow_risk_review | False | 11 | 3 | 54.5455 | 15.806625 | -21.389397 |
| KOSPI | shadow_top_section_only_until_gate_passes | shadow_risk_review | False | 29 | 9 | 96.5517 | 23.24624 | -18.025078 |

### Theme News Backfill
- source_backfill_report: runtime_state/reports/learning/kis_theme_news_emitted_news_backfill.json
- source_verify_report: runtime_state/reports/learning/kis_theme_news_emitted_news_backfill_verify.json
- rows_written: 3029
- evidence_rows: 3029
- news_checked_rows: 3029
- kis_news_api_calls: 1425
- strength_levels: {"medium": 2611, "strong": 418}
- no_dummy_data: True
- latency_policy: candidate-only existing-sidecar news enrichment with ticker/date de-duplication; not full-universe news calls during live scan

### UI Required Changes
- web: Place KIS Shadow candidates above the normal result sections, with gate status, production_ready, risk_review_required, and blocking reasons visible.
- web: Keep production_ready=false candidates labeled as Shadow/Risk Review, not as final buy candidates.
- web: Show existing Top1/Top3/Top5 versus KIS challenger delta in the same market/run context before any promotion decision.
- top_deep: Show KIS theme/news summary, evidence score/level, kis_backed, news_checked, and source_timing for each candidate.
- top_deep: Display coverage warnings when theme/news evidence is missing or not mature for training.
- discord: Include the same KIS gate, Shadow/Risk Review status, and theme/news summary in scan-result and precision-analysis messages.
- discord: Avoid promotion wording in Discord until the same gate used by the web UI passes.
- promotion_guard: Production switch requires both markets to have completed comparison reports and no hidden missing-field drift across web, archive, Top Deep, Discord, and Supabase rows.
- promotion_guard: KIS model promotion remains blocked when tail-risk gates fail even if average return delta is positive.
