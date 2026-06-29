from __future__ import annotations

from datetime import datetime, timezone

from multi_agent.tools.run_primary_market_session_ops import (
    PRIMARY_MARKETS,
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
    assert nasdaq_plan[1]["env"]["AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE"] == "1"
    assert nasdaq_plan[1]["env"]["AG_NASDAQ_SESSION_EDGE_PANEL"] == "latest"


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
