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


def test_target_is_still_plus_five_percent():
    """목표는 +5% 로 불변이다. **H 만 시장별로 갈렸다**(2026-08-23) — TP 까지 같이 움직이면
    두 시장 다 검증 밖으로 나간다."""
    src = __import__("pathlib").Path(swc.__file__).read_text(encoding="utf-8")
    assert "tgt = entry * (1.0 + CONTRACT_TP)" in src
    assert swc.CONTRACT_TP == 0.05
    assert "win5 = h.iloc[:_H]" in src, "보유창이 시장별 H 를 따라야 한다"


def test_kosdaq_never_gets_the_p_abstention():
    """운영자 2026-08-22: 기권은 KOSDAQ 에 걸지 않는다. (2026-08-23 에 KOSPI 에서도 뺐다.)

    w60q0.7 은 한 시장에서 도출돼 두 시장에 그대로 걸려 있었다. 같은 시드·같은 랭커·같은 픽에서
    기권만 켜고 끄면 부호가 반대다 — KOSPI 는 버린 날 net −1.072(버릴 만했다), KOSDAQ 은
    버린 날 +0.911(좋은 날을 버렸다). KOSDAQ 2026H1 음수 5/6 은 셀이 아니라 이 기권이 만들었다.
    이 테스트가 깨지면 그 정정이 조용히 되돌아간 것이다. KOSPI 는 2026-08-23 에 시장약세
    게이트로 옮겨가며 함께 빠졌으므로 `ABSTAIN_MARKETS` 는 지금 비어 있다 — 그러나
    **KOSDAQ 이 다시 들어오는 일은 어떤 경우에도 없어야 한다.**"""
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
    """게이트가 시장별로 정확히 하나여야 한다. 두 개를 겹쳐 걸면 발화가 무너진다 —
    KOSDAQ 에서 두 게이트를 같이 걸었을 때 5.35거래일로 운영자 3일 기준을 깼다(규율 13)."""
    both = set(swc.ABSTAIN_MARKETS) & set(swc.MKT_WEAKNESS_MARKETS)
    assert not both, f"두 게이트가 겹쳐 걸린 시장: {both}"
    for mkt in ("KOSPI", "KOSDAQ"):
        n = int(mkt in swc.ABSTAIN_MARKETS) + int(mkt in swc.MKT_WEAKNESS_MARKETS)
        assert n == 1, f"{mkt} 의 게이트가 {n} 개다 (정확히 1개여야 한다)"


# ── 2026-08-23 배선: 시장별 게이트 분위 + 시장별 계약 ────────────────────────

def test_both_markets_use_the_market_weakness_gate_now():
    """`w60q0.7` 은 더 이상 쓰이지 않는다. 두 시장 다 시장약세 게이트다.

    부수 효과가 크다 — `w60q0.7` 이 요구하던 이중모델(분기 재학습 B)이 통째로 사라져
    하루 4 fit 이 1 fit 이 된다. `gate_w60q07` 코드와 위 테스트들은 되돌리기를 위해 남겨 둔다."""
    assert swc.ABSTAIN_MARKETS == ()
    assert set(swc.MKT_WEAKNESS_MARKETS) == {"KOSPI", "KOSDAQ"}


def test_gate_quantile_is_per_market():
    """KOSPI 0.40 / KOSDAQ 0.50.

    KOSPI 0.40 은 격자 최댓값이 아니다 — 세션당 EV 가 Q 에 단조(0.374@0.25 → 0.077@0.70)라
    봉우리가 없고, **운영자의 기존 발화 기준(≤3거래일)을 세 창 전부에서 만족하는 가장 조인
    0.05격자 값**이다(Q0.35 는 OOS23 에서 3.04 로 깨진다).
    KOSDAQ 은 [U] 사전지정값 0.50 을 유지한다 — Q 조임을 KOSDAQ 에서 검정하지 않았다(규율 3)."""
    assert swc.MKT_WEAKNESS_Q == {"KOSPI": 0.40, "KOSDAQ": 0.50}


def test_quantile_actually_changes_the_threshold():
    """분위 인자가 실제로 문턱을 옮기는지. 상수만 있고 안 쓰이면 조용히 통과한다."""
    hist = list(np.linspace(-2.0, 2.0, 250))
    ser = _series(hist + [0.0])
    v40 = swc._mkt_weakness_decide(ser, ser.index[-1], q=0.40)
    v50 = swc._mkt_weakness_decide(ser, ser.index[-1], q=0.50)
    assert v40["gate_threshold"] < v50["gate_threshold"], "낮은 분위는 더 조인 문턱이어야 한다"
    assert v40["gate_threshold"] == pytest.approx(float(np.quantile(hist, 0.40)), abs=1e-9)
    # 조이면 발화가 준다 — 오늘이 중앙값이면 Q0.5 는 경계, Q0.4 는 미달이라 기권
    assert v50["fire"] is False and v40["fire"] is False


def test_contract_horizon_is_per_market():
    """KOSPI 10세션 / KOSDAQ 5세션. 각 시장이 **자기가 검증된 계약**을 쓴다.

    두 시장을 한 H 로 묶으면 한쪽이 검증 밖으로 나간다 — KOSDAQ 의 [U] 게이트는 H=5 에서
    검증됐고 H 조임을 KOSDAQ 에서 다시 재지 않았다."""
    assert swc.CONTRACT_H == {"KOSPI": 10, "KOSDAQ": 5}
    assert swc.CONTRACT_TP == 0.05


def test_settlement_waits_for_the_longer_window():
    """H=10 계약을 10일 뒤에 정산하면 **미완성 창**을 채점한다. 대기도 시장별이어야 한다."""
    src = __import__("pathlib").Path(swc.__file__).read_text(encoding="utf-8")
    assert "_wait = 10 if _H_row <= 5 else 18" in src
    assert "if pd.isna(d) or (today - d).days < _wait:" in src


def test_pending_picks_are_scored_under_the_contract_they_were_issued_with():
    """계약을 바꿔도 **미정산 과거 픽은 발행 당시 계약으로** 채점해야 한다.

    2026-08-23 에 KOSPI 계약이 H5 → H10 이 됐다. 그 순간 원장에 남아 있던 미정산 KOSPI 픽을
    H10 으로 채점하면, 그 픽이 약속하지 않은 창으로 재는 것이고 **전진 기록이 소급 변조된다.**
    `contract_h` 가 없는 행은 2026-08-23 이전 발행이므로 H=5 다."""
    src = __import__("pathlib").Path(swc.__file__).read_text(encoding="utf-8")
    assert '_H_row = int(row.get("contract_h") or 5)' in src
    assert "_H = _H_row" in src, "채점 창이 시장 현행값이 아니라 픽의 발행 계약을 따라야 한다"


def test_publish_depth_is_per_market():
    """KOSPI 3 / KOSDAQ 1. 깊이의 효과가 두 시장에서 **정반대**다.

    KOSDAQ: k=3→1 이 세션당 +88%, 승률 +3.5pp, 발화 불변. 사다리로 이득의 87% 가 깊이다.
    KOSPI:  k=1 은 `p_max` 0.207 로 랜덤과 구별되지 않는다(k=3 에서 0.00000).
    한 값으로 묶으면 반드시 한 시장이 손해다."""
    assert swc.TOP_K == {"KOSPI": 3, "KOSDAQ": 1}


def test_depth_defaults_to_the_per_market_map():
    """`--top-k` 를 안 주면 시장별 값을 써야 한다. 기본값이 숫자면 두 시장이 덮인다."""
    import inspect
    assert inspect.signature(swc.score_today).parameters["top_k"].default is None
    src = __import__("pathlib").Path(swc.__file__).read_text(encoding="utf-8")
    assert "_k = top_k if top_k is not None else TOP_K.get(mkt, 3)" in src


def test_both_publishers_respect_the_per_market_depth():
    """발행 경로가 둘이다. 한쪽만 고치면 09:35 자동스캔과 daily ops 가 어긋난다.

    과거에 같은 계열의 사고가 있었다 — 두 소비자가 서로 다른 어휘를 써서 한쪽만 게이트를 읽었다
    (`stream_exclusion` F1). 여기서는 **둘 다 깊이를 넘기지 않고** 생산자 기본값을 따라야 한다."""
    import pathlib
    scan = pathlib.Path("modules/model_lane_scan.py").read_text(encoding="utf-8")
    assert "swing_score()" in scan, "자동스캔이 깊이를 하드코딩하면 안 된다"
    assert "swing_score(3)" not in scan
    ops = pathlib.Path("multi_agent/tools/run_daily_ops.sh").read_text(encoding="utf-8")
    assert '--top-k "${AG_KR_SWING_CANDIDATE_TOPK:-3}"' not in ops, "항상 넘기면 시장별 값이 덮인다"
    assert 'KR_SWING_TOPK_ARGS[@]+"${KR_SWING_TOPK_ARGS[@]}"' in ops, "bash 3.2 빈 배열 확장 보호"
