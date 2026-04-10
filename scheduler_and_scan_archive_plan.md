# Scheduler + Scan Archive 설계안  
## 매크로/뉴스 체크 스케줄러부터 스캔 저장소 페이지까지

## 문서 목적

이 문서는 현재 스캐너 시스템을 다음 단계로 고도화하기 위해 필요한 두 축을 정리한다.

1. **매시간 시장 상태를 점검하는 Scheduler**
2. **스캔 결과를 다시 보고 비교/복기할 수 있는 Scan Archive 저장소 페이지**

핵심 목표는 다음과 같다.

- 전날/주말 스캔 결과를 장 시작 전에 다시 재평가할 수 있게 만들기
- VIX, 금리, 환율, 핵심 뉴스, 지수 변동 등 실시간 시장 컨텍스트를 스캐너 결과에 반영하기
- 과거 스캔 결과를 누적 저장하여 비교/복기/정확도 개선에 활용하기
- 단순 “실시간 화면”이 아니라, **저장 → 재평가 → 비교 → 복기** 가능한 운영 체계를 만드는 것

---

# 1. 왜 Scheduler가 필요한가

현재 문제는 다음과 같다.

- 종목 차트와 확률 모델은 스캔 시점 기준으로는 좋아 보인다.
- 하지만 실제 진입 시점에는
  - VIX 급등
  - 국채 금리 급등
  - 환율 급등
  - 지수 갭다운
  - 핵심 뉴스 악화
가 발생할 수 있다.
- 이 경우 종목 자체 품질과 무관하게 시장 매크로가 종목을 찍어누를 수 있다.

즉:

> **스캔 시점의 좋은 종목 = 실제 매수 시점의 좋은 종목** 이 아니다.

따라서, 스캔 결과를 그대로 쓰는 것이 아니라 **시간에 따라 다시 재평가하는 계층**이 필요하다.

---

# 2. 왜 매시간 전종목 재스캔이 아니라 “오버레이 스케줄러”가 맞는가

매시간 500~3000종목을 다시 전부 스캔하는 방식은 비효율적이다.

### 문제점
- 느림
- yfinance / 외부 API 부담 증가
- rate limit 위험
- 종목 자체 지표는 크게 안 바뀌는데, 매번 같은 계산 반복
- 운영 복잡도 증가

반면 **매시간 시장 상태만 재평가하고 기존 결과를 재랭크**하면:

### 장점
- 훨씬 가볍다
- 실시간성은 확보된다
- 시장 리스크 급변을 반영할 수 있다
- 전날 스캔 결과를 장전/장중에 다시 사용할 수 있다

즉 가장 좋은 구조는:

- **정적 스캔 결과 = Watchlist**
- **매시간 오버레이 재평가 결과 = Action List**

이다.

---

# 3. Scheduler의 핵심 역할

Scheduler는 종목 차트를 다시 계산하는 엔진이 아니라,  
**시장 컨텍스트를 주기적으로 갱신하는 엔진**이어야 한다.

## 3-1. 매시간 체크할 항목
### 시장/거시 지표
- VIX
- VIX 1일 변화율
- VIX 5일 변화율
- 10년물 금리 (^TNX)
- 10년물 금리 1일 변화율
- KRW=X (달러-원 환율, 한국 시장 한정)
- 환율 1일 변화율
- SPY / QQQ / KOSPI / KOSDAQ 지수 변화
- 지수 갭
- 시장 breadth (상승 종목 수 / 하락 종목 수) 가능하면 추가

### 뉴스/시황
- 핵심 매크로 헤드라인
- FOMC / 금리 / CPI / PPI / 고용 / 지정학 뉴스
- 시장 전체 심리 변화
- 섹터 수혜 / 피해 키워드

## 3-2. Scheduler 출력값
Scheduler는 여러 원천 데이터를 읽은 뒤, 최종적으로 아래 형태를 만들어야 한다.

```python
{
  "timestamp": "...",
  "macro_state": "NORMAL" | "CAUTION" | "RISK_OFF" | "CRASH",
  "macro_risk_score": 0~100,
  "vix": ...,
  "vix_change_1d": ...,
  "tnx": ...,
  "tnx_change_1d": ...,
  "krw": ...,
  "krw_change_1d": ...,
  "market_index_change": ...,
  "news_sentiment": ...,
  "headline_summary": "...",
  "flags": [
    "VIX_SPIKE",
    "YIELD_SURGE",
    "KRW_WEAKNESS",
    "GAP_DOWN"
  ]
}
```

즉 개별 수치와 함께,  
**현재 시장이 어떤 상태인지 판단한 결과물**을 만들어야 한다.

---

# 4. Scheduler와 스캔 결과를 어떻게 연결할 것인가

Scheduler는 단순 알림 시스템이 아니라,  
**기존 스캔 결과의 점수와 우선순위를 실시간 재평가하는 오버레이**로 연결되어야 한다.

## 4-1. 연결 원칙
매시간 새로 계산한 매크로 상태를 기존 스캔 결과에 적용하여:

- `Decision Score` 재보정
- `Clean Hit P` 재보정
- 신규 진입 허용 여부 재판단
- Top 5 재정렬
- Watchlist → Action List 갱신

을 수행한다.

---

## 4-2. 권장 Macro Overlay 적용 방식
매크로는 종목을 완전 제외시키는 하드컷보다는,  
**점수/확률을 감산하고 threshold를 올리는 방식**이 더 바람직하다.

### 예시
```python
macro_multiplier = 1.0
macro_penalty = 0

if macro_risk_score >= 80:
    macro_multiplier = 0.65
    macro_penalty = 12
elif macro_risk_score >= 60:
    macro_multiplier = 0.78
    macro_penalty = 8
elif macro_risk_score >= 40:
    macro_multiplier = 0.90
    macro_penalty = 4

adj_clean_hit = clean_hit_p * macro_multiplier
adj_decision = base_decision * macro_multiplier - macro_penalty
```

### 해석
- NORMAL: 거의 영향 없음
- CAUTION: 가벼운 감점
- RISK_OFF: 확률/점수 모두 유의미하게 감산
- CRASH: 신규 진입 거의 중단 수준

---

## 4-3. 가장 중요한 운영 구분
### Watchlist
- 하루 1~2회 전종목 스캔 결과
- 종목 자체 품질 중심
- 시장이 바뀌더라도 원본 후보군으로 유지

### Action List
- Scheduler가 매시간 재평가한 현재 실행 후보
- 매크로 상태 반영
- 진입 우선순위 반영
- 실제 매매 참고용 리스트

즉:

> **Watchlist는 “좋은 종목 후보 모음”,**
> **Action List는 “지금 당장 행동 가능한 종목 리스트”** 다.

---

# 5. Scheduler 동작 주기 제안

## 5-1. 권장 스케줄
### 하루 기준
- **장 시작 전 1회**
  - 핵심 시황/뉴스/지수 체크
  - 전날 Watchlist를 Action List로 변환

- **장중 매시간 1회**
  - VIX / TNX / KRW / 지수 / 뉴스 요약 갱신
  - 점수 재보정
  - Top 5 재정렬

- **장 마감 후 1회**
  - 당일 매크로 상태 최종 저장
  - 스캔 결과/Action List 성과 복기 기록 준비

## 5-2. 캐시 전략
거시 데이터는 종목별로 매번 호출하면 비효율적이므로  
**한 번 fetch 후 짧은 TTL 캐시**가 좋다.

추천:
- VIX / TNX / KRW / 지수: 5분~15분 캐시
- 뉴스 요약: 30분~60분 캐시

---

# 6. Scan Archive 저장소 페이지가 왜 필요한가

Scheduler와 Action List가 제대로 작동하려면  
과거 스캔 결과를 다시 보고 비교할 수 있어야 한다.

현재 저장소 페이지가 필요한 이유는 다음과 같다.

### 이유 1
전날/주말 스캔 결과를 장전/장중에 다시 불러와야 한다.

### 이유 2
매시간 매크로 오버레이가 붙으면서  
어떤 종목이 상위권에서 밀렸는지 비교해야 한다.

### 이유 3
실패한 종목을 복기해야 예측 정확도가 올라간다.

### 이유 4
향후 모델 버전 비교(Phase 18.2, 18.3 등)를 하려면  
과거 스캔 스냅샷이 반드시 남아 있어야 한다.

즉 저장소 페이지는 단순 보관함이 아니라:

> **저장 → 비교 → 복기 → 개선** 을 위한 운영 페이지

여야 한다.

---

# 7. Scan Archive 페이지 핵심 구조

권장 명칭:
- `📚 Scan Archive`
- 또는 `🗂 Scan Repository`

## 7-1. 상단: Scan Runs 목록
스캔 “회차” 단위 목록이 보여야 한다.

예:
- 실행 시각
- 시장 (KOSPI / KOSDAQ / NASDAQ / AMEX)
- 엔진 모드
- 결과 개수
- 매크로 상태
- VIX / TNX / KRW
- Top 5 평균 점수
- Clean Hit 평균
- notes

즉 사용자는 먼저 “어느 회차를 볼지”를 선택해야 한다.

---

## 7-2. 중간: 선택 회차의 Scan Results
선택한 회차에 포함된 종목 결과를 표로 보여준다.

### 필수 컬럼
- ticker / name
- tier
- antigravity_score
- decision_score
- base_decision
- rank_adjust
- macro_penalty
- prob_3
- prob_5
- prob_10
- clean_hit_p
- trend
- position
- whale_score
- volume_ratio
- volume_confirmed
- strategy_tag
- regime
- macro_state

핵심은 최종 점수만 저장하지 말고,  
**점수의 재료(raw components)** 도 함께 저장하는 것이다.

---

## 7-3. 하단: 종목 상세 복기
선택한 종목 하나를 열면 아래가 보여야 한다.

### 복기 항목
- 당시 점수 구성
- 당시 매크로 상태
- 이후 D+1 / D+3 / D+5 수익률
- MFE
- MAE
- target hit 여부
- clean hit 여부
- stop first 여부
- 이후 같은 종목이 다른 스캔에도 등장했는지

이 영역이 있어야  
나중에 “왜 이 종목은 실패했는가”를 볼 수 있다.

---

# 8. DB 설계 제안

## 8-1. `scan_runs`
스캔 1회 실행 단위의 메타데이터 저장

### 예시 컬럼
- `scan_id`
- `created_at`
- `market`
- `engine_mode`
- `scan_type` (`daily_scan`, `pre_open_rescan`, `hourly_overlay`, etc.)
- `macro_state`
- `macro_risk_score`
- `vix`
- `vix_change_1d`
- `tnx`
- `tnx_change_1d`
- `krw`
- `krw_change_1d`
- `headline_summary`
- `result_count`
- `top5_count`
- `notes`

---

## 8-2. `scan_results`
각 종목별 결과 저장

### 예시 컬럼
- `scan_id`
- `ticker`
- `name`
- `market`
- `tier`
- `antigravity_score`
- `decision_score`
- `base_decision`
- `rank_adjust`
- `macro_penalty`
- `prob_3`
- `prob_5`
- `prob_10`
- `clean_hit_p`
- `trend`
- `position`
- `whale_score`
- `volume_ratio`
- `volume_confirmed`
- `strategy_tag`
- `regime`
- `macro_state`
- `macro_risk_score`
- `watchlist_rank`
- `action_rank`

---

## 8-3. `scan_outcomes` (추천)
이후 실제 성과 복기용

### 예시 컬럼
- `scan_id`
- `ticker`
- `d1_return`
- `d3_return`
- `d5_return`
- `mfe`
- `mae`
- `target_hit_3`
- `target_hit_5`
- `target_hit_10`
- `clean_hit_5`
- `stop_first`
- `exit_reason`

이 테이블이 있어야  
모델/랭킹 수정 전후를 진짜 비교할 수 있다.

---

# 9. UI 기능 제안

## 9-1. 필터 기능
저장소 페이지에는 최소한 아래 필터가 있어야 한다.

- 날짜 범위
- 시장
- 엔진 모드
- 매크로 상태
- Tier
- Trend
- Volume Confirmed 여부
- Clean Hit P 범위
- Action List 여부

---

## 9-2. 비교 기능
같은 종목/같은 회차가 Scheduler 반영 전후 어떻게 바뀌었는지 보여야 한다.

예:
- Watchlist Rank → Action Rank 변화
- Decision Score 변화
- Clean Hit P 변화
- Macro Penalty 적용 여부

즉 “scan vs rescan diff” 가 핵심이다.

---

## 9-3. 종목 히스토리
특정 종목을 선택하면:

- 최근 10회 스캔 등장 여부
- Top 5 진입 횟수
- 평균 Decision Score
- 평균 Clean Hit P
- 실제 후속 성과

를 보여주는 것이 좋다.

---

# 10. 운영 흐름 제안 (End-to-End)

## 단계 1. 전종목 스캔
- 하루 1~2회
- 종목 자체 품질 평가
- Watchlist 생성
- `scan_runs` + `scan_results` 저장

## 단계 2. Scheduler 실행
- 매시간 매크로/뉴스/지수 체크
- `macro_state`, `macro_risk_score` 생성
- 기존 Watchlist 재평가
- Action List 생성
- 같은 `scan_id`에 Action Rank 업데이트 또는 별도 `scan_run` 생성

## 단계 3. UI 반영
- 상단에 Macro Weather 표시
- Action List 노출
- Scan Archive에서 모든 회차 복기 가능

## 단계 4. 사후 성과 기록
- D+1 / D+3 / D+5 성과 저장
- clean hit / stop first 판정
- 모델/랭킹 전후 비교 데이터 확보

---

# 11. 구현 우선순위

## 1순위 (즉시 필요)
1. Macro Scheduler 구축
2. Macro Weather 대시보드 추가
3. Watchlist / Action List 개념 분리
4. `scan_runs`, `scan_results` 저장 구조 추가

## 2순위
5. Scan Archive 탭 추가
6. 회차별 결과 조회
7. scan vs rescan diff 비교 기능
8. 종목별 히스토리 조회

## 3순위
9. `scan_outcomes` 사후 성과 저장
10. MFE / MAE / clean hit / stop first 복기
11. 모델 버전별 성능 비교 리포트

---

# 12. 최종 결론

현재 스캐너를 한 단계 더 실전적으로 만들려면,  
단순히 종목을 잘 찾는 것만으로는 부족하다.

반드시 아래 두 축이 필요하다.

### A. Scheduler
- 시장 상태를 매시간 갱신
- Watchlist를 Action List로 재평가
- 매크로 급변 리스크 반영

### B. Scan Archive
- 과거 스캔 결과 저장
- 회차별 비교
- 종목별 복기
- 모델/랭킹 개선의 근거 데이터 확보

가장 중요한 원칙은 다음과 같다.

> **전종목 스캔은 후보를 만드는 과정이고,**
> **Scheduler는 그 후보를 지금 시장에 맞게 다시 평가하는 과정이며,**
> **Scan Archive는 그 모든 과정을 저장하고 학습하는 운영 두뇌다.**

한 줄 요약:

> **하루 1~2회 스캔으로 Watchlist를 만들고, 매시간 Scheduler가 시장 컨텍스트를 반영해 Action List를 갱신하며, 모든 결과는 Scan Archive에 저장해 복기와 개선에 사용해야 한다.**
