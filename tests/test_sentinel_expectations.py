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


def test_registered_without_evaluator_is_not_green(tmp_path):
    """OD-47: 등록만 하면 판정이 초록인데 검사가 없는 상태가 된다 — 그걸 만들지 않는다."""
    out = sen.check_prereg_kill_criteria(
        {"prereg_kill_criteria": [{"id": "a"}, {"id": "b", "check": {"type": "unknown"}}]}, tmp_path)
    assert [f["verdict"] for f in out] == ["NOT_EVALUATED", "NOT_EVALUATED"]
    assert all(f["severity"] == "warn" for f in out)


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


# ---------------------------------------------------------------------------
# OD-49 — 면제에 기한이 있다
# ---------------------------------------------------------------------------

def test_expired_suspension_loses_its_exemption(tmp_path):
    """기한 검사가 없으면 정지 레인이 **무기한 면제**로 남는다 — 실제로 그 상태였다."""
    days = [f"2026-07-{d:02d}" for d in range(1, 27)]        # 07-03 이후 23거래일
    build_repo(tmp_path, kospi=days, swing=days, b=days[:2], nasdaq=days)
    gate_out = tmp_path / "runtime_state/reports/validation/research_recursion_gate_latest.json"
    gate_out.parent.mkdir(parents=True, exist_ok=True)
    gate_out.write_text(json.dumps({"results": [
        {"lane": "b_primary_top3", "suspended_since": "2026-07-03"}]}), encoding="utf-8")
    cfg = _cfg(deadlines=[{"id": "b", "lanes": ["b_primary_top3"], "market": "KR",
                           "suspended_since": "2026-07-03", "deadline_trading_days": 20}])

    rep = sen.run(tmp_path, cfg, TODAY, {})

    b = [f for f in rep["findings"]
         if f["check"] == "firing_qualification" and f["lane"] == "b_primary_top3"][0]
    assert b["verdict"] == "SUSPENSION_EXPIRED", "기한을 넘겼는데 면제로 남았다"
    assert b["severity"] == "alert" and b["action"] == "block_sizing"
    assert rep["lane_sizing"]["b_primary_top3"]["allowed"] is False


def test_suspension_within_deadline_is_still_exempt(tmp_path):
    days = [f"2026-07-{d:02d}" for d in range(1, 12)]        # 07-03 이후 8거래일
    build_repo(tmp_path, kospi=days, swing=days, b=days[:2], nasdaq=days)
    gate_out = tmp_path / "runtime_state/reports/validation/research_recursion_gate_latest.json"
    gate_out.parent.mkdir(parents=True, exist_ok=True)
    gate_out.write_text(json.dumps({"results": [
        {"lane": "b_primary_top3", "suspended_since": "2026-07-03"}]}), encoding="utf-8")
    cfg = _cfg(deadlines=[{"id": "b", "lanes": ["b_primary_top3"], "market": "KR",
                           "suspended_since": "2026-07-03", "deadline_trading_days": 20}])
    rep = sen.run(tmp_path, cfg, TODAY, {})
    b = [f for f in rep["findings"]
         if f["check"] == "firing_qualification" and f["lane"] == "b_primary_top3"][0]
    assert b["verdict"] == "EXEMPT"
    assert rep["lane_sizing"]["b_primary_top3"]["allowed"] is True


def test_deadline_is_checked_inside_the_checker_not_the_publish_path():
    """OD-49: 발행 경로에 되살리면 두 곳이 판단하게 되어 OD-44 가 막으려는 형태가 된다."""
    assert hasattr(sen, "expired_suspension_lanes")
    import inspect
    src = inspect.getsource(sen.check_firing_qualification)
    assert "expired" in src and "SUSPENSION_EXPIRED" in src


# ---------------------------------------------------------------------------
# OD-50 — 노후 문턱은 산출이 싣는다
# ---------------------------------------------------------------------------

def test_max_age_hours_is_always_present(tmp_path):
    """소비자가 자기 기본값을 갖지 않으려면 이 필드가 **항상** 실려야 한다."""
    for build in (lambda: build_repo(tmp_path),                       # 빈 리포
                  lambda: build_repo(tmp_path, kospi=["2026-07-01"], swing=["2026-07-01"])):
        build()
        rep = sen.run(tmp_path, _cfg(), TODAY, {})
        assert rep["freshness"]["max_age_hours"] == sen.MAX_AGE_HOURS
        assert isinstance(rep["freshness"]["max_age_hours"], (int, float))


# ---------------------------------------------------------------------------
# OD-47 — 술어 평가기
# ---------------------------------------------------------------------------

def _kc(root, item):
    return sen.check_prereg_kill_criteria({"prereg_kill_criteria": [item]}, root)[0]


def test_kill_enforced_fires_when_dead_board_resumes(tmp_path):
    rel = "runtime_state/reports/experimental/kr_ranking_shadow_ledger.jsonl"
    write_ledger(tmp_path, rel, ["2026-08-14", "2026-08-18"])       # 킬 이후 행 존재
    r = _kc(tmp_path, {"id": "k", "status": "active", "severity": "critical",
                       "check": {"type": "no_rows_after_date", "ledger": rel, "after": "2026-08-16"}})
    assert r["verdict"] == "FIRED" and r["severity"] == "critical"


def test_kill_enforced_is_ok_while_board_stays_dead(tmp_path):
    rel = "runtime_state/reports/experimental/kr_ranking_shadow_ledger.jsonl"
    write_ledger(tmp_path, rel, ["2026-08-14"])
    assert _kc(tmp_path, {"id": "k", "status": "active",
                          "check": {"type": "no_rows_after_date", "ledger": rel,
                                    "after": "2026-08-16"}})["verdict"] == "OK"


def test_field_min_catches_universe_floor_violation(tmp_path):
    rel = "l.jsonl"
    (tmp_path / rel).write_text("".join(json.dumps({"liq_eok": v}) + "\n" for v in (30.0, 12.5)),
                                encoding="utf-8")
    r = _kc(tmp_path, {"id": "u", "status": "active",
                       "check": {"type": "field_min", "ledger": rel, "field": "liq_eok", "min": 30}})
    assert r["verdict"] == "FIRED" and r["observed"]["violations"] == 1


def test_symbol_absent_check_reports_undecided_when_file_missing(tmp_path):
    """검사 대상 파일이 없으면 **통과가 아니라 판정 불가**다."""
    r = _kc(tmp_path, {"id": "s", "status": "active",
                       "check": {"type": "symbol_absent_in_file", "file": "nope.py", "symbol": "x"}})
    assert r["verdict"] == "UNDECIDED" and r["severity"] == "warn"


def test_monotonicity_reproduces_the_audit_numbers(tmp_path):
    """심도 단조성 — 상위 픽이 하위보다 못하면 발동(OD-3 와 같은 귀속 검사)."""
    rel = "l.jsonl"
    rows = []
    for d in range(1, 11):
        date = f"2026-08-{d:02d}"
        for rk in range(1, 21):
            # 순위가 낮을수록(1위) 수익이 나쁨 → corr 양수 + depth 음수 = 발동
            rows.append({"date": date, "market": "KOSPI", "rank": rk, "fwd5_cc": rk * 0.5})
    (tmp_path / rel).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    r = _kc(tmp_path, {"id": "m", "status": "active",
                       "check": {"type": "rank_return_monotonicity", "ledger": rel,
                                 "min_sample": {"scored_rows_per_market": 100, "days": 4}}})
    assert r["verdict"] == "FIRED"
    assert r["observed"]["KOSPI"]["corr"] > 0
    assert r["observed"]["KOSPI"]["top10_minus_bottom10"] < 0


def test_monotonicity_is_undecided_below_min_sample(tmp_path):
    """표본 하한 미달을 통과로 읽으면 0건이 집행의 증거가 된다."""
    rel = "l.jsonl"
    rows = [{"date": "2026-08-01", "market": "KOSPI", "rank": i, "fwd5_cc": 1.0} for i in range(1, 6)]
    (tmp_path / rel).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    r = _kc(tmp_path, {"id": "m", "status": "active",
                       "check": {"type": "rank_return_monotonicity", "ledger": rel,
                                 "min_sample": {"scored_rows_per_market": 100, "days": 4}}})
    assert r["verdict"] == "UNDECIDED"


def test_blocked_criterion_is_not_evaluated(tmp_path):
    r = _kc(tmp_path, {"id": "b", "status": "blocked", "blocked_by": "suspension",
                       "unblock_when": "정지 해제 시"})
    assert r["verdict"] == "BLOCKED" and r["severity"] == "info"


def test_narrowing_flag_travels_with_the_item(tmp_path):
    """술어가 원문을 좁힌 사실을 항목이 들고 다녀야 한다(스키마 필수 필드)."""
    rel = "l.jsonl"
    write_ledger(tmp_path, rel, ["2026-08-14"])
    r = _kc(tmp_path, {"id": "k", "status": "active", "narrowing": "원문은 더 넓다",
                       "check": {"type": "no_rows_after_date", "ledger": rel, "after": "2026-08-16"}})
    assert r["narrowing"] is True


def test_registered_criteria_all_have_narrowing_field():
    """등록된 전 항목이 narrowing 을 들고 있어야 한다 — 좁힌 사실이 사라지면 안 된다."""
    import yaml
    cfg = yaml.safe_load(sen.CONFIG.read_text(encoding="utf-8"))
    missing = [c.get("id") for c in cfg["prereg_kill_criteria"] if not c.get("narrowing")]
    assert not missing, f"narrowing 없는 항목: {missing}"


def test_one_shot_gates_are_kept_apart_from_standing_predicates():
    """OD-48: 일회형을 매일 술어로 박으면 매일 같은 답을 내는 가짜 감시가 된다."""
    import yaml
    cfg = yaml.safe_load(sen.CONFIG.read_text(encoding="utf-8"))
    standing_ids = {c["id"] for c in cfg["prereg_kill_criteria"]}
    gates = cfg.get("prereg_track_gates")
    assert gates, "트랙 종료 관문 섹션이 없다"
    dupes = [g["id"] for g in gates
             if g["id"] in standing_ids and g.get("status") != "see_standing_registry"]
    assert not dupes, f"상시형과 중복 등록: {dupes}"


# ---------------------------------------------------------------------------
# OD-48/56 — 트랙 종료 관문: 연구 술어가 아니라 판정 채무만 본다
# ---------------------------------------------------------------------------

def _gate(root, item, extra=None):
    cfg = {"prereg_track_gates": [item]}
    cfg.update(extra or {})
    return sen.check_prereg_track_gates(cfg, root)[0]


def test_gate_fires_when_precondition_met_and_no_record(tmp_path):
    """관문이 보는 것은 '선행조건 충족 AND 판정 기록 부재' 뿐이다."""
    r = _gate(tmp_path, {"id": "g", "status": "overdue", "severity": "warn",
                         "precondition": {"desc": "데이터 찼다", "met": True},
                         "adjudication_record": "RESEARCH_LOG.md"})
    assert r["verdict"] == "OVERDUE" and r["severity"] == "warn"
    assert "기록이 없다" in r["detail"]


def test_gate_is_blocked_while_precondition_unmet(tmp_path):
    """선행조건 미충족은 발동이 아니다 — 판정할 수 있게 되지도 않았다."""
    r = _gate(tmp_path, {"id": "g", "status": "blocked",
                         "precondition": {"desc": "분봉 축적", "met": False}})
    assert r["verdict"] == "BLOCKED" and r["severity"] == "info"


def test_gate_closes_when_adjudication_is_recorded(tmp_path):
    """판정 원장에 한 줄이 들어오면 닫힌다 — **이 자리가 §40 이 놓친 것**이다."""
    rec = tmp_path / "runtime_state/long_term/ops/adjudications.jsonl"
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(json.dumps({"gate_id": "g", "adjudicated_at": "2026-08-20",
                               "outcome": "기각", "where": "RESEARCH_LOG §42"}) + "\n",
                   encoding="utf-8")
    r = _gate(tmp_path, {"id": "g", "status": "overdue",
                         "precondition": {"met": True}})
    assert r["verdict"] == "CLOSED" and "2026-08-20" in r["detail"]


def test_gate_does_not_evaluate_the_research_predicate(tmp_path):
    """연간 기여 <1%p 같은 걸 매일 계산하는 척하면 가짜 감시가 된다.

    관문 결과는 킬 기준 원문을 **실어 나르기만** 한다.
    """
    crit = "연간 기여 <1%p 면 조연 등급"
    r = _gate(tmp_path, {"id": "g", "status": "overdue", "precondition": {"met": True},
                         "criterion_at_termination": crit})
    assert r["criterion_at_termination"] == crit
    assert "verdict" in r and r["verdict"] == "OVERDUE"      # 기준을 평가한 흔적이 없다
    assert "fired" not in r


def test_declared_precondition_is_marked_unverified(tmp_path):
    """선언을 조용히 사실로 승격시키지 않는다."""
    r = _gate(tmp_path, {"id": "g", "status": "overdue", "precondition": {"met": True}})
    assert r["precondition_verified"] is False


def test_precondition_can_be_machine_verified(tmp_path):
    rel = "runtime_state/x.jsonl"
    write_ledger(tmp_path, rel, ["2026-08-01"] * 5)
    ok = _gate(tmp_path, {"id": "g", "status": "overdue",
                          "precondition": {"check": {"type": "min_rows", "file": rel, "min": 3}}})
    short = _gate(tmp_path, {"id": "g", "status": "overdue",
                             "precondition": {"check": {"type": "min_rows", "file": rel, "min": 50}}})
    assert ok["verdict"] == "OVERDUE" and ok["precondition_verified"] is True
    assert short["verdict"] == "BLOCKED" and short["precondition_verified"] is True


def test_gate_referring_to_standing_registry_is_not_double_judged(tmp_path):
    r = _gate(tmp_path, {"id": "g", "status": "see_standing_registry", "ref": "x"})
    assert r["verdict"] == "IN_STANDING_REGISTRY" and r["severity"] == "info"


def test_registered_gates_match_the_confirmed_dispositions():
    """OD-53/54 확정값이 등록에 반영돼 있어야 한다."""
    import yaml
    cfg = yaml.safe_load(sen.CONFIG.read_text(encoding="utf-8"))
    g = {x["id"]: x for x in cfg["prereg_track_gates"]}
    assert g["mech_flow_h3_effective_day_intraday"]["status"] == "overdue"   # OD-54
    t1 = g["autopsy_t1_exit_contract_repair"]
    assert t1["importance_floor_pp"] == 0.3                                  # OD-53
    assert "0.3pp" in t1["criterion_at_termination"]
    assert g["mech_flow_h4_blockdeal_overhang"]["status"] == "overdue"
    assert g["autopsy_t2_b_lane_death"]["status"] == "see_standing_registry"


def test_every_gate_declares_where_the_verdict_gets_written():
    """adjudication_record 가 없으면 '판정했다'를 기계가 확인할 길이 없다."""
    import yaml
    cfg = yaml.safe_load(sen.CONFIG.read_text(encoding="utf-8"))
    missing = [g["id"] for g in cfg["prereg_track_gates"]
               if g.get("status") in (None, "overdue", "blocked") and not g.get("adjudication_record")]
    assert not missing, f"판정 기록처 미선언: {missing}"


# ---------------------------------------------------------------------------
# OD-51 — 재개봉 조건은 킬 기준의 거울상
# ---------------------------------------------------------------------------

def test_reopen_blocked_while_any_condition_unmet():
    """'표본 쌓였으니 다시 켜자' 를 막는 것이 이 등록의 존재 이유다."""
    cfg = {"prereg_reopen_conditions": [{"id": "r", "applies_to": "lane", "conditions": [
        {"id": "R1", "met": False}, {"id": "R2", "met": True}]}]}
    r = sen.check_prereg_reopen_conditions(cfg)[0]
    assert r["verdict"] == "NOT_REOPENABLE" and r["unmet"] == ["R1"]


def test_reopen_ready_is_review_not_publication():
    cfg = {"prereg_reopen_conditions": [{"id": "r", "conditions": [{"id": "R1", "met": True}]}]}
    r = sen.check_prereg_reopen_conditions(cfg)[0]
    assert r["verdict"] == "READY_FOR_REVIEW"
    assert "발행 재개 아님" in r["detail"]


def test_method_requirements_are_not_counted_as_unmet():
    """R4(플라시보 동반)는 방법 요건이라 술어화 대상이 아니다 — 미충족으로 세면 영원히 안 열린다."""
    cfg = {"prereg_reopen_conditions": [{"id": "r", "conditions": [
        {"id": "R1", "met": True},
        {"id": "R4", "machine_readable": False}]}]}
    r = sen.check_prereg_reopen_conditions(cfg)[0]
    assert r["verdict"] == "READY_FOR_REVIEW" and r["manual_only"] == ["R4"]


def test_registered_reopen_keeps_r1_as_the_blocking_condition():
    """R1 미충족 상태의 축적은 재개봉을 영원히 만족시키지 못한다(OD-51)."""
    import yaml
    cfg = yaml.safe_load(sen.CONFIG.read_text(encoding="utf-8"))
    conds = {c["id"]: c for c in cfg["prereg_reopen_conditions"][0]["conditions"]}
    assert conds["R1"]["met"] is False
    assert conds["R4"].get("machine_readable") is False
    out = sen.check_prereg_reopen_conditions(cfg)[0]
    assert out["verdict"] == "NOT_REOPENABLE" and "R1" in out["unmet"]


def test_kill_after_date_counts_rows_not_distinct_dates(tmp_path):
    """축소 보고 금지 — 한 날에 100행이 들어오면 100행으로 보고해야 한다.

    라이브에서 실제로 틀렸다: 2026-08-18/19 에 200행이 들어왔는데 서로 다른 날짜 2개를
    세어 "행 2건" 으로 냈다. 안전 판정기가 위반을 100배 줄여 보고하면 급한 일이
    급해 보이지 않는다 — 이 리포에서 가장 비쌌던 실패 형태 그대로다.
    """
    from multi_agent.tools.report_sentinel_expectations import _kc_no_rows_after

    led = tmp_path / "runtime_state" / "reports" / "experimental" / "dead.jsonl"
    led.parent.mkdir(parents=True, exist_ok=True)
    rows = ([{"date": "2026-08-18", "t": "A%d" % i} for i in range(100)]
            + [{"date": "2026-08-19", "t": "B%d" % i} for i in range(100)]
            + [{"date": "2026-08-10", "t": "old"}])
    led.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    got = _kc_no_rows_after(tmp_path, {
        "ledger": "runtime_state/reports/experimental/dead.jsonl",
        "after": "2026-08-16",
    })

    assert got["fired"] is True
    assert got["observed"]["rows_after"] == 200, "행이 아니라 날짜를 세면 200 이 2 로 줄어든다"
    assert got["observed"]["dates_after"] == 2
    assert "200" in got["detail"], "머리글에 행 수가 있어야 한다: " + got["detail"]
    assert got["observed"]["first_date_after"] == "2026-08-18"


def test_kill_after_date_stays_quiet_when_nothing_new(tmp_path):
    """오탐을 만들지 않는다 — 킬 이전 행만 있으면 조용해야 한다."""
    from multi_agent.tools.report_sentinel_expectations import _kc_no_rows_after

    led = tmp_path / "runtime_state" / "reports" / "experimental" / "dead.jsonl"
    led.parent.mkdir(parents=True, exist_ok=True)
    led.write_text(json.dumps({"date": "2026-08-10"}), encoding="utf-8")

    got = _kc_no_rows_after(tmp_path, {
        "ledger": "runtime_state/reports/experimental/dead.jsonl",
        "after": "2026-08-16",
    })
    assert got["fired"] is False
    assert got["observed"]["rows_after"] == 0
