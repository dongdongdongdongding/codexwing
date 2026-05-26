# Outcome Updater Cron Guide

`realized_outcomes.json`의 `PENDING`을 `signals.result_3d` 기반으로 `RESOLVED`로 갱신하고,
후보 단위 `post_scan_outcome_ledger.json`를 최신 성과 라벨로 채우는 운영 가이드입니다.

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
- 후보 성과 ledger: `runtime_state/shared_working/RUN-*/post_scan_outcome_ledger.json`
- DB 업서트 대상(가용 시): `agent_realized_outcomes`, `market_scan_results`, `post_scan_outcome_ledger`

## 4) Post-scan outcome ledger 범위

- 저장 범위는 스캐너가 실제 배출한 후보(Top/Shadow/Exception)만입니다.
- 원시 분봉/틱 데이터는 저장하지 않고 `10m/30m/1h/close/1D/3D/5D`, MFE, MAE, target-first/stop-first 요약값만 저장합니다.
- `entry_reference_price`는 일봉 성과 계산용 기준가이고, `scan_entry_reference_price`는 스캔 당시 화면에 노출된 진입 기준가입니다.
- `target_before_stop_5d`는 스캔 이후 경로 기준의 보수적 라벨입니다. 가능한 경우 당일 스캔 이후 30분봉을 먼저 쓰고, 이후 일봉 OHLC를 이어붙입니다.
- 같은 봉에서 목표가와 손절가가 모두 닿으면 `stop_first`로 기록합니다. 30분봉도 완전한 틱 순서는 아니므로 `outcome_path_warnings`에 부분봉/동일봉 경고를 남깁니다.
- `ordered_entry_at`, `ordered_target_hit_at`, `ordered_stop_hit_at`, `ordered_mae_before_target_5d_pct`는 모델 승격 검증용 정밀 경로 필드입니다. 원시 분봉 전체는 저장하지 않고 요약 라벨만 저장합니다.

## 5) 주의사항

- `supabase` 패키지/환경변수(`SUPABASE_URL`, `SUPABASE_KEY`)가 없으면 실제 해소는 진행되지 않고 통계만 출력됩니다.
- 이 프로젝트는 `.env`와 `.env.local`을 모두 읽습니다. Python 런타임에서 `SUPABASE_*`가 비어 있으면 `NEXT_PUBLIC_SUPABASE_*`를 fallback으로 사용합니다.
- `--resolve-all` 미사용 시 기본적으로 추천 시점 기준 `3일` 지난 `PENDING`만 처리합니다.
