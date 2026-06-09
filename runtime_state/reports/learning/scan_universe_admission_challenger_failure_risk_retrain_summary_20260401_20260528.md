# Failure-Risk Retrain Summary

## 결론
- 손실 티커/테마/섹터 이력을 날짜 기준 과거값으로만 계산한 실패위험 피처를 재학습에 반영했다.
- 신규 실패위험 재학습은 258개 조합을 검증했고, 기준선 포함 비교 조합은 290개다.
- 기준선 대비 최선의 KIS shadow 후보는 `failure_risk_numeric_hist_gb`이며, 5일 평균 수익률은 -3.47%에서 +8.39%, 5일 종가 방어율은 42.86%에서 92.59%, bad path는 71.43%에서 22.22%로 개선됐다.
- 그러나 운영 승격은 하지 않는다. 남은 차단 사유는 표본/활성일 부족과 `bad_path > 15%`, `stop5 > 10%`, `stop_before_target_5d` 초과다.
- Top5 후보는 평균 수익률은 높지만 bad path 46.15%, stop5 40.38%라 운영 후보 확장에는 위험 표시가 필요하다.

## 비교
| run | market | label | features | model | rule | n | days | hit5 | hit10 | close5 | avg5 | min_low | bad | stop | gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_kis_sidecar_smoke | KOSDAQ | touch5_guard_5d | kis_sidecar_augmented | hist_gb | top1 | 7 | 4 | 71.4286 | 71.4286 | 42.8571 | -3.470193 | -21.132898 | 71.4286 | 42.8571 | blocked |
| failure_risk_numeric_hist_gb | KOSPI | target_first_sustain_5d | kis_failure_risk_numeric | hist_gb | top1_p0.60 | 27 | 9 | 92.5926 | 77.7778 | 92.5926 | 8.39219 | -11.340683 | 22.2222 | 22.2222 | shadow_risk_review |
| failure_risk_focused_tree | KOSPI | target_first_sustain_5d | kis_sidecar_failure_risk_numeric | random_forest | top1_p0.60 | 28 | 10 | 100.0 | 89.2857 | 82.1429 | 6.128226 | -6.948244 | 32.1429 | 17.8571 | shadow_risk_review |
| failure_risk_top5_hist_gb | KOSDAQ | touch10_guard_5d | kis_sidecar_failure_risk_numeric | hist_gb | top5_p0.60 | 52 | 6 | 98.0769 | 96.1538 | 76.9231 | 22.491768 | -16.144519 | 46.1538 | 40.3846 | shadow_risk_review |

## 반영한 나쁜 특성
- 전체 touch5 후보 중 5일 종가 손실은 53.52%, bad path는 80.83%였다.
- KOSDAQ touch5는 종가 손실 58.18%, bad path 84.01%로 KOSPI보다 위험했다.
- 주요 위험 단서는 반복 스캔 과다, 낮은 우선순위, 낮은 EPS/저가/약한 이동평균, 정책 리스크 태그, 산업재/기계, 2차전지, 로봇/자동화 계열이었다.
- 이 단서들은 티커, 테마, KIS 테마, KIS 섹터, 시장 단위의 과거 실패율/방어율/스탑률/평균 수익률 피처로 모델에 들어갔다.

## 운영 판단
- 지금 저장 가능한 최선은 운영 교체 모델이 아니라 shadow 표시 후보 모델이다.
- 운영 교체를 위해서는 입장 모델보다 동적 TP/SL과 조기 이탈 정책이 먼저 필요하다.
- 빠른 운영 프리셋은 카테고리 폭발을 피하기 위해 숫자형 실패위험 피처만 사용하도록 제한했다.
