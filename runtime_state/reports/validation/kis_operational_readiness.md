# KIS 운영 전환 및 모델 개선 가능성 검증

## 결론
- 운영 전환 판단: KR 운영 전체를 지금 KIS로 일괄 전환하면 안 된다. 먼저 KIS를 단계적 보강 데이터 소스로 써야 한다.
- 원활한 운영 상태: 현재가/랭킹/뉴스 제목/KR 지수 경로는 사용 가능하다. OHLCV adapter, 시간 제한 수급, 섹터/테마 결측은 남아 있다.
- 모델 개선 판단: 모델 개선 가능성은 있지만 아직 증명되지 않았다. KIS 피처 병렬 아카이브와 challenger 검증이 필요하다.

## 실측 근거
- 전체+재시도 기준 quote 유효 커버리지: 2554/2554 (100.0%)
- KOSPI: 전체 스윕 835/835 성공, rate-limit 재시도 회복 0건, 실효 성공률 100.0%, sector_name 결측 53.892%
- KOSDAQ: 전체 스윕 1719/1719 성공, rate-limit 재시도 회복 0건, 실효 성공률 100.0%, sector_name 결측 82.664%
- 기능 endpoint 체크: 25/25 성공, 실패 0건
- 장후 종목별 수급 샘플: 4/4 성공
- KOSDAQ volume_rank 행 수: 30

## 운영 기능별 판단
| 영역 | KIS 준비도 | 판단 |
|---|---:|---|
| scanner_price_snapshot | ready_with_throttle | KIS가 이 경로를 지원할 수 있다. 운영 적용 전 초당 제한 대응, 캐시, 재시도 정책이 필요하다. |
| scanner_daily_ohlcv | adapter_work_needed | 샘플 endpoint는 동작했다. 다만 KIS 응답을 OHLCV DataFrame으로 바꾸는 이력 adapter와 장기간 커버리지 검증이 필요하다. |
| scanner_intraday_ohlcv | adapter_work_needed | 당일 분봉 샘플은 성공했다. 운영에는 기간/시간창 adapter와 fallback 정책이 필요하다. |
| investor_flow | ready_post_close_sampled | 15:40 KST 이후 샘플 4/4건에서 종목별 수급 조회가 성공했다. 운영에는 장후/장중 시간대별 경고와 fallback을 유지한다. |
| rank_and_market_microstructure | ready_with_verified_kosdaq_params | KOSDAQ volume_rank가 30행을 반환해 기존 1행 의심은 해소됐다. 랭킹 endpoint는 호출 제한과 캐시 정책을 두고 운영 보강 피처로 사용할 수 있다. |
| top_deep_price_news_flow | partial | KIS가 가격과 뉴스 제목은 보강할 수 있다. 감성 분석과 시간 제한 수급은 기존 provider 또는 wrapper가 필요하다. |
| sector_theme_context | not_enough_alone | KIS quote의 sector_name 커버리지가 부족하다. 기존 테마/종목 마스터 파이프라인은 유지해야 한다. |
| macro_context | partial | KIS는 KR 지수 조회를 보강할 수 있지만 FX/VIX/TNX/글로벌 리스크 컨텍스트는 대체하지 못한다. |
| model_training_features | promising_not_proven | KIS 보강 challenger는 유망하지만, 피처를 저장하고 백테스트하기 전까지 더 좋은 모델이라고 증명할 수 없다. |

## 모델 개선 가능성
- 판정: KIS 보강 모델은 가능성이 있다. 그러나 KIS 단독 즉시 대체와 모델 성능 개선은 아직 증명되지 않았다.
- 유망 KIS 추가 피처:
  - quote_snapshot의 거래대금(value_traded)과 시가총액(market_cap)
  - 전일대비 거래량 비율(prev_volume_ratio)과 분봉 기반 실시간 거래량 곡선
  - 종목별 endpoint가 가능한 시간대의 외국인/기관/개인 금액 수급
  - 거래량/등락률/체결강도 랭킹 포함 여부와 순위
  - VI/status warning 기반 위험 필터
  - PER/PBR/EPS/BPS 저빈도 스타일/레짐 통제 피처
- 아직 증명되지 않은 이유:
  - KIS 피처의 과거 아카이브가 아직 없어 직접적인 OOS 성능 개선을 측정할 수 없다.
  - 장후 종목별 수급 샘플은 성공했지만, 장중 시간제한과 fallback 정책은 운영에서 계속 검증해야 한다.
  - quote_snapshot의 sector_name 커버리지가 부족해 테마 컨텍스트를 대체할 수 없다.
  - 운영 스캐너는 아직 yfinance/PyKrx 형태의 OHLCV DataFrame을 기대한다.
- 권장 검증 순서:
  - quote/daily/minute/flow/rank용 비운영 KIS feature snapshot adapter를 만든다.
  - 추천 로직은 바꾸지 않고 기존 scanner row 옆에 KIS 피처를 병렬 저장한다.
  - KOSPI/KOSDAQ SWING 및 INTRADAY 결과를 최소 2-4주 수집한다.
  - KIS 피처군을 on/off한 challenger 모델을 학습하고 segment별 Top5 positive rate, 평균 5D 수익률, bad path, stop-first를 비교한다.
  - 현재 운영 release gate를 넘고 tail loss가 악화되지 않을 때만 승격한다.

## 실패/제약 endpoint
