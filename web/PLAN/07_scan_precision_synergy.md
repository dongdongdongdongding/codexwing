# 신웹 기획 — 07. 스캔×정밀분석 시너지 검토 + 분석로직 (빌드 전 정렬)

> 사용자 요구: 정밀분석 = 픽의 모든 티커 분석 + 누적. 스캔이 게시물(기본단위, 자동+수동+디스코드),
> 게시물 클릭→티커카드, 티커카드 클릭→정밀분석 패널. 시너지 검토 후 로직 잠그고 빌드.

---

## 1. 시너지 검토 결론 — ✅ 가능 (구조가 이미 맞음)
- **scan_deep_reports = 이미 모든 스캔을 run_id별로 누적**. 자동(daily ops)·수동(web Ops)·디스코드(/kospi_scan 등) **전부 `run_model_lane_scan(route=True)` → 같은 테이블**로 라우팅.
- **run_id = 스캔 게시물 ID** (관측: `SWING-ENS-20260629`, `KOSPI-ITD-…`, `RUN-…`). 하루 다중 스캔 누적.
- 각 행(픽)에 **스캔시점 데이터** 보유: `candidate_interpretation`(진입·피처), `prediction`(확률·점수), stock_name, ticker → **티커카드 + 정밀분석 입력 준비됨**.
- 즉 "게시물→티커카드→정밀분석"은 **새 저장소 불필요**, 기존 누적 위에 뷰+분석을 얹으면 됨.

### 메워야 할 갭 (3)
1. **소스 태깅 없음**: auto/manual/discord 구분 필드 비어있음(`scan_source_snapshot` 모델레인은 빈값). → 스캔 생성 시 source 태그 추가 필요.
2. **B·NASDAQ 위치**: NASDAQ는 scan_deep_reports에 있음. **B는 별도**(b_shadow/b_picks) → 게시물로 통합 필요.
3. **정밀분석 결과 캐시/누적 슬롯**: (scan_id,ticker)별 분석 저장 위치 정해야(과거 스캔 재열람).

---

## 2. 데이터 모델 (게시물 단위)
```
ScanPost(게시물)      = run_id 그룹
  { scan_id, time, source(auto|manual|discord), markets[], lanes[], pick_count }
  └ TickerCard(티커카드) = pick row
       { ticker, name, market, lane, prob, score, entry(스캔시점), badges }
       └ PrecisionAnalysis(정밀분석 패널) = (scan_id,ticker) 캐시·누적
            { 모델판정, 차트, 수급, 이벤트, 레짐, 지표, Gemini종합 }
```

## 3. 정밀분석 로직 (잠금 — as-of 명확히)
티커당 7블록 (현 /api/analyze 확장):
| 블록 | 내용 | as-of |
|---|---|---|
| ① 모델판정 | 이 스캔에서의 레인·확률·점수 | **스캔시점**(prediction) |
| ② 차트 | 일/분봉 + 진입가 선 | 라이브(진입선=스캔시점) |
| ③ 수급 | 외국인/기관 5·20일 | 스캔일 기준(가능시 스냅샷) |
| ④ 이벤트 | DART공시·PEAD실적 | 스캔일 이전 |
| ⑤ 레짐 | 시장국면 | 스캔시점 |
| ⑥ 지표 | RSI·볼린저·고가이격·ATR | **스캔시점**(candidate_interpretation) |
| ⑦ Gemini 종합 | ①~⑥ 종합 정직판정 | 최초 조회시 1회 생성 → **영구 캐시** |

- **모든 픽 분석**: 게시물의 전 티커에 카드+분석 제공.
- **누적**: (scan_id,ticker) 키로 분석 저장 → 과거 게시물 재열람시 그대로. Gemini는 비용 때문에 **lazy-once**(첫 클릭시 생성, 이후 캐시).
- **정직**: 모델 미픽 종목은 분석 안 함(게시물=픽만). 스캔시점 vs 현재 가격 괴리(갭) 표시.

## 4. 빌드 계획
- **백엔드**: `/api/scans`(게시물 목록·누적·페이지·source필터) · `/api/scans/{run_id}`(티커카드) · `/api/scans/{run_id}/analyze/{ticker}`(정밀분석, 캐시).
- **소스 태깅**: `run_model_lane_scan`·B scan·discord scan_executor·web jobs에 `source` 인자 → 저장. (run_id 접두사로도 일부 추론 가능)
- **B/NASDAQ 게시물화**: B scan 결과를 게시물 1건으로, NASDAQ run_id 포함.
- **프론트 재편**: ③정밀분석 탭 → **"스캔 피드"**(게시물 카드 목록) → 클릭 → 티커카드 그리드 → 클릭 → 정밀분석 패널. ④성과의 아카이브와 연결(아카이브=결과중심, 스캔피드=분석중심).

---

## 5. 결정 필요 (4)
1. **Gemini 생성 시점**: (a) 스캔 직후 전 픽 사전생성(즉시 누적, 비용↑·스캔느려짐) vs **(b) 클릭시 1회+영구캐시**(비용↓·첫조회 12s). → 권장 (b).
2. **분석 캐시 저장소**: (a) 로컬 JSON(`runtime_state/precision_cache/`) vs (b) scan_deep_reports의 `deep_analysis_source_snapshot` 컬럼 재사용 vs (c) Supabase 신규. → 권장 (a) 로컬(빠름·단순).
3. **IA 재편 범위**: (a) ③정밀분석을 "스캔 피드"로 전환(②픽=오늘 최신만 유지) vs (b) ②픽도 스캔피드로 흡수(픽=최신 게시물). → 권장 (a).
4. **과거 스캔 차트/수급 as-of**: (a) 스캔시점 정확 재현(복잡) vs **(b) 피처는 스냅샷·차트는 라이브+진입선**(단순·실용). → 권장 (b).

→ 4개 정해주시면 백엔드(scans API+소스태깅)부터 빌드.
