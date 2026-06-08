# Primary Market Session Ops Guide

KOSPI/KOSDAQ/NASDAQ 3개 주력 시장을 6개 장세 창구에서 반복 검증하는 운영 가이드입니다.
세션 스케줄은 `multi_agent/tools/run_primary_market_session_ops.py`가 시장별 현지 시간대로 계산하고,
각 세션 실행 후 기존 `multi_agent/tools/run_daily_ops.sh`를 호출해 outcome, 검증 리포트,
daily foundation gate를 갱신합니다.

## 1) 수동 검증

```bash
cd /Users/dongdong/Desktop/codex_swing/swing-main
python3 multi_agent/tools/run_primary_market_session_ops.py --print-schedule
python3 multi_agent/tools/run_primary_market_session_ops.py --session kr_regular_close --dry-run
python3 multi_agent/tools/run_primary_market_session_ops.py --session nasdaq_regular_open --dry-run
```

실운영 전환:

```bash
cd /Users/dongdong/Desktop/codex_swing/swing-main
python3 multi_agent/tools/run_primary_market_session_ops.py --run-due --continue-on-error
```

## 2) 권장 스케줄

세션 기준:

- `kr_regular_close`: 15:40 KST, 국장 장마감 후 KOSPI/KOSDAQ 스캔 및 검증
- `kr_nxt_close`: 20:05 KST, NXT 장마감 후 KOSPI/KOSDAQ 갱신 및 검증
- `nasdaq_premarket_early`: 04:15 ET, 나스닥 프리장 초 NASDAQ 스캔 및 검증
- `nasdaq_regular_open`: 09:35 ET, 나스닥 장초 NASDAQ 스캔 및 검증
- `nasdaq_regular_close`: 16:05 ET, 나스닥 장마감 NASDAQ 스캔 및 검증
- `nasdaq_afterhours_early`: 16:15 ET, 나스닥 애프터장초 NASDAQ 스캔 및 검증

미국 세션은 `America/New_York` 기준으로 계산하므로 DST 전환 때 KST 고정 시각을 수동 변경하지 않습니다.
cron/launchd는 5분마다 due-check만 실행하고, 같은 현지 날짜의 같은 세션은 state 파일로 중복 실행을 막습니다.

자동 등록:

```bash
cd /Users/dongdong/Desktop/codex_swing/swing-main
bash multi_agent/tools/install_daily_ops_cron.sh
```

`crontab` 권한이 막힌 macOS 환경이면 `launchd` 사용:

```bash
cd /Users/dongdong/Desktop/codex_swing/swing-main
bash multi_agent/tools/install_daily_ops_launchd.sh
```

수동 cron 예시:

```bash
*/5 * * * * cd /Users/dongdong/Desktop/codex_swing/swing-main && PRIMARY_OPS_MARKETS=KOSPI,KOSDAQ,NASDAQ DAILY_OPS_DRY_RUN=0 AG_STALE_FALLBACK_ALERT_DRY_RUN=0 python3 multi_agent/tools/run_primary_market_session_ops.py --run-due --continue-on-error >> runtime_state/long_term/ops/cron_primary_market_session_ops.log 2>&1
```

## 3) 환경변수 권장

- `PRIMARY_OPS_MARKETS=KOSPI,KOSDAQ,NASDAQ`
- `DAILY_OPS_LIMIT_RUNS=200`
- `DAILY_OPS_RESOLVE_ALL=0`
- `AG_DAILY_MODEL_FOUNDATION_GATE_ENABLE=1`
- `AG_PRIMARY_OPS_NASDAQ_BATCH_SIZE=300`
- `AG_PRIMARY_OPS_NASDAQ_MAX_WORKERS=3`
- `AG_PRIMARY_OPS_NASDAQ_LIMIT_TICKERS=0` (`0` 또는 미설정이면 전체 NASDAQ 유니버스)
- `AG_STALE_FALLBACK_ALERT_ENABLE=1`
- `AG_STALE_FALLBACK_ALERT_MIN=3`
- `AG_STALE_FALLBACK_ALERT_WEBHOOK_URL=<webhook>`

## 4) 주요 산출물

- 일간 요약(JSON/MD): `runtime_state/reports/daily/daily_summary_YYYY-MM-DD.json|md`
- 세션 실행 리포트: `runtime_state/reports/ops/primary_market_session_ops_*.json`
- 세션 중복 방지 state: `runtime_state/long_term/ops/primary_market_session_state.json`
- daily foundation gate: `runtime_state/reports/learning/daily_model_foundation_gate.json|md`
- 결과 업데이트 로그: `runtime_state/long_term/outcomes/realized_outcomes_updates.jsonl`
- outcome health 로그: `runtime_state/long_term/outcome_health/outcome_health.jsonl`
- cron 로그: `runtime_state/long_term/ops/cron_primary_market_session_ops.log`

## 5) 실패 시 체크

- DNS/네트워크: Supabase 조회 실패 시 일부 리포트는 local fallback 모드로 동작
- webhook: URL 미설정 시 알림 발송은 생략되고 payload 상태만 출력
- 스키마: `docs/migration/supabase_agent_tables.sql` 적용 상태 확인
- 스케줄 중복: 같은 현지 날짜의 같은 세션을 다시 실행해야 하면 `primary_market_session_state.json`에서 해당 key를 제거하거나 `--session <id>`로 수동 실행
