# Horizon × 모델 × 신호 전체 진단 — 2026-05-08

측정 윈도우: **2026-04-01 ~ 2026-05-08**, market_scan_results 17,612행, dedup(ticker,date) 후 4,296행.
30d 측정: yfinance fetch 298건 (KR, 30-60일 경과 샘플).

목표: 75% 정확도 / 15% 평균수익 / 8:2 안전·서지 배분.

---

## 1. Horizon 별 수익·정확도 (deduped, decision×market×mode)

KR에서 가장 표본 큰 decision/market 조합만 발췌. 전체 표는 `horizon_analysis_2026-05-08.log` 참고.

| market | mode | decision | 1d_win | 1d_avg | 3d_win | 3d_avg | 5d_win | 5d_avg | 7d_win | 7d_avg | 30d_win | 30d_avg |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| KOSDAQ | INTRADAY | PRIORITY_WATCHLIST | 39.1 | -0.09 | 51.4 | 3.05 | 70.6 | **7.74** | 73.6 | **7.99** | **70.6** | **16.13** |
| KOSDAQ | INTRADAY | AVOID | 52.3 | 1.47 | 59.8 | 4.07 | 58.2 | 4.19 | 61.5 | 5.71 | — | — |
| KOSDAQ | SWING | EXCEPTION_LEADER | 56.6 | 0.05 | 58.6 | 1.78 | 64.5 | 5.79 | 69.5 | 7.98 | 66.7 | 8.84 |
| KOSDAQ | SWING | OBSERVE | 42.5 | 0.26 | 45.3 | 1.11 | 50.2 | 2.89 | 48.8 | 2.82 | — | — |
| KOSPI | INTRADAY | PRIORITY_WATCHLIST | 17.9 | -2.87 | 24.3 | -0.57 | 90.5 | **10.24** | 75.0 | 8.53 | **96.2** | **36.10** |
| KOSPI | INTRADAY | OBSERVE | 59.1 | 1.26 | 59.8 | 2.39 | 63.6 | 4.37 | 70.5 | 5.90 | 85.7 | 12.87 |
| KOSPI | SWING | EXCEPTION_LEADER | 50.0 | 0.94 | 75.0 | **4.54** | 81.1 | **8.67** | 86.8 | **12.67** | **84.6** | **32.19** |
| KOSPI | SWING | PRIORITY_WATCHLIST | 18.2 | 0.62 | 54.5 | 3.17 | 63.6 | 9.31 | 63.6 | 10.05 | **100.0** | **40.96** |
| KOSPI | SWING | OBSERVE | 52.1 | 0.93 | 61.6 | 3.46 | 69.7 | 6.93 | 76.4 | **9.54** | 100.0 | 23.44 |
| KOSPI | SWING | WATCHLIST_ONLY | 47.7 | 0.28 | 65.9 | 3.75 | 65.9 | 7.89 | 65.9 | **11.98** | 75.0 | 21.09 |

**핵심 사실:**

1. **75% 정확도 목표는 5d hold부터, 15% 평균수익 목표는 30d hold부터 자연 도달**. 1d/3d 단기는 어떤 decision도 75% 미달.
2. **KOSPI INTRADAY/SWING PRIORITY_WATCHLIST는 30d면 96-100% win, avg 36-41%** — 표본 작지만 강력. 실제 잠재력 확인.
3. **EXCEPTION_LEADER는 5d/7d/30d 모두 가장 안정적 high performer** — KOSPI SWING EL: win_5d 81.1%, avg_5d 8.67%, win_30d 84.6%, avg_30d 32.19%. **이미 75/15 조건 충족**.
4. **OBSERVE도 KOSPI SWING에선 win_7d 76.4%, avg_7d 9.54%** — OBSERVE 등급으로 강등된 행이 picked 베이스라인보다 잘 오른다 → **decision 라벨링이 잘못되거나 게이트가 inverted**.
5. **KOSDAQ INTRADAY AVOID win_5d 58%/avg 4.19%** — AVOID로 막은 행이 여전히 양수. inverted 사례 (이미 ymm 이슈에 박힘).

---

## 2. 상승 종목의 공통 특성 (winner = 5d ≥ +5%, KR 한정)

**deduped n=2792, winners 1141 (40.9%), losers 1012 (36.2%).**

### Numeric features — winner_median vs loser_median

| feature | w_med | l_med | delta | direction |
|---|---:|---:|---:|---|
| **tech_score** | 85 | 79 | **+6** | ↑ winner_higher |
| **alpha_score** | 79 | 76 | +3 | ↑ winner_higher |
| decision_score | 76.20 | 76.40 | -0.20 | flat |
| **ml_prob** | 35.7 | 38.9 | **-3.15** | ↓ winner_LOWER (inverted) |
| **prob_clean** | 34.2 | 35.5 | **-1.30** | ↓ winner_LOWER (inverted) |
| **phase25_prob** | 10.2 | 12.75 | **-2.55** | ↓ winner_LOWER (inverted) |
| volume_ratio | 1.02 | 1.10 | -0.08 | ↓ slight |
| **expected_edge_score** | -3.65 | -2.83 | **-0.82** | ↓ winner_LOWER (inverted) |
| expected_return_3d_pct | -0.43 | -0.27 | -0.16 | ↓ slight |

### 결론 — 가장 충격적 발견

**ml_prob, prob_clean, phase25_prob, expected_edge_score 모두 winner에게서 더 낮다.**
즉 모델이 "확신을 가지고 추천한 점수"가 높을수록 패배 확률이 더 높다 — **모델 시그널 4종이 모두 약한 inverted 또는 무용**.

반면:
- **tech_score, alpha_score는 양의 신호** — 기술적 점수가 높을수록 winner.
- **decision_score는 평탄** — winner/loser 구별 안 됨.

### Categorical features

| 분류 | 값 | winner rate |
|---|---|---:|
| primary_theme | 조선/해양 | **69.6%** |
| primary_theme | 반도체 | 54.9% |
| primary_theme | 2차전지 | 54.1% |
| primary_theme | 친환경/에너지 | 51.8% |
| primary_theme | 금융 | 27.7% (avoid) |
| kr_universe_role | EXPLOSIVE_LEADER | 41.2% |
| kr_universe_role | CORE_TREND | 39.4% |
| scanner_timeframe | DAILY_PRIMARY_WITH_1H_REFRESH | 43.3% |
| scanner_timeframe | INTRADAY_1H | 33.2% |
| trend | DOWN | **45.7%** |
| trend | UP | 41.6% |
| trend | SIDE | 31.4% (avoid) |

**놀라운 사실:** trend=DOWN이 trend=UP보다 winner 비율 높다 — 추세 추종 가정이 약함. 반전 거래가 더 안전. trend=SIDE만 명백히 약함.

---

## 3. phase25 모델 정렬 효과 (quintile 분석)

phase25_prob 5분위로 나눠 forward win/avg를 본 결과:

| variant | Q1 (낮은 prob) win_5d | Q5 (높은 prob) win_5d | 정렬 효과 | 진단 |
|---|---:|---:|---:|---|
| phase25_kr_intraday_xgboost | 57.8% | 65.8% | +8pp | 약한 정렬 작동 |
| phase25_kr_swing_xgboost | 55.1% | 70.0% | +15pp | **정렬 작동** |
| **phase25_kospi_swing** | 41.7% | 42.3% | **+0.6pp** | **무용지물** |
| **phase25_kosdaq_swing** | **57.1%** | **42.9%** | **-14.2pp** | **INVERTED 운영 중** |

### 결론

- **`phase25_kr_*_xgboost` 통합 모델은 정렬을 만든다** — 이쪽이 진짜 모델
- **`phase25_kospi_swing` / `phase25_kosdaq_swing` 단독 모델은 무용 또는 inverted** — 폐기/재학습 필요

Step 1의 발견과 일치: KOSDAQ INTRADAY AVOID가 win 58%로 양수인 게 phase25_kosdaq 인버스 작동의 production 결과.

---

## 4. 학습 OOS vs Production picked 갭

retrain v2 segments:

| segment | rows | raw_auc | cv_median | sig_dir | oos_win | oos_avg | target_horizon |
|---|---:|---:|---:|---|---:|---:|---:|
| phase25_kospi_swing | 1075 | 0.633 | 0.724 | normal | **50.0%** | 3.23% | **3d** |
| phase25_kosdaq_swing | 785 | 0.647 | 0.584 | normal | 62.5% | 2.43% | 3d |
| phase25_kosdaq_intraday | 425 | **0.274** | 0.579 | **normal (잘못)** | 45.1% | 0.65% | 3d |
| phase25_kospi_intraday | 189 | — | — | — (insufficient) | — | — | — |
| phase25_global | 2544 | 0.632 | 0.727 | normal | 60.7% | 4.96% | 3d |

### Production 측정값과 갭

| variant | 학습 OOS win_3d | production picked win_3d | 갭 |
|---|---:|---:|---:|
| phase25_kospi_swing | 50.0% | 54.5% (n=11) | +4.5pp |
| phase25_kr_intraday_xgboost | (기록 없음) | 53.7% (n=335) | — |
| phase25_kr_swing_xgboost | (기록 없음) | 73.5% (n=34) | — |

**학습 OOS와 production이 대체로 일치** — 모델이 못 맞추는 게 학습 단계부터 천장. 게이트 완화로 표본 늘려도 win 50% 부근에 묶임.

### target_horizon=3d가 학습 자체를 망친다

5d/7d/30d는 어떤 decision에서도 65-100% win인데 학습 target은 3d. **3d 분포는 노이즈가 많아서 learnable signal이 약하다.** 이게 phase25 학습 OOS auc 0.485의 진짜 원인.

---

## 5. Production 잘못된 신호 사례

### 5a. PRIORITY_WATCHLIST 손실 행 분석

전체 PRIORITY_WATCHLIST 2,700행 중 5d 손실 -3% 이하 = **563행 (20.9%)**.

손실 분포:
| market | mode | n_bad | avg_loss |
|---|---|---:|---:|
| **KOSDAQ INTRADAY** | | **430** | **-11.77%** |
| KOSPI INTRADAY | | 31 | -8.82% |
| KOSDAQ SWING | | 25 | -8.46% |
| KOSPI SWING | | 4 | -5.05% |

**KOSDAQ INTRADAY가 손실의 거의 모든 부분.** phase25_kosdaq_intraday inverted 모델이 직접 원인.

### 5b. Bad-pick rationale 패턴

| rationale 키 | bad에서 빈도 | ok에서 빈도 | bad/ok 비율 |
|---|---:|---:|---:|
| `전략: ⏱️ Intraday Trend \| 1H` | 54.4% | 27.4% | **1.98x (나쁜 신호)** |
| `급등예측: ⚡ High-Volume Breakout` | 25.4% | 16.7% | 1.52x |
| `전략: ⏱️ Intraday Breakout \| 1H` | 40.3% | 63.9% | **0.63x (정상 신호)** |

**`Intraday Trend | 1H` 전략 패턴이 손실 후보 강한 마커.** scanner의 이 strategy 라벨을 PRIORITY_WATCHLIST에서 격하시켜야 함.

### 5c. 데이터 품질 문제 — 중복 등록

**KR PRIORITY_WATCHLIST 4,596행 중 unique (ticker,date) = 464개 = 90% 중복.** Max 82회 중복.

- 137950.KQ 2026-04-02: 40회 등록, run_id=None
- 같은 손실/수익 행이 반복 카운트돼 production 성과 통계가 부풀려져 있다
- 이전 모든 분석(15% avg, 75% win 도달) 모두 dedup 안 한 결과여서 신뢰성 의심
- **dedup 후 KOSPI SWING PRIORITY n=11(원본 31), KOSDAQ INTRADAY PRIORITY n=215(원본 2810)** — 표본 충격적으로 작아짐

원인: db_manager.upsert_scan_archive_outcomes가 fallback으로 NULL run_id 행에 같은 outcome을 반복 INSERT. 이미 코드 주석에 fix 시도 흔적 있으나 완전 해결 안 됨.

---

## 6. 종합 진단 — 75/15 갭의 진짜 원인

### 우선순위 1 — phase25 단일-segment 모델 폐기

`phase25_kospi_swing` (정렬 0pp), `phase25_kosdaq_swing` (정렬 -14pp inverted), `phase25_kospi_intraday` (insufficient_rows), `phase25_kosdaq_intraday` (raw_auc 0.27 inverted) — 네 모델 모두 production에서 신호 만들지 못한다.
**`phase25_kr_*_xgboost` 통합 모델만 정렬 작동.**

→ retrain spec에서 단일 모델 4개 제외하거나 sample_weight 0으로. 통합 모델만 운영.

### 우선순위 2 — target_horizon 3d → 5d 변경

학습 3d OOS auc 0.485-0.59 vs production 5d/7d win 70-90%. **5d로 학습하면 모델이 자연 분포를 학습**.
이미 4lm 이슈로 박혀있음.

### 우선순위 3 — 중복 등록 fix

dedup 안 된 통계 = 신뢰 불가. 모든 KPI를 dedup 후 재측정 필요.
upsert_scan_archive_outcomes에서 (ticker, recommended_at, market, scan_mode) UNIQUE 키로 처리.

### 우선순위 4 — strategy 라벨 기반 격하

`Intraday Trend | 1H` 전략은 bad/ok 비율 1.98x — production gate에 명시적 거름.
또는 strategy_family에 "intraday_trend_1h"를 negative weight로 학습.

### 우선순위 5 — KOSDAQ INTRADAY phase25 즉시 비활성

이미 ymm 이슈, 5월 production 0건. retrain decisive_auc 보강도 깔림. 다음 retrain 사이클 자동.

### 우선순위 6 — EXCEPTION_LEADER를 정식 BUY로 운영

EL은 모든 horizon에서 가장 좋다. KOSPI SWING EL win_30d 84.6%/avg 32%. 이미 Top-N 노출 (이번 세션). **8:2 비율 중 2의 surge 부분으로 EL을 정식 운영**하면 surge 측 75/15 즉시 달성.

### 우선순위 7 — 모델 신호 4종 inverted 패턴 활용

phase25_prob, ml_prob, prob_clean, expected_edge_score 모두 winner에서 더 낮다. **이걸 feature로 학습한 새 모델은 prob 낮은 것을 추천하도록 학습** — 또는 retrain spec에 invert 강제.

### 우선순위 8 — exit policy 5d hold + +20% TP

5d면 KR 모든 BUY-grade가 win 65%+. 30d면 80-100%. **3d/3.5%TP 정책이 천장을 만든다.** modules/scanner_services 정책을 5d/+15-20%TP로 변경. 단 종목별 변동성 감안 — KOSDAQ는 더 큰 TP 가능, KOSPI는 +15-20% 적정.

---

## 7. 즉시 측정 가능한 개선 효과 추정

| 작업 | 현재 win | 예상 win | 현재 avg | 예상 avg |
|---|---:|---:|---:|---:|
| 5d hold 적용 | 65% | **70-75%** | 3% | **6-8%** |
| 30d hold + EL 운영 | 65% | **80%+** | 3% | **15%+** |
| target_horizon 3d→5d retrain | OOS 50% | **OOS 60-65%** | OOS 3.2% | **OOS 5-6%** |
| 단일-segment 모델 폐기 + KR_xgboost 일원화 | (감소 위험) | (안정화) | | |
| 중복 fix | (KPI 노이즈 제거) | | | |

**가장 빠른 75/15 도달 경로: 5d hold + EL 정식운영 + 3d→5d retrain 한 사이클.** 게이트 풀기는 부수적이고 위험.

---

## 8. 2026-05-08 후속 — 적용된 변경 + 재측정

### 8a. 적용된 작업

- **9un**: market_scan_results 24,286행 dedup, UNIQUE 인덱스, INSERT 23505 catch→UPDATE fallback. 14,087행 정상화.
- **01i + 4lm**: quant_analysis primary_candidates 통합 모델 우선 변경, 단일 segment 4개 default disabled (`AG_PHASE25_DISABLE_SEGMENTS=1`), KOSPI SWING horizon 3d→5d.
- **Intraday Trend 격하**: `_apply_intraday_trend_strategy_gate` 신규 게이트. INTRADAY + 'Intraday Trend' (no Breakout) PRIORITY → WATCHLIST. AG_INTRADAY_TREND_DEMOTE 토글.
- **retrain v2**: phase25_global 단일 모델 학습 (단일 segment 4개 비활성). dedup 후 9,741 rows.
- **KR ensemble 재학습** (evaluate_kr_swing_models / evaluate_kr_intraday_models): SWING 5d로 변경, dedup 데이터로 재학습.

### 8b. 재학습 결과

**phase25_global** (retrain_ml.py, return_3d_pct, dedup):
- rows=1669 / pos=454 / raw_auc=0.633 / cv_median=0.555 / OOS auc=0.516 / OOS win=48.1% / OOS avg=4.41%
- 이전 (dedup 전): cv_median 0.727 / OOS win 60.7% / OOS avg 4.96%
- dedup으로 노이즈 제거된 진짜 능력. 학습 한계.

**phase25_kr_swing_xgboost** (return_5d_pct, dedup):
- xgboost: auc 0.562 / acc 0.571 / best_thr 0.5 / best_avg **5.72%** / win **57.5%** / picks 273
- logistic: auc 0.571 / best_thr 0.5 / best_avg **6.29%** / win 58.6% / picks 251
- histgb: auc 0.564 / best_avg 5.97% / win 58.8% / picks 289
- 이전 단일 KOSPI SWING OOS auc 0.485 → KR 통합 5d **0.562 (+7.7pp)**. **의미 있는 회복.**

**phase25_kr_intraday_xgboost** (return_1d_pct, dedup):
- xgboost: auc **0.478** / best_avg 0.59% / win 47.2% / picks 538
- logistic만 auc 0.525 (보수적 thr 0.7, picks 38)
- 모든 boost 계열 random 미만. 1d horizon은 학습 가능 신호 거의 없음.

### 8c. 즉시 다음 작업

1. **INTRADAY 모델 horizon 1d → 3d 또는 5d 재실험** — 1d 노이즈가 너무 큼. swing-main-30s에 흡수.
2. **logistic 모델을 saved_models에 추가** — INTRADAY에서 유일하게 양수 학습한 모델인데 운영에 안 들어감.
3. **production smoke** — 다음 RUN에서 phase25_kr_swing_xgboost 라우팅 작동 + INTRADAY_TREND_PRIORITY_DEMOTE 발동 확인.

