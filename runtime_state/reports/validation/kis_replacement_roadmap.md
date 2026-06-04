# KIS Replacement Roadmap

## Summary
- operator_answer: KIS can become the KR primary operational data source, but the current safe state is KIS-first test mode plus sidecar collection, not unconditional production default.
- current_replacement_level: contract-ready, not production-promoted
- source_only_change: The implementation keeps scanner/planner decisions unchanged by default and changes only optional source adapters behind explicit environment toggles.
- endpoint_ok_count: 17
- endpoint_failed_count: 2

## Implemented Now
- market_data_toggle: AG_KR_MARKET_DATA_PROVIDER=kis_first or kis_only
- investor_flow_toggle: AG_KR_INVESTOR_FLOW_PROVIDER=kis_first or kis_only
- scanner_sidecar_toggle: AG_ENABLE_KIS_SIDECAR=1
- sidecar_adapter: modules.kis_operational_adapter
- production_default_changed: False
- legacy_fallback_preserved: True

## 100 Percent Replacement Gates
| Gate | Target | Current Status |
|---|---|---|
| source_contract | KIS payloads map to existing OHLCV, quote, and whale-flow fields | implemented_and_unit_tested |
| quote_universe | 100% effective KR quote coverage with retry/cache | {"effective_quote_success_rate_pct": 100.0, "source": "prior live KIS readiness sweep"} |
| ohlcv_history | >=99% KOSPI/KOSDAQ daily OHLCV availability for scanner candidates and archive replay | adapter_added; live dual-run not complete |
| intraday_bars | same-day minute bars support intraday refresh without stale yfinance dependency | adapter_added; production replay not complete |
| investor_flow | KIS stock investor flow works after the exchange time gate and falls back explicitly when unavailable | KIS-first toggle added; prior live check saw time-gated failures |
| rank_vi_news_financial | rank membership, VI status, news-title count, and financial ratios persist as model sidecar fields | sidecar contract and scanner payload hook added; live rank/VI/news persistence still pending |
| consumer_parity | scanner, Discord, archive, top-deep, Supabase, and learning outputs consume the same normalized contract | not promoted to production default |
| model_lift | KIS-augmented challenger beats current segment gates without worse tail loss | needs sidecar archive and challenger training |

## Model Upgrade Plan
- sidecar_persistence: Persist KIS quote, OHLCV summary, flow, rank, VI, news-title, and financial fields next to KR scanner rows. Success: No recommendation order change; complete KIS sidecar for eligible KR candidates.
- dual_run_quality_report: Compare KIS-first and legacy outputs for scanner rows, archive rows, Discord lookup, and top-deep reports. Success: No silent missing-field drift; all consumer payloads carry source warnings.
- challenger_training: Train KIS-augmented segment challengers with feature groups on/off. Success: Segment Top5 positive-rate, average 5D return, bad-path rate, and stop-first rate improve.
- promotion: Promote KIS primary with explicit fallback after gates pass. Success: Production KR scanner uses KIS primary without lowering current release gates.
