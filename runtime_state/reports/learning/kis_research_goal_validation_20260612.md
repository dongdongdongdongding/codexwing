# KIS Research Goal Validation

- dummy_data_used: `false`
- goal: KIS 기반 피처와 모델을 실제 매수 기준 `touch5_dd10`으로 검증하고, 운영 대체는 성과와 표본 게이트를 동시에 통과할 때만 허용한다.
- trade standard: 진입가 `스캔 기준 +2%`, 5거래일 안에 `+5%` 터치, 5거래일 최저가 `-10%` 이탈 없음.

## 확인된 성과

KOSDAQ KIS sidecar tailgate shadow lane만 성과로 인정한다.

| 항목 | 값 |
|---|---:|
| source | `kis_shadow_admission_model_deployment_tailgate_20260612.json` |
| date scope | `2026-04-01..2026-06-10` |
| model | `lightgbm` |
| feature set | `kis_sidecar_failure_risk_augmented` |
| rule | `top2_p0.50_tail0.90` |
| n / active days / active runs | `40 / 11 / 20` |
| hit5_dd10_5d | `100.0%` |
| hit10_5d | `100.0%` |
| target_before_stop_5d | `92.5%` |
| close_win_5d | `95.0%` |
| avg_5d | `20.411507%` |
| avg_max_high_5d | `41.996894%` |
| min_5d | `-6.386166%` |
| min_min_low_5d | `-9.300619%` |
| expected +5 net | `4.601458%` |

## 승격 판단

- production: `false`
- shadow: `true`
- deep analysis: `true`
- production blockers: `n_lt_45`, `active_days_lt_20`
- model artifact: `models/scan_universe_challengers/kosdaq__touch5_dd10_5d__kis_sidecar_failure_risk_augmented__lightgbm__top2_p0p50_tail0p90.pkl`

## 연구 결론

이 성과는 실제 KIS sidecar cache에서 나온 것이므로 shadow 후보로는 의미가 있다. 하지만 운영 대체는 아직 안 된다. 이유는 수익 지표가 아니라 표본 게이트다. 현재 `n=40`, `active_days=11`이라 최소 운영 게이트 `n>=45`, `active_days>=20`을 못 넘었다.

KOSPI는 같은 tailgate 구조에서 `hit5_dd10=72.5806%`로 생산 기준 `73%`에 못 미쳐 성과로 승격하지 않는다.

## 인프라 검증

Supabase `scan_universe_snapshots` 최신 샘플 5,000행에서 `feature_snapshot.kis_sidecar`는 `0건`이었다. 즉 1월 시작 장기학습이 안 되는 핵심 원인은 모델 선택 이전에 Supabase 학습 테이블에 KIS sidecar가 아직 들어있지 않은 것이다.

다음 작업은 운영 DB에 `feature_snapshot.kis_sidecar`를 실제 KIS 데이터로 백필하고, 같은 tailgate 구조를 `2026-01-01..현재` 전 기간으로 다시 검증하는 것이다. 더미 데이터는 사용하지 않는다.
