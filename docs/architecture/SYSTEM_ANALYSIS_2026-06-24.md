# 종합 시스템 분석 - 2026-06-24

이 문서는 일봉 검증 교정, 분봉 연구, KOSDAQ 인트라데이 배포 이후의 현재 시스템 상태를 종합 분석한 것이다.

## 근거 문서

이 분석은 아래 문서를 기준으로 한다.

- `docs/operations/CURRENT_OPERATIONS_MANUAL_2026-06-24.md`
- `docs/architecture/BACKEND_DATA_ARCHITECTURE_2026-06-24.md`
- `docs/architecture/FRONTEND_OPERATOR_UI_2026-06-24.md`
- `docs/research/MODEL_TRADING_STRATEGIES_2026-06-24.md`
- 최신 Beads 상태와 `run_daily_ops.sh` 실제 실행 목록

## 현재 목표

운영자가 요구한 목표는 단순히 “스코어 높은 종목”이 아니다.

- 짧은 기간 안에 +5% 이상 수익 가능성이 높은 후보
- 인트라데이 기준으로는 3일 내 +5% touch 확률 70~75% 이상
- 8:2에 가까운 운영 프로필
- 실제 거래 가능한 유동성
- 충분한 forward ledger
- 월별/일별 붕괴 원인 분석과 생산 승급 기준

현재 시스템에서 이 목표에 가장 가까운 것은 KOSDAQ 15:00 VWAP guard `KR_INTRADAY_3D_T5` 레인이다.

## 주요 연구 교정

### 1. 일봉 벤치마크 교정

과거 일봉 edge 주장은 벤치마크에 민감했다.

- 외부 KS11 벤치마크는 KOSDAQ 평가에 교차시장 artifact를 만들 수 있었다.
- cap-weighted 내부 벤치마크는 대형주/소형주 편향을 만들 수 있었다.
- 종목 picker 평가에는 same-day size/liquidity matched control이 더 적합했다.

교정 결과:

- regime conditional: durable edge 없음
- NORMAL PEAD: durable edge 없음
- Practical-80: production edge로 검증되지 않음
- score/rerank edge: 매수 edge보다는 약한 회피/중립화 성격
- Exception Leader: 짧은 window 양성이나 durable 검증 부족

### 2. 일봉 price-ML 교정

가격전용 daily ML top slice는 교정 검증에서 통계적 신호가 있었다. 그러나 해석은 제한적이다.

- 목표 75% 모델은 아니다.
- `ft_5_5` modest signal이다.
- 현실 비용을 낮게 잡으면 일부 유동성 floor에서 생존 가능성이 있다.
- 운영적으로는 live-forward 보조 레인으로 두는 것이 맞다.

### 3. 인트라데이 연구 수렴

분봉 연구에서 더 중요한 결론:

- 종목선별보다 진입/체결/당일 경로가 중요하다.
- +5% touch 목표는 일봉 방향성보다 인트라데이 path feature와 잘 맞는다.
- VWAP 위 진입 품질이 공통 안정화 요소다.
- tight stop은 테스트된 구간에서 기대값을 깎았다.
- KOSDAQ 모델은 3일 close-hold가 현재 균형점이다.

## 현재 최선 모델 패밀리

현재 가장 중요한 공통 모델 패밀리:

```text
KR_INTRADAY_3D_T5_CONTEXT_VWAP_GUARD
```

핵심 구성:

1. 목표: 3거래일 내 +5% touch
2. 진입: 장중 VWAP 위 조건
3. feature: 분봉 path + 전일/최근 일봉 context
4. 시장: KOSDAQ 우선, KOSPI 보조
5. 유동성: `>=30억` main, `>=100억` tradeability 분리
6. 보유: 3D close hold
7. 검증: forward ledger로 touch/return/MFE/MAE 추적

## 영역별 운영 상태

### SWING 일봉 scanner/planner

상태: 운영 가능하지만 메인 edge frontier는 아님.

강점:

- scanner/planner trace가 성숙함
- artifact/archive 구조가 있음
- web/Discord 기본 표면이 있음
- realized outcome backfill 구조가 있음

약점:

- 오래된 일봉 edge narrative 다수가 교정/철회됨
- chart/flow/theme 축이 가격전용 모델 레인을 가릴 수 있음
- 목표 75%를 만족하지 못함

### SWING ensemble

상태: live-forward 검증.

사용 방식:

- modest daily price-ML signal
- forward evidence 축적
- 보조 운영 레인

사용하면 안 되는 방식:

- 75% 목표 달성 근거
- 인트라데이 목표 대체재

### KOSPI intraday

상태: live-forward 검증.

장점:

- `close_vwap>=0`, `idx_vol20>=8` guard 이후 aggregate backtest hit가 높음
- `>=100억` 유동성 floor
- 기존 route helper를 이용해 live surface로 전달

위험:

- volatility guard가 약한 월을 보수한 것이므로 과최적화 여부를 봐야 함
- producer 내부 학습 구조라 artifact 고정성이 약함
- SWING-style route helper를 쓰지만 의미는 intraday이므로 UI/문서에서 구분해야 함

### KOSDAQ intraday

상태: 현재 최선 배포 후보.

장점:

- 저장된 joblib bundle 사용
- candidate id/strategy family 명확
- 15:00 이전 데이터만 사용해 leakage를 줄임
- `p_cal>=0.80`, VWAP guard가 명확
- `>=30억`, `>=100억` 유동성 lane을 분리 기록
- ledger에 `touch3d_t5`, `ret3d`, `mfe3`, `mae3`를 남김

위험:

- forward sample이 아직 충분하지 않음
- 분봉 데이터 window가 약 1년으로 단일/제한 레짐
- `/signals` consumer whitelist 미통합
- drawdown이 크고 tight stop은 현재 primary contract가 아님

## 구조적 강점

1. `SWING`/`INTRADAY` scan mode가 명시됐다.
2. KIS live data가 adapter를 통해 들어온다.
3. runtime artifacts가 local/DB 양쪽에 남는다.
4. Top Deep/Archive가 local fallback으로 복구 가능하다.
5. Beads로 후속 작업과 연구 이슈를 추적한다.
6. candidate interpretation이 UI만의 임의 copy가 아니라 모듈화돼 있다.
7. model-lane producer가 ledger를 가진다.
8. 연구 과정에서 벤치마크/비용/표본 교정을 기록하고 있다.

## 구조적 약점

1. `app.py`가 아직 크다.
2. 일부 문서/Beads note는 최신 교정보다 stale할 수 있다.
3. KOSDAQ intraday consumer integration이 완전하지 않다.
4. KOSPI intraday는 producer 내부에서 학습한다.
5. Supabase timeout 이슈가 backfill/조회에 영향을 줄 수 있다.
6. repo 밖 `~/research_cache` 의존성이 크다.
7. retired/legacy 모델 파일이 `models/`에 남아 있다.
8. KIS 분봉 보존 한계 때문에 intraday 검증 window가 짧다.

## 하지 말아야 할 것

- PEAD/regime/Practical/Exception 과거 narrative를 production edge로 되살리지 않는다.
- INTRADAY 후보를 SWING gate로 평가하지 않는다.
- 승률만 보고 판단하지 않는다. return, drawdown, liquidity, active days, monthly floor를 같이 봐야 한다.
- 모델 파일이 있다고 live라고 판단하지 않는다.
- cautious action label 때문에 후보를 숨기지 않는다. 표시와 매수 가능성은 별개다.

## 다음 우선순위

### 1순위: KOSDAQ intraday consumer parity

- `kosdaq_intraday_3d_t5_vwap_guard`를 model-lane profile에 추가
- `/signals`에서 KOSDAQ intraday pick 표시
- Top Deep/Archive/Discord 카드에 entry=15:00, target=+5%, hold=3D, no tight stop, liquidity lane, probability 표시

### 2순위: KOSDAQ intraday forward gate

최소 기준:

- forward picks 60개 이상
- forward days 30일 이상
- forward months 2개월 이상
- touch3d_t5 75% 이상
- day hit 80% 이상
- net 3D close return > 0
- liquidity-decile excess > 0
- n>=5인 월에서 hit 65% 미만 없음
- realized slippage <= 0.50%

### 3순위: KOSPI intraday artifact 안정화

- live producer 내부 학습을 분리하거나 bundle cache
- feature list, data window, hyperparameter, validation, checksum 기록
- volatility guard가 forward에서도 필요한지 추적

### 4순위: SWING ensemble 보조 레인 유지

- modest daily signal로 ledger 유지
- 75% 목표 모델로 홍보하지 않음
- 일봉과 인트라데이 운영 문구 분리

## 최종 판단

프로젝트는 “일봉 점수 높은 종목 찾기”에서 “분봉 경로와 진입 품질로 3일 +5% touch 확률을 높이는 시스템”으로 이동했다. 현재 가장 설득력 있는 공통 모델은 KOSDAQ 15:00 VWAP guard `KR_INTRADAY_3D_T5` 레인이다.

남은 핵심 문제는 모델 후보 존재 여부가 아니다. 운영 성숙도다.

- consumer parity
- forward sample
- slippage/liquidity tracking
- drawdown-aware sizing
- INTRADAY/SWING 분리
- stale narrative 제거

KOSDAQ intraday가 forward에서 유지되면 현재 목표에 가장 가까운 길이다. 무너지면 분봉 데이터를 더 쌓고, 일봉 모델을 목표 이상으로 포장하지 않아야 한다.
