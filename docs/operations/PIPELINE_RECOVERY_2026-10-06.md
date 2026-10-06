# 2026-10-06 운영·개발 픽 진단

Beads: `swing-main-4lg8`, 첫 복구 `swing-main-99vt`.

## 실측

- 운영 백엔드 `127.0.0.1:8800`, 개발 Vite `127.0.0.1:5173`, 운영 Cloudflare 터널의 health 응답을 확인했다. 운영·개발 `/api/picks` JSON은 동일했다.
- 일봉·분봉·수급·공시의 API 최신일은 2026-10-06. 이 날짜는 전체 종목 커버리지를 보증하지 않는다.
- 실제 `kr_swing_candidate_latest.json`: KOSPI 시장 5일 수익률 2.4999%, 약세 문턱 0.5071%; KOSDAQ 10.3371%, 문턱 1.9318%. 두 시장 모두 `ABSTAIN`, 후보 0, 라우팅 0. 현재 무픽의 직접 원인은 기권 조건이다.
- 실제 코스닥 장중 보고서: 유니버스 237, 피처/스코어 216, 후보 0. 픽 원장만 읽으면 이 정상 실행 사실을 알 수 없다.
- 최신 배치 보고서 10건 모두 실패. 공통 실패는 `vintage_manifest(rc=1)`. 외부 스크립트가 외장 볼륨으로 이동한 `S/picks_top20.parquet`를 열다 PermissionError로 종료했다. 일부 이전 실행에는 별도 NASDAQ 빈 입력 오류도 있다.
- 운영 상태 API는 실제 스케줄러의 `runs[날짜::세션]` 형식을 읽지 못해 `runs/null/null` 한 줄을 반환했다.
- DB의 최신 스윙 row에는 발행 제외 상태가 있었으나 웹 DB 변환 경로는 해당 필드를 전달하지 않았다. 또한 producer의 DB 계약은 5일로 고정돼 현재 코스피 원장 H10 계약과 다르다. 이는 후속 정합성 이슈 `swing-main-w1b8`에서 다룬다.

## 첫 수정 및 검증

- 상태 파서를 공용 모듈로 분리했다. 실제 scheduler가 생성한 상태를 읽고, 세션별 최신 실실행과 실패 단계만 요약한다. dry-run은 실실행을 덮어쓰지 않는다.
- 원장에 새 row가 없는 날에도 생산자 보고서를 API·개요·픽·운영 화면에 표시한다. 기권, 후보 없음, 결과 지연, 파일/조회 실패를 구분한다.
- 빈티지 기록기를 저장소로 편입했다. 활성 입력은 누락/손상/변경 시 실패한다. 보관 연구 입력은 읽을 수 없을 때 그 사실을 기록하고 활성 입력 기록을 계속한다. 원자적으로 최신 매니페스트를 교체한다.
- `python3 -m pytest tests/test_pipeline_status.py tests/test_vintage_manifest.py tests/test_primary_market_session_ops.py tests/test_daily_ops_flag_switch.py tests/test_shell_portability.py tests/test_ops_write_endpoint_guard.py tests/test_web_blockers_consistency.py tests/test_web_expired_pick_hiding.py -q`: **114 passed**.
- `python3 multi_agent/tools/write_vintage_manifest.py --output-dir runtime_state/reports/validation/pipeline_recovery`: 실제 입력 기준 `status=ok`, 활성 입력 실패 0. 셸에서는 보관 볼륨에도 접근 가능했으므로 launchd의 과거 접근 실패 재현은 예외 주입 회귀 테스트로 확인했다.
- 공용 파서에 운영 디렉터리를 지정해 실제 보고서를 재읽었다. 현재 두 시장 기권, 장중 선별 0건, 실제 배치 실패 단계가 모두 보존됐다.

신규 전략의 수익 엣지·승격을 의미하는 변경은 없다. 10거래일 +5% 목표는 `swing-main-q6va`에서 별도 계약으로 검증한다.
