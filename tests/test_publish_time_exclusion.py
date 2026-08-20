"""저장된 해석에도 **발행시점** 판정이 적용되는가 (audit-stream-exclusion.md R1).

세 렌더 지점이 전부 같은 패턴이다 (renderers.py:520 / 981 / 1252):

    interpretation = row.get("candidate_interpretation") if isinstance(..., dict) \\
                     else build_candidate_interpretation(row)

**저장된 해석이 있으면 훅을 지나지 않는다.** 그런데 행의 출처는 영속 저장소다 —
생산자들이 스캔 시점에 `row["candidate_interpretation"]`을 박아 저장하고
(`report_kosdaq_intraday_vwap_guard.py:573` 등 5곳), 렌더러는 그 저장값을 우선한다.

운영자 확인(라이브 Supabase): `scan_deep_reports` 모델레인 행 **200/200 전부**가
`candidate_interpretation`을 들고 저장돼 있고 `buy_ready`·`operational_action_level`이
그대로 굳어 있다. 즉 카드에 굳는 건 **발행시점이 아니라 스캔시점의 게이트 상태**다.

- 스캔은 장중, 재귀게이트는 dailyops(야간) → 최소 한 사이클 지연이 상시 존재
- `build_archive_embed`는 과거 run을 렌더하므로 지연이 **무기한**
- 8067dc5 이전 저장행은 애초에 게이트를 안 거친 해석을 들고 있다
- **48h fail-closed도 이 경로는 못 막는다 — 게이트를 읽지를 않으므로**
"""
from __future__ import annotations

import pytest

from modules import stream_exclusion as se
from modules.candidate_interpretation import apply_publish_time_exclusion
from modules.discord_integration import renderers


@pytest.fixture
def degrade_gate(tmp_path, monkeypatch):
    from conftest import write_gate_report

    path = write_gate_report(tmp_path / "gate.json", {"swing_candidate": "DEGRADE"})
    monkeypatch.setattr(se, "DEFAULT_GATE_PATH", path)
    se.invalidate_cache()
    return path


def _row_with_stored_interpretation(**interp_extra):
    """8067dc5 **이전**에 저장된 모양 — 게이트를 한 번도 안 거친 해석."""
    stored = {
        "version": "candidate_interpretation_v2",
        "lane": "swing_candidate",
        "buy_ready": True,
        "buy_ready_blocked": False,
        "buy_ready_block_reasons": [],
        "operational_action_level": "MODEL_BUY",
        "operational_action_label": "모델 매수",
        "touch_vs_buy_ready_explanation": "…모델 매수 후보입니다. 진입=종가, 목표 +5%",
        "entry_reference_price": 71000,
    }
    stored.update(interp_extra)
    return {"decision_bucket": "swing_candidate", "ticker": "005930.KS",
            "stock_name": "삼성전자", "market": "KOSPI", "rank": 1,
            "candidate_interpretation": stored}


def test_stored_interpretation_is_re_judged_at_render_time(degrade_gate):
    """핵심 — 저장된 해석에도 오늘의 판정이 적용돼야 한다."""
    row = _row_with_stored_interpretation()

    interp = renderers._interpretation_for_render(row)

    assert interp["stream_excluded"] is True
    assert interp["buy_ready"] is False
    assert interp["operational_action_level"] == "OBSERVE_ONLY"
    assert "모델 매수 후보입니다" not in interp["touch_vs_buy_ready_explanation"]


def test_pre_commit_rows_are_covered(degrade_gate):
    """8067dc5 이전 저장행(stream_excluded 필드 자체가 없음)도 덮여야 한다."""
    row = _row_with_stored_interpretation()
    assert "stream_excluded" not in row["candidate_interpretation"]

    assert renderers._interpretation_for_render(row)["stream_excluded"] is True


def test_the_stored_row_itself_is_not_mutated(degrade_gate):
    """저장본을 제자리 수정하면 재계산이 1회성이 되고 원본이 오염된다."""
    row = _row_with_stored_interpretation()

    renderers._interpretation_for_render(row)

    assert row["candidate_interpretation"]["buy_ready"] is True
    assert "stream_excluded" not in row["candidate_interpretation"]


def test_recovered_lane_restores_the_buy_card(tmp_path, monkeypatch):
    """반대 방향 — 레인이 회복하면 굳어 있던 제외가 풀려야 한다.

    제외만 적용하고 해제를 못 하면, DEGRADE 시절 저장된 행이 레인 회복 후에도
    영원히 관측전용으로 남는다. 안전한 방향이긴 하나 '발행시점 판정'은 아니다.
    """
    from conftest import write_gate_report

    monkeypatch.setattr(se, "DEFAULT_GATE_PATH",
                        write_gate_report(tmp_path / "gate.json", {"swing_candidate": "OBSERVING"}))
    se.invalidate_cache()

    # DEGRADE 시절에 제외된 채로 저장된 해석
    row = _row_with_stored_interpretation(
        buy_ready=False, operational_action_level="OBSERVE_ONLY",
        stream_excluded=True, stream_exclusion_reason="degrade",
        buy_ready_before_exclusion=True)

    interp = renderers._interpretation_for_render(row)

    assert interp.get("stream_excluded") is not True
    assert interp["buy_ready"] is True
    assert interp["operational_action_level"] == "MODEL_BUY"


def test_reapplication_is_idempotent(degrade_gate):
    """두 번 적용해도 같은 결과여야 한다 (렌더가 여러 번 일어난다)."""
    row = _row_with_stored_interpretation()

    once = renderers._interpretation_for_render(row)
    twice = apply_publish_time_exclusion(dict(once), "swing_candidate")

    assert twice["buy_ready"] is False
    assert twice["stream_excluded"] is True
    assert twice["buy_ready_before_exclusion"] is True


def test_ungated_lane_stored_rows_are_also_blocked(degrade_gate):
    """무게이트 레인의 저장 해석도 발행 불가다 (2026-08-16 정책).

    사유는 `lane_unadjudicated` — tape의 DEGRADE를 물려받은 게 아니다.
    """
    row = _row_with_stored_interpretation()
    row["decision_bucket"] = "nasdaq_session_edge"
    row["candidate_interpretation"]["lane"] = "nasdaq_session_edge"

    interp = renderers._interpretation_for_render(row)

    assert interp["stream_excluded"] is True
    assert interp["stream_exclusion_reason"] == "lane_unadjudicated"
    assert interp["buy_ready"] is False


def test_rows_without_stored_interpretation_still_build_one(degrade_gate):
    """저장본이 없으면 종전대로 빌드한다 (경로 회귀 방지)."""
    row = {"decision_bucket": "swing_candidate", "ticker": "005930.KS", "market": "KOSPI",
           "prediction": {"phase25_prob": 0.7}, "price": {"close": 71000}}

    interp = renderers._interpretation_for_render(row)

    assert interp["stream_excluded"] is True
    assert interp["buy_ready"] is False


@pytest.mark.parametrize("render_fn_line", ["top_deep", "signals", "archive"])
def test_all_three_render_surfaces_use_the_publish_time_path(render_fn_line):
    """세 표면이 전부 같은 헬퍼를 지나는지 — 하나라도 빠지면 R1이 반쪽만 닫힌다."""
    import inspect

    src = inspect.getsource(renderers)
    # 저장본 우선 패턴이 남아 있으면 그 표면은 아직 발행시점 판정을 안 받는다
    assert 'row.get("candidate_interpretation") if isinstance' not in src
    assert 'r.get("candidate_interpretation") if isinstance' not in src
    assert src.count("_interpretation_for_render(") >= 4   # 정의 1 + 호출 3
