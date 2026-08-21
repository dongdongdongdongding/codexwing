"""진입기권 w60q0.7 의 규칙 검정 (사양: research/SPEC_w60q0.7.md).

순수 테스트다 — 모델도, parquet 도, runtime_state 도 건드리지 않는다. 일별 top-p 계열만
넣어서 판정 규칙 자체를 검정한다. 규칙이 조용히 바뀌면 여기서 깨져야 한다.

배경: 이 사양을 만든 에이전트 [Q] 는 재개 불가(전사 소실)였고 산출물도 /tmp 와 함께 사라졌다.
규칙은 EDGE_BOARD.md 본문에서 복원했다. 그래서 규칙을 코드가 아니라 **테스트로** 고정한다.
"""
import numpy as np
import pandas as pd
import pytest

import multi_agent.tools.report_kr_swing_candidate as swc


def _series(vals, start="2020-01-01"):
    return pd.Series(vals, index=pd.bdate_range(start, periods=len(vals)))


def test_window_is_60_trading_days_and_excludes_today():
    """창은 직전 60거래일이고 당일은 분위 계산에 들어가지 않는다(인과)."""
    hist = list(np.linspace(0.10, 0.69, 60))       # 60일: 0.10..0.69
    ser = _series(hist + [0.99])                   # 오늘 top-p = 0.99 (분포 밖)
    latest = ser.index[-1]
    v = swc._gate_decide(ser, latest)
    assert v["gate_history_days"] == 60
    # 오늘(0.99)이 창에 섞였다면 0.7분위가 위로 끌려간다. 창이 순수 과거면 그러지 않는다.
    assert v["gate_threshold"] == pytest.approx(float(np.quantile(hist, 0.7)), abs=1e-9)
    assert v["fire"] is True and v["gate"] == "FIRE"


def test_older_than_60_days_is_dropped():
    """60거래일보다 오래된 값은 창에 들어가지 않는다 — 창 길이가 이 셀의 핵심 부품이다."""
    ancient = [0.99] * 40                          # 창 밖의 아주 높은 값들
    recent = list(np.linspace(0.10, 0.69, 60))
    ser = _series(ancient + recent + [0.50])
    v = swc._gate_decide(ser, ser.index[-1])
    assert v["gate_history_days"] == 60
    assert v["gate_threshold"] == pytest.approx(float(np.quantile(recent, 0.7)), abs=1e-9)


def test_abstains_below_threshold():
    """미달이면 그날은 사지 않는다 — 순위 강등이 아니라 발행 취소다."""
    hist = list(np.linspace(0.10, 0.69, 60))
    thr = float(np.quantile(hist, 0.7))
    ser = _series(hist + [thr - 0.01])
    v = swc._gate_decide(ser, ser.index[-1])
    assert v["gate"] == "ABSTAIN" and v["fire"] is False


def test_fires_exactly_at_threshold():
    """경계는 '이상'이다 (top-p >= thr). 분위 미만일 때만 기권한다."""
    hist = list(np.linspace(0.10, 0.69, 60))
    thr = float(np.quantile(hist, 0.7))
    v = swc._gate_decide(_series(hist + [thr]), _series(hist + [thr]).index[-1])
    assert v["fire"] is True


def test_warmup_window_abstains():
    """창이 60개가 안 차면 보수적으로 기권한다. 라이브에서는 발생하지 않는다."""
    ser = _series(list(np.linspace(0.1, 0.6, 59)) + [0.95])
    v = swc._gate_decide(ser, ser.index[-1])
    assert v["gate"] == "WARMUP" and v["fire"] is False and v["gate_history_days"] == 59


def test_missing_today_scores_abstains():
    ser = _series(list(np.linspace(0.1, 0.7, 61)))
    v = swc._gate_decide(ser, pd.Timestamp("2031-01-01"))
    assert v["gate"] == "NO_SCORE" and v["fire"] is False


def test_spec_constants_are_pinned():
    """w60q0.7 = 창 60거래일 · 0.7분위. 라벨은 계약 라벨 t5_5 여야 한다."""
    assert (swc.GATE_W, swc.GATE_Q) == (60, 0.7)
    assert swc.LABEL == "t5_5"


def test_contract_is_still_tp5_h5():
    """계약부는 배선 대상이 아니었다 — TP5/H5 가 그대로인지 못박는다."""
    src = __import__("pathlib").Path(swc.__file__).read_text(encoding="utf-8")
    assert "tgt = entry * 1.05" in src
    assert "win5 = h.iloc[:5]" in src
