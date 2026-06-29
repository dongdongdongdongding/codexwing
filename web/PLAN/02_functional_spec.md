# 신웹 기획 — 02. 기능정의서 (페르소나·사용성·기능·데이터계약)

> 스택: **React(프론트) + FastAPI(백엔드)**. Streamlit(app.py) 폐기 대상.
> 원칙: 클로드/제네릭 템플릿 금지. **운영자용 트레이딩 터미널**의 밀도 + 서비스급 명료함 + **정직(알파/신선도/검증상태 항상 표면)**.
> 검증대상 인벤토리: [01_system_inventory.md](01_system_inventory.md).

---

## 1. 페르소나
### P1 — 운영자(나) · 주 사용자
- 목표: 매일 **신뢰할 픽**을 빠르게 확인 → 매매 결정. 모델·데이터·성과를 **검증·디버그**.
- 니즈: 기술적 깊이(근거·레짐·수급·알파), 데이터 신선도/누락 즉시 인지, 스캔/재학습 제어, "이거 진짜냐?"에 답하는 정직한 지표.
- 고통(현재 app.py): 느림(상호작용마다 재실행), 종목명 없음, 성과를 절대수익으로만 봐서 오해, 운영상태 안 보임.

### P2 — 소수 신뢰 팔로워 · 부 사용자
- 목표: 운영자가 띄운 **오늘의 픽**을 보고 따라 매매.
- 니즈: 종목명·진입가·목표·보유기간·**신뢰도(승률/알파/검증상태)**가 명확. 과한 기술용어·온보딩 불필요. 모바일에서도 픽 확인.
- 권한: 픽/성과 읽기. 운영(스캔·재학습)·디버그는 운영자 전용.

> 함의: **온보딩/요금/마케팅 불필요**(공개SaaS 아님). 대신 **밀도 높은 정보 + 명확한 신뢰지표 + 빠른 속도**. 권한 2단계(운영자/뷰어).

---

## 2. 사용성 원칙 (UX principles)
1. **3초 규칙** — 들어오면 3초 안에 "오늘 뭘 살까 + 믿을만한가"가 보인다.
2. **정직 우선** — 절대수익 옆에 항상 **알파(시장대비)**. forward-shadow/미성숙/낙관치는 **배지로 경고**. 데이터 신선도 항상 표시.
3. **밀도 ≠ 혼잡** — 운영자용 고밀도지만 시각 위계로 정리(핵심 픽 크게, 근거 접힘).
4. **즉답성** — 모든 화면 < 1초(서버 JSON + 클라 렌더, 재계산 없음). 실시간 시세는 폴링.
5. **단일 진실원** — 웹·Discord·저장픽이 **100% 동일 티커**(이미 정합성 코드 있음). 불일치=버그.
6. **점진적 노출** — 픽 카드(요약) → 클릭 → 근거/차트/계약(상세 드로어).

---

## 3. 정보구조 (IA)
```
┌ 상단바: 지수(KOSPI/KOSDAQ %)·레짐·데이터신선도·마지막스캔·권한
├ ① 개요 Overview        — 오늘 핵심픽(A+B 통합 랭킹) + 시장요약 + 헬스
├ ② 픽 Picks             — 5레인(코스피·코스닥×스윙·장중 + B) 탭/필터, 상세 드로어
├ ③ 성과 Performance      — 실현승률·알파·에쿼티·페이퍼원장·B forward-shadow
├ ④ 시장·근거 Market      — 지수/레짐, Gemini 요약, 공시(DART)·실적(PEAD)·수급(flow)·뉴스
└ ⑤ 운영 Ops [운영자전용]  — 스캔 트리거·진행, 스케줄러/신선도, 모델메타, Discord정합
```

---

## 4. 기능 요구사항 (FR) — 영역별

### ④영역A — ① 개요
- FR-O1 상단바: KOSPI/KOSDAQ 지수·등락%, 레짐(상승/중립/하락), **데이터 신선도**(일봉/분봉/수급 각 최신일), 마지막 스캔시각.
- FR-O2 오늘의 핵심픽: A 4레인 + B를 **통합 랭킹** 상위 N. 카드=종목명·실시간가·등락·레인배지·확률/점수·간단근거.
- FR-O3 시장 한줄요약(Gemini) + 오늘 주의(급락/이벤트).
- FR-O4 헬스 스트립: B forward-shadow 라이브알파·A 라이브알파·데이터 경고.

### ④영역B — ② 픽
- FR-P1 레인 필터: 코스피스윙/코스피장중/코스닥스윙/코스닥장중/B. (LANE_PROFILE 기준)
- FR-P2 픽 행: 순위·종목명(코드)·실시간가·등락%·진입가·목표(+5%)·손절/보유·확률(p)·점수·근거요약·신뢰배지.
- FR-P3 상세 드로어: 분봉/일봉 미니차트, 근거 풀(수급 외인/기관, 공시/실적, 레짐, 뉴스), 매매계획(진입/목표/보유), 과거 동일패턴 성과.
- FR-P4 정합성: 저장된 daily_ops 픽과 100% 동일(재계산 아님). run_id 표시.
- FR-P5 정직배지: SWING/INTRADAY/B, "보유미완료", "낙관치", "forward-shadow 관측중".

### ④영역C — ③ 성과/검증
- FR-PF1 레인별·전체: **실현 승률 + 절대수익 + 알파(시장대비)**. 알파 기본 강조, 절대는 보조.
- FR-PF2 에쿼티 곡선(누적), 기간 필터, 픽 성숙도(<3일 회색).
- FR-PF3 페이퍼 원장(build_paper_trade_ledger) — 가정 매매 손익.
- FR-PF4 B forward-shadow 스코어보드(누적 채점·알파·승률).
- FR-PF5 정직 경고: "표본 N 작음", "낙관치(비용·슬리피지 미반영)", "OOS 짧음".
- 데이터: Supabase agent_realized_outcomes·market_scan_results + 레인 ledger + b_shadow.

### ④영역D — ④ 시장·근거
- FR-M1 지수/레짐 패널(KS11/KQ11, 레짐분류 상태).
- FR-M2 Gemini 시장요약·뉴스(market_intelligence/news).
- FR-M3 근거 피드: DART 공시·PEAD 실적·flow 수급 — 종목 연결.

### ④영역E — ⑤ 운영 [운영자전용]
- FR-OP1 수동 스캔 트리거(레인/시장 선택) + 진행상태(heartbeat).
- FR-OP2 스케줄러 상태: dailyops 마지막 실행·결과, 자동스캔, discord-bot 상태.
- FR-OP3 데이터 신선도 상세: 각 저장소 최신일·갱신 트리거 버튼.
- FR-OP4 모델 메타: 레인별 trained_through·버전, 재학습 트리거.
- FR-OP5 Discord 정합: 웹 픽 = Discord 픽 동일성 점검.

---

## 5. 비기능 요구사항 (NFR)
| 항목 | 기준 |
|---|---|
| 성능 | 화면 전환·조회 < 1s (서버 캐시 JSON). 실시간 시세 폴링 15s, 타임아웃 가드(행 방지). |
| 정확도 | 웹 픽 = 저장 daily_ops 픽 = Discord 픽 100% 동일(run_id 검증). |
| 정직 | 알파 우선·절대수익 보조, 신선도/미성숙/낙관/표본 경고 상시. 추정·낙관 수치 라벨. |
| 보안 | 운영자/뷰어 2단계. 비밀키(KIS/Gemini/Supabase/Discord/DART)는 백엔드만, 프론트 노출 0. |
| 안정성 | 외부 API(KIS/Gemini) 실패시 폴백(종가·캐시), 화면 안 멈춤. |
| 반응형 | 운영자=데스크톱 고밀도, 뷰어=모바일 픽 확인 가능. |

---

## 6. 데이터 계약 (FastAPI 엔드포인트 ↔ 백엔드 모듈)
| 엔드포인트 | 반환 | 소스 모듈 |
|---|---|---|
| `GET /api/overview` | 지수·레짐·신선도·핵심픽·시장요약·헬스 | market_data·regime·model_lane_scan·b_engine·market_intelligence |
| `GET /api/picks?lane=` | 레인별 픽(종목명·근거·계약) | model_lane_scan·candidate_interpretation·b_engine·ticker_names |
| `GET /api/picks/{ticker}` | 상세(차트·근거풀·계획) | db_manager·flow·dart·pead·분봉캐시 |
| `GET /api/prices?codes=` | 실시간 시세 | kis_openapi.quote_snapshot |
| `GET /api/performance?lane=` | 실현승률·알파·에쿼티·원장 | db_manager·measure_model_lane_picks·paper_ledger·b_shadow |
| `GET /api/market` | 지수·레짐·Gemini·뉴스·근거피드 | market_data·market_intelligence·dart·flow |
| `GET /api/ops/status` | 스케줄러·신선도·모델메타·Discord정합 | launchd/로그·parquet mtime·model_meta·discord |
| `POST /api/ops/scan` | 스캔 트리거(운영자) | model_lane_scan·scanner_bridge |
| `POST /api/ops/rescan-b` | B 재스캔(운영자) | b_engine |
| `GET /api/health/freshness` | 일봉/분봉/수급/공시 최신일 | parquet·db |

---

## 7. 정직 지표 사전 (배지/라벨 표준)
- 🟢 SWING / 🔵 INTRADAY / 🟣 B(시장중립)
- ⏳ **보유미완료** (<목표보유일) · 📉 **알파 -** · 📈 **알파 +**
- ⚠️ **낙관치** (비용 0.3%·슬리피지/decay 미반영) · 🔬 **forward-shadow 관측중**
- 🕒 **데이터 N일 지연** · ✅ **Discord 정합**
- 절대수익 옆 항상 **(시장대비 αX.X%)** 병기.

---

## 다음 단계
03 화면설계서(IA·와이어프레임·상태) → 04 디자인시스템 → **검증(사용자)** → 수정 → 개발(FastAPI+React) → 검증.
