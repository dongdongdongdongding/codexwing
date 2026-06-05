# KIS Replacement Roadmap

## Summary
- operator_answer: KIS is now the default KR daily operational scan source with a legacy scanner fallback. Controlled production replacement is acceptable for the source path, but KIS-augmented model promotion remains blocked until real KIS sidecar/prefilter rows have enough resolved outcomes.
- current_replacement_level: production-primary default with legacy fallback; model lift pending
- source_only_change: The promotion changes the daily operational execution path, archives KIS prefilter/sidecar features, and now exposes those features to challenger training with maturity gates; scanner/planner scoring contracts remain compatible.
- endpoint_ok_count: 25
- endpoint_failed_count: 0

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
| rank_vi_news_financial | rank membership, VI status, news-title count, and financial ratios persist as model sidecar fields | KIS operational prefilter rank/VI/quote/flow payload is archived per run; news enrichment remains opt-in because of latency budget |
| consumer_parity | scanner, Discord, archive, top-deep, Supabase, and learning outputs consume the same normalized contract | daily KR autoscan defaults to KIS operational primary with explicit legacy fallback; Supabase compatibility was verified on live KIS rows; Top Deep now records KIS source timing when sidecar evidence is present |
| candidate_only_deep_analysis | Deep analysis runs only on emitted Top/Admission/Exception candidates, never on the whole raw universe | implemented_and_unit_tested |
| deep_analysis_source_timing | scan_as_of and deep_analysis_as_of are stored separately with price/flow/news source snapshots | implemented_and_unit_tested |
| nightly_full_universe_validation | Full-universe KIS validation is checkpointed per item and remains a validation lane, not the operational scan path | implemented_and_unit_tested |
| model_lift | KIS-augmented challenger beats current segment gates without worse tail loss | {"challenger_report": "runtime_state/reports/learning/kis_augmented_challenger_readiness.json", "prefilter_outcome_label_rows": 0, "prefilter_rows": 0, "readiness_status": "blocked", "required_days": 10, "required_rows": 60, "sidecar_outcome_label_rows": 0, "sidecar_rows": 2} |

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
