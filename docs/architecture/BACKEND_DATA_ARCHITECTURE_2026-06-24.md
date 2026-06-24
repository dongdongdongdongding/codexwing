# 백엔드 및 데이터 구조 - 2026-06-24

이 문서는 백엔드가 수행하는 일, 데이터 소스, 수집/정규화/저장/활용 경로, 운영 스캔과 모델 producer의 차이를 정리한다.

## 확인한 근거 파일

- 실행: `multi_agent/tools/run_daily_ops.sh`, `multi_agent/tools/run_kr_daily_auto_scans.py`, `multi_agent/tools/run_kis_operational_kr_scan.py`
- 파이프라인: `multi_agent/workflows/non_ui_scan_pipeline.py`, `legacy_export.py`, `legacy_orchestration.py`
- 스캐너: `modules/scanner_runtime.py`, `modules/scanner_services.py`, `modules/scan_policy.py`, `modules/strategy_family_policy.py`
- 데이터: `modules/kis_openapi.py`, `modules/kis_operational_adapter.py`, `modules/kis_operational_prefilter.py`, `modules/market_data.py`
- 모델 producer: `report_swing_ensemble.py`, `report_kospi_intraday_swing.py`, `report_kosdaq_intraday_vwap_guard.py`
- 인트라데이 모델: `modules/kosdaq_intraday_vwap_guard.py`, `modules/intraday_candidate_registry.py`
- 저장: `modules/db_schema.py`, `modules/db_manager.py`, `modules/scan_persistence.py`, `modules/runtime_artifact_store.py`, `modules/post_scan_outcome_ledger.py`, `modules/top_deep_report.py`
- 메모리 계층: `multi_agent/storage/memory_layers.py`
- 런타임 정책: `docs/migration/RUNTIME_ARTIFACT_POLICY.md`

## 전체 백엔드 모양

현재 백엔드는 두 갈래가 공존한다.

1. 범용 스캐너/멀티에이전트 파이프라인
   - 시장/모드/프로필을 받아 ticker universe를 스캔한다.
   - scanner handoff, aggregation, backtest diagnostics, market/news context, planner, postmortem을 만든다.
   - Top Deep, archive, Supabase, runtime artifact를 남긴다.

2. 모델 레인 producer
   - 특정 검증 모델을 고정 계약으로 실행한다.
   - 자체 ledger를 쓴다.
   - production flag가 켜져 있으면 직접 `market_scan_results`와 `scan_deep_reports`에 row를 넣는다.
   - 현재 핵심은 `swing_ensemble`, `kospi_intraday`, `kosdaq_intraday_3d_t5_vwap_guard`다.

운영에서 중요한 점은 두 경로의 의미가 다르다는 것이다. scanner/planner 후보와 model-lane producer 후보를 같은 gate로 해석하면 안 된다.

## 데이터 소스

### KIS Open API

파일: `modules/kis_openapi.py`

역할:

- KR daily OHLCV
- KR minute OHLCV
- rank API
- VI status
- quote snapshot
- stock info
- financial ratio
- investor flow
- symbol-scoped news

live call은 보통 `KIS_ENABLE_LIVE_CALLS=1`이 필요하다. import 자체는 안전해야 하지만 실제 네트워크 수집은 flag와 credential에 의존한다.

### FinanceDataReader/FDR

역할:

- 일봉 가격 fallback
- SWING ensemble 학습/스코어링의 daily price source
- KOSPI intraday producer의 daily context 보조

FDR은 실시간 체결 품질보다는 daily history와 fallback 성격이 강하다.

### 외부 research cache

위치:

```text
~/research_cache
```

현재 주요 파일:

- `px_long.parquet`: 일봉 장기 panel
- `intraday/{code}.parquet`: 종목별 1분 OHLCV raw store
- `intraday_3d_panel.parquet`: 3일 +5% 인트라데이 모델 학습용 panel
- flow, DART, events, fund, PEAD, shares 등 보조 cache

분봉 raw store는 프로젝트 production scan DB와 별도다. `runtime_state/reports/learning/kr_intraday_model_viability.*` 숫자와 섞으면 안 된다.

### Supabase

주요 테이블:

- `market_scan_results`: 후보 row의 주 저장소
- `scan_deep_reports`: Top Deep 상세 row
- `post_scan_outcome_ledger`: 사후 outcome
- `runtime_artifacts`: JSON/MD/TXT/CSV artifact 저장
- `scan_universe_snapshots`: emitted/rejected universe snapshot
- `agent_realized_outcomes`: realized outcome 계층

`modules/db_manager.py`는 schema drift에 대비해 존재하는 column만 필터링해서 write한다. 새 필드는 `modules/db_schema.py::SCAN_RESULT_COLUMNS`에 반영하는 것이 기준이다.

## 데이터 정규화

### 시장 데이터 정규화

파일: `modules/market_data.py`

역할:

- symbol suffix 변환
- OHLCV column 정규화
- KIS/FDR 데이터의 내부 DataFrame 계약 맞춤
- KR/US ticker 형식 처리

### KIS 정규화

파일: `modules/kis_operational_adapter.py`

역할:

- `normalize_kis_daily_bars`
- `normalize_kis_minute_bars`
- rank membership 정규화
- VI status 정규화
- stock info/financial ratio/quote/investor flow 정규화
- symbol-specific news scope filtering

`kis_intraday_input_hour()`는 현재 KST 시간 또는 `AG_KIS_INTRADAY_INPUT_HOUR`에 따라 KIS minute input hour를 정한다.

### KIS 운영 prefilter

파일: `modules/kis_operational_prefilter.py`

역할:

- 거래량 rank
- 등락률 rank
- 체결강도/거래대금 rank
- VI status
- quote activity
- investor flow

이 값으로 KR 운영 후보 universe를 만든다. 관리/주의/정지/과열 종목 제외 옵션도 포함한다.

## 스캐너 파이프라인

진입점:

```python
multi_agent.workflows.non_ui_scan_pipeline.run_non_ui_scan_pipeline()
```

주요 단계:

1. market, scan_mode, profile, ticker universe를 확정한다.
2. `RUN-*` id를 가진 run context를 만든다.
3. macro context와 market gate를 로드한다.
4. market intelligence/news adjustment를 계산한다.
5. `scan_symbol_with_retry`로 병렬 스캔한다.
6. 통과 후보를 `Decision Score`, `Antigrav` 기준으로 정렬한다.
7. local short-term memory에 `legacy_scan_results.json`을 쓴다.
8. OrchestratorAgent를 실행한다.
9. legacy orchestration으로 scanner/aggregation/backtest/market/planner/postmortem artifact를 만든다.
10. Top Deep report를 생성한다.
11. post-scan outcome ledger를 쓴다.
12. raw scan results와 CSV를 artifact store에 쓴다.
13. scan integrity artifact를 만든다.
14. daily summary와 stale fallback alert를 만든다.
15. `scan_universe_snapshots`를 저장한다.
16. 표준 runtime artifacts를 Supabase에 저장한다.

`scan_mode`는 반드시 유지해야 한다.

- `SWING`: 일봉 스윙 스캐너와 SWING 모델 레인
- `INTRADAY`: 장중 스캐너 후보와 인트라데이 모델 레인

## 후보 평가 로직

### `evaluate_app_kr_candidate`

KR SWING scanner evaluator다.

주요 조건:

- signal column 존재
- 최근 signal hit
- fallback dummy가 아닌 실제 ML inference
- baseline WR/PF filter
- KR market policy/hard filter
- precision gate
- sector gate
- ML probability/surge tag
- profile/rank/theme/context/segment/continuation/quant overlay
- KIS sidecar field

출력:

- UI row
- DB payload
- scanner timeframe profile
- KR universe role
- flow/theme/leader/context field
- expected edge field
- target/stop/hold
- model trace

### `evaluate_intraday_candidate`

범용 scanner `INTRADAY` evaluator다. 현재 KOSDAQ `KR_INTRADAY_3D_T5` producer와는 별도다.

사용 요소:

- 유동성/가격 filter
- EMA trend
- 3-bar breakout
- session open, previous close, intraday return
- ATR 기반 target/stop
- news adjustment
- ML probability
- market gate penalty
- theme overlay
- expected edge profile
- KR universe role
- KIS sidecar

현재 KR intraday scanner 기본 필터 예:

- 최소 가격 `1000`
- `AG_INTRADAY_KR_MIN_VOLUME` 기본 `20000`
- KOSPI turnover 기본 `700,000,000`
- KOSDAQ/KR turnover 기본 `300,000,000`

## 모델 레인 producer

### SWING Ensemble

파일: `multi_agent/tools/report_swing_ensemble.py`

역할:

- `px_long.parquet`에서 trailing daily price feature로 학습
- LGBM/XGB/ExtraTrees ensemble
- label: `ft_5_5`
- KOSPI/KOSDAQ 모두 score
- 최근 20D 거래대금 `>= min_liq * 1e8`
- market별 top probability percentile 추출
- `swing_ensemble_ledger.jsonl` 기록
- production ON이면 `_route_live`로 Supabase live surface write

### KOSPI Intraday

파일: `multi_agent/tools/report_kospi_intraday_swing.py`

역할:

- `~/research_cache/intraday_3d_panel.parquet`와 `px_long.parquet` daily context로 3모델 ensemble 학습
- 현재/full-session KIS minute bar fetch
- intraday path feature 생성
- daily context feature 생성
- `liq>=100억`, `close_vwap>=0`, `idx_vol20>=8`
- top2 emit
- `kospi_intraday_swing_ledger.jsonl` 기록
- `decision_bucket=kospi_intraday`로 live route

주의:

- live producer 안에서 학습한다. KOSDAQ처럼 고정 joblib bundle을 읽는 구조보다 artifact 안정성이 약하다.

### KOSDAQ Intraday VWAP Guard

파일:

- `modules/kosdaq_intraday_vwap_guard.py`
- `multi_agent/tools/report_kosdaq_intraday_vwap_guard.py`

모델 bundle:

```text
models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl
```

역할:

- KOSDAQ universe 구성
- 15:00 이전/시점 분봉만 사용
- open gap, pre-entry return/high/low/range, close location, VWAP distance, pre-entry traded value 등 feature 생성
- daily previous context 병합
- LightGBM + 이전월 isotonic calibration
- `p_cal>=0.80`
- `pre_vwap_dist_pct>=0`
- daily top2
- `>=30억` main lane, `>=100억` tradeability lane
- `target_touch3d_t5`, `ret3d`, `mfe3`, `mae3` ledger 기록
- production ON이면 `scan_mode=INTRADAY`로 live surface write

현재 이 레인이 운영 목표와 가장 가깝다.

## 저장 구조

### `market_scan_results`

후보 row의 중심 테이블이다. scanner 후보와 producer direct route row가 모두 들어갈 수 있다. `scan_mode`, `decision_bucket`, `strategy_family`를 반드시 봐야 한다.

### `scan_deep_reports`

Top Deep 상세 surface다. web/Discord가 후보 상세를 읽는 주요 테이블이다.

### `runtime_artifacts`

`modules/runtime_artifact_store.py`가 JSON/MD/TXT/CSV artifact를 저장한다. 로컬 artifact와 DB artifact가 함께 존재할 수 있다.

### `scan_universe_snapshots`

`modules/scan_persistence.py::_persist_scan_universe_snapshot`가 emitted/rejected universe row를 저장한다. scan 시점에는 forward return이 NULL이고, 이후 outcome backfill이 채운다.

### 로컬 `runtime_state`

운영 상태와 리포트 저장 위치다.

- `runtime_state/artifacts/RUN-*`: run별 raw artifact
- `runtime_state/shared_working/RUN-*`: handoff/planner output
- `runtime_state/reports/*`: validation, learning, experimental, trading report
- `runtime_state/long_term/*`: profile/theme/ticket/learning memory

이 디렉터리는 일반 소스코드가 아니다. generated artifact가 많이 생기므로 무조건 커밋 대상이 아니다.

## 멀티에이전트 메모리 계층

개념 계층:

- local short-term memory: run 중간 산출물
- shared working memory: 에이전트 간 handoff
- long-term memory: 지속 상태, profile/theme/cache
- artifact store: run/report 증거 파일

이 계층은 UI 텍스트나 agent chatter가 아니라 구조화된 상태여야 한다.

## outcome/validation pipeline

주요 작업:

- `update_realized_outcomes.py`
- `update_outcome_return_metrics.py`
- `backfill_scanner_full_returns.py`
- `build_paper_trade_ledger.py`
- `report_prediction_validation.py`
- `report_kr_walkforward_release_gate.py`
- `report_kr_cohort_release_gate.py`
- producer별 ledger resolve

운영 판단은 scan 당시 점수보다 outcome ledger와 forward validation을 우선해야 한다.

## 현재 백엔드 리스크

1. KOSDAQ intraday bucket이 아직 `MODEL_VALIDATED_LANES`에 없다.
2. KOSPI intraday는 live producer 안에서 학습한다.
3. `runtime_state`에 많은 generated file이 남아 있어 commit hygiene가 중요하다.
4. Supabase timeout 이슈가 backfill/조회 경로를 막을 수 있다.
5. research cache는 repo 밖에 있어 재현 시 경로/파일 존재가 필수다.
6. `models/`에는 오래된/retired artifact도 남아 있어 파일 존재만으로 운영 상태를 판단하면 안 된다.
