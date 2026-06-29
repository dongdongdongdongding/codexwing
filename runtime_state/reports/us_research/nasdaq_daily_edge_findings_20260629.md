# NASDAQ 일봉 엣지 연구 결론

- 데이터: `/Users/dongdong/research_cache/us_daily/NASDAQ/daily_features_20180101_20260630_20260629_113805.parquet`
- 검증일: `2026-06-29`
- 유니버스: 현재 상장 NASDAQ 기준. 상폐 포함 survivorship-free 히스토리는 아님.
- 운영형 필터: `close >= 1`, `feature_ready = 1`, `liq20 >= 10,000,000 USD`
- 검증 방식: 연도별 walk-forward, 학습일 이후 20일 embargo, same-day universe 및 same-day liquidity bucket 대비 초과 성과.

## 최종 후보

현재 가장 괜찮은 후보는 `ml_combo_touch_ft_risk`다.

- 점수식: `P(touch5_3d) + P(ft_5_5) - P(dd5_3d)`
- 학습: LightGBM, 2020~2026 연도별 OOS, 과거 데이터만 사용
- 운영 후보: `liq20 >= 100,000,000 USD`, 일별 top1~top5

## top1 성능

- 표본: `1,624`픽, `1,624`거래일, `313`종목
- 3일 내 +5% 터치율: `54.19%`
- 5일 first-touch(+5 before -5): `51.17%`
- 3일 내 -5% 터치율: `49.82%`
- 3일 close return liquidity-matched 초과: `+0.560%`, CI95 `[+0.075, +1.046]`
- 5일 close return liquidity-matched 초과: `+0.953%`, CI95 `[+0.263, +1.642]`
- 연도별 3일 초과수익 양수: `6/7`
- 연도별 5일 초과수익 양수: `6/7`
- 연도별 ft55 초과 양수: `7/7`

## top5 성능

- 표본: `8,120`픽, `1,624`거래일, `495`종목
- 3일 내 +5% 터치율: `52.55%`
- 5일 first-touch(+5 before -5): `50.34%`
- 3일 내 -5% 터치율: `51.26%`
- 3일 close return liquidity-matched 초과: `+0.265%`, CI95 `[+0.055, +0.476]`
- 5일 close return liquidity-matched 초과: `+0.511%`, CI95 `[+0.225, +0.796]`
- 연도별 3일 초과수익 양수: `5/7`
- 연도별 5일 초과수익 양수: `5/7`
- 연도별 ft55 초과 양수: `7/7`

## 70% 터치율 검증

70% 이상의 3일 +5% 터치율은 만들 수 있지만, 수익 모델이 아니다.

- `ml_touch5_3d`, `liq20 >= 30,000,000`, top1:
  - 3일 내 +5% 터치율: `70.6%`
  - 5일 first-touch: `58.2%`
  - 3일 내 -5% 터치율: `75.1%`
  - 3일 초과수익: `-1.193%`
  - 5일 초과수익: `-2.021%`
- `touch3 >= 65%`이면서 3일/5일 liquidity-matched 초과수익이 모두 양수인 후보: `0개`
- `touch3 >= 70%`이면서 3일/5일 liquidity-matched 초과수익이 모두 양수인 후보: `0개`

따라서 현재 데이터에서 운영 가능한 방향은 `70% 터치율 모델`이 아니라 `수익률 초과 모델`이다.

## 판정

- production 즉시 승급: 보류
- forward-shadow 후보: 가능
- 가장 좋은 운영 후보: `ml_combo_touch_ft_risk`, `liq20 >= 100,000,000`, 일별 top1 또는 top3
- 목적 함수: 3일/5일 close return 초과수익 + ft55 보조
- 폐기해야 할 헤드라인: 70% 터치율 단독 최적화

## 다음 작업

1. `ml_combo_touch_ft_risk`를 NASDAQ shadow scanner 후보로 연결한다.
2. 일별 top1/top3/top5를 forward ledger에 따로 기록한다.
3. 체결 비용을 보수적으로 `0.10%`, `0.20%`, `0.35%` 세 단계로 스트레스한다.
4. 2022년 음수 구간의 공통 조건을 별도 가드로 연구한다.
5. survivorship-free 유니버스를 확보하기 전까지 production narrative에는 생존편향 caveat를 반드시 붙인다.
