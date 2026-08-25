"""`subsample` 이 켜져 있다고 오해되는 것을 막는다.

`subsample=0.8` 은 `subsample_freq=0` 에서 **아무 일도 안 한다**. 8년 walk-forward 의
근거 셀이 전부 이 무효 상태에서 나왔으므로, 배깅을 켜면 라이브가 근거와 끊긴다.
[W5] 는 이 파라미터를 라이브 픽 비결정성의 원인으로 지목했는데, [W7] 이 행 순서를
세 가지로 섞어도 전 종목 `p` 최대차가 정확히 0 임을 보였다 — 무효라서 그렇다.
"""
from multi_agent.tools import report_kr_swing_candidate as R


def test_bagging_frequency_is_zero_so_subsample_does_nothing():
    m = R._model() if hasattr(R, "_model") else None
    if m is None:                       # 생성자명이 바뀌면 소스로 확인한다
        import inspect

        src = inspect.getsource(R)
        assert "subsample_freq=0" in src, "배깅이 켜지면 8y WF 근거 셀과 끊긴다"
        return
    params = m.get_params()
    assert params.get("subsample_freq", 0) == 0, "배깅이 켜지면 8y WF 근거 셀과 끊긴다"


def test_the_dead_parameter_is_documented_as_dead():
    """주석 없이 놔두면 다음 사람이 「배깅 켜져 있네」로 읽고 셀을 끊는다."""
    import inspect

    src = inspect.getsource(R)
    assert "무효" in src and "subsample" in src
