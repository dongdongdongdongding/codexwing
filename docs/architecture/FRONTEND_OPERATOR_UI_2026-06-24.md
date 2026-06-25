# 프론트엔드, Discord, 디자인 구조 - 2026-06-24

이 문서는 운영자가 실제로 보는 화면과 명령, 즉 Streamlit UI, Discord command, 디자인 시스템, 데이터 로딩 경로, 현재 consumer gap을 정리한다.

## 확인한 근거 파일

- `app.py`
- `ui/theme.py`
- `ui/components.py`
- `ui/scan_cockpit.py`
- `ui/top_deep_view.py`
- `ui/archive_data.py`
- `ui/performance_view.py`
- `ui/scan_integrity_view.py`
- `ui/kis_theme_network_view.py`
- `ui/intelligence_view.py`
- `ui/view_chrome.py`
- `modules/ui_helpers.py`
- `modules/operational_readiness_ui.py`
- `modules/candidate_interpretation.py`
- `modules/operational_candidate_scoring.py`
- `modules/discord_integration/commands.py`
- `modules/discord_integration/renderers.py`
- `modules/discord_integration/scan_executor.py`
- `multi_agent/tools/discord_bot.py`
- `multi_agent/tools/discord_register_commands.py`

## Streamlit의 역할

`app.py`가 아직 메인 페이지 composition entrypoint다. 여러 화면이 `ui/*`로 분리됐지만, `app.py`에는 여전히 scanner launch, global status, archive/deep-dive 구성 로직이 많이 남아 있다.

UI는 모델의 진실 공급원이 아니다. UI는 아래 저장소를 읽어 보여주는 운영 표면이다.

- local runtime artifacts
- Supabase `market_scan_results`
- Supabase `scan_deep_reports`
- Supabase/local runtime artifacts
- `runtime_state/reports`의 최신 report JSON

UI는 저장된 근거와 계약을 표시해야 하며, 누락 값을 임의로 만들어서는 안 된다.

## 기본 탭 구조

`AG_UI_ADVANCED`가 꺼져 있거나 unset이면 기본 탭은 아래 3개다.

- `스캐너`
- `Top 분석`
- `아카이브`

`AG_UI_ADVANCED=1`이면 아래 고급 탭이 추가된다.

- `인텔리전스`
- `테마 네트워크`
- `성과`
- `정밀분석`

기본 운영 화면은 의도적으로 좁게 유지된다. 운영자가 실제 판단해야 하는 것은 스캔, Top 분석, Archive다.

## 글로벌 상태 레이어

앱 시작 시 UI는 다음 정보를 모아 상단 상태를 만든다.

- 선택 시장
- `modules.macro_scheduler.get_macro_context`
- `compute_market_gate`
- `runtime_state/reports/learning/daily_model_foundation_gate.json`
- `modules.segment_accuracy` snapshot

`운영 판정 상세` expander는 `modules/operational_readiness_ui.py`를 사용한다. 운영자용 한국어 copy와 blocker/next action을 UI 내부에 흩뿌리지 않고 별도 모듈로 둔 구조다.

## 스캐너 탭

운영자가 선택하는 항목:

- 시장: KOSPI, KOSDAQ, NASDAQ, S&P500, AMEX
- scan mode: `스윙` 또는 `장중`
- max scan count

스캔 버튼은 background job을 시작하고, scanner runtime 및 artifact contract를 통해 결과를 남긴다.

중요 동작:

- 탭을 이동해도 스캔은 이어진다.
- scan continuity banner가 유지된다.
- 스캔 완료 후 Top Deep report가 생성된다.
- local 및 DB artifact가 archive 복구용으로 저장된다.

고급 파일 업로드 스캐너는 advanced path에 남아 있다.

## Top 분석 탭

구현 파일: `ui/top_deep_view.py`

데이터 소스:

- Supabase `scan_deep_reports`
- local `runtime_state/reports/top_deep` JSON

merge 원칙:

- DB row를 먼저 읽는다.
- local row를 병합한다.
- local의 analysis section/rank, decision, bucket, selection alignment, display contract, interpretation field는 존재 시 더 신뢰한다.

표시 내용:

- 후보 해석
- 매매 계획
- legacy planner 후보의 buy-premium execution gate
- 수급 caption
- policy metadata
- realized expectancy admission
- portfolio exposure
- scan integrity panel

## Archive 탭

구현: `app.py` + `ui/archive_data.py`

기본값:

- Supabase archive read는 `AG_SCAN_ARCHIVE_SUPABASE_ENABLED=1`일 때만 활성화된다.
- local fallback은 기본 ON이다.
- DB와 local artifact가 모두 있으면 병합한다.

필터:

- 날짜
- KR/US
- decision bucket
- scan mode: `SWING`/`INTRADAY`
- validation status
- run id

선택 run에서 읽는 항목:

- planner handoff
- profile diagnostics
- raw scan results
- scan integrity context
- scan-universe admission display

중요 원칙:

- Archive Top은 선택한 `run_id`의 scan-time/planner order를 반영해야 한다.
- 같은 날 여러 run을 섞거나 decision score로 조용히 재정렬하면 안 된다.

## 고급 화면

`AG_UI_ADVANCED=1`일 때:

- `ui/performance_view.py`: daily ops/performance overview
- `ui/intelligence_view.py`: market intelligence/theme momentum
- `ui/kis_theme_network_view.py`: KIS theme network
- 정밀분석: `QuantStrategy`, macro, news, prediction, technical level, flow, chart/image 경로

고급 화면은 진단용이다. 기본 execution surface로 보지 않는다.

## 디자인 시스템

파일: `ui/theme.py`

역할:

- background/surface token
- Toss 스타일 카드
- status banner
- compact card
- segmented tab
- dataframe/metric 스타일
- Pretendard font import

현재 UI 스타일:

- 한국어 우선
- wide layout
- 반복 후보 row는 card
- L0 status bar, L1 summary card, L2 detail grid
- main tab은 `st.segmented_control`

디자인 부채:

- `app.py`가 여전히 크다.
- archive/deep-dive composition이 완전히 모듈화되지 않았다.
- 추가 추출 작업은 별도 Beads 이슈로 다루는 것이 맞다.

## 후보 해석 구조

파일: `modules/candidate_interpretation.py`

두 가지 해석 경로가 있다.

1. 모델 검증 레인 해석
2. legacy operational candidate 해석

현재 whitelist:

```python
MODEL_VALIDATED_LANES = {"swing_ensemble", "kospi_intraday"}
```

whitelist bucket은 `build_model_lane_interpretation`이 아래를 만든다.

- `MODEL_BUY`
- entry reference price
- +5% target
- tight stop 없음
- fixed hold days
- probability label
- selection thesis

그 외 bucket은 legacy operational scoring과 buy-premium execution gate를 탄다.

## KOSDAQ 인트라데이 consumer gap

> **[2026-06-25 해결됨]** `kosdaq_intraday_3d_t5_vwap_guard`를 `MODEL_VALIDATED_LANES` + `LANE_PROFILE`(15:00 진입·VWAP가드·≥30억·3D)에 추가. `/signals` `bucket_order`에 포함(KOSPI인트라데이→KOSDAQ인트라데이→스윙). 카드는 🟢장중·코스닥 인트라데이 배지 + "진입 15:00" 표시. 아래는 갭 당시 기록.


KOSDAQ VWAP guard producer가 쓰는 주요 필드:

- `decision_bucket="kosdaq_intraday_3d_t5_vwap_guard"`
- `decision="KOSDAQ_INTRADAY_3D_T5_BUY"`
- `scan_mode="INTRADAY"`
- `strategy_family="KR_INTRADAY_3D_T5"`

그러나 이 bucket은 아직 `MODEL_VALIDATED_LANES`에 없다.

영향:

- `/signals`는 `build_model_signals_embed`에서 whitelist bucket만 필터링한다.
- 그래서 `/signals`에는 SWING ensemble과 KOSPI intraday는 잘 잡히지만, KOSDAQ intraday는 누락될 수 있다.
- Top Deep/Archive는 direct `scan_deep_reports` row를 읽기 때문에 보일 수 있다.

해결 방향:

- `kosdaq_intraday_3d_t5_vwap_guard`를 모델 레인 profile에 추가하거나, KOSDAQ 전용 profile을 만든다.
- 카드에는 15:00 진입, +5% 목표, 3D hold, no tight stop, liquidity lane, probability를 표시해야 한다.

## Discord 명령

정의 파일: `modules/discord_integration/commands.py`

명령:

- `/kospi_scan`: KOSPI scan 시작
- `/kosdaq_scan`: KOSDAQ scan 시작
- `/macro_refresh`: macro context refresh
- `/top_deep`: Top Deep 조회
- `/signals`: 모델 신호 전체 조회 (스윙+인트라데이)
- `/intraday`: 장중(인트라데이) 모델 레인만 조회 — 코스피 인트라데이 + 코스닥 15:00 VWAP가드 **[2026-06-25 추가]**
- `/swing`: 스윙 모델 레인만 조회 (가격앙상블) **[2026-06-25 추가]**
- `/archive`: archive 조회
- `/runs`: run 조회
- `/status`: bot/server/status 조회

실행 파일:

- `modules/discord_integration/scan_executor.py`
- `multi_agent/tools/discord_bot.py`

렌더링:

- `modules/discord_integration/renderers.py`

렌더러는 Supabase 또는 local fallback에서 row를 읽고, Discord field/문자 수 제한에 맞춰 embed를 쪼갠다.

## Web/Discord 정합성 규칙

모델 producer가 일반 planner 경로를 우회해 direct Top Deep row를 쓰더라도 web/Discord가 이해할 필드를 채워야 한다.

필수 의미:

- market
- ticker/name
- scan_mode
- decision_bucket
- strategy_family
- entry policy
- target
- hold period
- stop policy
- probability/confidence
- liquidity lane
- forward outcome placeholder

## UI 후속 작업

1. ~~KOSDAQ intraday bucket을 model-lane consumer에 추가한다.~~ **[2026-06-25 완료]**
2. ~~`/signals`에서 KOSDAQ intraday를 보이게 한다.~~ **[2026-06-25 완료]**
3. `app.py`의 archive/deep-dive 로직을 더 작은 모듈로 분리한다. (별도 작업)
4. ~~SWING/INTRADAY 표시가 섞이지 않게 UI badge와 filter를 고정한다.~~ **[2026-06-25 완료]** — 🔵스윙/🟢장중 배지 + run 선택 scan_mode prefix. (웹 Top분석은 run 1개만 표시라 본래 섞이지 않음.)
5. 오래된 phase25/legacy 문구가 현재 모델 레인과 혼동되지 않게 표시 copy를 정리한다. (별도 작업)
