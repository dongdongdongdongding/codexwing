"""사전등록 킬이 **선언만 되고 집행되지 않는 것**을 막는다.

`kr_ranking_shadow_depth_monotonicity` 는 2026-08-16 에 킬로 선언됐는데
`AG_SWING_RANKING_SHADOW` 기본값이 `"1"` 로 남아 있어 그 뒤로 **1,304행**이 더 쌓였다.
센티넬 `kr_ranking_shadow_kill_enforced`(critical)가 「죽은 보드가 생산을 재개했다」로
발동해 있었지만 아무도 기본값을 내리지 않았다.
"""
import inspect

from multi_agent.tools import report_kr_swing_candidate as R

SRC = inspect.getsource(R)


def test_shadow_ledger_is_off_by_default():
    assert 'os.getenv("AG_SWING_RANKING_SHADOW", "0")' in SRC, \
        "킬된 보드는 기본값이 꺼짐이어야 한다 — 선언만으론 집행되지 않는다"


def test_it_can_still_be_turned_back_on_deliberately():
    """되살리는 길은 남긴다 — 다만 명시적 opt-in 이어야 한다(킬을 되돌리는 결정)."""
    assert '"1", "true", "True"' in SRC


def test_the_kill_date_is_recorded_next_to_the_guard():
    """왜 꺼져 있는지가 코드에 없으면 다음 사람이 되켠다."""
    # 모듈 docstring 에도 이름이 나오므로 **가드 호출부**를 집어야 한다.
    i = SRC.index('os.getenv("AG_SWING_RANKING_SHADOW"')
    around = SRC[max(0, i - 700):i]
    assert "2026-08-16" in around and "킬" in around
