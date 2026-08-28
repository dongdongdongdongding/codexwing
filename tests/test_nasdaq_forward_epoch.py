"""나스닥 세션테이프 레인의 전진 수치가 **어느 구성을 채점했는지** 드러내게 한다.

실측(2026-08-28): 정산 56건 중 **55건이 편입컷 도입 이전** 픽인데 `ev_net_avg` −0.28 이
A1 셀의 성적처럼 읽혔다. KR 스윙 레인에서 같은 결함을 이미 고쳤다(`c8bb51b`).

표지는 `xq` — 편입자격 컷이 **발행 시점에** 쓰는 필드다. `contract_h` 는 표지가 아니다:
정산 시점에도 찍혀 전환 이전 픽에 붙는다.
"""
import inspect

from multi_agent.tools import report_nasdaq_session_tape as N

SRC = inspect.getsource(N)


def test_epoch_marker_is_the_admission_field_not_contract_h():
    body = SRC[SRC.index("def resolve_pending"):]
    assert 'r.get("xq") is not None' in body
    assert 'r.get("contract_h") is not None' not in body, "contract_h 는 정산 시점에도 찍힌다"


def test_summary_carries_both_epochs():
    body = SRC[SRC.index("def resolve_pending"):]
    assert '"epoch"' in body and '"current"' in body and '"previous"' in body


def test_a_thin_current_epoch_says_it_is_not_a_verdict_sample():
    body = SRC[SRC.index("def resolve_pending"):]
    assert "len(cur) < 30" in body, "레인 자체 승격 기준(n>=30)과 같은 문턱이어야 한다"
    assert "판정 표본이 아니다" in body


def test_the_lane_states_its_own_promotion_rule():
    """승격 기준이 코드에 남아 있어야 한다 — 이 경계의 문턱 근거다."""
    assert "no capital before forward n>=30" in SRC
