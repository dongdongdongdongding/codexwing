"""sentinel 판정기 (OD-37/38/39/40).

기준·재계산법·에스컬레이션 대상이 전부 적혀 있는데 **그걸 돌리는 것이 없었다.** §40 킬 기준이
산문으로만 적혀 두 달 뒤 우연히 발견됐고 `suspend_marker_broken` 은 아무도 읽지 않았다.

거래일 계산이 이 판정기의 급소다. 월~금을 분모로 쓰면 휴장일이 결석으로 잡히고, goblin 초판이
정확히 그렇게 틀렸다("정상 75~83%" → 셋을 고치면 1.000). 그래서 달력을 데이터에서 만든다.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sen = importlib.import_module("multi_agent.tools.report_sentinel_expectations")

TODAY = "2026-08-17"


def write_ledger(root: Path, rel: str, dates, date_key="date"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps({date_key: d, "x": 1}) + "\n" for d in dates), encoding="utf-8")
    return p


def build_repo(tmp_path, kospi=(), swing=(), kosdaq=(), nasdaq=(), b=()):
    L = sen.LANE_LEDGERS
    write_ledger(tmp_path, L["kospi_intraday_t5"][0], kospi)
    write_ledger(tmp_path, L["swing_candidate"][0], swing)
    write_ledger(tmp_path, L["kosdaq_intraday_t10"][0], kosdaq)
    write_ledger(tmp_path, L["nasdaq_session_tape"][0], nasdaq)
    write_ledger(tmp_path, L["b_primary_top3"][0], b, date_key="scan_date")
    return tmp_path


# ---------------------------------------------------------------------------
# 거래일 — 데이터에서 유래시킨다 (월~금 아님)
# ---------------------------------------------------------------------------

def test_calendar_comes_from_data_not_weekdays(tmp_path):
    """휴장일을 결석으로 세면 안 된다 — goblin 초판이 그렇게 틀렸다.

    08-14(금) 다음 거래일이 08-18(화)인 달력(08-17 대체휴일)을 준다.
    월~금 기준이면 08-17 이 결석으로 잡히지만, 데이터 유래면 애초에 거래일이 아니다.
    """
    days = ["2026-08-12", "2026-08-13", "2026-08-14", "2026-08-18"]
    build_repo(tmp_path, kospi=days, swing=days)
    cal = sen.trading_days(tmp_path, "KR", "2026-08-19")
    assert cal == days
    assert "2026-08-17" not in cal, "휴장일이 거래일로 잡혔다"


def test_calendar_excludes_today_as_incomplete(tmp_path):
    days = ["2026-08-13", "2026-08-14", "2026-08-17"]
    build_repo(tmp_path, kospi=days, swing=days)
    cal = sen.trading_days(tmp_path, "KR", "2026-08-17")
    assert cal == ["2026-08-13", "2026-08-14"], "당일(미완결)을 셌다"


def test_kr_calendar_is_the_union_of_two_lanes(tmp_path):
    """한 레인이 하루 쉬어도 달력이 줄면 안 된다 — union 이라야 한다."""
    build_repo(tmp_path, kospi=["2026-08-13"], swing=["2026-08-14"])
    assert sen.trading_days(tmp_path, "KR", "2026-08-17") == ["2026-08-13", "2026-08-14"]


# ---------------------------------------------------------------------------
# OD-34 발화 자격
# ---------------------------------------------------------------------------

def _cfg(window=10, floor=0.8, deadlines=None):
    return {"lane_firing_qualification": {
        "criterion": {"window_trading_days": window, "floor": floor},
        "active_deadlines": deadlines or []}}


def test_lane_firing_every_day_passes(tmp_path):
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, kosdaq=days)
    out = sen.check_firing_qualification(tmp_path, _cfg(), TODAY, {})
    kosdaq = [f for f in out if f["lane"] == "kosdaq_intraday_t10"][0]
    assert kosdaq["verdict"] == "PASS" and kosdaq["rate"] == 1.0


def test_lane_below_floor_fails_and_blocks_sizing(tmp_path):
    """미달은 경보가 아니라 사이징 차단이다(OD-7/OD-33)."""
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, kosdaq=days[:3])
    out = sen.check_firing_qualification(tmp_path, _cfg(), TODAY, {})
    k = [f for f in out if f["lane"] == "kosdaq_intraday_t10"][0]
    assert k["verdict"] == "FAIL" and k["severity"] == "alert"
    assert k["action"] == "block_sizing"


def test_new_lane_gets_grace(tmp_path):
    """첫 픽 이후 창 길이에 못 미치면 판정 보류 — 신규 레인 보호."""
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, kosdaq=days[-2:])
    k = [f for f in sen.check_firing_qualification(tmp_path, _cfg(), TODAY, {})
         if f["lane"] == "kosdaq_intraday_t10"][0]
    assert k["verdict"] == "GRACE"


def test_suspended_lane_is_exempt(tmp_path):
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, b=days[:2])
    out = sen.check_firing_qualification(tmp_path, _cfg(), TODAY,
                                         {"b_primary_top3": "2026-07-03"})
    b = [f for f in out if f["lane"] == "b_primary_top3"][0]
    assert b["verdict"] == "EXEMPT" and b["suspended_since"] == "2026-07-03"


def test_od39_stopped_without_marker_is_not_exempt(tmp_path):
    """OD-39: 면제를 주면 **고장이 정지로 위장된다.**"""
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, kosdaq=[])   # 픽 0건, 마커 없음
    k = [f for f in sen.check_firing_qualification(tmp_path, _cfg(), TODAY, {})
         if f["lane"] == "kosdaq_intraday_t10"][0]
    assert k["verdict"] == "FAIL", "마커 없이 멈춘 레인에 면제를 줬다"
    assert k["severity"] == "alert"


# ---------------------------------------------------------------------------
# OD-35 정지 기한 — 날짜를 박지 않는다
# ---------------------------------------------------------------------------

def _deadline_cfg(limit=20):
    return _cfg(deadlines=[{"id": "b_od35", "lanes": ["b_primary_top3"],
                            "suspended_since": "2026-07-03", "market": "KR",
                            "deadline_trading_days": limit}])


def test_deadline_counts_trading_days_not_calendar_days(tmp_path):
    days = [f"2026-07-{d:02d}" for d in range(1, 12)]      # 07-03 이후 8일
    build_repo(tmp_path, kospi=days, swing=days)
    d = sen.check_suspension_deadlines(tmp_path, _deadline_cfg(), TODAY)[0]
    assert d["elapsed_trading_days"] == 8
    assert d["verdict"] == "TRACKING" and d["remaining_trading_days"] == 12


def test_deadline_fires_only_when_exceeded(tmp_path):
    days = [f"2026-07-{d:02d}" for d in range(1, 27)]      # 07-03 이후 23일
    build_repo(tmp_path, kospi=days, swing=days)
    d = sen.check_suspension_deadlines(tmp_path, _deadline_cfg(20), TODAY)[0]
    assert d["verdict"] == "OVERDUE" and d["severity"] == "alert"


def test_a_market_holiday_pushes_the_deadline_out(tmp_path):
    """대체휴일이 끼면 기한이 하루 밀린다 — 날짜를 박으면 하루 일찍 울린다.

    운영자가 지적한 그 상황이다(2026-08-17 대체휴일이면 B 기한이 09-01 로).
    """
    full = [f"2026-07-{d:02d}" for d in range(1, 12)]
    holiday = [d for d in full if d != "2026-07-08"]        # 하루 휴장
    build_repo(tmp_path, kospi=full, swing=full)
    a = sen.check_suspension_deadlines(tmp_path, _deadline_cfg(), TODAY)[0]
    build_repo(tmp_path, kospi=holiday, swing=holiday)
    b = sen.check_suspension_deadlines(tmp_path, _deadline_cfg(), TODAY)[0]
    assert b["elapsed_trading_days"] == a["elapsed_trading_days"] - 1
    assert b["remaining_trading_days"] == a["remaining_trading_days"] + 1


def test_deadline_result_carries_no_hardcoded_date(tmp_path):
    days = [f"2026-07-{d:02d}" for d in range(1, 12)]
    build_repo(tmp_path, kospi=days, swing=days)
    d = sen.check_suspension_deadlines(tmp_path, _deadline_cfg(), TODAY)[0]
    assert "deadline_date" not in d, "기한을 날짜로 박았다 — 휴장일마다 틀어진다"
    assert d["remaining_trading_days"] >= 0


# ---------------------------------------------------------------------------
# 자격 전이 WARN
# ---------------------------------------------------------------------------

def test_pass_to_fail_transition_is_surfaced():
    findings = [{"check": "firing_qualification", "lane": "l", "verdict": "FAIL", "detail": "2/10"}]
    out = sen.check_qualification_transition(findings, {"firing_verdicts": {"l": "PASS"}})
    assert out and out[0]["verdict"] == "TRANSITION" and out[0]["severity"] == "warn"


def test_steady_fail_does_not_re_alert():
    """이미 FAIL 이던 레인이 매일 새 경보를 내면 아무도 안 본다."""
    findings = [{"check": "firing_qualification", "lane": "l", "verdict": "FAIL", "detail": "2/10"}]
    assert sen.check_qualification_transition(findings, {"firing_verdicts": {"l": "FAIL"}}) == []


# ---------------------------------------------------------------------------
# 신선도 — mtime 이 아니라 내용
# ---------------------------------------------------------------------------

def test_fresh_mtime_with_stale_content_is_caught(tmp_path):
    """매일 전량 재기록되는 원장은 mtime 이 늘 새것이다 — 내용으로 판정해야 한다."""
    days = [f"2026-07-{d:02d}" for d in range(1, 21)]
    build_repo(tmp_path, kospi=days, swing=days)
    rel = "runtime_state/reports/x_ledger.jsonl"
    write_ledger(tmp_path, rel, ["2026-07-01"])            # 내용은 20일 전
    cfg = {"artifacts": [{"path": rel, "severity": "critical", "producer_scheduled": True,
                          "content_max_age_days": 5, "mtime_is_meaningless": True}]}
    r = [f for f in sen.check_artifact_freshness(tmp_path, cfg, TODAY) if f.get("path") == rel][0]
    assert r["verdict"] == "STALE_CONTENT" and r["severity"] == "critical"
    assert r["max_date"] == "2026-07-01"


def test_retired_producer_stall_is_not_an_alert(tmp_path):
    """생산자가 은퇴했으면 정체가 정상이다."""
    build_repo(tmp_path, kospi=["2026-07-01"], swing=["2026-07-01"])
    rel = "runtime_state/reports/y_ledger.jsonl"
    write_ledger(tmp_path, rel, ["2026-01-01"])
    cfg = {"artifacts": [{"path": rel, "severity": "critical", "producer_scheduled": False}]}
    assert [f for f in sen.check_artifact_freshness(tmp_path, cfg, TODAY)
            if f.get("path") == rel] == []


def test_template_paths_are_not_reported_missing(tmp_path):
    """오탐이 쌓이면 경보 전체가 무시된다 — 템플릿 경로는 미검사로 드러낸다."""
    build_repo(tmp_path, kospi=["2026-07-01"], swing=["2026-07-01"])
    cfg = {"artifacts": [{"path": "~/research_cache/investor_estimate/{YYYYMM}.jsonl",
                          "severity": "critical", "producer_scheduled": True}]}
    out = sen.check_artifact_freshness(tmp_path, cfg, TODAY)
    assert not any(f.get("verdict") == "MISSING" for f in out), "템플릿 경로를 MISSING 으로 올렸다"
    assert any(f["verdict"] == "NOT_MACHINE_CHECKABLE" for f in out)


def test_prose_content_rules_are_surfaced_as_unrun(tmp_path):
    """산문 규칙을 조용히 통과시키면 OD-19 가 지적한 실패를 재생산한다."""
    build_repo(tmp_path, kospi=["2026-07-01"], swing=["2026-07-01"])
    rel = "runtime_state/reports/z.jsonl"
    write_ledger(tmp_path, rel, ["2026-07-01"])
    cfg = {"artifacts": [{"path": rel, "severity": "medium", "producer_scheduled": True,
                          "content_checks": [{"name": "max_date_recency", "rule": "5거래일 이내"}]}]}
    out = sen.check_artifact_freshness(tmp_path, cfg, TODAY)
    assert any(f["verdict"] == "PROSE_RULES_UNRUN" for f in out)


# ---------------------------------------------------------------------------
# OD-19 / 종료코드 / OD-40
# ---------------------------------------------------------------------------

def test_absent_kill_criteria_are_reported_not_assumed_clean():
    out = sen.check_prereg_kill_criteria({})
    assert out[0]["verdict"] == "NONE_REGISTERED" and out[0]["severity"] == "warn"


def test_registered_kill_criteria_are_counted():
    out = sen.check_prereg_kill_criteria({"prereg_kill_criteria": [{"id": "a"}, {"id": "b"}]})
    assert out[0]["verdict"] == "REGISTERED" and out[0]["count"] == 2


def test_run_returns_escalations_and_worst_severity(tmp_path):
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, kosdaq=days[:3])
    rep = sen.run(tmp_path, _cfg(), TODAY, {})
    assert rep["worst_severity"] in ("alert", "critical")
    assert any(e["check"] == "firing_qualification" for e in rep["escalations"])


def test_clean_repo_produces_no_escalation(tmp_path):
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, kosdaq=days, nasdaq=days, b=days)
    rep = sen.run(tmp_path, _cfg(), TODAY, {})
    firing = [f for f in rep["findings"] if f["check"] == "firing_qualification"]
    assert all(f["verdict"] in ("PASS", "GRACE", "EXEMPT") for f in firing), firing


def test_config_lives_inside_the_repo(tmp_path):
    """OD-40: 리포 밖 절대경로에 의존하면 다른 클론·CI 에서 깨진다."""
    assert sen.CONFIG.exists()
    assert sen.CONFIG.is_relative_to(REPO)
    body = sen.CONFIG.read_text(encoding="utf-8")
    assert "\nrepo_root: /Users/" not in body, "리포 밖 절대경로가 활성 키로 남아 있다"


def test_escalation_markdown_is_written_for_durability(tmp_path):
    """에스컬레이션은 파일로 남긴다 — 메시지는 승인 대기로 만료돼 사라진다."""
    rep = {"today": TODAY, "generated_at": "t", "worst_severity": "alert",
           "trading_days": {"KR": 10, "US": 10},
           "escalations": [{"check": "firing_qualification", "lane": "l",
                            "verdict": "FAIL", "detail": "2/10"}],
           "findings": [{"check": "firing_qualification", "lane": "l",
                         "verdict": "FAIL", "severity": "alert", "detail": "2/10"}]}
    md = sen._escalation_markdown(rep)
    assert "FAIL" in md and "l" in md and "sentinel 에스컬레이션" in md


# ---------------------------------------------------------------------------
# OD-44 — 이 산출이 발행 경로의 입력이 된다 (fail-closed 계약)
# ---------------------------------------------------------------------------

def test_output_carries_freshness_evidence(tmp_path):
    """소비자가 '낡았다'를 판단할 수 없으면 fail-closed 가 성립하지 않는다."""
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, nasdaq=days)
    rep = sen.run(tmp_path, _cfg(), TODAY, {})
    assert rep["schema_version"] == 1
    fr = rep["freshness"]
    assert fr["max_age_hours"] > 0
    assert fr["last_trading_day"]["KR"] == days[-1]
    assert "fail-closed" in fr["contract"]


def test_lane_sizing_is_explicit_not_derived(tmp_path):
    """소비자가 findings 를 재해석하게 두면 해석이 갈린다 — 허용 여부를 명시한다."""
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, kosdaq=days[:3], nasdaq=days)
    rep = sen.run(tmp_path, _cfg(), TODAY, {})
    ls = rep["lane_sizing"]
    assert ls["kosdaq_intraday_t10"]["allowed"] is False
    assert ls["kosdaq_intraday_t10"]["verdict"] == "FAIL"
    assert ls["kospi_intraday_t5"]["allowed"] is True


def test_exempt_and_grace_are_allowed_but_fail_is_not(tmp_path):
    """면제는 **게이트 산출의 suspended_since 에서만** 나온다 — 임의 입력이 아니다."""
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, b=days[:2], nasdaq=days)
    gate_out = tmp_path / "runtime_state/reports/validation/research_recursion_gate_latest.json"
    gate_out.parent.mkdir(parents=True, exist_ok=True)
    gate_out.write_text(json.dumps({"results": [
        {"lane": "b_primary_top3", "suspended_since": "2026-07-03"},
        {"lane": "b_all_top10", "suspended_since": None}]}), encoding="utf-8")

    rep = sen.run(tmp_path, _cfg(), TODAY, {})

    assert rep["lane_sizing"]["b_primary_top3"]["allowed"] is True     # EXEMPT
    assert rep["lane_sizing"]["b_all_top10"]["allowed"] is False       # 마커 없음 → OD-39


def test_missing_lane_must_be_read_as_disallowed(tmp_path):
    """지도에 없는 레인이 통과가 되면 fail-closed 가 깨진다 — 계약에 명시돼 있어야 한다."""
    days = [f"2026-07-{d:02d}" for d in range(1, 16)]
    build_repo(tmp_path, kospi=days, swing=days, nasdaq=days)
    rep = sen.run(tmp_path, _cfg(), TODAY, {})
    assert "없는 레인도 불허" in rep["freshness"]["contract"]
