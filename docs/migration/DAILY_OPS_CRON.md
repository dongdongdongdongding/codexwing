# Daily Ops Cron Guide

`multi_agent/tools/run_daily_ops.sh` 기준의 일간 운영 가이드입니다.

## 1) 수동 검증

```bash
cd /Users/dongdong/Desktop/codex_swing/swing-main
DAILY_OPS_DRY_RUN=1 AG_STALE_FALLBACK_ALERT_DRY_RUN=1 bash multi_agent/tools/run_daily_ops.sh
```

실운영 전환:

```bash
cd /Users/dongdong/Desktop/codex_swing/swing-main
DAILY_OPS_DRY_RUN=0 AG_STALE_FALLBACK_ALERT_DRY_RUN=0 bash multi_agent/tools/run_daily_ops.sh
```

## 2) 권장 스케줄

KR 운영 기준:

- 매일 `18:30` 1차 성과 측정
- 매일 `23:30` 2차 보정 측정

둘 다 서버 로컬 시간 기준입니다.

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
30 18 * * * cd /Users/dongdong/Desktop/codex_swing/swing-main && DAILY_OPS_MARKETS=KOSPI,KOSDAQ,NASDAQ DAILY_OPS_DRY_RUN=0 AG_STALE_FALLBACK_ALERT_DRY_RUN=0 /bin/bash multi_agent/tools/run_daily_ops.sh >> runtime_state/long_term/ops/cron_daily_ops_1830.log 2>&1
30 23 * * * cd /Users/dongdong/Desktop/codex_swing/swing-main && DAILY_OPS_MARKETS=KOSPI,KOSDAQ,NASDAQ DAILY_OPS_DRY_RUN=0 AG_STALE_FALLBACK_ALERT_DRY_RUN=0 /bin/bash multi_agent/tools/run_daily_ops.sh >> runtime_state/long_term/ops/cron_daily_ops_2330.log 2>&1
```

## 3) 환경변수 권장

- `DAILY_OPS_MARKETS=KOSPI,KOSDAQ,NASDAQ`
- `DAILY_OPS_LIMIT_RUNS=200`
- `DAILY_OPS_RESOLVE_ALL=0`
- `AG_STALE_FALLBACK_ALERT_ENABLE=1`
- `AG_STALE_FALLBACK_ALERT_MIN=3`
- `AG_STALE_FALLBACK_ALERT_WEBHOOK_URL=<webhook>`

## 4) 주요 산출물

- 일간 요약(JSON/MD): `runtime_state/reports/daily/daily_summary_YYYY-MM-DD.json|md`
- 결과 업데이트 로그: `runtime_state/long_term/outcomes/realized_outcomes_updates.jsonl`
- outcome health 로그: `runtime_state/long_term/outcome_health/outcome_health.jsonl`
- cron 로그: `runtime_state/long_term/ops/cron_daily_ops.log`

## 5) 실패 시 체크

- DNS/네트워크: Supabase 조회 실패 시 일부 리포트는 local fallback 모드로 동작
- webhook: URL 미설정 시 알림 발송은 생략되고 payload 상태만 출력
- 스키마: `docs/migration/supabase_agent_tables.sql` 적용 상태 확인
