#!/usr/bin/env python3
"""Run the primary-market operating cadence at named market sessions.

The schedule is defined in market-local time so the NASDAQ windows follow
US daylight-saving changes without changing launchd/cron entries.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = PROJECT_ROOT / "runtime_state" / "long_term" / "ops" / "primary_market_session_state.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "runtime_state" / "reports" / "ops"
PRIMARY_MARKETS = ("KOSPI", "KOSDAQ", "NASDAQ")


@dataclass(frozen=True)
class SessionSpec:
    session_id: str
    label_ko: str
    timezone_name: str
    trigger_time: str
    markets: tuple[str, ...]
    scan_scope: str
    actions: tuple[str, ...]
    rationale: str

    @property
    def trigger_clock(self) -> time:
        hour, minute = self.trigger_time.split(":", 1)
        return time(int(hour), int(minute), tzinfo=ZoneInfo(self.timezone_name))


SESSION_SPECS: tuple[SessionSpec, ...] = (
    SessionSpec(
        session_id="kr_premarket_refresh",
        label_ko="국장 개장 데이터 갱신",
        timezone_name="Asia/Seoul",
        trigger_time="09:35",
        markets=("KOSPI", "KOSDAQ"),
        scan_scope="kr_premarket_refresh_plus_primary_daily_ops",
        actions=("kr_confirmed_scan", "primary_daily_ops"),
        rationale=(
            "매일 개장 직후 전 데이터(일봉 px_long·분봉·수급 flow) 갱신 후 KR 스캔/픽 생성. "
            "KIS 투자자수급 API는 00:00~15:40만 호출 가능 → 15:40/20:05 마감세션은 수급을 못 받으므로 "
            "수급 갱신은 이 아침 세션이 담당(직전 거래일 확정치 반영)."
        ),
    ),
    SessionSpec(
        session_id="kr_regular_close",
        label_ko="국장 장마감",
        timezone_name="Asia/Seoul",
        trigger_time="15:40",
        markets=("KOSPI", "KOSDAQ"),
        scan_scope="kr_kis_confirmed_scan_plus_primary_daily_ops",
        actions=("kr_confirmed_scan", "primary_daily_ops"),
        rationale="KRX 정규장 종가 확정 이후 KOSPI/KOSDAQ 스캔, 결과 저장, 검증 게이트를 실행",
    ),
    SessionSpec(
        session_id="kr_nxt_close",
        label_ko="넥스트 장마감",
        timezone_name="Asia/Seoul",
        trigger_time="20:05",
        markets=("KOSPI", "KOSDAQ"),
        scan_scope="kr_nxt_close_refresh_plus_primary_daily_ops",
        actions=("kr_confirmed_scan", "primary_daily_ops"),
        rationale="NXT 20:00 마감 이후 국내 연장장 반영 후보와 일일 학습 게이트를 갱신",
    ),
    SessionSpec(
        session_id="nasdaq_premarket_early",
        label_ko="나스닥 프리장 초",
        timezone_name="America/New_York",
        trigger_time="04:15",
        markets=("NASDAQ",),
        scan_scope="nasdaq_full_universe_swing_research_plus_primary_daily_ops",
        actions=("nasdaq_full_universe_scan", "primary_daily_ops"),
        rationale="프리마켓 초기 갭/뉴스 반응을 NASDAQ 후보와 KR 다음날 테마 컨텍스트에 반영",
    ),
    SessionSpec(
        session_id="nasdaq_regular_open",
        label_ko="나스닥 장초",
        timezone_name="America/New_York",
        trigger_time="09:35",
        markets=("NASDAQ",),
        scan_scope="nasdaq_full_universe_swing_research_plus_primary_daily_ops",
        actions=("nasdaq_full_universe_scan", "primary_daily_ops"),
        rationale="정규장 개장 직후 체결/거래대금 기반 후보를 갱신",
    ),
    SessionSpec(
        session_id="nasdaq_regular_close",
        label_ko="나스닥 장마감",
        timezone_name="America/New_York",
        trigger_time="16:05",
        markets=("NASDAQ",),
        scan_scope="nasdaq_full_universe_swing_research_plus_primary_daily_ops",
        actions=("nasdaq_full_universe_scan", "primary_daily_ops"),
        rationale="정규장 종가 확정 후 NASDAQ 성과/후보/학습 산출물을 갱신",
    ),
    SessionSpec(
        session_id="nasdaq_afterhours_early",
        label_ko="나스닥 애프터장초",
        timezone_name="America/New_York",
        trigger_time="16:15",
        markets=("NASDAQ",),
        scan_scope="nasdaq_full_universe_swing_research_plus_primary_daily_ops",
        actions=("nasdaq_full_universe_scan", "primary_daily_ops"),
        rationale="애프터마켓 초기 실적/가이던스 반응을 후보와 다음 KR 세션 컨텍스트에 반영",
    ),
)


def _session_map() -> Dict[str, SessionSpec]:
    return {spec.session_id: spec for spec in SESSION_SPECS}


def _parse_now(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": "primary_market_session_state_v1", "runs": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": "primary_market_session_state_v1", "runs": {}}
    if not isinstance(payload, dict):
        return {"version": "primary_market_session_state_v1", "runs": {}}
    if not isinstance(payload.get("runs"), dict):
        payload["runs"] = {}
    return payload


def _write_state(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_report(report_dir: Path, report: Mapping[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"primary_market_session_ops_{report.get('session_id')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _state_key(spec: SessionSpec, now_utc: datetime) -> str:
    local = now_utc.astimezone(ZoneInfo(spec.timezone_name))
    return f"{local.date().isoformat()}::{spec.session_id}"


def due_sessions(
    now_utc: datetime,
    *,
    state: Optional[Mapping[str, Any]] = None,
    due_window_minutes: int = 10,
    include_weekends: bool = False,
) -> List[SessionSpec]:
    runs = (state or {}).get("runs") if isinstance((state or {}).get("runs"), dict) else {}
    due: List[SessionSpec] = []
    window = timedelta(minutes=max(1, int(due_window_minutes)))
    for spec in SESSION_SPECS:
        tz = ZoneInfo(spec.timezone_name)
        local_now = now_utc.astimezone(tz)
        if not include_weekends and local_now.weekday() >= 5:
            continue
        scheduled = datetime.combine(local_now.date(), spec.trigger_clock, tzinfo=tz)
        if scheduled <= local_now < scheduled + window:
            key = _state_key(spec, now_utc)
            if key not in runs:
                due.append(spec)
    return due


def _env_csv(name: str, default: Sequence[str]) -> str:
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    return ",".join(default)


def _session_env(spec: SessionSpec) -> Dict[str, str]:
    return {
        "AG_PRIMARY_SESSION_ID": spec.session_id,
        "AG_PRIMARY_SESSION_LABEL": spec.label_ko,
        "AG_PRIMARY_SESSION_TIMEZONE": spec.timezone_name,
        "AG_PRIMARY_SESSION_TRIGGER_TIME": spec.trigger_time,
        "AG_PRIMARY_SESSION_CUTOFF": f"{spec.trigger_time} {spec.timezone_name}",
        "AG_PRIMARY_SESSION_SCAN_SCOPE": spec.scan_scope,
    }


def _command_row(
    *,
    name: str,
    argv: Sequence[str],
    env: Optional[Mapping[str, str]] = None,
    required: bool = True,
) -> Dict[str, Any]:
    return {
        "name": name,
        "argv": list(argv),
        "env": dict(env or {}),
        "required": bool(required),
    }


def build_command_plan(spec: SessionSpec) -> List[Dict[str, Any]]:
    commands: List[Dict[str, Any]] = []
    session_env = _session_env(spec)
    if "kr_confirmed_scan" in spec.actions:
        commands.append(
            _command_row(
                name="kr_confirmed_scan",
                argv=[
                    sys.executable,
                    "multi_agent/tools/run_kr_daily_auto_scans.py",
                    "--phase",
                    "scan",
                ],
                env={
                    **session_env,
                    "AG_KR_DAILY_SCAN_ENGINE": os.getenv("AG_KR_DAILY_SCAN_ENGINE", "kis_operational"),
                    "AG_KR_DAILY_LEGACY_FALLBACK": os.getenv("AG_KR_DAILY_LEGACY_FALLBACK", "1"),
                    "AG_KR_DAILY_SCAN_TARGETS": os.getenv(
                        "AG_KR_DAILY_SCAN_TARGETS",
                        "KOSPI:SWING,KOSDAQ:SWING,KOSPI:INTRADAY,KOSDAQ:INTRADAY",
                    ),
                },
                required=False,
            )
        )
    if "nasdaq_full_universe_scan" in spec.actions:
        commands.append(
            _command_row(
                name="nasdaq_full_universe_scan",
                argv=[
                    sys.executable,
                    "multi_agent/tools/run_us_full_universe_research.py",
                    "--market",
                    "NASDAQ",
                    "--profile",
                    os.getenv("AG_PRIMARY_OPS_NASDAQ_PROFILE", "prod"),
                    "--batch-size",
                    os.getenv("AG_PRIMARY_OPS_NASDAQ_BATCH_SIZE", "300"),
                    "--max-workers",
                    os.getenv("AG_PRIMARY_OPS_NASDAQ_MAX_WORKERS", "3"),
                    "--max-retries",
                    os.getenv("AG_PRIMARY_OPS_NASDAQ_MAX_RETRIES", "1"),
                    "--scan-mode",
                    os.getenv("AG_PRIMARY_OPS_NASDAQ_SCAN_MODE", "SWING"),
                    "--strategy-version",
                    f"primary-session-{spec.session_id}",
                    "--model-version",
                    os.getenv("AG_PRIMARY_OPS_NASDAQ_MODEL_VERSION", "phase25"),
                    "--code-version",
                    "primary-market-session-ops",
                ]
                + (
                    ["--limit-tickers", os.getenv("AG_PRIMARY_OPS_NASDAQ_LIMIT_TICKERS", "0")]
                    if os.getenv("AG_PRIMARY_OPS_NASDAQ_LIMIT_TICKERS")
                    else []
                ),
                env=session_env,
                required=False,
            )
        )
    if "primary_daily_ops" in spec.actions:
        commands.append(
            _command_row(
                name="primary_daily_ops",
                argv=["/bin/bash", "multi_agent/tools/run_daily_ops.sh"],
                env={
                    **session_env,
                    "DAILY_OPS_MARKETS": _env_csv("PRIMARY_OPS_MARKETS", PRIMARY_MARKETS),
                    "DAILY_OPS_DRY_RUN": os.getenv("DAILY_OPS_DRY_RUN", "0"),
                    "AG_STALE_FALLBACK_ALERT_DRY_RUN": os.getenv("AG_STALE_FALLBACK_ALERT_DRY_RUN", "0"),
                    "AG_DAILY_MODEL_FOUNDATION_GATE_ENABLE": os.getenv("AG_DAILY_MODEL_FOUNDATION_GATE_ENABLE", "1"),
                    "AG_NASDAQ_SWING_MODEL_ENABLE": os.getenv("AG_NASDAQ_SWING_MODEL_ENABLE", "1"),
                    "AG_NASDAQ_SWING_PANEL": os.getenv("AG_NASDAQ_SWING_PANEL", "latest"),
                },
                required=True,
            )
        )
    return commands


def _redacted_env(env: Mapping[str, str]) -> Dict[str, str]:
    redacted: Dict[str, str] = {}
    for key, value in env.items():
        if any(token in key.upper() for token in ("TOKEN", "SECRET", "KEY", "WEBHOOK", "PASSWORD")):
            redacted[key] = "***"
        else:
            redacted[key] = str(value)
    return redacted


def _run_command(command: Mapping[str, Any], *, dry_run: bool) -> Dict[str, Any]:
    argv = [str(item) for item in command.get("argv") or []]
    env_delta = {str(k): str(v) for k, v in (command.get("env") or {}).items() if v is not None}
    started_at = datetime.now(timezone.utc).isoformat()
    if dry_run:
        return {
            "name": command.get("name"),
            "argv": argv,
            "env": _redacted_env(env_delta),
            "required": bool(command.get("required", True)),
            "returncode": 0,
            "dry_run": True,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }

    env = os.environ.copy()
    env.update(env_delta)
    proc = subprocess.run(
        argv,
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "name": command.get("name"),
        "argv": argv,
        "env": _redacted_env(env_delta),
        "required": bool(command.get("required", True)),
        "returncode": int(proc.returncode),
        "stdout_tail": (proc.stdout or "")[-6000:],
        "stderr_tail": (proc.stderr or "")[-6000:],
        "dry_run": False,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


def run_session(
    spec: SessionSpec,
    *,
    dry_run: bool = False,
    continue_on_error: bool = True,
    report_dir: Path = DEFAULT_REPORT_DIR,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    now_utc = now_utc or datetime.now(timezone.utc)
    commands = build_command_plan(spec)
    results: List[Dict[str, Any]] = []
    for command in commands:
        result = _run_command(command, dry_run=dry_run)
        results.append(result)
        if result.get("returncode") != 0 and command.get("required", True) and not continue_on_error:
            break
    required_failures = [
        row for row in results if row.get("required") and int(row.get("returncode") or 0) != 0
    ]
    optional_failures = [
        row for row in results if not row.get("required") and int(row.get("returncode") or 0) != 0
    ]
    if required_failures:
        status = "failed"
    elif optional_failures:
        status = "degraded"
    else:
        status = "ok"
    report: Dict[str, Any] = {
        "version": "primary_market_session_ops_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session_id": spec.session_id,
        "label_ko": spec.label_ko,
        "scheduled_timezone": spec.timezone_name,
        "scheduled_trigger_time": spec.trigger_time,
        "markets": list(spec.markets),
        "primary_markets": list(PRIMARY_MARKETS),
        "scan_scope": spec.scan_scope,
        "rationale": spec.rationale,
        "status": status,
        "dry_run": bool(dry_run),
        "required_failure_count": len(required_failures),
        "optional_failure_count": len(optional_failures),
        "commands": results,
    }
    report_path = _write_report(report_dir, report)
    report["report_path"] = str(report_path)
    return report


def mark_session_state(
    state: Dict[str, Any],
    *,
    spec: SessionSpec,
    now_utc: datetime,
    report: Mapping[str, Any],
) -> Dict[str, Any]:
    key = _state_key(spec, now_utc)
    state.setdefault("runs", {})[key] = {
        "session_id": spec.session_id,
        "status": report.get("status"),
        "dry_run": bool(report.get("dry_run")),
        "report_path": report.get("report_path"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    return state


def schedule_report(now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    now_utc = now_utc or datetime.now(timezone.utc)
    sessions = []
    for spec in SESSION_SPECS:
        tz = ZoneInfo(spec.timezone_name)
        local_now = now_utc.astimezone(tz)
        scheduled = datetime.combine(local_now.date(), spec.trigger_clock, tzinfo=tz)
        if scheduled < local_now:
            scheduled = scheduled + timedelta(days=1)
        sessions.append(
            {
                **asdict(spec),
                "primary_markets": list(PRIMARY_MARKETS),
                "next_local": scheduled.isoformat(),
                "next_utc": scheduled.astimezone(timezone.utc).isoformat(),
                "command_plan": build_command_plan(spec),
            }
        )
    return {
        "version": "primary_market_schedule_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_markets": list(PRIMARY_MARKETS),
        "sessions": sessions,
    }


def _session_arg(value: str) -> SessionSpec:
    by_id = _session_map()
    key = str(value or "").strip()
    if key not in by_id:
        raise SystemExit(f"Unknown session '{value}'. Expected one of: {', '.join(sorted(by_id))}")
    return by_id[key]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run primary KOSPI/KOSDAQ/NASDAQ market session ops.")
    parser.add_argument("--session", choices=sorted(_session_map()), help="Run one explicit session.")
    parser.add_argument("--run-due", action="store_true", help="Run sessions due at --now, using state for idempotence.")
    parser.add_argument("--print-schedule", action="store_true", help="Print the six-window schedule and command plan.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true", default=True)
    parser.add_argument("--due-window-minutes", type=int, default=10)
    parser.add_argument("--include-weekends", action="store_true")
    parser.add_argument("--now", default=None, help="ISO timestamp for tests/replays. Defaults to current UTC.")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    now_utc = _parse_now(args.now)
    report_dir = Path(args.report_dir)
    if args.print_schedule:
        print(json.dumps(schedule_report(now_utc), ensure_ascii=False, indent=2))
        return 0

    if args.session:
        report = run_session(
            _session_arg(args.session),
            dry_run=bool(args.dry_run),
            continue_on_error=bool(args.continue_on_error),
            report_dir=report_dir,
            now_utc=now_utc,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report.get("status") in {"ok", "degraded"} else 1

    if args.run_due:
        state_path = Path(args.state_path)
        state = _load_state(state_path)
        sessions = due_sessions(
            now_utc,
            state=state,
            due_window_minutes=int(args.due_window_minutes),
            include_weekends=bool(args.include_weekends),
        )
        reports = []
        for spec in sessions:
            report = run_session(
                spec,
                dry_run=bool(args.dry_run),
                continue_on_error=bool(args.continue_on_error),
                report_dir=report_dir,
                now_utc=now_utc,
            )
            reports.append(report)
            if not args.dry_run:
                state = mark_session_state(state, spec=spec, now_utc=now_utc, report=report)
        if not args.dry_run:
            _write_state(state_path, state)
        payload = {
            "version": "primary_market_session_due_run_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "now_utc": now_utc.isoformat(),
            "due_count": len(sessions),
            "sessions": [spec.session_id for spec in sessions],
            "dry_run": bool(args.dry_run),
            "reports": reports,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if all(report.get("status") in {"ok", "degraded"} for report in reports) else 1

    parser.error("Use --print-schedule, --session, or --run-due.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
