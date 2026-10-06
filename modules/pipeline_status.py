"""Read producer and scheduler evidence without recomputing trading decisions."""
from __future__ import annotations

import json
from pathlib import Path


def read_object(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("expected JSON object")
        return value, None
    except (OSError, ValueError) as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def session_status(repo):
    """The scheduler writes runs[date::session], not sessions[session]."""
    root = Path(repo) / "runtime_state"
    state, error = read_object(root / "long_term/ops/primary_market_session_state.json")
    if error:
        return {"sessions": [], "session_error": error}
    runs = state.get("runs", state.get("sessions", {}))
    if not isinstance(runs, dict):
        return {"sessions": [], "session_error": "invalid scheduler runs"}
    latest = {}
    for key, run in runs.items():
        if not isinstance(run, dict) or run.get("dry_run"):
            continue
        sid = run.get("session_id") or str(key).split("::")[-1]
        stamp = run.get("recorded_at") or run.get("last_ran_at") or run.get("last_run_date") or str(key)
        if sid not in latest or stamp > latest[sid][0]:
            latest[sid] = (stamp, run)
    rows = []
    for sid, (stamp, run) in sorted(latest.items()):
        row = {"id": sid, "last_run": stamp, "status": run.get("status") or run.get("last_status"),
               "failures": []}
        if run.get("report_path"):
            report, err = read_object(root / "reports/ops" / Path(run["report_path"]).name)
            if err:
                row["report_error"] = err
            for command in report.get("commands", []):
                if command.get("returncode"):
                    steps = [line for line in command.get("stdout_tail", "").splitlines()
                             if line.startswith("[FAILED]")]
                    row["failures"].append({"step": command.get("name"),
                                            "returncode": command["returncode"], "details": steps})
        rows.append(row)
    return {"sessions": rows, "session_error": None}


def kr_producer_status(repo, *, daily_date=None, lane=None):
    """A zero-pick run is visible even though it cannot add a row to the pick ledger."""
    exp = Path(repo) / "runtime_state/reports/experimental"
    swing, swing_error = read_object(exp / "kr_swing_candidate_latest.json")
    intraday, intraday_error = read_object(exp / "kosdaq_intraday_1500_3d_t5_vwap_guard_latest.json")
    output = []
    for key, market, label, report, error in (
        ("kospi_swing", "KOSPI", "코스피 스윙", swing, swing_error),
        ("kosdaq_swing", "KOSDAQ", "코스닥 스윙", swing, swing_error),
        ("kosdaq_intraday", "KOSDAQ", "코스닥 장중", intraday, intraday_error),
    ):
        if lane and lane != key:
            continue
        asof = str(report.get("as_of") or report.get("trade_date") or "")
        if len(asof) == 8 and asof.isdigit():
            asof = f"{asof[:4]}-{asof[4:6]}-{asof[6:]}"
        count = sum(1 for p in report.get("picks", []) if p.get("market") == market)
        gate = (report.get("gate") or {}).get(market, {})
        status, reason = "picks", f"최근 실행 후보 {count}건"
        if report.get("routed", 0) == -1:
            status, reason = "error", "후보 계산 후 DB 저장에 실패했습니다"
        elif error or report.get("error"):
            status, reason = "error", "생산자 실행 결과를 확인할 수 없습니다"
        elif not asof or (daily_date and asof < str(daily_date)[:10]):
            status, reason = "stale", "최신 데이터에 대한 생산자 실행 결과가 아직 없습니다"
        elif not count and gate.get("gate") == "ABSTAIN":
            status, reason = "abstain", "시장 조건에 따라 진입을 보류했습니다"
            if gate.get("gate_kind") == "mkt_weakness":
                reason = (f"약세장 진입 조건 미충족: 시장 5일 수익률 {gate.get('gate_mkt_ret5')}%"
                          f" / 기준 {gate.get('gate_threshold')}% 이하")
        elif not count and gate and not gate.get("fire"):
            status, reason = "blocked", f"모델 판정 보류: {gate.get('gate', 'UNKNOWN')}"
        elif not count and key == "kosdaq_intraday" and not report.get("scored_rows"):
            status, reason = "blocked", "계산 가능한 분봉 피처가 없습니다"
        elif not count:
            status, reason = "no_candidates", "계산을 완료했으나 선별 조건을 통과한 종목이 없습니다"
        output.append({"lane": key, "label": label, "market": market, "status": status,
                       "reason": reason, "as_of": asof or None,
                       "generated_at": report.get("generated_at"), "pick_count": count,
                       "scored_rows": report.get("scored_rows"), "gate": gate,
                       "diagnostics": report.get("diagnostics", {}), "error": error or report.get("error")})
    return output
