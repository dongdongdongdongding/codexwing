"""픽 계약 레벨 DEGRADE 스트림 제외 (audit-gate.md F1·F2).

F1: 제외가 `web/backend/services.py:281-288` **한 경로에만** 배선돼 있어 Discord 카드와
    top_deep은 게이트를 아예 읽지 않았다 → DEGRADE 5레인 픽이 ⛔ 표시 없이
    진입가·목표가를 단 실행가능 매수카드로 나갔다.
F2: 게이트 리더가 fail-**open**이었다 — JSON이 깨지거나 없으면 `{}`를 돌려주고
    제외가 통째로 건너뛰어져 DEGRADE 레인이 조용히 2% 사이징으로 복귀했다.
    신선도 검사도 없어 낡은 판정이 무한정 쓰였다.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from modules import stream_exclusion as se


def _gate_payload(verdicts: dict, *, generated_at: str | None = None) -> dict:
    now = generated_at or datetime.now(timezone.utc).isoformat()
    return {
        "generated_at": now,
        "results": [
            {"lane": lane, "verdict": v, "n": 61, "fwd_ev": -1.23, "fwd_win": 48.0}
            for lane, v in verdicts.items()
        ],
    }


def _write_gate(tmp_path, verdicts, *, age_hours: float = 0.0):
    stamp = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    path = tmp_path / "research_recursion_gate_latest.json"
    path.write_text(json.dumps(_gate_payload(verdicts, generated_at=stamp)), encoding="utf-8")
    return path


def _sized_row(**kw):
    row = {"code": "005930", "size_pct_total": 2.0, "size_note": "총자본 2%/픽"}
    row.update(kw)
    return row


# --------------------------------------------------------------------------
# F2 — fail-closed
# --------------------------------------------------------------------------

def test_missing_gate_report_removes_sizing_instead_of_silently_allowing_it(tmp_path):
    """게이트 산출물이 없으면 사이징을 **뺀다**. 예전에는 통과시켰다."""
    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=tmp_path / "nope.json")

    assert row["stream_excluded"] is True
    assert "size_pct_total" not in row
    assert row["stream_exclusion_reason"] == "gate_unavailable"


def test_corrupt_gate_report_removes_sizing(tmp_path):
    path = tmp_path / "research_recursion_gate_latest.json"
    path.write_text('{"results": [ truncated', encoding="utf-8")

    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=path)

    assert row["stream_excluded"] is True
    assert row["stream_exclusion_reason"] == "gate_unavailable"


def test_stale_gate_report_removes_sizing(tmp_path):
    """낡은 판정을 무한정 쓰지 않는다 — 일일 산출물 기준 48h."""
    path = _write_gate(tmp_path, {"swing_candidate": "OBSERVING"}, age_hours=se.MAX_GATE_AGE_HOURS + 1)

    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=path)

    assert row["stream_excluded"] is True
    assert row["stream_exclusion_reason"] == "gate_stale"
    assert "48" in row["size_note"] or "낡" in row["size_note"]


def test_fresh_healthy_gate_keeps_sizing(tmp_path):
    path = _write_gate(tmp_path, {"swing_candidate": "OBSERVING"})

    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=path)

    assert row.get("stream_excluded") is not True
    assert row["size_pct_total"] == 2.0


def test_degrade_removes_sizing_and_labels_observation_only(tmp_path):
    path = _write_gate(tmp_path, {"swing_candidate": "DEGRADE"})

    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=path)

    assert row["stream_excluded"] is True
    assert row["stream_exclusion_reason"] == "degrade"
    assert "size_pct_total" not in row
    assert "⛔" in row["size_note"]


# --------------------------------------------------------------------------
# F1 — 단일 지점이 세 소비자 표기를 모두 덮는가
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "lane_key,gate_lane",
    [
        ("kospi_swing", "swing_candidate"),          # web
        ("kosdaq_swing", "swing_candidate"),         # web
        ("kospi_intraday", "kospi_intraday_t5"),     # web + discord(decision_bucket 동일 문자열)
        ("kosdaq_intraday", "kosdaq_intraday_t10"),  # web
        ("swing_candidate", "swing_candidate"),      # discord decision_bucket
        ("kosdaq_intraday_3d_t5_vwap_guard", "kosdaq_intraday_t10"),  # discord decision_bucket
    ],
)
def test_every_published_lane_key_resolves_to_its_gate_lane(tmp_path, lane_key, gate_lane):
    """웹 레인키와 Discord decision_bucket이 **같은 판정**을 읽어야 한다.

    F1의 본질은 두 소비자가 서로 다른 어휘를 써서 한쪽만 배선됐다는 것이다.
    """
    path = _write_gate(tmp_path, {gate_lane: "DEGRADE"})

    row = se.apply_stream_exclusion(_sized_row(), lane_key, gate_path=path)

    assert row["stream_excluded"] is True, f"{lane_key} → {gate_lane} 매핑이 끊겼다"


def test_unmapped_lanes_are_excluded_without_inheriting_another_verdict(tmp_path):
    """게이트 미판단 레인은 발행 불가(2026-08-16 정책)지만, **남의 판정을 입히지는 않는다.**

    `nasdaq_session_edge`는 원장이 `nasdaq_session_edge_operational_ledger.jsonl`이고
    게이트의 `nasdaq_session_tape`는 `nasdaq_session_tape_ledger.jsonl`을 보는 **별개 스트림**이다.
    제외 사유가 `degrade`가 아니라 `lane_unadjudicated`여야 그 구분이 지켜진 것이다 —
    tape가 DEGRADE라서 막힌 게 아니라 **판단받은 적이 없어서** 막힌 것이다.
    """
    path = _write_gate(tmp_path, {"nasdaq_session_tape": "DEGRADE"})

    for lane_key in ("nasdaq_session_edge", "b_market_neutral", "swing_ensemble"):
        row = se.apply_stream_exclusion(_sized_row(), lane_key, gate_path=path)
        assert row["stream_excluded"] is True
        assert row["stream_exclusion_reason"] != "degrade", f"{lane_key}가 타 레인 판정을 물려받았다"
        assert lane_key in se.UNGATED_PUBLISHED_LANES


def test_ungated_lanes_are_excluded_regardless_of_gate_availability(tmp_path):
    """게이트 유무와 무관하다 — 애초에 게이트가 판단하지 않는 레인이기 때문이다.

    2026-09-02 운영자 결정으로 **은퇴**했다. 불변식(발행 불가)은 그대로고 사유만 바뀐다 —
    은퇴는 게이트 판정보다 앞서므로 `lane_retired` 가 나와야 한다.
    """
    row = se.apply_stream_exclusion(_sized_row(), "nasdaq_session_edge", gate_path=tmp_path / "nope.json")

    assert row["stream_excluded"] is True
    assert row["stream_exclusion_reason"] == "lane_retired"


# --------------------------------------------------------------------------
# 롤백 스위치 · 계약 불변식
# --------------------------------------------------------------------------

def test_rollback_switch_disables_exclusion_entirely(tmp_path, monkeypatch):
    """AG_DEGRADE_STREAM_EXCLUSION=0 롤백 경로가 살아 있어야 한다(기존 계약)."""
    monkeypatch.setenv("AG_DEGRADE_STREAM_EXCLUSION", "0")
    path = _write_gate(tmp_path, {"swing_candidate": "DEGRADE"})

    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=path)

    assert row.get("stream_excluded") is not True
    assert row["size_pct_total"] == 2.0


def test_exclusion_keeps_the_pick_visible_and_scorable(tmp_path):
    """nyg6 계약: 픽은 계속 보이고 원장 채점도 계속된다 — 라우팅만 막는다."""
    path = _write_gate(tmp_path, {"swing_candidate": "DEGRADE"})
    row = se.apply_stream_exclusion(_sized_row(code="005930", prob=61.0), "kospi_swing", gate_path=path)

    assert row["code"] == "005930"
    assert row["prob"] == 61.0          # 픽 내용은 그대로
    assert row["stream_excluded"] is True


def test_verdict_details_are_carried_for_the_operator(tmp_path):
    path = _write_gate(tmp_path, {"swing_candidate": "DEGRADE"})

    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=path)

    assert "n=61" in row["size_note"]
    assert "-1.23" in row["size_note"]


def test_buy_ready_is_withdrawn_for_excluded_streams(tmp_path):
    """Discord 카드가 실행가능 매수로 나가는 것을 막는 지점 (F1의 실제 피해)."""
    path = _write_gate(tmp_path, {"swing_candidate": "DEGRADE"})
    row = _sized_row(buy_ready=True, operational_action_level="MODEL_BUY")

    row = se.apply_stream_exclusion(row, "swing_candidate", gate_path=path)

    assert row["buy_ready"] is False
    assert row["operational_action_level"] == "OBSERVE_ONLY"


# --------------------------------------------------------------------------
# F1 — Discord/top_deep 실제 발행 경로 (build_candidate_interpretation)
# --------------------------------------------------------------------------

def _degrade_gate(monkeypatch, tmp_path, lane="swing_candidate"):
    from conftest import write_gate_report

    path = write_gate_report(tmp_path / "gate.json", {lane: "DEGRADE"})
    monkeypatch.setattr(se, "DEFAULT_GATE_PATH", path)
    se.invalidate_cache()
    return path


def _model_lane_row(bucket="swing_candidate"):
    return {
        "decision_bucket": bucket,
        "ticker": "005930.KS",
        "stock_name": "삼성전자",
        "market": "KOSPI",
        "rank": 1,
        "prediction": {"phase25_prob": 0.71},
        "price": {"close": 71000, "day_change_pct": 1.2},
    }


def test_degrade_lane_no_longer_renders_an_executable_buy_card(monkeypatch, tmp_path):
    """F1 회귀: DEGRADE 레인이 Discord에서 매수카드로 나가면 안 된다.

    수정 전에는 `build_candidate_interpretation`이 게이트를 **아예 읽지 않아**
    `operational_action_level="MODEL_BUY"`, `buy_ready=True`,
    "…모델 매수 후보입니다. 진입=종가, 목표 +N%"를 그대로 내보냈다.
    """
    from modules.candidate_interpretation import build_candidate_interpretation

    _degrade_gate(monkeypatch, tmp_path)

    interp = build_candidate_interpretation(_model_lane_row())

    assert interp["stream_excluded"] is True
    assert interp["buy_ready"] is False
    assert interp["operational_action_level"] == "OBSERVE_ONLY"
    assert "⛔" in interp["operational_action_label"]
    assert "모델 매수 후보입니다" not in interp["touch_vs_buy_ready_explanation"]
    assert interp["buy_ready_blocked"] is True


def test_healthy_lane_still_renders_a_buy_card(monkeypatch, tmp_path):
    """제외가 과잉작동해 정상 레인까지 죽이면 안 된다 (양성 대조)."""
    from conftest import write_gate_report
    from modules.candidate_interpretation import build_candidate_interpretation

    path = write_gate_report(tmp_path / "gate.json")   # 전 레인 OBSERVING
    monkeypatch.setattr(se, "DEFAULT_GATE_PATH", path)
    se.invalidate_cache()

    interp = build_candidate_interpretation(_model_lane_row())

    assert interp.get("stream_excluded") is not True
    assert interp["buy_ready"] is True
    assert interp["operational_action_level"] == "MODEL_BUY"


def test_missing_gate_file_also_withdraws_the_discord_buy_card(monkeypatch, tmp_path):
    """F2가 Discord 경로에도 걸리는지 — 게이트를 못 읽으면 매수카드가 나가면 안 된다."""
    from modules.candidate_interpretation import build_candidate_interpretation

    monkeypatch.setattr(se, "DEFAULT_GATE_PATH", tmp_path / "absent.json")
    se.invalidate_cache()

    interp = build_candidate_interpretation(_model_lane_row())

    assert interp["stream_excluded"] is True
    assert interp["buy_ready"] is False
    assert interp["stream_exclusion_reason"] == "gate_unavailable"


# --------------------------------------------------------------------------
# R3 — 레인 선언 불변식
# --------------------------------------------------------------------------

def test_web_nasdaq_lane_is_declared(tmp_path):
    """`nasdaq_swing`(services.py)이 두 집합 어디에도 없어 조용히 통과했었다.

    커밋이 내세운 계약은 "공백을 코드에 명시한다"였는데 그 명시가 **Discord 어휘에만**
    적용됐다. 잡겠다던 근본원인(두 어휘)이 선언 계층에서 재발한 것이다.
    **이 테스트의 의도는 '어느 집합인가'가 아니라 '반드시 한쪽에 선언돼 있는가'다.**

    2026-08-20 이동: UNGATED -> GATE_LANE_MAP.
    08-16 분류는 이 레인이 nasdaq_session_edge 의 웹 어휘라고 적었지만,
    `services.nasdaq_picks()` 는 **2026-07-07 `10f6dfc` 에서 이미**
    nasdaq_session_tape_ledger.jsonl 로 바뀌어 있었다 — 게이트가 판정하는 그 원장이다.
    분류가 한 달 묵은 사실 위에 세워져, 게이트가 CONFIRM 을 낸 레인이 화면에선
    "게이트가 판단하지 않는 레인"으로 막혔다. 같은 '두 어휘' 실패의 재발이다.
    """
    declared_in = [name for name, coll in
                   (("GATE_LANE_MAP", se.GATE_LANE_MAP),
                    ("UNGATED", se.UNGATED_PUBLISHED_LANES))
                   if "nasdaq_swing" in coll]
    assert declared_in == ["GATE_LANE_MAP"], (
        f"정확히 한 집합에 선언돼야 한다 — 현재 {declared_in}")
    assert se.GATE_LANE_MAP["nasdaq_swing"] == "nasdaq_session_tape"


def test_web_nasdaq_lane_reads_the_ledger_its_mapping_claims(tmp_path):
    """매핑이 가리키는 원장을 웹이 실제로 읽는가.

    08-16 분류가 틀린 이유가 이것이다 — 코드가 읽는 파일을 확인하지 않고
    레인 이름만 보고 분류했다. 이름은 그대로인데 원장이 바뀌어 있었다.
    """
    from pathlib import Path as _P
    from web.backend import services as S
    from multi_agent.tools.report_research_recursion_gate import LANES as GATE_LANES
    web_ledger = S.LANES["nasdaq_swing"]["ledger"]
    gate_ledger = _P(str(GATE_LANES["nasdaq_session_tape"]["ledger"])).name
    assert web_ledger == gate_ledger, (
        f"웹은 {web_ledger} 를 읽는데 매핑은 {gate_ledger} 를 판정한다 — 배선이 틀렸다")


def test_lane_sets_are_disjoint():
    """'정확히 하나' — 두 집합에 동시에 들어가면 의미가 모순된다."""
    assert not (set(se.GATE_LANE_MAP) & set(se.UNGATED_PUBLISHED_LANES))


def test_every_discord_publish_lane_is_declared():
    from modules.operational_candidate_scoring import MODEL_VALIDATED_LANES

    assert not (set(MODEL_VALIDATED_LANES) - se.DECLARED_PUBLISHED_LANES)


def test_undeclared_lane_is_fail_closed_at_the_publish_chokepoint(tmp_path):
    """불변식을 **프로덕션 코드**로 강제한다 — 테스트 단언 하나로는 다음 레인을 못 막는다.

    발행 관문(`_pick_row`)에서 미선언 레인은 조용히 통과하는 대신 사이징을 잃고
    이유를 남긴다. 선언을 잊으면 조용히 새는 게 아니라 눈에 띄게 막힌다.
    """
    row = se.apply_stream_exclusion(
        _sized_row(), "brand_new_lane_nobody_declared", gate_path=tmp_path / "absent.json", strict=True)

    assert row["stream_excluded"] is True
    assert row["stream_exclusion_reason"] == "lane_undeclared"
    assert "size_pct_total" not in row


def test_arbitrary_discord_buckets_are_not_fail_closed(tmp_path):
    """비-strict 경로(해석 빌더)는 admission 등 임의 버킷을 지나므로 막으면 안 된다."""
    row = se.apply_stream_exclusion(_sized_row(), "", gate_path=tmp_path / "absent.json")

    assert row.get("stream_excluded") is not True
    assert row["size_pct_total"] == 2.0


# --------------------------------------------------------------------------
# R4 — verdict 화이트리스트 + 미래시각
# --------------------------------------------------------------------------

@pytest.mark.parametrize("verdict", ["CONFIRM", "OBSERVING", "EXCEED"])
def test_known_healthy_verdicts_keep_sizing(tmp_path, verdict):
    path = _write_gate(tmp_path, {"swing_candidate": verdict})

    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=path)

    assert row.get("stream_excluded") is not True


@pytest.mark.parametrize("verdict", ["DEGRADE", "DEGRADED", "degrade", 0, None, "", "UNKNOWN"])
def test_anything_not_on_the_whitelist_is_excluded(tmp_path, verdict):
    """`== "DEGRADE"` 블랙리스트는 값만 오염돼도 fail-**open**이었다.

    리포에 이미 다른 의미의 "DEGRADED"(파이프라인 헬스)가 있어 어휘충돌은 가설이 아니다.
    """
    path = _write_gate(tmp_path, {"swing_candidate": verdict})

    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=path)

    assert row["stream_excluded"] is True, f"verdict={verdict!r} 가 통과했다"


def test_future_dated_gate_report_is_rejected(tmp_path):
    """음수 age 미검사 — 미래시각 리포트가 영원히 '신선'했다."""
    path = _write_gate(tmp_path, {"swing_candidate": "OBSERVING"}, age_hours=-100)

    row = se.apply_stream_exclusion(_sized_row(), "kospi_swing", gate_path=path)

    assert row["stream_excluded"] is True
    assert row["stream_exclusion_reason"] == "gate_stale"


def test_ungated_lane_loses_its_card(monkeypatch, tmp_path):
    """2026-08-16 정책 — 게이트가 판단하지 않는 레인은 매수카드를 못 낸다."""
    from modules.candidate_interpretation import build_candidate_interpretation

    monkeypatch.setattr(se, "DEFAULT_GATE_PATH", tmp_path / "absent.json")
    se.invalidate_cache()

    interp = build_candidate_interpretation(_model_lane_row("nasdaq_session_edge"))

    assert interp["stream_excluded"] is True
    assert interp["buy_ready"] is False


# --------------------------------------------------------------------------
# R5 — 사문화된 옛 리더 제거
# --------------------------------------------------------------------------

def test_old_fail_open_gate_reader_is_gone():
    """`_gate_verdicts`/`_GATE_LANE_MAP`는 호출자가 없는 **두 번째 낡은 사본**이다.

    단일 출처를 만든다는 목적과 정반대다 — 나중에 이쪽을 고치면 아무 효과가 없고,
    `_gate_verdicts`를 재사용하면 F2(fail-open)가 되살아난다.
    """
    from web.backend import services

    assert not hasattr(services, "_gate_verdicts")
    assert not hasattr(services, "_GATE_LANE_MAP")
    assert not hasattr(services, "_GATE_VERDICT_CACHE")
