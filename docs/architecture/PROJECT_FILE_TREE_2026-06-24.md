# 프로젝트 트리와 파일별 사용 상태 - 2026-06-24

이 문서는 현재 저장소의 주요 파일/디렉터리 구조, 목적, 운영 사용 여부를 정리한다. 기준은 2026-06-24 현재 파일 트리, daily ops, 자동 스캔, producer, UI/Discord 코드다.

## 사용 상태 정의

| 상태 | 의미 |
|---|---|
| 운영 사용 | daily ops, 자동 스캔, Streamlit, Discord, live producer, 저장/조회 경로에서 직접 쓰인다. |
| 운영 보조 | 운영 진단, validation, archive, ledger, backfill, UI 보조에 쓰인다. |
| 연구/검증 | 모델 탐색, 리서치 리포트, sweep, backtest, challenger 학습용이다. |
| 레거시/호환 | 과거 시스템 호환 또는 fallback 용도다. 현재 핵심 edge로 해석하면 안 된다. |
| 문서/스키마 | 운영/마이그레이션/계약 설명 또는 DB 스키마다. |
| 생성물/상태 | 런타임 산출물이다. 일반 소스코드처럼 커밋하면 안 된다. |
| 미사용/주의 | 파일은 있으나 현재 운영 경로에서 핵심 사용이 확인되지 않았거나, retired/inverted/stale 이력이 있다. |

## 최상위 구조

```text
swing-main/
├── README.md
├── AGENTS.md
├── app.py
├── app_public.py
├── auto_bot.py
├── retrain_ml.py
├── train_*.py
├── analyze_*.py
├── backtest_framework.py
├── modules/
├── multi_agent/
├── ui/
├── docs/
├── models/
├── scripts/
├── tests/
├── agents/
├── runtime_state/
├── .beads/
├── .codex/
└── requirements.txt
```

## 최상위 파일

| 파일 | 목적 | 사용 상태 | 비고 |
|---|---|---|---|
| `README.md` | 현재 운영 기준 진입 문서 | 문서/운영 기준 | 한국어 기준 문서로 교체됨. |
| `AGENTS.md` | Codex/Claude/agent 작업 규칙, Beads 규칙, 세션 종료 규칙 | 운영 사용 | 모든 작업에서 따라야 하는 프로젝트 규칙. |
| `.env.example` | 환경 변수 예시 | 운영 보조 | secrets는 커밋 금지. |
| `.env.local` | 로컬 실제 환경값 | 운영 사용/비공개 | git 추적 대상이면 안 된다. |
| `.gitignore` | generated/runtime/model ignore 정책 | 운영 보조 | runtime/model hygiene와 관련. |
| `requirements.txt` | Python dependency 목록 | 운영 사용 | 설치/실행 전제. |
| `app.py` | Streamlit 메인 UI | 운영 사용 | 아직 큰 composition 파일. scanner, archive, advanced view 일부 포함. |
| `app_public.py` | 공개/간소 UI 성격 파일 | 레거시/보조 | 현재 핵심 운영 진입은 `app.py`. |
| `auto_bot.py` | 과거 자동 봇 | 레거시/주의 | `PROJECT_HISTORY.md`상 과거 로직 불일치 이력. 현재 핵심 자동화는 `multi_agent/tools/run_kr_daily_auto_scans.py`. |
| `retrain_ml.py` | phase25/legacy 모델 재학습 | 레거시/연구 | 일부 phase25 모델 생성. 현재 핵심 intraday 모델 아님. |
| `train_model.py` | 구 모델 학습 | 레거시/연구 | 현재 daily ops 직접 호출 아님. |
| `train_ml_targets.py` | ML target 학습 | 연구/검증 | 현재 핵심 live producer 직접 호출 아님. |
| `train_global_brain.py` | global brain 모델 학습 | 연구/레거시 | 운영 메인 아님. |
| `backtest_framework.py` | 백테스트 프레임워크 | 연구/검증 | 운영 producer보다 연구용 성격. |
| `analyze_accuracy.py` | 정확도 분석 스크립트 | 연구/검증 | ad hoc 분석용. |
| `analyze_short_term.py` | 단기 분석 스크립트 | 연구/검증 | ad hoc 분석용. |
| `sector_analysis.py` | 섹터 분석 | 연구/검증 | 운영 core 아님. |
| `add_columns.sql` | DB column 추가 SQL | 문서/스키마 | phase25 등 과거 column 포함. |
| `optimal_params.json` | 과거 최적 파라미터 | 레거시/연구 | 현재 live intraday 계약의 source of truth 아님. |
| `gpt_upgrade.xlsx` | 스프레드시트 자료 | 문서/보조 | 운영 실행 파일 아님. |
| `issues_graph.html` | 이슈 그래프 시각화 | 문서/보조 | generated/inspection 성격. |
| `PROJECT_HISTORY.md` | 프로젝트 과거 이력 | 문서/히스토리 | 현재 운영 기준은 최신 docs 우선. |
| `SETUP_GUIDE.md` | 설치/실행 안내 | 문서 | 일부 오래된 내용 가능. |
| `document.md` | 독립 문서 | 미사용/주의 | 현재 운영 기준 문서 아님. |
| `scheduler_and_scan_archive_plan.md` | 과거 계획 | 문서/히스토리 | 현재 구현과 다를 수 있음. |
| `prediction_accuracy_improvement_master_plan.md` | 정확도 개선 계획 | 문서/히스토리 | 연구 계획 성격. |
| `ranking_diagnosis_and_accuracy_improvement_plan.md` | 랭킹 진단 계획 | 문서/히스토리 | 현재 production truth 아님. |

## `modules/` 구조

`modules/`는 스캐너, 데이터 어댑터, UI 해석, persistence, 정책, 리서치 helper가 섞인 엔진 모듈이다.

### 운영 핵심 모듈

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `modules/scanner_runtime.py` | ticker 스캔 실행, retry, runtime orchestration | 운영 사용 |
| `modules/scanner_services.py` | KR/US 후보 evaluator, SWING/INTRADAY candidate logic | 운영 사용 |
| `modules/quant_analysis.py` | `QuantStrategy`, 기술/ML 분석, phase25 호환 | 운영 사용/레거시 혼재 |
| `modules/market_data.py` | FDR/KIS 데이터 정규화, OHLCV 로딩 | 운영 사용 |
| `modules/kis_openapi.py` | KIS API client | 운영 사용 |
| `modules/kis_operational_adapter.py` | KIS payload를 내부 계약으로 정규화 | 운영 사용 |
| `modules/kis_operational_prefilter.py` | KIS rank/quote 기반 KR 후보 universe 구성 | 운영 사용 |
| `modules/db_schema.py` | Supabase column 계약 | 운영 사용 |
| `modules/db_manager.py` | Supabase read/write, schema drift 방어 | 운영 사용 |
| `modules/scan_persistence.py` | scan_universe_snapshot persistence | 운영 사용 |
| `modules/runtime_artifact_store.py` | local/DB runtime artifact 저장 | 운영 사용 |
| `modules/post_scan_outcome_ledger.py` | scan 이후 outcome ledger | 운영 사용 |
| `modules/top_deep_report.py` | Top Deep 리포트 생성 | 운영 사용 |
| `modules/candidate_interpretation.py` | stored row를 운영자 해석으로 변환 | 운영 사용 |
| `modules/operational_candidate_scoring.py` | 모델 레인 whitelist/운영 점수 | 운영 사용 |
| `modules/strategy_family_policy.py` | 전략 family 정책 | 운영 사용 |
| `modules/scan_policy.py` | scan 정책/필터 | 운영 사용 |

### 현재 인트라데이 관련 핵심

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `modules/kosdaq_intraday_vwap_guard.py` | KOSDAQ 15:00 VWAP guard feature/scoring/selection | 운영 사용 |
| `modules/intraday_candidate_registry.py` | 인트라데이 후보 registry와 gate 정의 | 운영/연구 혼재 |
| `modules/kr_intraday_adapter_contract.py` | KR intraday adapter 계약 | 운영 보조 |
| `modules/kosdaq_3d_continuation_ranker.py` | KOSDAQ 3D continuation ranker | 연구/보조 |
| `modules/kosdaq_shadow_observer.py` | KOSDAQ shadow 관찰 | 연구/관찰 |

### 수급/테마/뉴스/시장 컨텍스트

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `modules/market_intelligence.py` | 시장 intelligence/context | 운영 보조 |
| `modules/news_analysis.py` | 뉴스 분석 | 운영 보조 |
| `modules/naver_news_scraper.py` | Naver 뉴스 수집 | 운영 보조/레거시 |
| `modules/kis_news_scope.py` | KIS 뉴스 symbol scope 검증 | 운영 보조 |
| `modules/kis_theme_news_evidence.py` | 테마/뉴스 evidence | 운영 보조 |
| `modules/theme_*` | theme catalog/router/signal/transfer/momentum | 운영 보조/연구 |
| `modules/kr_stock_theme_master.py` | KR theme master | 운영 보조 |
| `modules/kis_theme_valuechain.py` | KIS 테마 value-chain | 운영 보조 |
| `modules/kis_ticker_valuechain_master.py` | ticker value-chain master | 운영 보조 |
| `modules/us_overnight_theme_lead.py` | 미국 야간 lead -> KR 테마 prior | 운영 보조 |
| `modules/us_sector_enrichment.py` | US sector enrichment | 보조 |

### 리스크/정책/사후분석

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `modules/loss_risk_features.py` | 손실 위험 feature | 운영 보조 |
| `modules/structural_exclusion_risk.py` | 구조적 제외 리스크 | 운영 보조 |
| `modules/overextension.py` | 과열/연장 리스크 | 운영 보조 |
| `modules/execution_stop_display.py` | stop/청산 표시 | 운영 보조 |
| `modules/horizon_policy.py` | 보유 horizon 정책 | 운영 보조 |
| `modules/portfolio_exposure.py` | 포트폴리오 노출 | 운영 보조 |
| `modules/tradable_pnl.py` | 거래 가능 PnL 계산 | 운영 보조 |
| `modules/good_stock_falling_postmortem.py` | 좋은 종목 하락 postmortem | 연구/보조 |
| `modules/missed_winner_postmortem.py` | 놓친 winner postmortem | 연구/보조 |
| `modules/incident_regression.py` | incident regression | 운영 보조 |

### 모델/레거시/검증 모듈

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `modules/phase25_governance.py` | phase25 OOS governance | 레거시/보조 |
| `modules/model_governance.py` | 모델 governance | 운영 보조 |
| `modules/kis_model_features.py` | KIS sidecar model feature | 연구/보조 |
| `modules/kis_model_gate.py` | KIS model gate | 연구/보조 |
| `modules/kis_shadow_model_runtime.py` | KIS shadow model runtime | 연구/보조 |
| `modules/regime_*` | regime classifier/router/policy/calibration | 연구/보조 |
| `modules/regime_conditional_scorer.py` | regime conditional scorer | 연구/레거시 |
| `modules/practical_entry_gate.py` | Practical entry gate | 레거시/주의 |
| `modules/next_day_explosive_radar.py` | 익일 급등 radar | 연구/보조 |
| `modules/experimental_target_touch.py` | target touch 실험 | 연구 |
| `modules/scan_universe_admission.py` | scan universe admission | 연구/운영 보조 |

### UI/표시 모듈

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `modules/ui_helpers.py` | Streamlit 표시 helper, legacy card logic | 운영 사용/레거시 혼재 |
| `modules/operational_readiness_ui.py` | 운영 판정 상세 copy | 운영 사용 |
| `modules/korean_display_copy.py` | 한국어 표시 copy | 운영 보조 |
| `modules/segment_accuracy.py` | segment accuracy 표시 | 운영 보조 |
| `modules/scanner_product_contract.py` | scanner product semantics | 문서/운영 보조 |
| `modules/scanner_performance_contract.py` | scanner performance contract | 운영 보조 |

### Discord subpackage

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `modules/discord_integration/commands.py` | slash command 정의 | 운영 사용 |
| `modules/discord_integration/config.py` | Discord 설정 | 운영 사용 |
| `modules/discord_integration/permissions.py` | 권한 검사 | 운영 사용 |
| `modules/discord_integration/register.py` | command 등록 | 운영 사용 |
| `modules/discord_integration/scan_executor.py` | Discord scan job 실행 | 운영 사용 |
| `modules/discord_integration/renderers.py` | embed 렌더링 | 운영 사용 |
| `modules/discord_integration/delivery.py` | 메시지 전달 | 운영 사용 |

## `multi_agent/` 구조

`multi_agent/`는 비UI 파이프라인, 에이전트 runtime, 도구 스크립트, schema, storage를 담는다.

### 핵심 workflow

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `multi_agent/workflows/non_ui_scan_pipeline.py` | Streamlit 없이 전체 scan pipeline 실행 | 운영 사용 |
| `multi_agent/workflows/legacy_orchestration.py` | scanner/aggregation/backtest/context/planner/postmortem 연결 | 운영 사용 |
| `multi_agent/workflows/legacy_export.py` | legacy format export | 운영 보조 |
| `multi_agent/workflows/scaffold_run.py` | run directory/context 생성 | 운영 보조 |
| `multi_agent/workflows/daily_summary.py` | daily summary 생성 | 운영 보조 |
| `multi_agent/workflows/run_quality.py` | run quality 검사 | 운영 보조 |
| `multi_agent/workflows/postmortem.py` | postmortem workflow | 운영 보조 |
| `multi_agent/workflows/alerts.py` | alert workflow | 운영 보조 |
| `multi_agent/workflows/outcome_buckets.py` | outcome bucket 처리 | 운영 보조 |

### agents

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `multi_agent/agents/scanner.py` | scanner agent | 운영/프레임워크 |
| `multi_agent/agents/aggregation.py` | aggregation agent | 운영/프레임워크 |
| `multi_agent/agents/backtest_runtime.py` | backtest runtime | 운영 보조 |
| `multi_agent/agents/market_context_runtime.py` | market/news context runtime | 운영 보조 |
| `multi_agent/agents/planner_runtime.py` | planner runtime | 운영 사용 |
| `multi_agent/agents/orchestrator_runtime.py` | orchestrator runtime | 운영 사용 |
| `multi_agent/agents/pm_planner.py` | PM planner | 운영 보조 |
| `multi_agent/agents/kr_quant_reranker.py` | KR quant reranker | 연구/보조 |
| `multi_agent/agents/base.py` | agent base class | 운영/프레임워크 |

### tools: 운영 직접 호출

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `multi_agent/tools/run_daily_ops.sh` | 일일 운영 배치 | 운영 사용 |
| `multi_agent/tools/run_kr_daily_auto_scans.py` | KR 자동 스캔 | 운영 사용 |
| `multi_agent/tools/run_kis_operational_kr_scan.py` | KIS primary 운영 스캔 | 운영 사용 |
| `multi_agent/tools/report_swing_ensemble.py` | SWING ensemble live producer | 운영 사용 |
| `multi_agent/tools/report_kospi_intraday_swing.py` | KOSPI intraday live producer | 운영 사용 |
| `multi_agent/tools/report_kosdaq_intraday_vwap_guard.py` | KOSDAQ intraday live producer | 운영 사용 |
| `multi_agent/tools/update_realized_outcomes.py` | realized outcome 갱신 | 운영 사용 |
| `multi_agent/tools/update_outcome_return_metrics.py` | return metrics 보강 | 운영 사용 |
| `multi_agent/tools/backfill_scanner_full_returns.py` | scanner full return backfill | 운영 보조 |
| `multi_agent/tools/export_scan_archive_learning_dataset.py` | archive learning dataset export | 운영 보조 |
| `multi_agent/tools/build_paper_trade_ledger.py` | paper trade ledger | 운영 보조 |
| `multi_agent/tools/report_prediction_validation.py` | prediction validation | 운영 보조 |
| `multi_agent/tools/report_kr_walkforward_release_gate.py` | KR walk-forward gate | 운영 보조 |
| `multi_agent/tools/report_kr_cohort_release_gate.py` | KR cohort gate | 운영 보조 |
| `multi_agent/tools/report_daily_model_foundation_gate.py` | daily model foundation gate | 운영 보조 |
| `multi_agent/tools/discord_bot.py` | Discord bot 실행 | 운영 사용 |
| `multi_agent/tools/discord_register_commands.py` | Discord command 등록 | 운영 사용 |
| `multi_agent/tools/discord_setup_doctor.py` | Discord 설정 점검 | 운영 보조 |

### tools: shadow/validation/research

| 범주 | 대표 파일 | 사용 상태 |
|---|---|---|
| PEAD/down shadow | `report_kospi_normal_pead_shadow.py`, `report_firsttouch_down_shadow.py` | 관찰/비활성 |
| KIS touch5/dd10 연구 | `train_scan_universe_admission_challenger.py`, `sweep_kis_sidecar_thresholds.py`, `research_kis_three_stage_ev_ranker.py` | 연구/검증 |
| KIS sidecar/backfill | `backfill_kis_*`, `augment_kis_*`, `save_kis_*` | 연구/백필 |
| 리포트 생성 | `report_*` 다수 | 운영 보조/연구 혼재 |
| experimental | `experimental_*`, `search_*`, `mine_*` | 연구 |
| 설치/스케줄 | `install_*`, `run_outcome_updater.sh` | 운영 보조 |

`multi_agent/tools`에는 170개 이상 파일이 있다. daily ops에 직접 호출되는 파일과 research sweep 파일을 구분해야 한다. 파일명이 `report_`라고 모두 production이 아니다.

### schemas/contracts/storage/config

| 경로 | 목적 | 사용 상태 |
|---|---|---|
| `multi_agent/schemas/*.schema.json` | handoff/report/profile schema | 문서/운영 계약 |
| `multi_agent/contracts/types.py` | 타입 계약 | 운영 보조 |
| `multi_agent/contracts/serialization.py` | 직렬화 helper | 운영 보조 |
| `multi_agent/storage/memory_layers.py` | memory layer read/write | 운영 사용 |
| `multi_agent/storage/long_term_memory.py` | long-term memory | 운영 보조 |
| `multi_agent/config/scan_profiles.py` | scan profile 설정 | 운영 사용 |

## `ui/` 구조

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `ui/theme.py` | Streamlit CSS/theme token | 운영 사용 |
| `ui/components.py` | 공통 UI component | 운영 보조 |
| `ui/scan_cockpit.py` | scanner cockpit UI | 운영 사용 |
| `ui/top_deep_view.py` | Top 분석 탭 | 운영 사용 |
| `ui/archive_data.py` | Archive data access | 운영 사용 |
| `ui/performance_view.py` | 성과 탭 | 운영 보조/advanced |
| `ui/intelligence_view.py` | intelligence 탭 | 운영 보조/advanced |
| `ui/kis_theme_network_view.py` | 테마 네트워크 탭 | 운영 보조/advanced |
| `ui/scan_integrity_view.py` | scan integrity 표시 | 운영 보조 |
| `ui/view_chrome.py` | 화면 chrome/layout helper | 운영 보조 |
| `ui/__init__.py` | package marker | 운영 보조 |

## `models/` 구조

모델 파일은 존재 여부와 운영 사용 여부가 다르다.

### 현재 핵심 사용

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl` | KOSDAQ 15:00 VWAP guard live model | 운영 사용 |
| `models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_returnmax.pkl` | KOSDAQ returnmax 변형 | 연구/주의 |
| `models/kr_intraday_3d_t5/kosdaq_liq30_1400_lgbm_isotonic.pkl` | 14:00 변형 | 연구/주의 |

### 레거시/보조 모델

| 파일/패턴 | 목적 | 사용 상태 |
|---|---|---|
| `models/phase25_*` | phase25 legacy ML | 레거시/주의 |
| `models/firsttouch_down_v1.pkl` | down shadow model | 비활성/관찰 |
| `models/kosdaq_3d_continuation_ranker.pkl` | continuation ranker | 연구/보조 |
| `models/kr_lane_champions/*.pkl` | KR lane champion models | 연구/보조 |
| `models/scan_universe_challengers/*.pkl` | KIS/touch5/dd10 challenger models | 연구/검증 |
| `models/model_5pct_*`, `universal_rf.pkl`, `xgb_meta.json`, `optimal_threshold.pkl` | 과거/범용 모델 | 레거시/주의 |
| `models/regime_scan_policies.json`, `regime_ticker_profiles.json` | regime 정책/profile | 연구/보조 |
| `models/theme_catalog_kr.json`, `theme_transfer_us_to_kr.json` | theme catalog/transfer | 운영 보조 |

## `docs/` 구조

| 경로 | 목적 | 사용 상태 |
|---|---|---|
| `docs/operations/` | 운영 매뉴얼, Discord, scanner contract, intraday adapter | 문서/운영 기준 |
| `docs/architecture/` | 현재 아키텍처/프론트/백엔드/파일 트리 | 문서/운영 기준 |
| `docs/research/` | 연구 여정, 전략, 성과 roadmap | 문서/연구 기준 |
| `docs/migration/` | DB SQL, 과거 migration, 감사/roadmap | 문서/스키마/히스토리 |
| `docs/model_lanes_consumer_integration.md` | 모델 레인 consumer 통합 | 문서/일부 stale 가능 |

현재 기준 문서는 2026-06-24 날짜가 붙은 파일이다.

## `scripts/` 구조

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `scripts/issue` | Beads shortcut | 운영 사용 |
| `scripts/run_kr_daily_auto_scans.sh` | KR daily auto scan wrapper | 운영 보조 |
| `scripts/run_discord_bot.sh` | Discord bot wrapper | 운영 보조 |
| `scripts/keep_bd_dolt_alive.sh` | Beads Dolt server 유지 | 운영 보조 |
| `scripts/launchd/*.plist` | macOS launchd 등록 파일 | 운영 보조 |
| `scripts/launchd/wrappers/*.sh` | launchd wrapper | 운영 보조 |

## `tests/` 구조

`tests/`는 140개 이상 테스트 파일을 포함한다. 핵심 커버리지 범주:

- KIS adapter/openapi/prefilter
- scanner runtime/persistence/product contract
- UI archive/top_deep/theme/performance
- Discord integration
- post-scan outcome ledger
- runtime artifact store
- KOSDAQ intraday VWAP guard
- KOSPI NORMAL PEAD shadow
- KR daily auto scan runner
- KIS touch5/dd10 research
- model governance/phase25 governance
- strategy family policy

문서만 바꿀 때는 전체 테스트를 매번 돌릴 필요는 없지만, 코드 변경 시 관련 테스트를 선택 실행해야 한다.

## `agents/` 구조

| 파일 | 목적 | 사용 상태 |
|---|---|---|
| `agents/scanner_agent.md` | Scanner Agent 역할 문서 | 문서/계약 |
| `agents/aggregation_agent.md` | Aggregation Agent 역할 문서 | 문서/계약 |
| `agents/backtest_agent.md` | Backtest Agent 역할 문서 | 문서/계약 |
| `agents/market_news_agent.md` | Market/News Agent 역할 문서 | 문서/계약 |
| `agents/pm_planner_agent.md` | PM Planner Agent 역할 문서 | 문서/계약 |
| `agents/orchestrator_agent.md` | Orchestrator Agent 역할 문서 | 문서/계약 |

AGENTS.md의 mandatory agent 개념과 연결된다.

## `runtime_state/` 구조

| 경로 | 목적 | 사용 상태 |
|---|---|---|
| `runtime_state/artifacts/RUN-*` | run별 raw artifact | 생성물/상태 |
| `runtime_state/shared_working/RUN-*` | 에이전트 handoff/planner output | 생성물/상태 |
| `runtime_state/reports/experimental` | experimental/live producer report | 생성물/일부 추적 |
| `runtime_state/reports/learning` | learning/validation report | 생성물/일부 추적 |
| `runtime_state/reports/validation` | validation report | 생성물/일부 추적 |
| `runtime_state/reports/trading` | paper ledger | 생성물/일부 추적 |
| `runtime_state/long_term` | long-term memory/cache | 생성물/상태 |

주의:

- 이 디렉터리는 현재 dirty file이 많다.
- 문서 작업과 무관한 generated file은 건드리지 않는다.
- 커밋 여부는 `docs/migration/RUNTIME_ARTIFACT_POLICY.md` 기준으로 판단한다.

## 숨김/도구 디렉터리

| 경로 | 목적 | 사용 상태 |
|---|---|---|
| `.beads/` | Beads/Dolt issue DB | 운영 사용 |
| `.codex/` | Codex skill/config | 운영 보조 |
| `.claude/` | Claude skill/config | 운영 보조 |
| `.pytest_cache/` | pytest cache | 생성물, 커밋 불필요 |
| `catboost_info/` | CatBoost 학습 산출물 | 생성물/연구, 커밋 주의 |

## 운영상 중요한 구분

1. `app.py`는 UI entrypoint지만 모델의 source of truth가 아니다.
2. `multi_agent/tools/run_daily_ops.sh`가 현재 일일 운영의 실제 목록이다.
3. `run_kr_daily_auto_scans.py`는 자동 스캔 entrypoint다.
4. `report_kosdaq_intraday_vwap_guard.py`는 현재 KOSDAQ 인트라데이 핵심 producer다.
5. `models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl`만 KOSDAQ live intraday 핵심 모델 artifact로 본다.
6. `models/phase25_*`는 레거시/호환 모델이며 현재 목표 달성 모델로 해석하지 않는다.
7. `runtime_state`는 운영 증거이지만 대부분 generated state다.
8. `docs/research`의 과거 연구 문서는 히스토리이고, 최신 교정은 2026-06-24 문서를 우선한다.

## 다음 파일 구조 개선 포인트

- `app.py`의 archive/deep-dive composition 추가 분리
- KOSPI intraday 모델을 producer 내부 학습에서 versioned artifact로 분리
- KOSDAQ intraday bucket을 model-lane consumer whitelist에 추가
- `models/`의 retired/active 상태 metadata 정리
- `multi_agent/tools`의 production/research/backfill 분류 문서화 또는 subdirectory 분리
- runtime_state 추적 정책 재점검
