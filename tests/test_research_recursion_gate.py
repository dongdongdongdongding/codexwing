"""재귀 연구 게이트 — EXCEED 승격 3조건 강제(F3)와 승률 축(F5) 회귀.

근거: orca/reports/audit-gate.md F3·F5 (cardinalfish, 2026-08-14).

F3 — 승격 3조건(①성숙시차 지연표본 재확인 ②n≥100 ③EXCEED 10영업일 유지)이 note 문자열로만
존재했다. verdict 는 n 과 무관하게 EXCEED 였고 승격 티켓도 그대로 나갔으며, `verdict_since` 는
기록만 될 뿐 **리포 전체에 읽는 코드가 없었다**. §36 whipsaw(EXCEED 5영업일 뒤 DEGRADE)를
막으라고 만든 래칫이 사람이 그냥 우회할 수 있는 텍스트였다.

F5 — evaluate() 가 expect_ev 만 비교하고 expect_win 은 어떤 분기에도 없었다.

테스트는 전부 합성 원장(tmp_path)으로 돈다. 실 원장은 gitignore 라 다른 클론에서 깨진다.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
gate = importlib.import_module("multi_agent.tools.report_research_recursion_gate")

TODAY = "2026-08-14"


def bdays_before(anchor: str, n: int) -> str:
    return str(np.busday_offset(np.datetime64(anchor), -n, roll="backward"))


def write_ledger(path: Path, vals, dates=None, date_key="date", extra=None) -> Path:
    """값 리스트로 합성 원장 한 개. dates 미지정이면 anchor 에서 하루씩 거슬러 배치."""
    if dates is None:
        dates = [bdays_before(TODAY, len(vals) - i) for i in range(len(vals))]
    with path.open("w", encoding="utf-8") as fh:
        for v, d in zip(vals, dates):
            row = {"ret": v, date_key: d}
            row.update(extra or {})
            fh.write(json.dumps(row) + "\n")
    return path


def cfg_for(path: Path, expect_ev=1.0, expect_win=60.0, n_min=20, **kw):
    c = {"ledger": path, "field": "ret", "cost": 0.0, "expect_ev": expect_ev,
         "expect_win": expect_win, "n_min": n_min, "basis": "테스트",
         "publish_scope": gate.WHOLE_LEDGER}
    c.update(kw)
    return c


def state_for(verdict: str, since: str):
    return {"lane": {"verdict": verdict, "since": since}}


# ---------------------------------------------------------------------------
# F3 — 승격 3조건
# ---------------------------------------------------------------------------

def test_exceed_with_small_n_is_pending_not_promotable(tmp_path):
    """②n≥100 미달: 예전에는 verdict=EXCEED 라 승격 티켓이 그대로 나갔다."""
    led = write_ledger(tmp_path / "l.jsonl", [3.0] * 40)      # 기대 1.0 의 3배
    r = gate.evaluate("lane", cfg_for(led), state_for("EXCEED_PENDING", bdays_before(TODAY, 30)), TODAY)
    assert r["verdict"] == "EXCEED_PENDING", r
    assert r["exceed_gate"]["n"] is False
    assert r["exceed_gate"]["n_have"] == 40


def test_exceed_hold_days_are_actually_counted(tmp_path):
    """③EXCEED 10영업일 유지 — verdict_since 를 실제로 소비하는지.

    F3 의 핵심. 같은 표본·같은 코드에서 **since 만** 바꾸면 판정이 갈려야 한다.
    예전에는 verdict_since 를 읽는 코드가 리포에 존재하지 않았다.
    """
    led = write_ledger(tmp_path / "l.jsonl", [3.0] * 120)
    fresh = gate.evaluate("lane", cfg_for(led), state_for("EXCEED_PENDING", bdays_before(TODAY, 3)), TODAY)
    aged = gate.evaluate("lane", cfg_for(led), state_for("EXCEED_PENDING", bdays_before(TODAY, 10)), TODAY)
    assert fresh["verdict"] == "EXCEED_PENDING"
    assert fresh["exceed_gate"]["hold"] is False and fresh["exceed_gate"]["hold_bdays"] == 3
    assert aged["verdict"] == "EXCEED_ELIGIBLE"
    assert aged["exceed_gate"]["hold"] is True and aged["exceed_gate"]["hold_bdays"] == 10


def test_first_ever_exceed_starts_the_clock_at_zero(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [3.0] * 120)
    r = gate.evaluate("lane", cfg_for(led), {}, TODAY)
    assert r["verdict"] == "EXCEED_PENDING"
    assert r["verdict_since"] == TODAY
    assert r["exceed_gate"]["hold_bdays"] == 0


def test_pending_to_eligible_does_not_reset_the_clock(tmp_path):
    """PENDING→ELIGIBLE 에서 since 가 리셋되면 10일을 영원히 못 채우고 플립플롭한다."""
    led = write_ledger(tmp_path / "l.jsonl", [3.0] * 120)
    since = bdays_before(TODAY, 12)
    elig = gate.evaluate("lane", cfg_for(led), state_for("EXCEED_PENDING", since), TODAY)
    assert elig["verdict"] == "EXCEED_ELIGIBLE"
    assert elig["verdict_since"] == since, "EXCEED 계열 안에서 since 가 리셋됐다"
    # 다음날에도 유지돼야 한다 (리셋됐다면 여기서 PENDING 으로 되돌아간다)
    nxt = str(np.busday_offset(np.datetime64(TODAY), 1, roll="forward"))
    assert gate.evaluate("lane", cfg_for(led), state_for("EXCEED_ELIGIBLE", since), nxt)["verdict"] \
        == "EXCEED_ELIGIBLE"


def test_clock_resets_when_leaving_the_exceed_family(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [3.0] * 120)
    r = gate.evaluate("lane", cfg_for(led), state_for("DEGRADE", bdays_before(TODAY, 40)), TODAY)
    assert r["verdict"] == "EXCEED_PENDING"
    assert r["verdict_since"] == TODAY, "DEGRADE→EXCEED 인데 옛 시계를 물려받았다"


def test_maturity_lag_recheck_blocks_promotion_driven_by_fresh_rows(tmp_path):
    """①성숙시차 재확인: 최근 5영업일을 빼면 기대 초과가 사라지는 표본은 승격 불가.

    §36 whipsaw 의 형태 — 갓 채점된 최신분이 EXCEED 를 만들고, 성숙하며 무너졌다.
    """
    old = [0.5] * 110          # 기대 1.0 의 1.5배(=1.5) 미만 → 지연표본만으로는 EXCEED 아님
    fresh = [40.0] * 12        # 최신 5영업일에 몰린 폭발적 표본
    dates = ([bdays_before(TODAY, 20 + i % 40) for i in range(len(old))]
             + [bdays_before(TODAY, i % 4) for i in range(len(fresh))])
    led = write_ledger(tmp_path / "l.jsonl", old + fresh, dates=dates)
    r = gate.evaluate("lane", cfg_for(led), state_for("EXCEED_PENDING", bdays_before(TODAY, 30)), TODAY)
    assert r["verdict"] == "EXCEED_PENDING"
    assert r["exceed_gate"]["lag"] is False
    assert r["exceed_gate"]["lag_ev"] is not None and r["exceed_gate"]["lag_ev"] < r["fwd_ev"]


def test_maturity_lag_recheck_passes_when_edge_is_broad(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [3.0] * 120)
    r = gate.evaluate("lane", cfg_for(led), state_for("EXCEED_PENDING", bdays_before(TODAY, 15)), TODAY)
    assert r["exceed_gate"]["lag"] is True
    assert r["verdict"] == "EXCEED_ELIGIBLE"


def test_lane_without_usable_dates_cannot_be_promoted(tmp_path):
    """날짜를 못 읽으면 성숙시차 재확인이 불가능 → 보수적으로 승격 차단."""
    led = tmp_path / "l.jsonl"
    led.write_text("".join(json.dumps({"ret": 3.0}) + "\n" for _ in range(120)), encoding="utf-8")
    r = gate.evaluate("lane", cfg_for(led), state_for("EXCEED_PENDING", bdays_before(TODAY, 30)), TODAY)
    assert r["verdict"] == "EXCEED_PENDING"
    assert r["exceed_gate"]["lag"] is False


def test_alternate_date_key_and_compact_format(tmp_path):
    """b_shadow 는 scan_date, kosdaq 원장은 YYYYMMDD 도 쓴다."""
    led = write_ledger(tmp_path / "l.jsonl", [3.0] * 120, date_key="scan_date",
                       dates=[bdays_before(TODAY, 120 - i).replace("-", "") for i in range(120)])
    r = gate.evaluate("lane", cfg_for(led, date_field="scan_date"),
                      state_for("EXCEED_PENDING", bdays_before(TODAY, 15)), TODAY)
    assert r["exceed_gate"]["lag"] is True, r["exceed_gate"]


# ---------------------------------------------------------------------------
# F5 — 승률 축
# ---------------------------------------------------------------------------

def test_win_shortfall_is_measured_and_reported(tmp_path):
    """kospi_intraday_t5 형태: EV 는 통과하는데 승률이 크게 미달."""
    vals = [2.0] * 69 + [-2.0] * 31          # win 69% (net>0.3 기준)
    led = write_ledger(tmp_path / "l.jsonl", vals)
    r = gate.evaluate("lane", cfg_for(led, expect_ev=0.5, expect_win=92.0), {}, TODAY)
    assert r["win_verdict"] == "SHORT"
    assert r["fwd_win"] == pytest.approx(69.0, abs=0.1)
    assert r["win_shortfall_pp"] == pytest.approx(23.0, abs=0.1)
    assert r["fwd_win_ci"][1] < 92.0


def test_win_shortfall_blocks_exceed_promotion(tmp_path):
    """추가 조건으로서의 승률 — 3조건을 다 채워도 승률 미달이면 ELIGIBLE 이 아니다."""
    vals = ([12.0] * 70 + [-6.0] * 50) * 1   # EV 강함, 승률 58.3%
    led = write_ledger(tmp_path / "l.jsonl", vals)
    r = gate.evaluate("lane", cfg_for(led, expect_ev=1.0, expect_win=95.0),
                      state_for("EXCEED_PENDING", bdays_before(TODAY, 30)), TODAY)
    assert r["exceed_gate"]["n"] is True and r["exceed_gate"]["hold"] is True
    assert r["exceed_gate"]["win"] is False
    assert r["verdict"] == "EXCEED_PENDING", "승률 미달인데 승격 가능으로 판정됐다"


def test_win_shortfall_never_forces_degrade(tmp_path):
    """승률 미달만으로는 강등하지 않는다 — expect_win 의 근거가 레인마다 불균질(F4)하고,
    DEGRADE 는 발행 제외까지 끌고 가는 되돌리기 어려운 방향이라 fail-safe 로 설계했다."""
    vals = [1.0] * 55 + [-0.5] * 45          # EV +0.30, 기대 0.3 과 정합 / 승률 55% vs 기대 95%
    led = write_ledger(tmp_path / "l.jsonl", vals)
    r = gate.evaluate("lane", cfg_for(led, expect_ev=0.3, expect_win=95.0), {}, TODAY)
    assert r["win_verdict"] == "SHORT"
    assert r["verdict"] == "CONFIRM", f"승률 미달이 EV 판정을 뒤집었다: {r['verdict']}"


def test_win_ok_when_forward_meets_expectation(tmp_path):
    vals = [2.0] * 80 + [-2.0] * 20
    led = write_ledger(tmp_path / "l.jsonl", vals)
    r = gate.evaluate("lane", cfg_for(led, expect_ev=0.5, expect_win=75.0), {}, TODAY)
    assert r["win_verdict"] == "OK"


def test_win_verdict_is_na_below_n_min(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 8)
    r = gate.evaluate("lane", cfg_for(led, expect_win=95.0, n_min=20), {}, TODAY)
    assert r["verdict"] == "OBSERVING"
    assert r["win_verdict"] == "NA", "표본 미성숙인데 승률을 판정했다"


def test_win_shortfall_is_not_declared_on_noise(tmp_path):
    """작은 표본의 승률 흔들림으로는 SHORT 가 뜨지 않아야 한다 (CI 상단 기준)."""
    vals = [2.0] * 15 + [-2.0] * 10          # 60% 지만 n=25, CI 상단 넓음
    led = write_ledger(tmp_path / "l.jsonl", vals)
    r = gate.evaluate("lane", cfg_for(led, expect_ev=0.1, expect_win=75.0), {}, TODAY)
    assert r["fwd_win_ci"][1] >= 75.0 * gate.WIN_TOL
    assert r["win_verdict"] == "OK"


# ---------------------------------------------------------------------------
# 기존 판정 불변 — 안전축이 약해지지 않았는지
# ---------------------------------------------------------------------------

def test_degrade_verdict_string_is_unchanged(tmp_path):
    """web/backend/services.py:283 이 == "DEGRADE" 로 소비한다. 이 문자열은 계약이다."""
    led = write_ledger(tmp_path / "l.jsonl", [-1.0] * 40)
    r = gate.evaluate("lane", cfg_for(led), {}, TODAY)
    assert r["verdict"] == "DEGRADE"
    assert "스트림 제외" in r["note"]


def test_confirm_and_observing_are_unchanged(tmp_path):
    led = write_ledger(tmp_path / "c.jsonl", [1.0] * 40)
    assert gate.evaluate("lane", cfg_for(led, expect_ev=1.0, expect_win=50.0), {}, TODAY)["verdict"] == "CONFIRM"
    few = write_ledger(tmp_path / "o.jsonl", [1.0] * 8)
    assert gate.evaluate("lane", cfg_for(few, n_min=20), {}, TODAY)["verdict"] == "OBSERVING"
    tiny = write_ledger(tmp_path / "t.jsonl", [1.0] * 3)
    assert gate.evaluate("lane", cfg_for(tiny), {}, TODAY)["verdict"] == "OBSERVING"


def test_degrade_still_wins_over_exceed_family(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [-3.0] * 120)
    r = gate.evaluate("lane", cfg_for(led), state_for("EXCEED_ELIGIBLE", bdays_before(TODAY, 40)), TODAY)
    assert r["verdict"] == "DEGRADE"


def test_live_lane_config_is_intact():
    assert list(gate.LANES) == ["kospi_intraday_t5", "kosdaq_intraday_t10", "swing_candidate",
                                "b_primary_top3", "b_all_top10", "nasdaq_session_tape"]
    assert gate.LANES["kospi_intraday_t5"]["expect_win"] == 92.0
    assert gate.LANES["b_primary_top3"]["date_field"] == "scan_date"


# ---------------------------------------------------------------------------
# F4 — 기대값 정정 3건 (audit-lane-basis.md, 운영자 승인)
# ---------------------------------------------------------------------------

def test_b_all_top10_expect_ev_uses_the_point_estimate():
    """§11-B:271 top10 점추정은 +1.63 이고 1.20 은 CI 하단(1.19)에 가까운 값이었다.

    임계가 곱셈(0.5x/1.5x)이라 기대를 낮게 잡는 것은 보수적이지 않다 — 강등 문턱과 승격
    문턱이 **동시에** 내려가 부실 레인을 살려두면서 승격은 앞당긴다. 이 상수는 그 함정이었다.
    """
    assert gate.LANES["b_all_top10"]["expect_ev"] == 1.63
    lane = gate.LANES["b_all_top10"]
    assert lane["expect_ev"] * 0.5 == pytest.approx(0.815)    # DEGRADE 임계 (구 0.600)
    assert lane["expect_ev"] * 1.5 == pytest.approx(2.445)    # EXCEED  임계 (구 1.800)


def test_b_lane_expect_win_is_no_longer_the_ungrounded_55():
    """§11-B 표에 승률 열 자체가 없다 — 55.0 은 리포 어디에도 근거가 없었다."""
    for lane in ("b_primary_top3", "b_all_top10"):
        assert gate.LANES[lane]["expect_win"] != 55.0, f"{lane} 근거 없는 55.0 이 남아 있다"
        assert 30.0 < gate.LANES[lane]["expect_win"] < 50.0


def test_win_is_net_gt_zero_not_net_gt_0_3(tmp_path):
    """승률 정의를 하니스(threshold_frontier.py:44,78 win=(net>0))에 맞춘다.

    게이트만 net>0.3 을 써서, 정의가 다른 두 수를 같은 표에 나란히 놓고 비교하고 있었다.
    """
    led = write_ledger(tmp_path / "l.jsonl", [0.15] * 60 + [-1.0] * 40)   # 0<net<0.3 이 60건
    r = gate.evaluate("lane", cfg_for(led, expect_ev=0.01, expect_win=60.0), {}, TODAY)
    assert r["fwd_win"] == pytest.approx(60.0), "net>0.3 기준이 남아 있다 (그 기준이면 0%)"


def test_win_definition_matches_the_b_ledger_win_field(tmp_path):
    """B 레인은 cost=0 이라 net>0 == alpha>0 == 원장 win 필드. 정의가 셋 다 일치해야 한다.

    실측: 라이브 b_shadow 458행(top3 58 + top10 400) 전부에서 int(alpha>0) == win, 불일치 0.
    """
    rows = [{"alpha": a, "win": int(a > 0), "date": "2026-07-01", "status": "settled"}
            for a in (2.0, 0.1, -0.1, 0.25, -3.0, 1.5, 0.05, -0.5, 4.0, 0.2) * 4]
    led = tmp_path / "b.jsonl"
    led.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    cfg = {"ledger": led, "field": "alpha", "cost": 0.0, "expect_ev": 1.0, "expect_win": 60.0,
           "n_min": 20, "basis": "테스트", "filter": {"status": "settled"},
           "publish_scope": gate.WHOLE_LEDGER}
    r = gate.evaluate("b", cfg, {}, TODAY)
    ledger_win = round(100 * sum(x["win"] for x in rows) / len(rows), 1)
    assert r["fwd_win"] == pytest.approx(ledger_win), (r["fwd_win"], ledger_win)


def test_cost_is_deducted_before_the_win_test(tmp_path):
    """net = gross - cost. 비용 차감 후 0 을 넘는지가 기준이다."""
    led = write_ledger(tmp_path / "l.jsonl", [0.2] * 50 + [0.4] * 50)
    r = gate.evaluate("lane", cfg_for(led, cost=0.3, expect_ev=0.01, expect_win=50.0), {}, TODAY)
    assert r["fwd_win"] == pytest.approx(50.0)   # 0.2-0.3<0 패, 0.4-0.3>0 승


# ---------------------------------------------------------------------------
# F7 — 정지 선언 이후 생성된 표본의 판정 제외
# ---------------------------------------------------------------------------
# 근거: orca/reports/trace-b-lane-f7.md (goblin). b 레인은 2026-08-03 정지 선언됐는데
# 웹 스캔 경로(jobs.py::_run_step)에 가드가 없어 08-04·08-05·08-10 에 30건이 더 생성됐다.
# 생성 경로는 정지를 무시하고 표시 경로는 정지를 지켜서, 아무도 모르는 채 정지된 레인의
# 판정 표본이 정지 이후 표본으로 불어났다. 규칙: 정지된 레인은 정지 시각 이후 표본으로
# 판정하지 않는다.

def marker(path: Path, since="2026-08-03", suspended=True, raw=None) -> Path:
    path.write_text(raw if raw is not None else
                    json.dumps({"suspended": suspended, "since": since}), encoding="utf-8")
    return path


def test_post_suspension_rows_are_excluded_from_the_verdict(tmp_path):
    pre = [(bdays_before(TODAY, 30 + i), 1.0) for i in range(40)]
    post = [("2026-08-04", 9.0)] * 10 + [("2026-08-05", 9.0)] * 10 + [("2026-08-10", 9.0)] * 10
    led = write_ledger(tmp_path / "l.jsonl", [v for _, v in pre + post],
                       dates=[d for d, _ in pre + post])
    mk = marker(tmp_path / "susp.json")
    r = gate.evaluate("b", cfg_for(led, suspend_marker=mk), {}, TODAY)
    assert r["n"] == 40, f"정지 이후 30건이 표본에 남아 있다 (n={r['n']})"
    assert r["excluded_post_suspension"] == 30
    assert r["suspended_since"] == "2026-08-03"


def test_rows_on_the_suspension_date_are_kept(tmp_path):
    """정지 커밋은 08-03 22:28 이고 그날 픽 13건은 그 전에 생성됐다 — 경계는 배타적이어야 한다."""
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 13, dates=["2026-08-03"] * 13)
    r = gate.evaluate("b", cfg_for(led, n_min=10, suspend_marker=marker(tmp_path / "s.json")), {}, TODAY)
    assert r["n"] == 13 and r["excluded_post_suspension"] == 0


def test_no_marker_means_no_exclusion(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 40, dates=["2026-08-10"] * 40)
    r = gate.evaluate("b", cfg_for(led, suspend_marker=tmp_path / "absent.json"), {}, TODAY)
    assert r["n"] == 40
    assert r["excluded_post_suspension"] == 0 and r["suspended_since"] is None


def test_marker_with_suspended_false_means_no_exclusion(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 40, dates=["2026-08-10"] * 40)
    mk = marker(tmp_path / "s.json", suspended=False)
    r = gate.evaluate("b", cfg_for(led, suspend_marker=mk), {}, TODAY)
    assert r["n"] == 40 and r["excluded_post_suspension"] == 0


def test_unreadable_marker_does_not_silently_shrink_the_sample(tmp_path):
    """마커가 깨지면 표본을 **건드리지 않는다**.

    표본을 줄이면 n<n_min 에서 DEGRADE 가 OBSERVING 으로 바뀌고, services.py 는
    DEGRADE 만 발행 제외하므로 정지된 레인이 조용히 발행으로 되돌아간다. 파싱 실패가
    안전장치를 푸는 방향으로 작동해선 안 된다.
    """
    led = write_ledger(tmp_path / "l.jsonl", [-1.0] * 40, dates=["2026-08-10"] * 40)
    mk = marker(tmp_path / "s.json", raw="{ not json")
    r = gate.evaluate("b", cfg_for(led, suspend_marker=mk), {}, TODAY)
    assert r["n"] == 40 and r["excluded_post_suspension"] == 0
    assert r["verdict"] == "DEGRADE"
    assert "정지 마커" in r["note"], f"마커 파손이 조용히 지나갔다: {r['note']}"


def test_shrinking_the_sample_never_reopens_publication(tmp_path):
    """제외로 n 이 n_min 아래로 떨어져도 발행 차단이 풀리면 안 된다.

    d42d1a2 에서 fail-open 을 택한 근거가 바로 이 경로였다("표본을 줄이면 DEGRADE 가
    OBSERVING 이 되고 stream_exclusion 은 verdict 만 읽는다"). 정지 자체가 발행을 막게
    하면 이 경로가 닫히고, 그래야 fail-closed 로 갈 수 있다.
    """
    pre = [(bdays_before(TODAY, 40), 1.0)] * 5
    post = [("2026-08-10", 1.0)] * 60
    led = write_ledger(tmp_path / "l.jsonl", [v for _, v in pre + post],
                       dates=[d for d, _ in pre + post])
    r = gate.evaluate("b", cfg_for(led, n_min=30, suspend_marker=marker(tmp_path / "s.json")), {}, TODAY)
    assert r["n"] == 5, "제외가 안 됐다 — 전제가 무너졌다"
    assert r["verdict"] == "DEGRADE", (
        f"n={r['n']}<n_min 에서 {r['verdict']} 가 됐다 — stream_exclusion 이 발행을 못 막는다")
    assert r["publication_block"] is True
    assert "이후 60건 제외" in r["note"] and "2026-08-03" in r["note"], r["note"]


def test_both_b_lanes_are_wired_to_the_suspension_marker():
    for lane in ("b_primary_top3", "b_all_top10"):
        mk = gate.LANES[lane].get("suspend_marker")
        assert mk is not None, f"{lane} 에 정지 마커가 배선되지 않았다"
        assert Path(mk).name == "b_lane_suspended.json"
    for lane in ("kospi_intraday_t5", "swing_candidate", "nasdaq_session_tape"):
        assert "suspend_marker" not in gate.LANES[lane], f"{lane} 은 정지 레인이 아니다"


def test_exclusion_also_applies_to_the_primary_sublane(tmp_path):
    """b_primary_top3 도 같은 원장·같은 정지 레인이다 — 한쪽만 거르면 규칙이 깨진다."""
    rows = ([("2026-08-01", 1.0, "PRIMARY")] * 40 + [("2026-08-01", 1.0, "CANDIDATE")] * 40
            + [("2026-08-10", 9.0, "PRIMARY")] * 3 + [("2026-08-10", 9.0, "CANDIDATE")] * 7)
    led = tmp_path / "l.jsonl"
    with led.open("w", encoding="utf-8") as fh:
        for d, v, t in rows:
            fh.write(json.dumps({"ret": v, "date": d, "tier": t, "status": "settled"}) + "\n")
    mk = marker(tmp_path / "s.json")
    prim = gate.evaluate("b_primary", cfg_for(led, suspend_marker=mk,
                                              filter={"status": "settled", "tier": "PRIMARY"}), {}, TODAY)
    allr = gate.evaluate("b_all", cfg_for(led, suspend_marker=mk,
                                          filter={"status": "settled"}), {}, TODAY)
    assert prim["n"] == 40 and prim["excluded_post_suspension"] == 3
    assert allr["n"] == 80 and allr["excluded_post_suspension"] == 10


def test_suspension_exclusion_survives_compact_dates(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 20 + [9.0] * 20,
                       dates=["20260801"] * 20 + ["20260810"] * 20)
    r = gate.evaluate("b", cfg_for(led, n_min=10, suspend_marker=marker(tmp_path / "s.json")), {}, TODAY)
    assert r["n"] == 20 and r["excluded_post_suspension"] == 20


# ---------------------------------------------------------------------------
# 티켓 발행 — 승격 티켓은 ELIGIBLE 일 때만
# ---------------------------------------------------------------------------

@pytest.fixture
def harness(tmp_path, monkeypatch):
    """main() 을 tmp 산출물로 돌리고 bd 호출을 가로챈다 (실 bd 를 건드리지 않는다)."""
    created = []
    monkeypatch.setattr(gate, "_bd_create", lambda t, d: (created.append((t, d)), True)[1])
    monkeypatch.setattr(gate, "OUT_JSON", tmp_path / "out.json")
    monkeypatch.setattr(gate, "OUT_MD", tmp_path / "out.md")
    monkeypatch.setattr(gate, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(sys, "argv", ["gate"])
    return created


def _install_lane(monkeypatch, tmp_path, vals, state=None, **cfgkw):
    led = write_ledger(tmp_path / "lane.jsonl", vals)
    monkeypatch.setattr(gate, "LANES", {"lane": cfg_for(led, **cfgkw)})
    if state is not None:
        (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")


def test_pending_never_files_a_promotion_ticket(harness, tmp_path, monkeypatch):
    """F3 의 실제 피해: n=40 인데도 승격 티켓이 나가던 경로."""
    _install_lane(monkeypatch, tmp_path, [3.0] * 40)
    gate.main()
    assert harness == [], f"EXCEED_PENDING 인데 티켓이 나갔다: {harness}"
    assert json.loads((tmp_path / "state.json").read_text())["lane"]["verdict"] == "EXCEED_PENDING"


def test_eligible_files_the_promotion_ticket(harness, tmp_path, monkeypatch):
    _install_lane(monkeypatch, tmp_path, [3.0] * 120,
                  state=state_for("EXCEED_PENDING", bdays_before(gate._today(), 15)))
    gate.main()
    assert len(harness) == 1, harness
    assert "EXCEED_ELIGIBLE" in harness[0][0]
    assert "승격" in harness[0][1]


def test_degrade_ticket_still_fires(harness, tmp_path, monkeypatch):
    _install_lane(monkeypatch, tmp_path, [-1.0] * 40)
    gate.main()
    assert len(harness) == 1 and "DEGRADE" in harness[0][0]


def test_win_shortfall_ticket_only_when_not_degraded(harness, tmp_path, monkeypatch):
    """이미 DEGRADE 로 티켓이 나간 레인에 승률 티켓을 겹쳐 내지 않는다.

    F5 가 지목한 사각지대는 'EV 로만 통과하는' 레인이다 — 거기서만 울려야 신호가 된다.
    """
    _install_lane(monkeypatch, tmp_path, [-1.0] * 60, expect_win=95.0)
    gate.main()
    assert len(harness) == 1 and "DEGRADE" in harness[0][0], harness


def test_win_shortfall_ticket_fires_for_ev_only_pass(harness, tmp_path, monkeypatch):
    _install_lane(monkeypatch, tmp_path, [1.0] * 55 + [-0.5] * 45, expect_ev=0.3, expect_win=95.0)
    gate.main()
    assert len(harness) == 1, harness
    assert "승률" in harness[0][0]


def test_tickets_are_deduped_across_runs(harness, tmp_path, monkeypatch):
    _install_lane(monkeypatch, tmp_path, [-1.0] * 40)
    gate.main()
    gate.main()
    assert len(harness) == 1, f"같은 판정으로 티켓이 두 번 나갔다: {harness}"


def test_state_survives_legacy_string_entries(harness, tmp_path, monkeypatch):
    """실 state 파일에 구형 문자열 항목이 남아 있다 ("swing_ensemble": "DEGRADE")."""
    _install_lane(monkeypatch, tmp_path, [-1.0] * 40, state={"lane": "DEGRADE", "swing_ensemble": "DEGRADE"})
    gate.main()
    assert harness == [], "동일 판정인데 구형 state 를 못 읽어 티켓이 재발행됐다"


def test_report_exposes_the_promotion_conditions(harness, tmp_path, monkeypatch):
    """승격 조건이 산출물에 실려야 사람이 판정을 검증할 수 있다."""
    _install_lane(monkeypatch, tmp_path, [3.0] * 40)
    gate.main()
    rep = json.loads((tmp_path / "out.json").read_text())
    g = rep["results"][0]["exceed_gate"]
    assert set(g) >= {"n", "hold", "lag", "win"}
    md = (tmp_path / "out.md").read_text()
    assert "EXCEED_PENDING" in md and "승률" in md


# ---------------------------------------------------------------------------
# 마커 계약 — 엔진과 게이트가 같은 파일을 같은 의미로 읽는가
# ---------------------------------------------------------------------------
# 근거: verify-gate-d42d1a2.md §2·§3 (handfish) + 66c9725 (seaslug, 엔진 fail-closed).
# F7 의 근본 원인이 "정지가 엔진의 계약이 아니라 호출자 각각의 관례"였다. 두 벌이 서로 다르게
# 읽으면 그 사고가 다른 얼굴로 재발한다 — 엔진은 멈추는데 게이트는 계속 판정하는 형태로.

# 엔진 b_engine/model_scan.suspension() 의 의미론을 명세로 고정한다.
# (엔진은 `marker.get("suspended") is False` 로 **정체 비교**하므로 0·"false"·null 은 전부 정지다)
MARKER_SPEC = [
    (None,                                          False, "파일 없음"),
    ('{"suspended": false}',                         False, "명시적 해제"),
    ('{"suspended": true, "since": "2026-08-03"}',   True,  "정상 정지"),
    ('{}',                                           True,  "suspended 키 누락"),
    ('{"since": "2026-08-03"}',                      True,  "since 만 있고 키 누락"),
    ('{"suspended": null}',                          True,  "null"),
    ('{"suspended": 0}',                             True,  "falsy 지만 False 아님"),
    ('{"suspended": "false"}',                       True,  "문자열 false"),
    ('[1, 2, 3]',                                    True,  "리스트"),
    ('"just a string"',                              True,  "문자열 JSON"),
    ('{ not json',                                   True,  "JSON 깨짐"),
    ('',                                             True,  "빈 파일"),
]


@pytest.mark.parametrize("raw,expected,label", MARKER_SPEC, ids=[s[2] for s in MARKER_SPEC])
def test_gate_marker_semantics_match_the_engine_spec(tmp_path, raw, expected, label):
    """게이트의 마커 판독이 엔진 명세와 일치해야 한다.

    d42d1a2 의 게이트는 `if not d.get("suspended")` 라 **키 누락·리스트·falsy 를 해제로 읽었다**.
    엔진은 같은 경우를 전부 정지로 읽는다. 마커가 손상되면 엔진은 신규 픽을 멈추는데 게이트는
    정지 이후 표본으로 계속 판정하는 어긋남이 생긴다.
    """
    mk = tmp_path / "s.json"
    if raw is None:
        mk = tmp_path / "absent.json"
    else:
        mk.write_text(raw, encoding="utf-8")
    assert gate._suspension(cfg_for(tmp_path / "x", suspend_marker=mk), {})["suspended"] is expected, label


def test_gate_matches_the_live_engine_implementation(tmp_path):
    """명세표가 아니라 **실제 엔진 코드**와 대조한다 (b_engine 병합 후 활성화).

    명세표는 내가 읽은 엔진을 옮겨 적은 것이라 엔진이 바뀌면 같이 틀릴 수 있다. 실물 대조가
    있어야 두 벌의 어긋남을 양방향으로 잡는다.
    """
    model_scan = pytest.importorskip(
        "b_engine.model_scan",
        reason="b_engine.model_scan 미존재 — main 병합 후 활성화된다")
    if not hasattr(model_scan, "suspension"):
        pytest.skip("b_engine.model_scan.suspension 미존재 — 66c9725 병합 후 활성화된다")
    mk = tmp_path / "s.json"
    for raw, expected, label in MARKER_SPEC:
        if raw is None:
            if mk.exists():
                mk.unlink()
        else:
            mk.write_text(raw, encoding="utf-8")
        model_scan.SUSPEND_MARKER = str(mk)
        engine = model_scan.suspension() is not None
        mine = gate._suspension(cfg_for(tmp_path / "x", suspend_marker=mk), {})["suspended"]
        assert engine is mine is expected, f"{label}: 엔진={engine} 게이트={mine} 기대={expected}"


# ---------------------------------------------------------------------------
# 발행 차단 — 손상 신호가 실제로 소비되는가
# ---------------------------------------------------------------------------

def test_suspended_lane_is_publication_blocked_regardless_of_performance(tmp_path):
    """정지 레인은 성적이 아무리 좋아도 발행되지 않는다.

    handfish: suspend_marker_broken 은 결과 JSON 에 실리지만 stream_exclusion 은 verdict 만
    읽어 아무도 소비하지 않는다. 그래서 신호를 **verdict 로 내보낸다** — 새 문자열을 만들면
    소비자가 모르는 값이라 오히려 발행이 열린다.
    """
    led = write_ledger(tmp_path / "l.jsonl", [5.0] * 40, dates=["2026-07-01"] * 40)
    mk = marker(tmp_path / "s.json")               # 정지, since=2026-08-03 (표본은 그 이전)
    r = gate.evaluate("b", cfg_for(led, expect_ev=1.0, suspend_marker=mk), {}, TODAY)
    assert r["excluded_post_suspension"] == 0, "이 표본은 배제 대상이 아니다(정지 이전)"
    assert r["publication_block"] is True
    assert r["publication_block_reason"]
    assert r["verdict"] == "DEGRADE", (
        f"정지 레인인데 {r['verdict']} — 배제가 0건이면 발행이 열린다")


def test_publication_block_reason_is_specific(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 40, dates=["2026-07-01"] * 40)
    ok = gate.evaluate("b", cfg_for(led, suspend_marker=marker(tmp_path / "a.json")), {}, TODAY)
    broken = gate.evaluate("b", cfg_for(led, suspend_marker=marker(tmp_path / "b.json", raw="{x")), {}, TODAY)
    assert "정지" in ok["publication_block_reason"]
    assert "마커" in broken["publication_block_reason"]
    assert ok["publication_block_reason"] != broken["publication_block_reason"]


def test_unsuspended_lane_is_not_publication_blocked(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 40)
    r = gate.evaluate("lane", cfg_for(led), {}, TODAY)
    assert r["publication_block"] is False
    assert r["verdict"] == "CONFIRM"


# ---------------------------------------------------------------------------
# 마커 삭제 감지 — 재개는 정지 중 생성분을 소급 정당화하지 않는다
# ---------------------------------------------------------------------------

def test_marker_deletion_keeps_excluding_the_recorded_window(tmp_path):
    """마커 삭제는 문서화된 재개 절차(resume_condition)이자 사고 경로다.

    삭제되면 정지 창이 사라져 **정지 중 생성된 30건이 조용히 표본으로 복귀**한다.
    재개는 앞으로를 여는 것이지 정지 중 계약 위반 표본을 정당화하지 않는다.
    """
    pre = [("2026-07-01", 1.0)] * 40
    during = [("2026-08-10", 9.0)] * 30
    led = write_ledger(tmp_path / "l.jsonl", [v for _, v in pre + during],
                       dates=[d for d, _ in pre + during])
    state = {"b": {"verdict": "DEGRADE", "since": "2026-08-03",
                   "suspension": {"since": "2026-08-03", "first_seen": "2026-08-03"}}}
    r = gate.evaluate("b", cfg_for(led, suspend_marker=tmp_path / "gone.json"), state, TODAY)

    assert r["excluded_post_suspension"] == 30, "마커가 사라지자 정지 중 표본이 복귀했다"
    assert r["marker_resumed"] is True
    assert "재개" in r["note"] or "삭제" in r["note"], r["note"]


def test_marker_deletion_allows_publication_again(tmp_path):
    """재개 자체는 막지 않는다 — 마커 삭제가 문서화된 재개 절차이기 때문이다."""
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 40, dates=["2026-07-01"] * 40)
    state = {"b": {"verdict": "DEGRADE", "since": "2026-08-03",
                   "suspension": {"since": "2026-08-03", "first_seen": "2026-08-03"}}}
    r = gate.evaluate("b", cfg_for(led, suspend_marker=tmp_path / "gone.json"), state, TODAY)
    assert r["publication_block"] is False, "재개 절차를 밟았는데 영구히 막혔다"
    assert r["marker_resumed"] is True


def test_never_suspended_lane_has_no_resume_signal(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 40)
    r = gate.evaluate("lane", cfg_for(led, suspend_marker=tmp_path / "absent.json"), {}, TODAY)
    assert r["marker_resumed"] is False
    assert r["suspended_since"] is None


def test_suspension_window_is_recorded_for_persistence(tmp_path):
    """삭제 감지가 가능하려면 정지 창을 게이트가 스스로 기억해야 한다."""
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 40, dates=["2026-07-01"] * 40)
    r = gate.evaluate("b", cfg_for(led, suspend_marker=marker(tmp_path / "s.json")), {}, TODAY)
    assert r["suspension_record"] == {"since": "2026-08-03", "first_seen": TODAY}


def test_main_persists_and_reuses_the_suspension_record(harness, tmp_path, monkeypatch):
    """state 에 실제로 저장되고 다음 실행에서 읽히는지 — 삭제 감지의 전제."""
    led = write_ledger(tmp_path / "lane.jsonl", [1.0] * 40, dates=["2026-07-01"] * 40)
    mk = marker(tmp_path / "s.json")
    monkeypatch.setattr(gate, "LANES", {"lane": cfg_for(led, suspend_marker=mk)})
    gate.main()
    saved = json.loads((tmp_path / "state.json").read_text())["lane"]
    assert saved["suspension"]["since"] == "2026-08-03"

    mk.unlink()                                   # 운영자가 재개 절차대로 삭제
    gate.main()
    rep = json.loads((tmp_path / "out.json").read_text())["results"][0]
    assert rep["marker_resumed"] is True, "삭제를 감지하지 못했다"
    assert rep["suspended_since"] == "2026-08-03", "기록된 정지 창을 잃었다"


# ---------------------------------------------------------------------------
# 마커 시각 — since 의 시각을 버리지 않는다
# ---------------------------------------------------------------------------

def test_same_day_rows_after_the_suspension_time_are_excluded(tmp_path):
    """handfish §2: since='2026-09-01T09:00:00Z' 인데 09:30·14:00 픽이 표본에 남았다.

    `str(since)[:10]` 이 시각을 버려서 같은 날 정지 이후 픽이 그대로 남는다 — 이 커밋이
    제거하려는 바로 그 희석이다.
    """
    rows = [("2026-09-01T08:00:00Z", 1.0), ("2026-09-01T09:30:00Z", 9.0),
            ("2026-09-01T14:00:00Z", 9.0)]
    led = tmp_path / "l.jsonl"
    led.write_text("".join(json.dumps({"ret": v, "date": "2026-09-01", "logged_at": t}) + "\n"
                           for t, v in rows), encoding="utf-8")
    cfg = cfg_for(led, n_min=1, suspend_marker=marker(tmp_path / "s.json", since="2026-09-01T09:00:00Z"))
    r = gate.evaluate("b", cfg, {}, TODAY)
    assert r["excluded_post_suspension"] == 2, f"정지 시각 이후 픽이 표본에 남았다 (n={r['n']})"
    assert r["n"] == 1


def test_date_only_since_keeps_the_whole_suspension_day(tmp_path):
    """시각이 없으면 날짜 경계를 유지한다 — 08-03 정지 당일 13건은 정지 이전 생성이었다.

    handfish 가 실측으로 확인한 현 동작이고, 이를 깨면 정상 표본을 지운다.
    """
    led = tmp_path / "l.jsonl"
    led.write_text("".join(json.dumps({"ret": 1.0, "date": "2026-08-03",
                                       "logged_at": f"2026-08-03T{h}:00:00Z"}) + "\n"
                           for h in ("13", "20", "23")), encoding="utf-8")
    r = gate.evaluate("b", cfg_for(led, n_min=1, suspend_marker=marker(tmp_path / "s.json")), {}, TODAY)
    assert r["n"] == 3 and r["excluded_post_suspension"] == 0


def test_rows_without_timestamps_fall_back_to_date_comparison(tmp_path):
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 3 + [9.0] * 3,
                       dates=["2026-09-01"] * 3 + ["2026-09-02"] * 3)
    cfg = cfg_for(led, n_min=1, suspend_marker=marker(tmp_path / "s.json", since="2026-09-01T09:00:00Z"))
    r = gate.evaluate("b", cfg, {}, TODAY)
    assert r["excluded_post_suspension"] == 3, "타임스탬프가 없으면 날짜 비교로 떨어져야 한다"


# ---------------------------------------------------------------------------
# 오기 2건 + 자기참조 명시 (handfish §5)
# ---------------------------------------------------------------------------

def test_win_definition_wording_matches_the_code():
    """3-c 가 net>0.3 → net>0 으로 바꿨는데 문구가 남아 있었다.

    티켓 본문 쪽이 특히 문제였다 — 승률 미달 티켓을 받은 사람이 틀린 정의로 원인을 판별한다.
    """
    src = Path(gate.__file__).read_text(encoding="utf-8")
    assert "0.3%" not in src, "승률 정의 오기(0.3%)가 남아 있다"
    assert "순수익>0.3" not in src and "순수익 > 0.3" not in src


def test_self_reference_of_b_lane_expect_win_is_documented():
    """b 레인 expect_win 이 측정치와 같아 CI 상단이 항상 기대 이상 → 영원히 SHORT 가 안 된다.

    이 사실이 코드에 적혀 있지 않으면 다음 사람이 승률 축이 살아 있다고 오해한다.
    """
    src = Path(gate.__file__).read_text(encoding="utf-8")
    assert "자기참조" in src, "b 레인 승률축 무력화(자기참조)가 코드에 명시돼 있지 않다"


def test_kosdaq_expect_win_matches_the_web_consumer():
    """소비자 간 동결값 불일치 해소 (audit-lane-basis.md, 운영자 승인 2026-08-16).

    게이트가 §11-A(2026-07-03, n=66)의 75.8 을, 웹 폴백이 §27(2026-07-13, n=101)의 72 를
    써서 같은 레인에 두 개의 "백테스트 승률"이 동시에 노출됐다. 더 늦고 표본이 큰 §27 이 정본.
    """
    assert gate.LANES["kosdaq_intraday_t10"]["expect_win"] == 72.0
    basis = gate.LANES["kosdaq_intraday_t10"]["basis"]
    assert "§27" in basis and "§11-A" in basis, (
        f"EV 와 승률의 근거 §가 다른 레인인데 basis 가 한쪽만 가리킨다: {basis}")


def test_kosdaq_expect_ev_is_unchanged():
    """§27 은 EV 를 주지 않는다 — EV 는 §11-A 그대로 둔다."""
    assert gate.LANES["kosdaq_intraday_t10"]["expect_ev"] == 3.14


# ---------------------------------------------------------------------------
# 판정 범위 = 발행 스트림 (audit-lane-champions.md, 운영자 승인 2026-08-16)
# ---------------------------------------------------------------------------
# 게이트가 **발행되지 않는 픽으로 발행 레인을 강등**하고 있었다. kospi_intraday_t5 는
# §7-E:178 상 PRIMARY 만 라우팅하는데, 게이트는 원장 전체 43건(베토 3 + 티어제 이전 15 +
# CANDIDATE 15 포함)으로 DEGRADE 를 냈다. 실제 발행 스트림(PRIMARY n=10)은 +1.62 다.

def test_every_lane_declares_its_publish_scope():
    """미선언이 조용히 '원장 전체'로 떨어지면 같은 버그가 다른 레인에서 반복된다."""
    missing = [n for n, c in gate.LANES.items() if "publish_scope" not in c]
    assert not missing, f"publish_scope 미선언 레인: {missing}"


def test_undeclared_scope_is_an_error_not_a_default(tmp_path):
    """기본값을 주면 그 기본값이 조용히 정책이 된다 — 플래그 P0 의 교훈."""
    led = write_ledger(tmp_path / "l.jsonl", [1.0] * 30)
    cfg = cfg_for(led)
    del cfg["publish_scope"]
    with pytest.raises(KeyError, match="publish_scope"):
        gate.evaluate("lane", cfg, {}, TODAY)


def test_kospi_intraday_judges_only_the_routed_tier():
    assert gate.LANES["kospi_intraday_t5"]["publish_scope"] == {"tier": "PRIMARY"}


def test_b_all_top10_watches_the_whole_stream_by_design():
    """이 레인은 전체 스트림 감시가 존재 이유다 — 발행분만 보면 사각지대가 되살아난다."""
    assert gate.LANES["b_all_top10"]["publish_scope"] == gate.WHOLE_LEDGER
    assert gate.LANES["b_primary_top3"]["publish_scope"] == {"tier": "PRIMARY"}


def test_scope_excludes_vetoed_and_unrouted_rows(tmp_path):
    """라이브 실패 형태 재현: 베토·티어제 이전·미라우팅 행이 판정에서 빠져야 한다."""
    led = tmp_path / "l.jsonl"
    rows = ([{"ret": 1.62, "date": "2026-07-01", "tier": "PRIMARY"}] * 10
            + [{"ret": 1.60, "date": "2026-07-01", "tier": "CANDIDATE"}] * 15
            + [{"ret": -4.83, "date": "2026-07-01", "tier": "VETO_REBOUND_PHASE"}] * 3
            + [{"ret": -3.03, "date": "2026-07-01"}] * 15)
    led.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    whole = gate.evaluate("l", cfg_for(led, n_min=5), {}, TODAY)
    scoped = gate.evaluate("l", cfg_for(led, n_min=5, publish_scope={"tier": "PRIMARY"}), {}, TODAY)

    assert whole["n"] == 43 and scoped["n"] == 10
    assert scoped["fwd_ev"] == pytest.approx(1.62, abs=0.01)
    assert whole["fwd_ev"] < 0, "전제가 바뀌었다 — 원장 전체가 음수여야 이 버그가 재현된다"
    assert scoped["ledger_rows_before_scope"] == 43, "범위 적용 전 규모가 보고돼야 한다"


def test_scope_narrowing_can_drop_below_n_min(tmp_path):
    """발행분만 보면 표본이 줄어 OBSERVING 이 될 수 있다 — 그건 정상이고 숨기면 안 된다.

    ⚠️ 다만 OBSERVING 은 DEGRADE 가 아니므로 stream_exclusion 의 발행 제외가 **풀린다.**
    범위 수정이 곧 발행 재개를 뜻할 수 있다는 점이 이 테스트가 고정하는 사실이다.
    """
    led = tmp_path / "l.jsonl"
    rows = ([{"ret": 1.62, "date": "2026-07-01", "tier": "PRIMARY"}] * 10
            + [{"ret": -3.0, "date": "2026-07-01", "tier": "CANDIDATE"}] * 33)
    led.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    whole = gate.evaluate("l", cfg_for(led, expect_ev=5.65, n_min=20), {}, TODAY)
    scoped = gate.evaluate("l", cfg_for(led, expect_ev=5.65, n_min=20,
                                        publish_scope={"tier": "PRIMARY"}), {}, TODAY)

    assert whole["verdict"] == "DEGRADE"
    assert scoped["verdict"] == "OBSERVING", "발행분 n<n_min 이면 판정 불가가 맞다"
    assert scoped["publish_block" if False else "publication_block"] is False, (
        "OBSERVING 은 발행 제외를 걸지 않는다 — 이 변경이 발행을 되살릴 수 있다")


def test_scope_and_maturity_filter_are_separate_concepts(tmp_path):
    """filter(성숙: settled) 와 publish_scope(발행 범위: tier) 는 다른 개념이다."""
    led = tmp_path / "l.jsonl"
    rows = [{"ret": 2.0, "date": "2026-07-01", "status": "settled", "tier": "PRIMARY"}] * 8 \
         + [{"ret": 9.0, "date": "2026-07-01", "status": "open", "tier": "PRIMARY"}] * 8 \
         + [{"ret": 2.0, "date": "2026-07-01", "status": "settled", "tier": "CANDIDATE"}] * 8
    led.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    r = gate.evaluate("l", cfg_for(led, n_min=5, filter={"status": "settled"},
                                   publish_scope={"tier": "PRIMARY"}), {}, TODAY)
    assert r["n"] == 8 and r["ledger_rows_before_scope"] == 16
