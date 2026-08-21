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


def test_abstention_is_kospi_only():
    """운영자 2026-08-22: 기권은 KOSPI 에만 건다.

    w60q0.7 은 한 시장에서 도출돼 두 시장에 그대로 걸려 있었다. 같은 시드·같은 랭커·같은 픽에서
    기권만 켜고 끄면 부호가 반대다 — KOSPI 는 버린 날 net −1.072(버릴 만했다), KOSDAQ 은
    버린 날 +0.911(좋은 날을 버렸다). KOSDAQ 2026H1 음수 5/6 은 셀이 아니라 이 기권이 만들었다.
    이 테스트가 깨지면 그 정정이 조용히 되돌아간 것이다."""
    assert swc.ABSTAIN_MARKETS == ("KOSPI",)
    assert "KOSDAQ" not in swc.ABSTAIN_MARKETS


def test_gate_reason_is_recorded_in_source():
    """왜 KOSDAQ 을 뺐는지가 코드 옆에 남아 있어야 한다 — 근거 없이 상수만 있으면 되돌려진다."""
    src = __import__("pathlib").Path(swc.__file__).read_text(encoding="utf-8")
    assert "좋은 날을 버렸다" in src and "+0.911" in src and "-1.072" in src


# ── [U] 시장약세 게이트 (KOSDAQ) ────────────────────────────────────────────

def test_market_weakness_buys_on_weakness_not_strength():
    """부호가 급소다 — **약할 때** 산다. 뒤집히면 정확히 반대 규칙이 되고 조용히 통과한다."""
    hist = list(np.linspace(-2.0, 2.0, 250))          # 중앙값 0.0
    weak = swc._mkt_weakness_decide(_series(hist + [-1.5]), _series(hist + [-1.5]).index[-1])
    strong = swc._mkt_weakness_decide(_series(hist + [+1.5]), _series(hist + [+1.5]).index[-1])
    assert weak["gate"] == "FIRE" and weak["fire"] is True
    assert strong["gate"] == "ABSTAIN" and strong["fire"] is False


def test_market_weakness_threshold_excludes_today():
    """인과: 오늘 값은 중앙값 계산에 들어가지 않는다."""
    hist = list(np.linspace(-2.0, 2.0, 250))
    ser = _series(hist + [-9.9])                       # 오늘이 극단값
    v = swc._mkt_weakness_decide(ser, ser.index[-1])
    assert v["gate_threshold"] == pytest.approx(float(np.median(hist)), abs=1e-9)
    assert v["gate_history_days"] == 250


def test_market_weakness_window_is_250_and_drops_older():
    ancient = [99.0] * 80
    recent = list(np.linspace(-2.0, 2.0, 250))
    ser = _series(ancient + recent + [-1.0])
    v = swc._mkt_weakness_decide(ser, ser.index[-1])
    assert v["gate_history_days"] == 250
    assert v["gate_threshold"] == pytest.approx(float(np.median(recent)), abs=1e-9)


def test_market_weakness_warmup_abstains():
    ser = _series(list(np.linspace(-1, 1, 59)) + [-5.0])
    v = swc._mkt_weakness_decide(ser, ser.index[-1])
    assert v["gate"] == "WARMUP" and v["fire"] is False


def test_each_market_has_exactly_one_gate():
    """게이트가 시장별로 정확히 하나여야 한다.

    KOSDAQ 에 두 게이트를 같이 걸면 발화가 5.35거래일이 되어 운영자 3일 기준에 걸린다(규율 13:
    EV 를 사려고 검증가능성을 판다). KOSPI 에 시장약세를 걸면 기여가 +0.234 뿐이고 2026H1 음수 2/6 이다."""
    assert swc.ABSTAIN_MARKETS == ("KOSPI",)
    assert swc.MKT_WEAKNESS_MARKETS == ("KOSDAQ",)
    assert not set(swc.ABSTAIN_MARKETS) & set(swc.MKT_WEAKNESS_MARKETS)
