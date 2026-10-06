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
| `px_long.parquet` | 피처 패널 + 라벨 `ft_5_5` | `build_px_long.py` | 스윙 레인 적합·스코어링 | **OHLC 가 미조정이다.** 다일 경로에 쓰면 액면분할이 섞인다 |
| `px_delisted.parquet` | **조정** OHLC + `adj_factor` + `delist_date` | `build_px_delisted.py` | 연구 계약 경로 · 시장 지도 폴백 | 상장폐지 포함 = 생존편향 없음 |
| `p2_label.parquet` | 학습 라벨 `t5_5`/`r5_5` | `build_p2_label.py` (← `refresh_label_chain.py`) | 스윙 레인 학습 타깃 | 계약이 끝나야 확정 → 항상 `오늘 − 17일` 근처 |
| `intraday/*.parquet` | 1분봉 종목당 1파일 | `intraday_backfill.py` | 장중 레인 · 일중 경로 연구 | **소급 조정이다.** `adj_factor` 곱셈으로 안 맞는다 — 하루 단위 종가 자가보정 필요 |
| `us_daily/NASDAQ/` | 미국 일봉 패널 118열 | (수집기 별도) | 나스닥 레인 | **생존편향 심각** — 사라진 3,272 심볼 중 35개(1.1%)만 보유 |

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
