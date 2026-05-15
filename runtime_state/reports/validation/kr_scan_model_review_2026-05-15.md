# KR Scan Model Reliability Review - 2026-05-15

## Executive Verdict

현재 코스피/코스닥 스캐너는 "좋은 후보를 발굴하는 엔진"으로는 일부 신호가 확인된다. 그러나 "정확한 매수 판단 엔진"으로 운영하기에는 아직 신뢰 구간이 부족하다.

- 코스피: 방향은 맞다. 특히 5거래일 기준 `Exception Leader`, `rank1`, `expected_edge` 게이트에는 유의미한 신호가 있다. 다만 1거래일 즉시 진입 성능은 약하고, 워크포워드 release gate는 통과하지 못했다.
- 코스닥: 기존 Top5 운영 방향은 충분히 강하지 않다. `Exception Leader`가 Top5보다 낫지만, 손실 경로가 여전히 높다. 별도의 1D/INTRADAY, 저거래량-반전형 후보군은 가능성이 있으나 표본이 작다.
- 공통: 현재 모델은 "상승 가능 후보"와 "지금 매수해도 되는 후보"를 완전히 분리하지 못한다. 따라서 자동 매수 판단이 아니라 조건부 관찰/진입 판단으로 취급해야 한다.

## Evidence Sources

- `runtime_state/reports/validation/prediction_validation_kospi.md`
- `runtime_state/reports/validation/prediction_validation_kosdaq.md`
- `runtime_state/reports/trading/paper_trade_ledger_kospi_swing_top5.md`
- `runtime_state/reports/trading/paper_trade_ledger_kosdaq_swing_top5.md`
- `runtime_state/reports/validation/kr_walkforward_release_gate_kospi.md`
- `runtime_state/reports/validation/kr_walkforward_release_gate_kosdaq.md`
- `runtime_state/reports/experimental/kospi_ordered_candidate_search_latest.md`
- `runtime_state/reports/experimental/kosdaq_ordered_candidate_search_latest.md`
- `runtime_state/reports/validation/kr_scanner_direction_audit.md`
- `runtime_state/reports/validation/low_drawdown_winner_traits.json`
- `runtime_state/reports/validation/kospi_swing_5d_slice_validation.json`
- `runtime_state/reports/validation/kosdaq_swing_5d_slice_validation.json`
- `runtime_state/reports/validation/kr_quant_rerank_validation_kospi.md`
- `runtime_state/reports/validation/kr_quant_rerank_validation_kosdaq.md`

## KOSPI Review

### Prediction Validation

KOSPI 전체 스캔 검증은 64개 run, 2,116개 row 기준이다.

| bucket | horizon | n | avg_return | win_rate |
|---|---:|---:|---:|---:|
| picked | 1d | 268 | -2.04% | 25.0% |
| picked | 3d | 253 | +0.94% | 37.1% |
| picked | 5d | 197 | +6.42% | 81.2% |
| watchlist | 5d | 1114 | +5.47% | 63.6% |
| exception_leader | 1d | 72 | +0.85% | 45.8% |
| exception_leader | 3d | 72 | +5.17% | 79.2% |
| exception_leader | 5d | 63 | +9.89% | 87.3% |

판단:

- KOSPI는 5D 기준 신호가 강하다.
- 그러나 1D 즉시 진입은 약하다. picked 1D는 평균 -2.04%, 승률 25.0%로 즉시 매수 판단으로 사용할 수 없다.
- Exception Leader는 3D/5D에서 Top5보다 우수하지만, 1D 승률은 45.8%라 당일 매수 신호라고 보기 어렵다.

### Paper Trade Shadow Ledger

KOSPI Top5 섀도우 장부는 closed 239건 기준:

- win_rate: 69.46%
- avg_return: +3.75%
- median_return: +3.43%
- max_return: +20.0%
- min_return: -10.0%
- rank1: win_rate 74.47%, avg_return +6.10%

판단:

- KOSPI Top5는 완전히 무작위가 아니다.
- rank1과 Exception Leader는 의미 있는 우위가 있다.
- 하지만 손실 꼬리(min -10%)가 남아 있고, release gate가 실패했으므로 "정확한 매수 판단"으로 승격할 단계는 아니다.

### 5D Slice Validation

KOSPI 5D resolved 2,162건:

- all_resolved: win5 61.98%, avg5 +5.15%
- rank_top5: win5 68.80%, avg5 +5.66%
- rank_top2: win5 70.54%, avg5 +7.04%
- rank1: win5 76.79%, avg5 +7.92%
- bucket_exception_leader: win5 85.71%, avg5 +8.99%
- expected_edge >= 6: win5 74.52%, avg5 +8.38%

판단:

- KOSPI는 Top5 전체보다 rank1, Exception Leader, expected_edge 게이트가 더 낫다.
- 현재 방향은 "Top5를 그대로 매수"보다 "Top5/Exception/edge 조건을 결합한 admission gate"가 맞다.

## KOSDAQ Review

### Prediction Validation

KOSDAQ 전체 스캔 검증은 71개 run, 2,448개 row 기준이다.

| bucket | horizon | n | avg_return | win_rate |
|---|---:|---:|---:|---:|
| picked | 1d | 201 | -2.88% | 25.9% |
| picked | 3d | 201 | -1.20% | 33.8% |
| picked | 5d | 201 | +4.32% | 54.2% |
| watchlist | 5d | 893 | +2.11% | 49.9% |
| exception_leader | 1d | 192 | -1.22% | 45.3% |
| exception_leader | 3d | 168 | +1.58% | 60.7% |
| exception_leader | 5d | 154 | +4.78% | 66.2% |

판단:

- KOSDAQ picked Top5는 현재 운영 신뢰도가 낮다.
- Exception Leader가 상대적으로 낫지만, 5D 승률 66.2%로 목표 70% 이상 안정권에는 부족하다.
- KOSDAQ은 KOSPI와 같은 스윙 랭킹 방식으로 처리하면 안 된다.

### Paper Trade Shadow Ledger

KOSDAQ Top5 섀도우 장부는 closed 167건 기준:

- win_rate: 57.49%
- avg_return: +0.80%
- median_return: +1.23%
- max_return: +10.0%
- min_return: -10.0%
- rank1: win_rate 56.25%, avg_return -0.67%
- rank4: win_rate 81.25%, avg_return +4.45%

판단:

- KOSDAQ은 rank1이 약하다.
- 순위 자체가 매수 우선순위를 제대로 설명하지 못하고 있다.
- 이 상태에서 "Top5 상단일수록 좋다"는 UI/Discord 표현은 잘못된 해석을 유도할 수 있다.

### 5D Slice Validation

KOSDAQ 5D resolved 1,950건:

- all_resolved: win5 50.05%, avg5 +2.00%
- rank_top5: win5 57.47%, avg5 +3.47%
- rank1: win5 46.05%, avg5 +0.24%
- bucket_exception_leader: win5 65.64%, avg5 +5.00%
- expected_edge >= 10: win5 58.62%, avg5 +4.44%

판단:

- 기존 KOSDAQ Top5는 최선이 아니다.
- Exception Leader와 일부 실험 후보군이 더 낫지만, 아직 운영 승격 기준에는 부족하다.

## Walk-Forward Release Gate

### KOSPI

Release-ready: false

- EXPLOSIVE_LEADER 1D: mean avg_return +1.69%, lower CI -0.37%, positive lower 26.66%
- CORE_TREND 3D: mean avg_return +2.42%, lower CI -1.78%, positive lower 40.56%

### KOSDAQ

Release-ready: false

- EXPLOSIVE_LEADER 1D: mean avg_return -0.38%, lower CI -1.35%
- CORE_TREND 3D: mean avg_return -2.61%, lower CI -11.74%

판단:

- 양 시장 모두 워크포워드 release gate를 통과하지 못했다.
- 평균값이 좋아 보이는 구간이 있어도, 신뢰 하한이 음수면 운영 매수 신호로 쓰면 안 된다.

## Experimental Candidate Search

### KOSPI

기존 ordered baseline은 좋지 않다.

- 5D ordered 8v4 test win_rate 28.94%, test_stop 67.73%
- 10v5 test win_rate 27.35%, test_stop 66.35%

그러나 좁은 admission 후보군은 가능성이 있다.

- Top3, explosive=0, prob_clean [28.1,31.8], decision_score>=100
- all n=19, win 73.68%
- train n=10, win 70.0%
- test n=9, win 77.78%
- test_stop 22.22%

판단:

- KOSPI는 넓은 ordered baseline이 아니라 좁은 admission gate가 맞다.
- 단, n=19는 운영 확정 표본으로는 작다.

### KOSDAQ

기존 ordered baseline은 매우 약하다.

- 5v5 test win_rate 35.11%, test_stop 63.52%
- 8v5 test win_rate 27.10%, test_stop 69.85%
- 10v5 test win_rate 21.62%, test_stop 73.75%

가능성 있는 후보군:

- volume_ratio <= 1.23
- trend = DOWN
- selection_lane = 1d
- all n=20, win 85.0%
- train n=11, win 81.82%
- test n=9, win 88.89%
- test_stop 11.11%

판단:

- KOSDAQ은 "강한 종목 추격"보다 "저거래량 조정 후 1D 반전" 쪽이 더 맞을 가능성이 있다.
- 하지만 표본이 너무 작아 즉시 운영 모델로 갈 수 없다.

## Regression And Data Integrity Risks

### 1. Factor Trace Coverage Is Weak

`kr_scanner_direction_audit` 기준 누락률:

| market | whale_score missing | expected_edge missing | theme missing | theme_route missing |
|---|---:|---:|---:|---:|
| KOSPI | 93.57% | 96.62% | 94.29% | 95.30% |
| KOSDAQ | 93.38% | 96.34% | 95.78% | 96.32% |

판단:

- 현재 백테스트/회귀 검증은 스캐너가 실제로 쓰는 주요 factor를 충분히 기록하지 못했다.
- 모델 설명은 있어도, 과거 데이터에서 그 설명이 검증 가능한 형태로 남아 있지 않다.
- 이 상태에서는 "왜 맞았는지/왜 틀렸는지"를 강하게 단정할 수 없다.

### 2. Top5 Promotion Rule Is Not Fully Aligned

감사 결과:

- picked bucket이 watchlist보다 항상 우수하지 않다.
- KOSDAQ rank1은 Top5 평균보다 약하다.
- KOSPI도 Top5 전체보다 Exception Leader/edge/rank1이 더 우수하다.

판단:

- 현재 "스캔 상단 = 최우선 매수" 표현은 위험하다.
- UI/Discord는 "운영 Top", "Exception Leader", "실험 Shadow", "관찰 전용"을 명확히 분리해야 한다.

### 3. Theme Overfit Risk

일부 실험 후보는 theme 조건에서 성과가 좋아 보일 수 있다. 그러나 테마는 고정 변수가 아니라 시장 국면에 따라 유동적으로 바뀐다.

판단:

- 고정 theme whitelist는 위험하다.
- 테마는 정적 필터가 아니라 당일 상대강도, 동반 상승 종목 수, 거래대금 증가율, 뉴스/수급 동시성으로 매일 재계산해야 한다.
- 운영 승격 후보는 theme 이름 자체보다 theme strength delta, breadth, liquidity expansion 같은 동적 변수로 검증해야 한다.

## Can It Make Accurate Buy Decisions Now?

현재 답은 "아니다".

정확히 말하면:

- KOSPI: 후보 발굴과 5D 조건부 관찰은 가능하다. 즉시 매수 판단은 아직 불가하다.
- KOSDAQ: 기존 Top5 기반 매수 판단은 불가하다. Exception/1D 반전 실험군은 연구 가치가 있으나 운영 확정 전이다.

현재 가능한 최선의 운영 해석:

1. Top5는 매수 리스트가 아니라 후보 리스트다.
2. Exception Leader는 보조 후보가 아니라 별도 우위 후보군으로 분리해서 봐야 한다.
3. KOSPI는 rank1/edge/Exception 중심으로 admission gate를 좁혀야 한다.
4. KOSDAQ은 Top5 순위보다 1D 반전/저거래량/손실제어 후보군을 별도 모델로 검증해야 한다.
5. 추천 문구는 "매수"가 아니라 "조건부 진입 가능/관찰/무효 조건"으로 표현해야 한다.

## When Can Accurate Buy Decisions Be Claimed?

날짜로 약속하면 안 된다. resolved observation 기준으로만 승격해야 한다.

최소 승격 기준:

- 시장/전략 lane별 20-30 active trading days 이상 전진 관찰
- broad policy는 100건 이상 resolved 후보
- narrow admission gate는 최소 30건 이상 resolved 후보
- walk-forward release gate 통과
- confidence lower bound가 양수
- positive rate lower bound >= 60%
- avoid-down lower bound >= 70%
- stop-before-target <= 20-25%
- factor trace coverage >= 95%
- Discord/Web/Supabase archive 간 결과 정합성 100%

현재 데이터 기준 예상:

- KOSPI narrow admission gate: 추가 2-4주 관찰 후 30-50건 이상 resolved가 쌓이고 현재 우위가 유지되면 제한적 운영 승격 검토 가능.
- KOSDAQ: 추가 4-8주 이상 필요. 현재 broad Top5는 승격 대상이 아니고, 별도 1D/반전형 후보군을 검증해야 한다.

## Recommended Direction

### Keep

- KOSPI Exception Leader 별도 표시
- KOSPI rank1/edge 기반 admission gate 연구
- Shadow model daily tracking
- 1D/3D/5D realized outcome tracking

### Change Before Trusting

- Top5를 "최우선 매수"처럼 보이게 하는 UI/Discord 표현 제거
- KOSDAQ Top5를 운영 핵심 모델처럼 취급하지 않기
- Exception Leader를 Top5 아래 보조가 아니라 별도 카드/섹션으로 명확히 구분
- archive에 factor traces를 완전 저장
- 손실경로 기준을 `1D drawdown`, `stop-before-target`, `MAE`, `MFE` 중심으로 고정
- 테마는 이름 필터가 아니라 동적 strength/breadth/liquidity 변수로 처리

### Do Not Change Yet

- 기존 운영 스캐너를 새 실험 후보로 즉시 대체하지 않는다.
- 표본 n<30 후보를 production 매수 신호로 승격하지 않는다.
- KOSDAQ rank1을 최고 후보로 강조하지 않는다.

## Final Conclusion

지금 방향은 일부 맞지만, 최선은 아니다.

- KOSPI는 "후보 발굴 + 조건부 5D 우위"는 확인된다.
- KOSDAQ은 기존 Top5 운영 방향이 약하고, 별도 모델로 분리해야 한다.
- 양 시장 모두 아직 "정확한 매수 판단"이라고 부를 수 있는 release gate를 통과하지 못했다.

가장 중요한 다음 단계는 모델을 더 복잡하게 만드는 것이 아니라, 실제로 돈을 잃게 만든 경로를 데이터 구조로 고정하는 것이다.

운영 승격 판단은 다음 한 줄로 정리한다.

> 상승률 평균이 아니라, 목표 수익에 먼저 도달하고 손절선에 먼저 닿지 않는 후보를 일관되게 고르는가.

