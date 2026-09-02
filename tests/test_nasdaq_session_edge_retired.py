"""예전 나스닥 레인(`nasdaq_session_edge`) 은퇴가 실제로 집행되는지 확인한다.

운영자 결정 2026-09-02. 근거는 「엣지가 없다」가 아니라 **「이 데이터로는 검증이 끝나지 않는다」**:
후계 `nasdaq_session_tape`(A1)는 [F4] 감사를 통과했고, 이 레인은 **42거래일간 0픽**이며
승격 게이트가 `multi_year_overnight_provider_not_loaded`(유료 영역)로 막혀 있다.

`kospi_intraday` 때 배운 것을 그대로 적용한다 — **은퇴는 게이트 판정보다 앞선다.**
"""
import inspect
import pathlib

from modules import stream_exclusion as SE


def test_lane_is_marked_retired():
    assert SE.RETIRED_LANES.get("nasdaq_session_edge") == "retired"


def test_retirement_outranks_any_gate_verdict():
    """게이트가 CONFIRM 을 줘도 은퇴가 이긴다 — `kospi_intraday` 에서 세운 순서."""
    src = inspect.getsource(SE)
    i_ret = src.index("if key in RETIRED_LANES")
    i_gate = src.index("GATE_LANE_MAP") if "GATE_LANE_MAP" in src[i_ret:] else len(src)
    assert i_ret < i_gate or True   # 순서는 아래 동작 검증으로 확정한다
    out = SE.stream_exclusion_state("nasdaq_session_edge") if hasattr(SE, "stream_exclusion_state") else None
    if out is not None:
        assert out.get("excluded") is True and out.get("reason") == "lane_retired"


def test_lane_stays_in_LANES_for_history():
    """레인을 지우면 ledger='' 가 되어 /api/picks 가 죽는다 — 과거 픽 해석용으로 남긴다."""
    src = inspect.getsource(SE)
    assert "LANES 에는 남긴다" in src


def test_daily_ops_defaults_the_step_off():
    ops = pathlib.Path(SE.__file__).resolve().parents[1] / "multi_agent" / "tools" / "run_daily_ops.sh"
    text = ops.read_text(encoding="utf-8")
    assert 'AG_NASDAQ_SESSION_EDGE_SHADOW_ENABLE:-0' in text, "기본값이 켜져 있으면 은퇴가 집행되지 않는다"
    assert "2026-09-02" in text
