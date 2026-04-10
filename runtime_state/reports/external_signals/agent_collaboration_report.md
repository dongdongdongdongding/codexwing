# External Signals Agent Collaboration Report

## Agent Roles
- Scanner Agent: CSV 정규화, 시장 분류, 스캔 표본 정리
- Market & News Context Agent: 일별 시장 레짐(BULL/NEUTRAL/BEAR) 라벨링
- Backtest & Learning Agent: 1/2/3/5일 후행 수익률, MFE/MAE, 변동성 계산
- Aggregation Agent: 티커별 적응형 손절/안전 익절 정책 생성
- PM Planner Agent: 레짐별 성과와 티커 정책을 종합해 운영 해석 정리

## Scanner Agent
- rows: 3,167
- unique tickers: 933
- markets: {'KOSPI': 1414, 'KOSDAQ': 1179, 'US': 574}

## Market Context Agent
- 레짐 기준: benchmark 일간 수익률이 +0.8% 이상이면 BULL, -0.8% 이하이면 BEAR, 그 사이는 NEUTRAL

## Backtest & Learning Agent
- 1d avg=+2.35% / win rate=64.4% / samples=3,018
- 2d avg=+1.45% / win rate=60.7% / samples=3,018
- 3d avg=+1.04% / win rate=55.9% / samples=3,018
- 5d avg=+1.86% / win rate=50.1% / samples=3,018

### Best Regime Buckets (by 5d avg return)
| market | regime | signals | tickers | avg_1d_pct | win_1d_pct | avg_2d_pct | win_2d_pct | avg_3d_pct | win_3d_pct | avg_5d_pct | win_5d_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KOSDAQ | BULL | 164 | 36 | 2.60 | 67.07 | 0.36 | 54.88 | -0.37 | 56.10 | 5.87 | 64.02 |
| KOSPI | BULL | 909 | 107 | 4.34 | 76.46 | 3.55 | 69.97 | 1.65 | 60.29 | 5.42 | 59.63 |
| KOSDAQ | BEAR | 896 | 434 | 3.33 | 66.63 | 2.78 | 63.69 | 2.74 | 60.76 | 2.46 | 52.57 |
| KOSPI | BEAR | 422 | 348 | 0.12 | 62.04 | -1.36 | 65.72 | 1.10 | 65.72 | 2.20 | 66.86 |
| KOSPI | NEUTRAL | 83 | 83 | 0.75 | 55.42 | 2.32 | 61.45 | 3.55 | 57.83 | -2.05 | 30.12 |
| US | BULL | 215 | 57 | -0.26 | 40.47 | -0.35 | 53.02 | -1.73 | 43.26 | -3.20 | 32.56 |
| KOSDAQ | NEUTRAL | 119 | 66 | 0.54 | 45.38 | -2.56 | 40.34 | 0.28 | 44.54 | -3.28 | 27.73 |
| US | NEUTRAL | 294 | 66 | -0.52 | 48.98 | -1.99 | 37.07 | -3.11 | 30.95 | -4.89 | 21.09 |

### Weak Regime Buckets (by 5d avg return)
| market | regime | signals | tickers | avg_1d_pct | win_1d_pct | avg_2d_pct | win_2d_pct | avg_3d_pct | win_3d_pct | avg_5d_pct | win_5d_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| US | BEAR | 63 | 38 | 0.75 | 68.25 | 1.28 | 50.79 | 0.26 | 53.97 | -6.12 | 12.70 |
| US | NEUTRAL | 294 | 66 | -0.52 | 48.98 | -1.99 | 37.07 | -3.11 | 30.95 | -4.89 | 21.09 |
| KOSDAQ | NEUTRAL | 119 | 66 | 0.54 | 45.38 | -2.56 | 40.34 | 0.28 | 44.54 | -3.28 | 27.73 |
| US | BULL | 215 | 57 | -0.26 | 40.47 | -0.35 | 53.02 | -1.73 | 43.26 | -3.20 | 32.56 |
| KOSPI | NEUTRAL | 83 | 83 | 0.75 | 55.42 | 2.32 | 61.45 | 3.55 | 57.83 | -2.05 | 30.12 |
| KOSPI | BEAR | 422 | 348 | 0.12 | 62.04 | -1.36 | 65.72 | 1.10 | 65.72 | 2.20 | 66.86 |
| KOSDAQ | BEAR | 896 | 434 | 3.33 | 66.63 | 2.78 | 63.69 | 2.74 | 60.76 | 2.46 | 52.57 |
| KOSPI | BULL | 909 | 107 | 4.34 | 76.46 | 3.55 | 69.97 | 1.65 | 60.29 | 5.42 | 59.63 |

## Aggregation Agent
- `adaptive_stop_pct`: 티커별 ATR20과 5일 내 adverse excursion(MAE) 분포를 합쳐 계산
- `safe_take_profit_pct`: 티커별 positive MFE / 5일 수익률 분포를 보수적으로 반영

### Stable Ticker Policies (signals >= 3)
| ticker | stock_name | signals | avg_5d_pct | win_5d_pct | adaptive_stop_pct | safe_take_profit_pct | risk_reward_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL | Apple Inc | 33 | -4.67 | 3.03 | 5.90 | 8.26 | 1.40 |
| AMGN | Amgen Inc | 24 | -2.56 | 0.00 | 4.73 | 6.62 | 1.40 |
| ADI | Analog Devices Inc | 24 | -7.62 | 0.00 | 9.83 | 13.76 | 1.40 |
| AMAT | Applied Materials Inc | 24 | -10.75 | 0.00 | 14.13 | 19.78 | 1.40 |
| 009150.KS | 삼성전기 | 18 | 28.58 | 76.47 | 14.38 | 33.47 | 2.33 |
| 000660.KS | SK하이닉스 | 18 | 13.27 | 72.22 | 5.69 | 21.25 | 3.73 |
| 066570.KS | LG전자 | 18 | 12.60 | 76.47 | 5.15 | 27.22 | 5.28 |
| 006400.KS | 삼성SDI | 18 | 12.08 | 76.47 | 6.61 | 20.45 | 3.10 |
| 402340.KS | SK스퀘어 | 18 | 10.70 | 77.78 | 7.32 | 20.19 | 2.76 |
| 006800.KS | 미래에셋증권 | 18 | 10.33 | 66.67 | 7.07 | 22.68 | 3.21 |
| 034730.KS | SK | 18 | 9.70 | 70.59 | 5.48 | 15.94 | 2.91 |
| 032830.KS | 삼성생명 | 18 | 7.69 | 76.47 | 4.88 | 26.28 | 5.38 |
| 105560.KS | KB금융 | 18 | -3.87 | 5.56 | 4.29 | 7.03 | 1.64 |
| 055550.KS | 신한지주 | 18 | -4.15 | 0.00 | 4.49 | 6.98 | 1.56 |
| 086790.KS | 하나금융지주 | 18 | -5.26 | 0.00 | 4.34 | 7.10 | 1.64 |

## PM Planner Agent
- 제공된 `result_3d` 값에는 극단 outlier가 있어, 본 분석은 외부 가격 데이터로 1/2/3/5일 수익률을 다시 계산함
- 상승/하락/평범장을 분리해 봐야 전략의 진짜 민감도를 볼 수 있음
- 손절/익절은 고정 퍼센트보다 티커별 MAE/MFE/ATR 기반 정책이 더 안전함