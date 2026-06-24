# Swing Main 운영 기준 문서

최종 갱신일: 2026-06-24

이 저장소는 한국/미국 주식의 스윙 및 인트라데이 후보를 만들고, 검증하고, 운영자가 판단할 수 있게 보여주는 퀀트 리서치/운영 지원 시스템이다. 단순 백테스트 저장소가 아니라 다음 기능을 함께 가진다.

- KIS/FDR 기반 시장 데이터 수집
- KOSPI/KOSDAQ/NASDAQ 등 스캐너 실행
- SWING/INTRADAY 후보 분리
- 모델 레인별 실시간 후보 생성
- Streamlit 운영 화면
- Discord 원격 스캔/조회
- Supabase 및 로컬 런타임 저장
- 사후 실현성과/검증/리서치 리포트
- Beads 기반 작업 추적

현재 프로젝트의 핵심 방향은 일봉 종목선별만으로 목표를 억지로 달성하는 것이 아니다. 최근 검증 결과 일봉 모델은 보조 신호로 유지하고, 목표 달성 가능성이 더 높은 분봉 기반 `3일 내 +5% 터치` 인트라데이 모델을 메인 축으로 운영한다. 현재 가장 중요한 배포 후보는 KOSDAQ 15:00 VWAP 가드 `KR_INTRADAY_3D_T5` 레인이다.

## 먼저 읽을 문서

- [운영 매뉴얼](docs/operations/CURRENT_OPERATIONS_MANUAL_2026-06-24.md)
- [백엔드/데이터 구조](docs/architecture/BACKEND_DATA_ARCHITECTURE_2026-06-24.md)
- [프론트엔드/Discord/디자인 구조](docs/architecture/FRONTEND_OPERATOR_UI_2026-06-24.md)
- [종합 시스템 분석](docs/architecture/SYSTEM_ANALYSIS_2026-06-24.md)
- [모델별 매매전략](docs/research/MODEL_TRADING_STRATEGIES_2026-06-24.md)
- [프로젝트 트리와 파일별 사용 상태](docs/architecture/PROJECT_FILE_TREE_2026-06-24.md)

이전 문서들은 히스토리로는 가치가 있지만, 일부는 철회된 일봉 엣지 주장이나 오래된 운영 상태를 포함한다. 현재 운영 기준은 위 문서들이다.

## 현재 살아있는 주요 레인

| 레인 | 시장 | 모드 | 진입 | 목표 | 운영 상태 |
|---|---|---|---|---|---|
| SWING ensemble | KOSPI/KOSDAQ | `SWING` | 일봉 계약, 최근/다음 세션 기준 | `ft_5_5`, 5거래일 | 보조 일봉 레인, forward 검증 |
| KOSPI intraday | KOSPI | `INTRADAY` 성격의 모델 레인 | 종가/장 전체 분봉 컨텍스트 | 3일 내 +5% 터치 | forward 검증 |
| KOSDAQ intraday VWAP guard | KOSDAQ | `INTRADAY` | 15:00 분봉 확정 | 3일 내 +5% 터치 | 현재 핵심 인트라데이 배포 후보 |

관찰/비활성 레인에는 KOSPI NORMAL PEAD shadow, first-touch down shadow, KOSPI 09:05 5D intraday shadow, KOSDAQ tail guard research, KIS touch5/dd10 연구 스트림이 있다.

## 주요 실행 명령

일일 운영 배치:

```bash
multi_agent/tools/run_daily_ops.sh
```

자동 KR 스캔:

```bash
python3 multi_agent/tools/run_kr_daily_auto_scans.py
```

KIS 운영 스캔:

```bash
python3 -m multi_agent.tools.run_kis_operational_kr_scan --market KOSDAQ --scan-mode INTRADAY
```

KOSDAQ 인트라데이 VWAP 가드 모델 직접 실행:

```bash
KIS_ENABLE_LIVE_CALLS=1 python3 multi_agent/tools/report_kosdaq_intraday_vwap_guard.py --min-liq 30 --tradeability-liq 100 --daily-context-source cache
```

Streamlit UI:

```bash
streamlit run app.py
```

Discord 봇:

```bash
python3 multi_agent/tools/discord_bot.py
```

## 핵심 구조

스캐너 파이프라인:

1. KIS/FDR/fallback 데이터 소스에서 시장 데이터를 가져온다.
2. `SWING` 또는 `INTRADAY` 모드를 명시한 후보를 만든다.
3. scanner handoff를 local short-term memory에 쓴다.
4. aggregation, backtest diagnostics, market/news context, planner, postmortem trace를 생성한다.
5. Top Deep 리포트를 생성한다.
6. 로컬 artifact, Supabase rows, runtime artifacts, scan-universe snapshots, post-scan outcome ledger를 저장한다.

모델 레인 producer 경로:

1. 특정 검증 모델 레인을 고정 계약으로 스코어링한다.
2. 자체 JSON/MD 리포트와 JSONL ledger를 쓴다.
3. 보유 기간이 지난 pending outcome을 해소한다.
4. production flag가 켜져 있으면 `market_scan_results`와 `scan_deep_reports`에 직접 라우팅한다.

두 경로는 공존한다. 모든 live pick이 동일한 planner gate를 거쳤다고 보면 안 된다.

## 데이터 위치

저장소 내부 운영 상태:

- `runtime_state/artifacts/RUN-*`
- `runtime_state/shared_working/RUN-*`
- `runtime_state/reports/*`
- `runtime_state/long_term/*`

외부 리서치 캐시:

- `~/research_cache/px_long.parquet`
- `~/research_cache/intraday/{code}.parquet`
- `~/research_cache/intraday_3d_panel.parquet`
- 기타 flow, DART, fund, PEAD, shares 캐시

Supabase 주요 테이블:

- `market_scan_results`
- `scan_deep_reports`
- `post_scan_outcome_ledger`
- `runtime_artifacts`
- `scan_universe_snapshots`
- `agent_realized_outcomes`

## 현재 중요한 주의점

KOSDAQ 인트라데이 VWAP 가드 producer는 live route를 수행하지만, 기존 모델 레인 consumer whitelist에는 현재 아래 두 bucket만 들어 있다.

```python
{"swing_ensemble", "kospi_intraday"}
```

따라서 `/signals` 또는 일부 간결한 모델 카드에서는 KOSDAQ 인트라데이 bucket이 누락되거나 generic 해석으로 표시될 수 있다. Top Deep과 Archive는 direct row를 읽을 수 있다. 이 문제는 리서치 실패가 아니라 consumer 통합 미완성 문제다.

## 개발/운영 원칙

- 스캐너, 백엔드, UI, planner 로직을 분리한다.
- 핵심 엔진 로직을 Streamlit 파일 안에 묻지 않는다.
- 모든 작업 추적은 Beads를 사용한다.
- 추천 후보는 scanner reason, aggregation note, backtest diagnostic, market/news context, planner decision, realized outcome placeholder를 가져야 한다.
- 누락 데이터는 누락으로 둔다. 가격/수급/스탑을 임의 생성하지 않는다.
- `SWING`과 `INTRADAY`는 데이터 수집, 저장, UI까지 끝까지 분리한다.
- 모델 파일이 존재한다는 이유만으로 운영 중이라고 판단하지 않는다. 운영 상태는 daily ops flag, producer route, ledger로 판단한다.

## Beads 작업 관리

프로젝트 shortcut:

```bash
scripts/issue
scripts/issue start <id>
scripts/issue end <id> "reason"
scripts/issue sync
scripts/issue log
```

Claude/Codex 공유 스레드:

```bash
bd comments swing-main-0to
bd comment swing-main-0to "[Codex] ..."
```

## 검증 규율

높은 승률 하나만으로 production mature가 아니다. 최소한 아래가 필요하다.

- 고정 진입/청산 계약
- 명시적 비용/유동성 가정
- same-day 또는 liquidity/size-matched 대조
- walk-forward/OOS 검증
- forward ledger
- 충분한 pick 수, 거래일 수, 월 수
- web/archive/Discord/DB consumer parity

현재 우선순위는 KOSDAQ 인트라데이 `KR_INTRADAY_3D_T5` 레인의 forward 검증과 운영 통합 강화다.
