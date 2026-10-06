# 레인 · 데이터 · 스케줄 지도

**이 문서의 목적**: 「어느 레인이 어느 모델로 픽을 내고, 그 입력이 어디서 오고, 무엇이 언제 돌리는가」를
한 곳에 둔다. **기억으로 답하지 말고 여기를 보고, 여기가 코드와 다르면 코드가 맞다.**

> 🔴 **왜 이 문서가 생겼나 (2026-09-12)**
> 한 세션에서 조정관이 모델·데이터를 **다섯 번** 혼동했고 그중 둘은 라이브에 영향을 줬다:
> 1. `phase25_kr_intraday_xgboost`(auc 0.478, 5월자)를 **코스닥 장중 레인의 모델로 착각**해
>    그 레인을 정지시켰다 → 철회(`e9ed2b0`). **그 레인은 자기 번들을 매일 재학습한다.**
> 2. `_base_prob`(가중치 0.6)을 **스윙 레인의 성분으로 착각**했다 → 스윙 레인에 `grep` 0건.
>    그것은 `quant_analysis` 스캔 경로의 것이다.
> 3. `M2` 격자 수치를 라이브 성과로 인용 → **무게이트 값**이었다(게이트 적용 시 26배 차이).
> 4. `px_long` 의 미조정 OHLC 를 다일 경로에 쓸 뻔했다.
> 5. `cmp35_*` 를 정본으로 인용 → **가드 수정 이전** 산출물이었다.
>
> 공통 원인은 하나다 — **이름이 비슷한 것들이 서로 다른 파이프라인에 속해 있는데 그 경계가 어디에도 안 적혀 있었다.**

---

## 1. 발행 레인 (웹 `/api/picks` 가 읽는 것)

레지스트리: `web/backend/services.py: LANES` · 차단 판정: `modules/stream_exclusion.py`

| 레인 | 생산자 | **모델 조달** | 계약 | 원장 |
|---|---|---|---|---|
| `kospi_swing` | `report_kr_swing_candidate.py` | **매 실행 자체 적합** (저장 모델 없음) | TP5 / H10 / top-3 | `experimental/kr_swing_candidate_ledger.jsonl` |
| `kosdaq_swing` | 〃 (같은 파일) | 〃 | TP5 / H5 / top-1 | 〃 (같은 원장) |
| `kosdaq_intraday` | `report_kosdaq_intraday_vwap_guard.py` | **저장 번들 로드** → `models/kr_intraday_3d_t5/kosdaq_liq30_1500_lgbm_isotonic_vwapguard.pkl` | TP5 / 3일 / 15:00 진입 | `experimental/kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl` |
| `nasdaq_swing` | `report_nasdaq_session_tape.py` | **매 실행 자체 적합** (저장 모델 없음) | TP5 / H20 / **종가 진입** | `us_research/nasdaq_session_tape_ledger.jsonl` |
| `kospi_intraday` | `report_kospi_intraday_swing.py` | — | — | **죽음** (2026-08-22, 체결 불가능한 진입) |

### 은퇴·정지 레인 (`stream_exclusion.RETIRED_LANES` — **게이트보다 우선한다**)
| 레인 | 상태 | 사유 | 복귀 경로 |
|---|---|---|---|
| `kospi_intraday` | **killed** (2026-08-22) | 측정된 엣지가 **체결 불가능한 진입** 위에 있었다 — 랭커 top-1 의 19.2% 가 신호일 상한가 종가(유니버스 0.21%, 91배 농축). 체결 가능만 남기면 net +1.620 → −0.009 | 없음 |
| `nasdaq_session_edge` | **retired** (2026-09-02) | 후계 `nasdaq_session_tape` 가 감사 통과. 이 레인은 42거래일 0픽이고 승격 게이트가 `multi_year_overnight_provider_not_loaded` 로 막힘 | 다년 장중 공급원(유료) 확보 |

⚠️ 은퇴해도 `LANES` 에서 **지우지 않는다** — 지우면 `ledger=""` 가 되어 `/api/picks` 가 죽는다.
과거 픽 해석을 위해 남기고 발행만 막는다.

### 🔴 여기가 가장 많이 헷갈린 지점
- **스윙 두 레인은 저장된 `.pkl` 이 없다.** `_fit()` 이 매 실행 LGBM 을 새로 적합한다
  (`report_kr_swing_candidate.py:130`). 그래서 **`models/` 의 어떤 파일도 스윙 픽을 정하지 않는다.**
- **`models/phase25_*.pkl` 은 이 표의 어느 레인도 쓰지 않는다.** 그건 `modules/quant_analysis.py` 의
  스캔 스코어링(`_blended = _base_prob*0.6 + _p25_prob*0.4`) 경로다 — **별개 파이프라인**이다.
- **`kosdaq_intraday` 만** 저장 번들을 쓴다. 그 번들은 매일 재학습된다(아래 §3).
- 두 스윙 레인은 **원장을 공유**한다. 시장 컬럼으로 가른다.
- 같은 신호일 재실행은 원장에 처음 기록한 종목·가격·점수·계약을 다시 라우팅한다.
  `modules/model_lane_contract.py`가 개별 픽의 `contract_h`/`contract_tp`를 DB·deep report·웹에 전달한다.
  학습 라벨(`t5_5`)과 실제 보유 계약(H10)은 구분한다. 웹은 신호일이 같은 경우 원장을 우선하며,
  DB 저장 시각을 매수 신호일로 바꾸지 않는다.

---

## 2. 데이터 (모두 `~/research_cache/`)

| 파일 | 내용 | 만드는 것 | 쓰는 곳 | ⚠️ |
|---|---|---|---|---|
| `px_long.parquet` | 피처 패널 + 라벨 `ft_5_5` | `build_px_long.py` (FDR 기본 NAVER) | 스윙 레인 적합·스코어링 | **일관된 미조정 KRX 가격 또는 조정가격으로 가정하면 안 된다.** 082740의 2026-09-17~10-02 종가는 KIS 통합시장(UN)과 10/10 일치. KRX/조정 경로와 분모 혼합 금지 |
| `px_delisted.parquet` | 휴리스틱 **조정** OHLC + `adj_factor` + `delist_date` | `build_px_delisted.py` (KRX marcap) | 연구 계약 경로 · 시장 지도 폴백 | 상폐 가격 포함; 피처 모집단의 PIT 완전성은 별도 검증. 082740 원종가는 KIS KRX(J)와 10/10 일치. 기업행위 휴리스틱이 KIS 수정가와 다를 수 있음 |
| `p2_label.parquet` | 학습 라벨 `t5_5`/`r5_5` | `build_p2_label.py` (← `refresh_label_chain.py`) | 스윙 레인 학습 타깃 | 계약이 끝나야 확정 → 항상 `오늘 − 17일` 근처 |
| `intraday/*.parquet` | 1분봉 종목당 1파일 | `multi_agent/tools/backfill_kr_intraday.py` (daily ops) | 장중 레인 · 일중 경로 연구 | **소급 조정이다.** `adj_factor` 곱셈으로 안 맞는다 — 하루 단위 종가 자가보정 필요. 최신 관측 거래일 우선·전 관측 종목·요청별 시간예산·원자 저장. `.backfill/journal/<code>`에 최초 전체 백업과 추가 행 차분을 보존하고 저장 전 복원을 검증한다. 여유 공간 10GiB 하한, 기존 증거 자동 삭제 없음. `.backfill/latest.json`은 수집 상태이며 전일 완전성이나 PIT 유니버스를 보증하지 않는다 |
| `intraday_ext/*.parquet` | KIS UN 통합시장 08:00–20:00 분봉 | `multi_agent/tools/backfill_kr_extended_intraday.py` (daily ops) | 확장세션 가격발견 연구; 발행 없음 | 기존 203종목 코호트 유지, 전체시장/PIT 유니버스 아님. `px_long` 관측 날짜 기준·20시 이후 당일 포함·최신 날짜 우선. 기본 600초(`EXT_TIME_BUDGET`), 부분 요청 재개·오류 기록·차분 백업/복원 검사. 정규장 J 파일과 별도 경로/잠금. 6구간 응답을 전일 완전성으로 간주하지 않음 |
| `us_daily/NASDAQ/` | 미국 일봉 패널 120열 (`v2_quality_segments`) | `backfill_us_daily_features.py --daily-refresh` → `us_daily_session_refresh.py` | 나스닥 레인 | SPY 원천의 완료 관측 세션별 갱신·종목별 영수증/해시 검증. 최근 14일 겹침 구간 우선, 조정 기준 변화 시 전체 이력 재확인. 기존 원본 검증 백업 후 원자 교체, 요청 세션 미도달·미방문은 partial/실패. 패널은 요청 종료일 이후 행을 제외한다. 오류 OHLCV 날짜는 `source_bar_valid=0/source_issue`와 NULL 계산값으로 보존하고 지표·EMA·라벨은 정상 연속구간별로 계산한다. 미완성 지평 라벨은 NULL; 구조검증은 누락 세션·기업행동·PIT 완전성 인증이 아니다. **생존편향 심각** — 사라진 3,272 심볼 중 35개(1.1%)만 보유; 수집 최신성과 PIT 유니버스는 별개 |
| `T1_nasdaq_listing_snapshots.parquet` | NASDAQ 과거 상장목록 스냅샷 | 기존 아카이브 수집본; 정기 갱신 미확인 | `report_nasdaq_session_tape._listed_pit` | 평가일 이전의 **전역 최신 스냅샷** 내 적격 멤버십을 사용한다. 종목별 마지막 적격 행을 이월하면 퇴출·ETF/우선주 전환을 놓친다. 2026-10-07 확인한 최신 스냅샷은 06-11이며, 사이 구간과 당일 수집 시각의 완전성은 별도 문제 |

미국 일봉 피처 재사용은 `us_daily_panel_cache.py`가 관리한다. 전체 원본 SHA(없는 파일도 포함), 유니버스, 기간, 피처 코드·검증 코드·캐시 코드와 라이브러리 버전이 같고 현재 소비자 패널 및 세 산출물 해시가 검증될 때만 재사용한다. 패널 옆 `.provenance.json`과 `.refresh/feature_panels/`에 근거를 보존한다. 재사용은 원천 수집 `partial`을 성공으로 바꾸지 않는다. `--force-refresh`는 재생성을 강제하고, 제한된 `--max-symbols` 실행은 전체 최신 상태를 인증하지 않는다.

### 학습 데이터 ≠ 픽 데이터
- **픽**: `px_long` 의 **오늘 행**으로 스코어링
- **학습**: `px_long` 과거 2년 × `p2_label` 의 `t5_5` (엠바고 17일)
- 두 시장은 **유동성 문턱이 다르다**: KOSPI ≥100억 / KOSDAQ ≥30억

---

## 3. 스케줄 (launchd, `~/Library/LaunchAgents/com.codex.swing.*`)

| 작업 | 주기 | 하는 일 |
|---|---|---|
| `dailyops` | **300초 폴링** | 세션 경계를 보고 해당 시점 운영을 실행 |
| `kr-daily-auto-scan` | 매일 **09:35** | 개장 데이터 갱신 + 스캔 |
| `kr-premarket-theme-prior` | 매일 **08:20** | 장전 테마 사전확률 |
| `investor-estimate` | **10:03 / 11:33 / 13:23 / 14:33** | 수급 추정 |
| `learning.nightly` | 매일 **23:50** | `run_learning_cycle.py --mode nightly` (신규 정산 ≥20건) |
| `learning.weekly` | **일요일 09:00** | 〃 `--mode weekly` (총 ≥50 · 신규 ≥10) |
| `web-backend` · `web-frontend` · `tunnel` · `discord-bot` | KeepAlive | 상시 |

### 일일 운영(`run_daily_ops.sh`) 안의 학습 단계
| 단계 | 대상 |
|---|---|
| `train_kosdaq_1500_bundle` | **`kosdaq_intraday` 레인의 서빙 번들** ← 이것만 레인 모델을 직접 바꾼다 |
| `evaluate_kr_swing_models` / `evaluate_kr_intraday_models` | `models/phase25_kr_*` (스캔 경로용, 레인 아님) |
| `b_retrain` | b_engine 앙상블 (별도 레인) |

⚠️ **「재학습이 돌았다」 ≠ 「서빙 모델이 바뀌었다」.** `retrain_ml.py` 는 `phase25_model.pkl` 만
갱신하는데 그 파일은 KR 후보 목록 **맨 뒤**라 선택되지 않는다(2026-09-03 실측).

---

## 4. 발행을 막는 것들 (픽이 안 보이면 여기부터)

1. **시장약세 게이트** — `gate_market_weakness`, KOSPI q=0.40 / KOSDAQ q=0.50.
   시장이 강하면 **의도적으로 기권**한다. 픽 0은 이 경우 정상이다.
2. **재귀게이트 DEGRADE** — `report_research_recursion_gate.py`. forward EV 가 기대선 미달.
3. **은퇴/정지 레인** — `stream_exclusion.RETIRED_LANES`. **게이트보다 우선한다.**
4. **유니버스 소멸 가드** — 한 시장이 0종목이면 **중단**(2026-09-10 사고 이후).
5. **라벨 신선도** — 엠바고 너머 63일 초과면 중단.
6. **현행 스윙 구성 자격** — 재귀게이트 `current_epochs`가 시장·발행시 gate/q/top_k·계약별로 분리한다.
   과거 합산 `swing_candidate`의 CONFIRM을 현재 구성에 승계하지 않는다. 2026-10-07 기준 두 시장 모두
   표본/고유일 및 동일 구성의 검증된 연구 근거가 부족해 관측 전용이다. 일별 쿼터 초과 발행의 순위가
   불명확한 2026-08-24는 해당 날짜 전체를 판정에서 제외하고 원장은 보존한다.

### 2026-10-07 성과 정규화

`repair_issued_outcomes.py`로 격리된 22행을 복구한 뒤, `refresh_issued_outcomes.py`로 현행 발행 64행 전체의 일별 성과를 조정 신호일 종가 기준으로 재산출했다.
최초 발행 기준가는 유지한다. 익일 시가 체결·터치익절 계약 성과와는 다른 열이다.
`feature_snapshot.daily_outcome_basis`에 분모·자료 기준일·가격 출처를 기록한다.
기존 검증 제외는 유지하며, 일반 미조정 history fallback은 SWING-CAND 행의 빈 기간 성과를 채우지 않는다.
일일 작업은 라벨 사슬·일봉 갱신 → 성과 동기화/조정가격 재산출 → 아카이브 내보내기 순서다.
자료가 늦으면 확인된 세션까지만 갱신하고 보고서에 지연 세션 수를 남긴다. 거래정지일은 달력에서 제거하지 않으며,
유지된 종가는 평가액으로만 사용하고 고가 미관측 구간의 터치 라벨은 미확정이다. 모든 DB 갱신은 가격 증거·원문 백업과 CAS 감사 로그를 갖춘다.
아카이브는 원자적으로 교체하고 웹이 파일 변경을 감지한다. SWING-CAND 신호일은 저장 시각 대신 고정 run_id에서 읽는다.
화면의 기준가·3/5일 기간 수익률·상승/하락 표시는 실제 체결가나 터치 계약의 승패와 구분한다.

### 독립 H10 전진 검증

`prereg_kr_touch10_prospective_20261007.json`에 2026-10-07 이후 최초 60시장세션의 평가창을 사전 고정했다.
`observe_kr_touch10_prospective.py`가 일일 스윙 생산 직후, 긴 분봉 백필 전에 실행된다.
신호·기권·같은날 유동성 유니버스를 다음 달력일 09:00 KST 이전에 불변 저장하며 뒤늦은 역사 채우기는 금지한다.
평가창의 H10 결과가 성숙해야 판정한다. 그 전의 성과는 중간 관측이며 표본을 골라 조기 통과하지 않는다.
시장별·합산 터치/순수익/동일일 초과/블록 CI·종목 플라시보와 날짜 순환 대조를 기록한다.
이 도구는 발행·사이징을 수행하지 않으며 통과해도 재귀게이트와 생산/소비 연결 검토를 따로 거쳐야 한다.
산출물은 `runtime_state/reports/experimental/kr_touch10_prospective/`와
`runtime_state/reports/validation/kr_touch10_prospective_latest.json`이다.

별도 `--study cadence`는 `prereg_kr_touch10_cadence_20261007.json`의 최초 120시장세션을 관측한다.
현재일 포함 최근 5관측세션의 **합산 발행일 최대 3**을 시간순으로 적용한다. 양시장이 같은날 발행해도 1회이며,
종목 순위·시장 게이트는 그대로다. 원래 픽은 `source_picks`로 보존한다. 이전 캡처가 없으면 기권으로 취급하지 않고
해당 캡처를 거부한다. 이 상한이 최소 2회나 70% 성공률을 보장하지 않으며, 미달하면 후보가 실패한다.
저빈도 코스닥 표본을 확보할 기회를 주기 위해 관측창을 사전에 120세션으로 고정했고 n30/고유일20 기준은 유지했다.
이는 발행 빈도/계약 변형의 검증이며 신규 알파를 확보했다는 주장이 아니다.
원 60세션 후보와 두 후보 가족을 선언해 종목 플라시보 p에 Bonferroni 2배 보정을 기록한다.
원 후보의 최초 판정은 보존하되 어떤 후보든 승격 검토는 가족 보정까지 통과해야 한다. 95% 구간은 개별 진단 구간이다.
같은 수집기가 별도 디렉터리 `experimental/kr_touch10_cadence_prospective/`와
`validation/kr_touch10_cadence_prospective_latest.json`에 기록하며 두 경로 모두 발행·사이징은 하지 않는다.

---

## 5. 이 문서를 갱신해야 하는 때

**갱신 없이 병합하면 안 되는 변경:**
- 레인 추가·은퇴·정지 (`LANES`, `RETIRED_LANES`)
- 계약 변경 (`CONTRACT_TP`, `CONTRACT_H`, `TOP_K`, `LIQ`)
- 모델 조달 방식 변경 (자체 적합 ↔ 저장 번들)
- 캐시 파일 추가/성격 변경, 스케줄 변경
- 새 모델 연구 결과 배선

**자동 검사**: `tests/test_lane_data_map_is_current.py` 가 이 문서와 코드의 레인 목록·계약을 대조한다.
문서를 안 고치면 **테스트가 깨진다** — 약속이 아니라 관문이다.

---

## 6. 연구 산출물을 인용하기 전에 (규율 54·55)

- **그 격자가 라이브 구성으로 계산됐는지 확인해라.** `M2/analyze.py` 에 「gate」가 0회였다 —
  무게이트 격자를 라이브 성과로 인용해 26배 틀렸다.
- **열 이름이 아니라 생성 코드가 의미를 정한다.** `k_tp_H` 는 「보유기간」이 아니라
  **첫 터치 세션이고 미터치는 0** 이다.
- **README 는 맨 위(최신 개정)부터 읽어라.** `Y/README.md` 최종 개정이 이식 **취소**인데
  중간 절의 수치를 인용해 틀렸다.

### 공통 관측 세션
`modules/market_sessions.py`가 KR `px_long.parquet`, US 최신 `daily_features_*.parquet`의
완료된 관측 날짜를 게이트·미정산 경보·웹 발화 빈도에 공급한다. 픽 발화일은 시장 캘린더가 아니다.
원천 결측은 휴장과 구별되지 않으므로 별도 데이터 신선도 진단이 필요하다.

매수 타이밍 화면도 KR `px_delisted` 조정가격과 개별 `contract_h`/`contract_tp`를 읽는다.
현재 원시 시세와 비교할 때 종목별 최신 조정계수로 단위를 맞춘다. 미조정 OHLC로 다일 경로를
계산하지 않는다. 조정가격이 피처 관측 세션보다 지연되거나 종목 세션이 누락되면 `UNKNOWN`이다.
국내 스윙 원시 `t5_5` 점수는 웹에서 모델 점수로 표시하고 H10 적중확률로 부르지 않는다.

### 세션 누락 따라잡기 (2026-10-07)
`dailyops` 300초 폴러는 각 시장 현지 당일의 **가장 최근 지난 경계**를 실행한다.
절전으로 10분 창을 놓쳐도 그날 안에 복구하며, 더 이른 경계는 지난 시각으로 재실행하지 않는다.
완료된 최신 경계는 재실행하지 않으며 각 세션 완료 직후 상태를 저장한다.
`--no-catch-up`으로 종전의 10분 창 진단이 가능하다.
