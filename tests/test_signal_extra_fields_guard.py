"""`/signals` 카드의 extra 필드가 계약을 지나는가 (audit-stream-exclusion.md R2).

`build_model_signals_embed`는 모델레인 행을 훅에 통과시킨 뒤, **같은 카드에**
훅 **밖에서** 두 종류의 필드를 덧붙인다(renderers.py:910-916, 936):

    extra += _nasdaq_signal_fields()   # mode in ("", "SWING")
    extra += _b_signal_fields()        # mode == ""

`_b_signal_fields()`는 `b_picks_latest.json`을 **직독**한다 —
`build_candidate_interpretation` 미경유 · 게이트 미조회 · **`b_lane_suspended.json` 가드 없음**.

웹은 같은 픽을 `services.py:453`에서 `return []`로 막고 주석에 이유까지 적어놨다:
"스캔이 멈추면 b_picks_latest.json 날짜가 동결되므로 명시적 서스펜션 게이트 필요".
실측: 그 파일은 **scan_date 2026-08-10에 동결**됐는데 10픽이 확률 98.1%를 달고
지금도 Discord `/signals`로 나간다. **같은 픽에 대해 두 소비자가 정반대로 동작한다.**

이건 8067dc5와 무관한 **기존 라이브 결함**이다.
"""
from __future__ import annotations

import json

import pytest

from modules.discord_integration import renderers


@pytest.fixture
def b_picks(tmp_path, monkeypatch):
    """b_picks_latest.json + 정지 마커를 tmp로 돌린다."""
    from b_engine import model_scan

    picks = tmp_path / "b_picks_latest.json"
    picks.write_text(json.dumps({
        "scan_date": "2026-08-10",
        "picks": [{"code": "005930", "name": "삼성전자", "prob_win": 98.1,
                   "pred_alpha_5d": 12.735, "close": 1513, "hold_days": 5}],
    }), encoding="utf-8")
    monkeypatch.setattr(renderers, "_B_PICKS_PATH", str(picks))
    monkeypatch.setattr(model_scan, "SUSPEND_MARKER", str(tmp_path / "b_lane_suspended.json"))
    return tmp_path


def _suspend(root):
    (root / "b_lane_suspended.json").write_text(
        json.dumps({"suspended": True, "since": "2026-08-03", "reason": "PKG-A §40"}), encoding="utf-8")


def test_suspended_b_lane_does_not_reach_the_signals_card(b_picks):
    """라이브 결함 회귀 — 정지된 레인의 동결 픽이 Discord로 나가면 안 된다."""
    _suspend(b_picks)

    assert renderers._b_signal_fields() == []


def test_b_picks_render_only_when_the_lane_is_both_live_and_adjudicated(b_picks, monkeypatch, tmp_path):
    """양성 대조 — 과잉차단이 아님을 보인다.

    2026-08-16 정책 이후 b_market_neutral은 UNGATED라 정지 여부와 무관하게 막힌다.
    그래서 '정지 아님'만으로는 부족하고, 게이트에 배선돼 정상 판정을 받아야 나간다.
    """
    from conftest import write_gate_report
    from modules import stream_exclusion as se

    monkeypatch.setattr(se, "DEFAULT_GATE_PATH",
                        write_gate_report(tmp_path / "g.json", {"b_all_top10": "OBSERVING"}))
    monkeypatch.setitem(se.GATE_LANE_MAP, "b_market_neutral", "b_all_top10")
    se.invalidate_cache()

    fields = renderers._b_signal_fields()

    assert len(fields) == 1
    assert "98.1" in fields[0]["value"]


def test_signals_embed_drops_b_fields_while_suspended(b_picks, monkeypatch):
    """카드 조립 지점에서도 실제로 빠지는지 (필드 함수만이 아니라 소비자까지)."""
    _suspend(b_picks)
    monkeypatch.setattr(renderers, "_load_top_deep_reports", lambda **kw: [])
    monkeypatch.setattr(renderers, "_nasdaq_signal_fields", lambda *a, **k: [])

    embeds = renderers.build_model_signals_embed()

    blob = json.dumps(embeds, ensure_ascii=False)
    assert "B 시장중립" not in blob
    assert "98.1" not in blob


def test_unreadable_suspension_marker_blocks_publication(b_picks):
    """마커를 못 읽으면 정지로 취급 — 엔진 계약(fail-closed)과 같은 방향."""
    (b_picks / "b_lane_suspended.json").write_text("{truncated", encoding="utf-8")

    assert renderers._b_signal_fields() == []


def test_extra_field_lanes_go_through_the_stream_contract(b_picks, monkeypatch, tmp_path):
    """R2의 구조적 요지 — 나중에 b_market_neutral을 매핑하면 이 경로도 걸려야 한다.

    지금은 두 레인 다 UNGATED라 판정 결과가 안 바뀐다. 그래서 '오늘 안 바뀐다'가 아니라
    '매핑되면 걸린다'를 못박는다. 이게 없으면 F1이 났던 방식 그대로 반쪽만 적용된다.
    """
    from conftest import write_gate_report
    from modules import stream_exclusion as se

    path = write_gate_report(tmp_path / "gate.json", {"b_all_top10": "DEGRADE"})
    monkeypatch.setattr(se, "DEFAULT_GATE_PATH", path)
    monkeypatch.setitem(se.GATE_LANE_MAP, "b_market_neutral", "b_all_top10")
    se.invalidate_cache()

    assert renderers._b_signal_fields() == []


def test_nasdaq_extra_fields_go_through_the_stream_contract(monkeypatch, tmp_path):
    """`_nasdaq_signal_fields()`도 훅을 안 지나던 같은 계열이다."""
    from conftest import write_gate_report
    from modules import stream_exclusion as se

    monkeypatch.setattr(renderers, "_nasdaq_rows", lambda limit: [
        {"ticker": "AAPL", "stock_name": "Apple", "prediction": {"phase25_prob": 71},
         "candidate_interpretation": {"entry_reference_price": 210.0}}])

    path = write_gate_report(tmp_path / "gate.json", {"nasdaq_session_tape": "DEGRADE"})
    monkeypatch.setattr(se, "DEFAULT_GATE_PATH", path)
    monkeypatch.setitem(se.GATE_LANE_MAP, "nasdaq_session_edge", "nasdaq_session_tape")
    se.invalidate_cache()

    assert renderers._nasdaq_signal_fields() == []
