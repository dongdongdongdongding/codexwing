# Outcome Updater Cron Guide

`realized_outcomes.json`의 `PENDING`을 `signals.result_3d` 기반으로 `RESOLVED`로 갱신하는 운영 가이드입니다.

전체 운영 배치(요약/리포트/stale 알림 포함)가 필요하면
`docs/migration/DAILY_OPS_CRON.md`를 사용하세요.

## 1) 수동 실행 (권장 시작)

```bash
cd /Users/dongdong/Desktop/codex_swing/swing-main
python3 multi_agent/tools/update_realized_outcomes.py --dry-run --limit-runs 50 --resolve-all
python3 multi_agent/tools/update_realized_outcomes.py --limit-runs 50 --resolve-all
python3 multi_agent/tools/report_outcome_conversion.py --limit-runs 50
```

## 2) Cron 등록 예시

아래는 6시간마다 실행 예시입니다.

```bash
0 */6 * * * cd /Users/dongdong/Desktop/codex_swing/swing-main && /bin/bash multi_agent/tools/run_outcome_updater.sh >> runtime_state/long_term/outcomes/cron_outcome_updater.log 2>&1
```

## 3) 로그/산출물

- 업데이트 로그(JSONL): `runtime_state/long_term/outcomes/realized_outcomes_updates.jsonl`
- Cron 로그(텍스트): `runtime_state/long_term/outcomes/cron_outcome_updater.log`
- 갱신 대상 파일: `runtime_state/shared_working/RUN-*/realized_outcomes.json`
- DB 업서트 대상(가용 시): `agent_realized_outcomes`

## 4) 주의사항

- `supabase` 패키지/환경변수(`SUPABASE_URL`, `SUPABASE_KEY`)가 없으면 실제 해소는 진행되지 않고 통계만 출력됩니다.
- 이 프로젝트는 `.env`와 `.env.local`을 모두 읽습니다. Python 런타임에서 `SUPABASE_*`가 비어 있으면 `NEXT_PUBLIC_SUPABASE_*`를 fallback으로 사용합니다.
- `--resolve-all` 미사용 시 기본적으로 추천 시점 기준 `3일` 지난 `PENDING`만 처리합니다.
