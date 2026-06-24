# 현재 운영 매뉴얼 - 2026-06-24

이 문서는 현재 코드가 실제로 무엇을 실행하는지, 어떤 모델 레인이 live/관찰/비활성인지, 운영자가 어떤 명령과 화면을 써야 하는지 정리한 운영 기준 문서다.

## 확인한 근거 파일

- 프로젝트 규칙: `AGENTS.md`
- Beads 상태: `bd list --json`, `bd comments swing-main-0to`, `scripts/issue log`
- 일일 실행: `multi_agent/tools/run_daily_ops.sh`
- 자동 스캔: `multi_agent/tools/run_kr_daily_auto_scans.py`
- KIS 운영 스캔: `multi_agent/tools/run_kis_operational_kr_scan.py`
- 비UI 파이프라인: `multi_agent/workflows/non_ui_scan_pipeline.py`
- 스캐너 엔진: `modules/scanner_runtime.py`, `modules/scanner_services.py`
- live producer: `report_swing_ensemble.py`, `report_kospi_intraday_swing.py`, `report_kosdaq_intraday_vwap_guard.py`
- shadow producer: `report_kospi_normal_pead_shadow.py`, `report_firsttouch_down_shadow.py`
- 인트라데이 모델: `modules/kosdaq_intraday_vwap_guard.py`, `modules/intraday_candidate_registry.py`
- UI/Discord: `app.py`, `ui/*`, `modules/discord_integration/*`
- 저장/ledger: `modules/db_schema.py`, `modules/db_manager.py`, `modules/scan_persistence.py`, `modules/runtime_artifact_store.py`, `modules/post_scan_outcome_ledger.py`
- 최신 리서치 증거: `runtime_state/reports/learning/intraday_claude_codex_synthesis_latest.md`, `intraday_3d_t5_*` 리포트, `docs/research/RESEARCH_JOURNEY_2026-06.md`

## 운영 목적

이 시스템은 자동 매매 엔진이 아니다. 현재 목적은 아래다.

- 한국/미국 시장 후보를 스캔한다.
- 후보의 근거, 플래너 판단, 리스크, 사후 성과를 구조화한다.
- 검증된 모델 레인은 별도 producer로 live-forward ledger를 쌓는다.
- 운영자가 UI/Discord/Archive에서 후보와 실패 원인을 확인한다.
- 연구 결론이 뒤집히면 narrative와 flag를 함께 교정한다.

현재 KR 방향은 일봉 종목선별만으로 70~75% 목표를 달성하려는 것이 아니다. 일봉 모델은 보조/검증 레인으로 유지하고, 분봉 기반 `3일 내 +5% 터치` 후보를 메인 프론티어로 본다.

## 현재 live 주요 레인

| 레인 | 시장 | 모드 | producer | 기본값 | 매매 계약 | 현재 판단 |
|---|---|---|---|---|---|---|
| `swing_ensemble` | KOSPI/KOSDAQ | `SWING` | `report_swing_ensemble.py` | ON, production ON | 가격전용 LGBM/XGB/ExtraTrees ensemble. `ft_5_5`, top 약 1%, `>=100억`, 5거래일 보유, +5% first-touch 진단. | 보조 일봉 레인. 목표 75% 모델이 아니라 modest forward 검증 레인. |
| `kospi_intraday` | KOSPI | `INTRADAY` 성격 | `report_kospi_intraday_swing.py` | ON, production ON | 분봉 경로+일봉 컨텍스트 ensemble. 3일 내 +5% MFE touch. `>=100억`, `close_vwap>=0`, `idx_vol20>=8`, top2, 3일 종가 보유. | live-forward 검증. 월별 약한 구간 보완용 변동성 guard가 있다. |
| `kosdaq_intraday_3d_t5_vwap_guard` | KOSDAQ | `INTRADAY` | `report_kosdaq_intraday_vwap_guard.py` | ON, production ON | 저장된 LGBM+전월 isotonic bundle. 15:00 진입, `p_cal>=0.80`, `pre_vwap_dist_pct>=0`, top2, `>=30억` main/`>=100억` tradeability, 3일 종가 보유, +5% touch 목표. | 현재 핵심 KOSDAQ 인트라데이 배포 후보. forward ledger 필수. |

## 관찰/비활성 레인

| 레인 | 시장 | 모드 | 상태 | 이유 |
|---|---|---|---|---|
| KOSPI NORMAL PEAD shadow | KOSPI | `SWING` | shadow ON, production OFF | 엣지 주장이 아니라 반증 ledger로 재정의됨. 이전 KS11/외부 벤치마크 narrative는 철회됨. |
| First-touch down shadow | KR | `SWING` | 기본 OFF | 하락장 반등/베타로 판정. 명시 flag 없이는 운영 노출 금지. |
| KOSPI intraday 09:05 5D candidate | KOSPI | `INTRADAY` | registry only | live forward ledger 연결 이슈가 남아 있음. |
| KOSDAQ tail guard 5D research | KOSDAQ | `INTRADAY` | 연구 전용 | 수익/초과는 일부 양호하나 win/day-win이 낮아 운영 승급 후보 아님. |
| Practical/Exception/old cohort promotion | KOSPI 중심 | `SWING` | stale/주의 | 과거 높은 win-rate narrative가 벤치마크/표본/비용 교정으로 약화됨. 새 검증 없이 production edge로 보지 않는다. |

## 일일 운영 배치

실행 파일:

```bash
multi_agent/tools/run_daily_ops.sh
```

주요 순서:

1. `update_realized_outcomes.py`로 사후 성과를 갱신한다.
2. `update_outcome_return_metrics.py`로 수익률 메트릭을 보강한다.
3. `backfill_scanner_full_returns.py`로 scanner full return을 보강한다.
4. `export_scan_archive_learning_dataset.py`로 학습용 archive dataset을 만든다.
5. outcome conversion, contaminated run 보고서를 만든다.
6. 시장별 daily summary, outcome health, fallback health, prediction validation, paper ledger, walk-forward gate, cohort gate를 생성한다.
7. dynamic theme profile, scan cohort performance, operational admission optimizer, exit policy watch를 생성한다.
8. regime signal shadow와 PEAD falsification shadow를 실행한다.
9. SWING ensemble producer를 실행한다.
10. KOSPI intraday producer를 실행한다.
11. KOSDAQ intraday VWAP guard producer를 실행한다.
12. drift alert와 daily model foundation gate를 생성한다.

이 배치는 research report만 만드는 것이 아니라 일부 producer가 production flag에 따라 Supabase live surface까지 라우팅한다.

## KR 자동 스캔

실행 파일:

```bash
python3 multi_agent/tools/run_kr_daily_auto_scans.py
```

기본 대상:

- `KOSPI/SWING`
- `KOSDAQ/SWING`
- `KOSPI/INTRADAY`
- `KOSDAQ/INTRADAY`

운영 시간대:

- `premarket`: 08:20 KST. 미국 lead/macro/theme prior를 만든다. 매수 리스트가 아니다.
- `confirmed`: 09:30 이후, 보통 09:35. 실제 KOSPI/KOSDAQ SWING/INTRADAY 스캔을 실행한다.

기본 엔진은 KIS 운영 primary + legacy fallback 구조다.

## 수동 실행 명령

KIS 운영 스캔:

```bash
python3 -m multi_agent.tools.run_kis_operational_kr_scan --market KOSDAQ --scan-mode INTRADAY
```

KOSDAQ 인트라데이 모델:

```bash
KIS_ENABLE_LIVE_CALLS=1 python3 multi_agent/tools/report_kosdaq_intraday_vwap_guard.py --min-liq 30 --tradeability-liq 100 --daily-context-source cache
```

SWING ensemble:

```bash
python3 multi_agent/tools/report_swing_ensemble.py --top-pct 1.0 --min-liq 100
```

KOSPI 인트라데이:

```bash
KIS_ENABLE_LIVE_CALLS=1 python3 multi_agent/tools/report_kospi_intraday_swing.py --min-liq 100
```

Streamlit:

```bash
streamlit run app.py
```

Discord bot:

```bash
python3 multi_agent/tools/discord_bot.py
```

Discord slash command 등록:

```bash
python3 multi_agent/tools/discord_register_commands.py
```

## 중요한 환경 변수

| 변수 | 의미 |
|---|---|
| `AG_SWING_ENSEMBLE_ENABLE` | SWING ensemble report step 활성화. daily ops 기본 ON. |
| `AG_SWING_ENSEMBLE_PRODUCTION` | SWING ensemble pick을 live surface로 라우팅. producer 기본 ON. |
| `AG_KOSPI_INTRADAY_ENABLE` | KOSPI intraday producer 활성화. daily ops 기본 ON. |
| `AG_KOSPI_INTRADAY_PRODUCTION` | KOSPI intraday live route 활성화. producer 기본 ON. |
| `AG_KOSDAQ_INTRADAY_ENABLE` | KOSDAQ intraday VWAP guard 활성화. daily ops 기본 ON. |
| `AG_KOSDAQ_INTRADAY_PRODUCTION` | KOSDAQ intraday live route 활성화. producer 기본 ON. |
| `AG_KOSDAQ_INTRADAY_MIN_LIQ` | KOSDAQ main lane 유동성 floor. 기본 `30`. |
| `AG_KOSDAQ_INTRADAY_TRADEABILITY_LIQ` | tradeability lane 유동성 floor. 기본 `100`. |
| `AG_KOSDAQ_INTRADAY_DAILY_CONTEXT_SOURCE` | `cache` 또는 `kis`. daily ops 기본 cache. |
| `AG_KOSPI_NORMAL_PEAD_SHADOW_ENABLE` | PEAD falsification ledger 활성화. 기본 ON. |
| `AG_KOSPI_NORMAL_PEAD_PRODUCTION` | PEAD production route. 현재 OFF 유지가 기준. |
| `AG_FIRSTTOUCH_DOWN_SHADOW_ENABLE` | first-touch down observation lane. 기본 OFF. |
| `AG_UI_ADVANCED` | 고급 Streamlit 탭 표시. 기본 OFF. |
| `AG_SCAN_ARCHIVE_SUPABASE_ENABLED` | Archive UI의 Supabase read 활성화. 기본 OFF, local fallback ON. |
| `AG_RUNTIME_ARTIFACT_WRITE_DB` | runtime artifacts를 Supabase에 저장. 기본 ON. |
| `KIS_ENABLE_LIVE_CALLS` | 실제 KIS 네트워크 호출 허용. live producer에 필요. |

## 운영자 사용 흐름

1. daily ops가 돌았는지 확인한다.
2. `runtime_state/reports/experimental`과 `runtime_state/reports/learning`에 최신 리포트가 생성됐는지 본다.
3. Streamlit `스캐너`에서 ad hoc 스캔을 실행한다.
4. `Top 분석`에서 현재 Top Deep 후보를 본다.
5. `아카이브`에서 run_id별 후보 순서와 실현 성과를 본다.
6. Discord `/signals`, `/top_deep`, `/archive`, `/runs`로 운영 표면을 확인한다.
7. live route 여부와 production maturity를 혼동하지 않는다. live route는 관찰 시작일 수 있고, 충분한 forward ledger가 쌓여야 진짜 승급이다.

## 현재 consumer caveat

`modules/operational_candidate_scoring.py`의 현재 whitelist:

```python
MODEL_VALIDATED_LANES = {"swing_ensemble", "kospi_intraday"}
```

`modules/discord_integration/renderers.py::build_model_signals_embed`는 `/signals`에서 이 whitelist에 있는 bucket만 모델 신호로 필터링한다.

KOSDAQ intraday producer는 아래 bucket으로 live route를 쓴다.

```text
kosdaq_intraday_3d_t5_vwap_guard
```

따라서 Top Deep/Archive에는 row가 보일 수 있지만 `/signals` 모델 카드에는 누락될 수 있다. 이건 모델 실패가 아니라 consumer 통합 미완성이다.

## 현재 Beads 운영 관련 상태

중요한 open/in-progress 성격:

- `swing-main-ho2w`: KR_INTRADAY_5D shadow candidate live forward ledger 연결.
- `swing-main-gkl2`: KIS ticker-period raw sidecar Supabase 저장.
- `swing-main-n6u3`, `swing-main-xuy1`, `swing-main-u9sq`, `swing-main-yf9n`: KIS touch5/dd10 및 sidecar 연구/백필.
- `swing-main-yk25`: Supabase authenticated PostgREST timeout 이슈.
- `swing-main-30s`: 구 INTRADAY learning pipeline 복구. 현재 KOSDAQ VWAP guard와 혼동 금지.

최근 완료된 관련 작업:

- KOSDAQ `KR_INTRADAY_3D_T5` VWAP-guard live scoring ledger.
- KOSDAQ intraday liquidity floor 비교.
- weak month failure diagnosis.
- model-lane consumer surface consistency 일부 개선.

## 승급 기준

아래가 없으면 production mature로 보지 않는다.

- 명확한 candidate id와 strategy family
- 고정 진입 시각/가격
- 고정 목표/보유/청산 계약
- 유동성 floor와 비용 가정
- same-day 또는 liquidity/size-matched control
- walk-forward/OOS 검증
- 충분한 forward ledger
- web, archive, Discord, DB, local artifact의 의미 일치
- stale narrative 제거

## 즉시 운영 방향

- KOSDAQ 15:00 VWAP guard를 계속 live-forward로 측정한다.
- KOSPI intraday는 보조 live-forward로 유지하되 volatility guard 과최적화 여부를 본다.
- SWING ensemble은 modest daily signal로 유지한다.
- PEAD/regime/Practical/Exception old narrative는 production edge로 되살리지 않는다.
- 모든 인트라데이 후보는 source부터 storage/UI까지 `INTRADAY`로 유지한다.
