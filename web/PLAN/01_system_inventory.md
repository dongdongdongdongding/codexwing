# 신웹 기획 — 01. 시스템 전수 인벤토리 (검증본)

> 목적: 새 웹(React+FastAPI)이 **빠뜨리는 핵심 로직이 없도록** 전 시스템을 검증·기록.
> 상태: 코드베이스 전수 grep 검증 완료 (2026-06-29). 사용자 확인 대기.
> ⚠️ 처음 매핑(10개)에서 **누락했던 것**을 ★로 표시 — 정직 기록.

---

## A. 데이터 소스 (수집/ingestion)
| 소스 | 무엇 | 코드 |
|---|---|---|
| **KIS OpenAPI** | 일봉·분봉·투자자수급·실시간시세(quote)·지수·업종 | `modules/kis_openapi.py`, `market_data.py`, `kis_operational_adapter.py` |
| **FinanceDataReader** | 지수(KS11/KQ11)·상장목록(종목명)·일봉보강 | `market_data.py`, `~/research_cache/build_px_long.py`, `names.parquet` |
| ★ **OpenDART** | 공시(dart_events)·실적서프라이즈(pead_surprise)·펀더멘털(fund) | `OPENDART_API_KEY`, `~/research_cache/dart_*.py`, `flow_bf.py` |
| ★ **뉴스** | 뉴스 수집·임베딩(LLM) | `news_analysis.py`, `news_embedding.py` |

## B. 데이터 저장소 (stores)
| 저장소 | 내용 |
|---|---|
| **Supabase** (Postgres) | `market_scan_results`, `scan_deep_reports`, `signals`, `agent_realized_outcomes`, `agent_run_summaries`, `agent_postmortems`, `agent_outcome_health`, `agent_profile_diagnostics`, `agent_improvement_tickets`, `market_features`, `runtime_artifacts`, `scan_universe_snapshots` |
| ★ **로컬 데이터레이크** `~/research_cache/` | 일봉 `px_long.parquet`(4.8M행/2649종목), 분봉 `intraday/`(2602종목), 수급 `flow.parquet`, 공시 `dart_*`, 실적 `pead_surprise`, 펀더 `fund`, 섹터 `sector_panel`, `names`, `ohlc_daily` |
| **runtime_state/** | 리포트·레인 원장(ledger.jsonl)·JSON 아티팩트·학습 데이터셋 |
| ★ **Beads/Dolt** | 이슈 트래커 DB (launchd keepalive) |

## C. 모델
| 레인 | 모델 | 프로듀서 |
|---|---|---|
| KOSPI 스윙 | `models/phase25_kospi_swing.pkl` | `report_swing_ensemble.py` |
| KOSDAQ 스윙 | `models/phase25_kosdaq_swing.pkl` | `report_swing_ensemble.py` |
| KOSPI 장중 | `models/phase25_kr_intraday*.pkl` | `report_kospi_intraday_swing.py` |
| KOSDAQ 장중 | `models/phase25_kosdaq_intraday.pkl` | `report_kosdaq_intraday_vwap_guard.py` |
| **B (시장중립)** | `b_engine/data/b_model.pkl` | `b_engine/model_engine.py` |
| 레인 정의/스캔 | `MODEL_VALIDATED_LANES` (`operational_candidate_scoring.py`) · `model_lane_scan.py` |
| ★ 재학습 | `retrain_ml.py`, `train_global_brain.py`, `train_ml_targets.py`, `train_model.py` |

## D. 핵심 로직
| 영역 | 코드 |
|---|---|
| **스캔 파이프라인** (codex 전체실행) | `multi_agent/workflows/non_ui_scan_pipeline.py`, `legacy_orchestration.py`, `scanner_bridge.py`, `scanner_runtime.py` |
| ★ **레짐 분류** | `regime_classifier.py`, `regime_conditional_scorer.py`, `kis_industry_regime.py` |
| **지수/시장** | `market_data.py` (KS11/KQ11, _kis_index_code) |
| **LLM (Gemini)** | `market_intelligence.py` (_run_gemini_http, gemini-2.5-flash/pro), `news_embedding.py`, `vision_analysis.py` |
| **점수/해석** | `operational_candidate_scoring.py`, `candidate_interpretation.py`, `ticker_names.py` |
| ★ **성과/검증 분석** | `update_realized_outcomes.py`, `build_paper_trade_ledger.py`, `report_outcome_health_db.py`, `segment_accuracy.py`, postmortem |
| **DB 입출력** | `db_manager.py`(write/fetch/query), `scan_persistence.py`, `top_deep_report.py` |
| **DB 갱신 배치** | `run_daily_ops.sh` + update_realized_outcomes·update_outcome_return_metrics·backfill_* |

## E. 소비 표면 (consumers) — 신웹이 대체/통합 대상
| 표면 | 코드 | 신웹에서 |
|---|---|---|
| **내부 웹** (느림) | `app.py` (164KB Streamlit) | **폐기 → React** |
| ★ **공개 웹** | `app_public.py` ("AI Quant Pro Public", Streamlit) | 통합 검토 |
| **Discord 봇** | `modules/discord_integration/` | 유지(웹과 동일 데이터) |
| ★ **자동 봇** | `auto_bot.py` (schedule → scanner_bridge) | 유지(백엔드) |
| **B 대시보드** | `b_engine/server.py`+html | **신웹에 흡수** |

## F. 스케줄러 (★ 전부 누락했던 부분)
| launchd | 역할 | 스크립트 |
|---|---|---|
| `com.codex.swing.dailyops` | 일일 배치(DB갱신·리포트) | `run_daily_ops.sh` |
| `com.codex.swing.discord-bot` | 디스코드 봇 상주 | `run_discord_bot.sh` |
| `com.codex.swing.bd-dolt.keepalive` | Beads DB 유지 | `keep_bd_dolt_alive.sh` |
| (스캔) | KR 일일 자동 스캔 | `run_kr_daily_auto_scans.sh` |

## G. 비밀키/연결
KIS(app_key/secret/account) · Supabase(url/key/service_role) · **Gemini**(GEMINI_API_KEY) · **Discord**(bot_token/webhook/channels/roles) · **OpenDART**(OPENDART_API_KEY)

---

## 데이터 흐름 (요약)
```
[KIS·FDR·DART·뉴스] → 수집 → [~/research_cache 데이터레이크 + Supabase]
   → [모델 A(스윙/장중) + B(시장중립)] 스캔 → 픽 → [Supabase scan_deep_reports + 레인 ledger]
   → [성과추적: realized_outcomes·paper_ledger·outcome_health] → 재학습
   → 소비: [웹 / Discord / 자동봇]    배치: [launchd dailyops/scan/bot]
   LLM(Gemini): 시장요약·뉴스·비전     레짐: 지수→레짐분류→조건부 스코어
```

## 신웹이 절대 빠뜨리면 안 되는 것 (체크리스트)
- [ ] Supabase 10+ 테이블 read (scan_deep_reports/market_scan_results/signals/agent_*)
- [ ] 일봉(px_long)·분봉(intraday) 저장소 조회
- [ ] A 4레인(코스피·코스닥 × 스윙·장중) 픽 + 종목명 + 실시간시세
- [ ] B 시장중립 픽 (흡수)
- [ ] 지수/레짐 상태
- [ ] Gemini 시장요약/뉴스
- [ ] 공시(DART)·실적(PEAD)·수급(flow) — 픽 근거
- [ ] 성과/실현승률(realized_outcomes, paper_ledger) — 알파 기준
- [ ] 스캔 트리거(수동/자동) + 진행상태
- [ ] Discord와 동일 데이터 정합성
- [ ] 스케줄러 상태(dailyops 마지막 실행) 가시화
