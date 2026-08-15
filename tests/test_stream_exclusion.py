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


def test_unmapped_lanes_are_left_alone_and_declared(tmp_path):
    """게이트가 덮지 않는 레인은 건드리지 않는다 — 남의 판정을 입히지 않는다.

    `nasdaq_session_edge`는 라이브 모델 레인이고 원장이
    `nasdaq_session_edge_operational_ledger.jsonl`이다. 게이트의 `nasdaq_session_tape`는
    `nasdaq_session_tape_ledger.jsonl`을 보는 **별개 스트림**이라 판정을 물려받으면 틀린다.
    """
    path = _write_gate(tmp_path, {"nasdaq_session_tape": "DEGRADE"})

    for lane_key in ("nasdaq_session_edge", "b_market_neutral", "swing_ensemble"):
        row = se.apply_stream_exclusion(_sized_row(), lane_key, gate_path=path)
        assert row.get("stream_excluded") is not True, f"{lane_key}는 무게이트여야 한다"
        assert row["size_pct_total"] == 2.0
        assert lane_key in se.UNGATED_PUBLISHED_LANES


def test_unmapped_lanes_stay_sized_even_when_the_gate_is_missing(tmp_path):
    """fail-closed 범위는 '게이트가 덮는 레인'뿐 (운영자 결정 2026-08-15)."""
    row = se.apply_stream_exclusion(_sized_row(), "nasdaq_session_edge", gate_path=tmp_path / "nope.json")

    assert row.get("stream_excluded") is not True
    assert row["size_pct_total"] == 2.0


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


def test_ungated_lane_keeps_its_card_even_without_a_gate(monkeypatch, tmp_path):
    """nasdaq_session_edge는 무게이트 — 게이트가 없어도 현상 유지 (운영자 결정)."""
    from modules.candidate_interpretation import build_candidate_interpretation

    monkeypatch.setattr(se, "DEFAULT_GATE_PATH", tmp_path / "absent.json")
    se.invalidate_cache()

    interp = build_candidate_interpretation(_model_lane_row("nasdaq_session_edge"))

    assert interp.get("stream_excluded") is not True
    assert interp["buy_ready"] is True
