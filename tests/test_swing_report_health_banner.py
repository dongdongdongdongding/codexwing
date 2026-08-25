"""데이터 건강 경고가 **읽히는 곳**에 나오는지 확인한다.

가드를 넣어도 아무도 안 보는 곳에 찍으면 소용이 없다. 실측으로 이 도구의 산출을
읽는 것은 **일일 운영이 잡는 stdout 한 줄** 뿐이다 — 웹은 이 보고서를 아예 안 읽고
(`kr_swing_candidate_latest.json` 참조 0건), MD 를 읽는 소비자도 없다.
"""
import inspect

from multi_agent.tools import report_kr_swing_candidate as R


SRC = inspect.getsource(R)


def test_stdout_summary_carries_the_health_fields():
    """일일 운영이 잡는 유일한 줄이다. 여기 없으면 경고가 사라진다."""
    tail = SRC[SRC.index("print(json.dumps({\"as_of\""):]
    assert "label_stale_days" in tail
    assert "universe_anomalous" in tail


def test_markdown_puts_health_above_the_picks():
    """픽 아래에 적으면 안 읽는다."""
    body = SRC[SRC.index("lines = [f\"# KR swing CANDIDATE picks"):]
    banner = body.index("데이터 건강 경고")
    table = body.index("| Market | Ticker |")
    assert banner < table, "경고가 픽 표보다 뒤에 있으면 안 된다"


def test_a_healthy_run_says_nothing():
    """정상일 때 경고가 뜨면 다음부터 아무도 안 읽는다."""
    body = SRC[SRC.index("health = []"):SRC.index("lines = [f\"# KR swing CANDIDATE picks")]
    # 두 경고 모두 조건부여야 한다
    assert "if scored.get(\"label_stale_days\")" in body
    assert "if _u.get(\"anomalous\")" in body
