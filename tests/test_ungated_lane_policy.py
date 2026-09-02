"""UNGATED = '게이트가 판단하지 않는다' ≠ '발행해도 된다' (운영자 정책 2026-08-16).

이전 정책(2026-08-15)은 "fail-closed 범위는 게이트가 덮는 레인뿐"이었고,
그래서 `UNGATED_PUBLISHED_LANES`는 **선언만 하고 통과**시켰다.
그 결과 2026-07-19에 아카이브된 `swing_ensemble`의 저장행 77건이 지금도
`buy_ready=True`로 매수카드가 됐다. 게이트가 판단하지 않는다는 사실이
발행 허가로 읽히고 있었던 것이다.

**새 정책: 게이트 미판단 레인은 발행 불가.**

일괄 차단을 택한 근거 (실측):

| 레인 | forward 근거 | 상태 |
|---|---|---|
| `swing_ensemble` | 판정 완료 **DEGRADE** (n=112, EV −0.72) | 2026-07-19 아카이브, 게이트 LANES에서 제거 |
| `nasdaq_session_edge` | 자기 원장 **1행, 2026-06-26** (7주 경과) | 근거 없음 |
| `nasdaq_swing` | 위 레인의 웹 어휘 | 동일 |
| `b_market_neutral` | 게이트가 b 두 레인 모두 DEGRADE | 2026-08-03 정지 |

**네 레인 중 현재 forward 근거를 가진 레인이 하나도 없다.**
즉 '자기 원장 근거로 가른다'는 분기는 오늘 결과를 바꾸지 못하고,
**게이트 밖에 두 번째 판정 권위를 만드는 것**뿐이다 — F1·R5에서 닫아 온
'판정 사본이 둘'이라는 실패 계열 그 자체다. `nasdaq_session_edge`를 다시 발행하려면
그 레인을 게이트 LANES에 배선하는 게 정답이지, 여기서 예외를 두는 게 아니다.
"""
from __future__ import annotations

import pytest

from modules import stream_exclusion as se


def _sized_row(**kw):
    row = {"code": "005930", "size_pct_total": 2.0, "buy_ready": True,
           "operational_action_level": "MODEL_BUY"}
    row.update(kw)
    return row


@pytest.mark.parametrize("lane", sorted(se.UNGATED_PUBLISHED_LANES))
def test_every_ungated_lane_is_blocked_from_publishing(lane, tmp_path):
    """정책의 본문 — 게이트가 판단하지 않는 레인은 발행하지 않는다."""
    from conftest import write_gate_report

    row = se.apply_stream_exclusion(_sized_row(), lane, gate_path=write_gate_report(tmp_path / "g.json"))

    assert row["stream_excluded"] is True, f"{lane} 이 발행 가능 상태로 남았다"
    assert "size_pct_total" not in row
    assert row["buy_ready"] is False
    assert row["operational_action_level"] == "OBSERVE_ONLY"


def test_archived_lane_says_it_is_retired(tmp_path):
    """`swing_ensemble` — 판정이 없는 게 아니라 **DEGRADE 판정 후 은퇴**한 레인이다."""
    from conftest import write_gate_report

    row = se.apply_stream_exclusion(_sized_row(), "swing_ensemble",
                                    gate_path=write_gate_report(tmp_path / "g.json"))

    assert row["stream_exclusion_reason"] == "lane_retired"
    assert "2026-07-19" in row["size_note"]


def test_unadjudicated_lane_says_how_to_get_back(tmp_path):
    """`nasdaq_session_edge` — 별개 스트림이라 tape 판정을 물려줄 수 없다.

    2026-09-02 은퇴. 복귀 경로가 게이트 배선에서 **데이터 확보**로 바뀌었으므로 사유도 바뀐다 —
    사유 문구는 레인마다 달라야 한다(하나로 뭉쳐 두면 남의 은퇴 사유가 붙는다. 실제로 그랬다).
    """
    from conftest import write_gate_report

    row = se.apply_stream_exclusion(_sized_row(), "nasdaq_session_edge",
                                    gate_path=write_gate_report(tmp_path / "g.json"))

    assert row["stream_exclusion_reason"] == "lane_retired"   # 2026-09-02 은퇴
    assert "은퇴" in row["size_note"]
    assert "multi_year_overnight_provider_not_loaded" in row["size_note"], \
        "복귀에 필요한 것이 무엇인지 적혀 있어야 한다"
    # 남의 레인 은퇴 사유가 붙지 않는다
    assert "상한가" not in row["size_note"]


def test_suspended_lane_is_named_as_suspended(tmp_path):
    from conftest import write_gate_report

    row = se.apply_stream_exclusion(_sized_row(), "b_market_neutral",
                                    gate_path=write_gate_report(tmp_path / "g.json"))

    assert row["stream_exclusion_reason"] == "lane_suspended"


def test_gated_healthy_lane_is_untouched(tmp_path):
    """양성 대조 — 정책이 게이트가 판단한 정상 레인까지 죽이면 안 된다."""
    from conftest import write_gate_report

    path = write_gate_report(tmp_path / "g.json", {"kosdaq_intraday_t10": "OBSERVING"})
    row = se.apply_stream_exclusion(_sized_row(), "kosdaq_intraday", gate_path=path)

    assert row.get("stream_excluded") is not True
    assert row["size_pct_total"] == 2.0
    assert row["buy_ready"] is True


def test_arbitrary_non_publish_buckets_are_still_not_blocked(tmp_path):
    """admission 등 **발행 레인이 아닌** decision_bucket은 계속 통과해야 한다.

    이걸 막으면 top_deep의 일반 후보 카드가 통째로 죽는다. 정책 대상은
    '선언된 발행 레인'이지 임의 버킷이 아니다.
    """
    for bucket in ("", "admission_pass", "admission_near_miss", "kis_shadow_blocked_watch"):
        row = se.apply_stream_exclusion(_sized_row(), bucket, gate_path=tmp_path / "absent.json")
        assert row.get("stream_excluded") is not True, f"{bucket!r} 가 막혔다"


def test_archived_lane_stored_interpretation_loses_its_buy_card(tmp_path, monkeypatch):
    """실제 피해 지점 — 저장된 swing_ensemble 해석 77건이 매수카드로 나가던 경로."""
    from conftest import write_gate_report
    from modules.discord_integration import renderers

    monkeypatch.setattr(se, "DEFAULT_GATE_PATH", write_gate_report(tmp_path / "g.json"))
    se.invalidate_cache()
    row = {"decision_bucket": "swing_ensemble", "ticker": "005930.KS",
           "candidate_interpretation": {"buy_ready": True, "operational_action_level": "MODEL_BUY",
                                        "touch_vs_buy_ready_explanation": "…모델 매수 후보입니다."}}

    interp = renderers._interpretation_for_render(row)

    assert interp["stream_excluded"] is True
    assert interp["buy_ready"] is False
    assert interp["operational_action_level"] == "OBSERVE_ONLY"


def test_every_ungated_lane_has_a_declared_kind():
    """새 레인을 UNGATED에 넣으면서 사유 분류를 빠뜨리면 안 된다 (조용한 공백 방지)."""
    assert set(se.UNGATED_PUBLISHED_LANES) == set(se.UNGATED_LANE_KINDS)
