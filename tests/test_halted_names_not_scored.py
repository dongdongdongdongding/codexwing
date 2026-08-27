"""신호일에 거래가 없던 종목이 픽 후보에 들어가는 것을 막는다.

실측([E4] + 원장 직접 검증): 유동성 필터가 롤링 `liq` 라 거래정지 시작 후에도 한참
통과한다. 정지일 픽이 백테 4,632건 중 98건(거래당 −3.94 vs 정상 +1.57)이고,
**라이브 원장에 이미 6건이 나가 평균 −5.75%** 였다. `px_long` 은 정지일
open/high/low 를 종가로 평탄화하므로 그 봉 위의 피처는 합성값이다.

학습에서는 빼지 않는다 — 함정 3(「못 사는 행은 학습에 넣는다」). 이 필터는
**선택 시점**에만 걸리고, 신호일 거래량은 그 시점에 관측 가능하므로 미래정보가 아니다.
"""
import inspect

from multi_agent.tools import report_kr_swing_candidate as R

SRC = inspect.getsource(R)


def test_volume_column_is_loaded_for_scoring():
    assert '"volume"' in SRC.split("def score_today")[1].split("for mkt in")[0]


def test_candidates_exclude_zero_volume_signal_days():
    body = SRC.split('te = d[d["date"] == latest]')[1].split('te["p"] =')[0]
    assert 'te["volume"].fillna(0) > 0' in body, "정지일 종목이 후보에 들어가면 안 된다"


def test_training_set_is_not_filtered_by_volume():
    """함정 3 — 못 사는 행은 학습에 남긴다. tr 에 volume 필터가 생기면 위반이다."""
    body = SRC.split("def score_today")[1]
    tr_part = body.split("tr = d[")[1].split("te = d[")[0]
    assert "volume" not in tr_part
