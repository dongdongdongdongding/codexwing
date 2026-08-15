from __future__ import annotations

from datetime import datetime, timezone

from multi_agent.tools.run_primary_market_session_ops import (
    PRIMARY_MARKETS,
    _run_command,
    SESSION_SPECS,
    build_command_plan,
    due_sessions,
    run_session,
    schedule_report,
)


def test_primary_market_schedule_has_user_requested_windows():
    by_id = {spec.session_id: spec for spec in SESSION_SPECS}

    assert tuple(PRIMARY_MARKETS) == ("KOSPI", "KOSDAQ", "NASDAQ")
    assert set(by_id) == {
        "kr_premarket_refresh",
        "kr_regular_close",
        "kr_nxt_close",
        "nasdaq_premarket_early",
        "nasdaq_regular_open",
        "nasdaq_regular_close",
        "nasdaq_afterhours_early",
    }
    assert by_id["kr_premarket_refresh"].trigger_time == "09:35"
    assert by_id["kr_regular_close"].trigger_time == "15:40"
    assert by_id["kr_nxt_close"].trigger_time == "20:05"
    assert by_id["nasdaq_premarket_early"].trigger_time == "04:15"
    assert by_id["nasdaq_regular_open"].trigger_time == "09:35"
    assert by_id["nasdaq_regular_close"].trigger_time == "16:05"
    assert by_id["nasdaq_afterhours_early"].trigger_time == "16:15"


def test_due_sessions_detects_kr_regular_close_in_kst_window():
    now = datetime.fromisoformat("2026-06-09T15:42:00+09:00").astimezone(timezone.utc)

    due = due_sessions(now, state={"runs": {}}, due_window_minutes=10)

    assert [spec.session_id for spec in due] == ["kr_regular_close"]


def test_due_sessions_detects_nasdaq_premarket_in_new_york_time():
    now = datetime.fromisoformat("2026-06-09T04:16:00-04:00").astimezone(timezone.utc)

    due = due_sessions(now, state={"runs": {}}, due_window_minutes=10)

    assert [spec.session_id for spec in due] == ["nasdaq_premarket_early"]


def test_due_sessions_uses_state_to_avoid_duplicate_same_local_date():
    now = datetime.fromisoformat("2026-06-09T04:16:00-04:00").astimezone(timezone.utc)
    state = {"runs": {"2026-06-09::nasdaq_premarket_early": {"status": "ok"}}}

    due = due_sessions(now, state=state, due_window_minutes=10)

    assert due == []


def test_command_plan_runs_session_scan_then_primary_daily_ops():
    by_id = {spec.session_id: spec for spec in SESSION_SPECS}

    kr_plan = build_command_plan(by_id["kr_regular_close"])
    nasdaq_plan = build_command_plan(by_id["nasdaq_regular_open"])

    assert [row["name"] for row in kr_plan] == ["kr_confirmed_scan", "primary_daily_ops"]
    assert "run_kr_daily_auto_scans.py" in " ".join(kr_plan[0]["argv"])
    assert kr_plan[1]["env"]["DAILY_OPS_MARKETS"] == "KOSPI,KOSDAQ,NASDAQ"
    assert kr_plan[1]["env"]["AG_PRIMARY_SESSION_ID"] == "kr_regular_close"
    assert [row["name"] for row in nasdaq_plan] == ["nasdaq_full_universe_scan", "primary_daily_ops"]
    assert "run_us_full_universe_research.py" in " ".join(nasdaq_plan[0]["argv"])
    assert nasdaq_plan[0]["env"]["AG_PRIMARY_SESSION_ID"] == "nasdaq_regular_open"
    assert nasdaq_plan[1]["env"]["AG_PRIMARY_SESSION_ID"] == "nasdaq_regular_open"
    assert nasdaq_plan[1]["env"]["AG_PRIMARY_SESSION_CUTOFF"] == "09:35 America/New_York"
    assert nasdaq_plan[1]["env"]["AG_DAILY_MODEL_FOUNDATION_GATE_ENABLE"] == "1"
    assert nasdaq_plan[1]["env"]["AG_NASDAQ_SWING_MODEL_ENABLE"] == "1"
    assert nasdaq_plan[1]["env"]["AG_NASDAQ_SWING_PANEL"] == "latest"
    assert nasdaq_plan[1]["env"]["AG_NASDAQ_SESSION_EDGE_PANEL"] == "latest"


def test_orchestrator_does_not_manufacture_the_session_edge_default():
    """이 단언은 예전에 `== "1"` 이었고, **틀린 동작을 고정하고 있었다**.

    호출자가 os.getenv(..., "1") 로 기본값을 만들어 주입하면 그것이 실질 스위치가 되어
    run_daily_ops.sh 의 기본값이 도달 불가해진다 — 2026-07-05 의 중지 선언이 no-op 이 된
    원인이 정확히 이것이고(trace-ops-flag-mismatch.md), `== "1"` 단언은 그 상태를 "정상"으로
    못박아 두고 있었다. 보장해야 할 것은 "켜져 있다"가 아니라 **"기본값을 여기서 만들지
    않는다"** 이다. 값 자체의 진실은 가드가 갖고, 그 동작은 test_daily_ops_flag_switch.py 가 본다.
    """
    by_id = {spec.session_id: spec for spec in SESSION_SPECS}
    env = build_command_plan(by_id["nasdaq_regular_open"])[1]["env"]

    assert "AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE" not in env, (
        "호출자가 다시 기본값을 주입한다 — 스크립트 쪽 기본값이 도달 불가해진다")


def test_operator_setting_reaches_the_child_without_injection(monkeypatch):
    """주입을 없앤 대가를 확인한다 — 없애도 운영자 설정은 자식에 도달해야 한다.

    _run_command 가 os.environ 을 복사한 뒤 delta 를 덮기 때문에 성립한다. 이 성질이
    깨지면 주입 제거가 곧 '끌 방법이 사라짐'이 되므로 반드시 고정해 둔다.
    """
    monkeypatch.setenv("AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE", "0")
    result = _run_command(
        {
            "name": "probe",
            "argv": ["/bin/bash", "-c", 'echo "flag=${AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE:-unset}"'],
            "env": {"UNRELATED_DELTA": "x"},
        },
        dry_run=False,
    )

    assert result["returncode"] == 0, result
    assert "flag=0" in result["stdout_tail"], result


def test_schedule_report_exposes_local_and_utc_next_times():
    report = schedule_report(datetime.fromisoformat("2026-06-09T00:00:00+00:00"))

    assert report["version"] == "primary_market_schedule_v1"
    assert report["primary_markets"] == ["KOSPI", "KOSDAQ", "NASDAQ"]
    assert len(report["sessions"]) == 7
    first = report["sessions"][0]
    assert "next_local" in first
    assert "next_utc" in first
    assert first["command_plan"]


def test_run_session_marks_optional_scan_failure_as_degraded(monkeypatch, tmp_path):
    by_id = {spec.session_id: spec for spec in SESSION_SPECS}

    def fake_run_command(command, *, dry_run):
        return {
            "name": command["name"],
            "required": command["required"],
            "returncode": 1 if command["name"] == "nasdaq_full_universe_scan" else 0,
        }

    monkeypatch.setattr(
        "multi_agent.tools.run_primary_market_session_ops._run_command",
        fake_run_command,
    )

    report = run_session(
        by_id["nasdaq_regular_open"],
        report_dir=tmp_path,
        now_utc=datetime.fromisoformat("2026-06-09T13:36:00+00:00"),
    )

    assert report["status"] == "degraded"
    assert report["optional_failure_count"] == 1
    assert report["required_failure_count"] == 0
