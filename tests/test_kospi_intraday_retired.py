"""`kospi_intraday` 은퇴 (2026-08-22 운영자 결정).

죽인 이유가 「EV 가 낮다」가 아니라 **「엣지가 체결 불가능한 진입 위에 있었다」**는 점이 중요하다.
이 레인은 신호일 종가 진입인데 랭커 top-1 의 19.2% 가 신호일 상한가 종가였다(유니버스 0.21% =
91배 농축). 상한가에는 매도호가가 없어 못 산다. 체결 가능한 픽만 남기면 백테스트 net 이
+1.620 → −0.009 로 사라지고, 전진도 n=53 EV −1.87 이다.

되살리려면 체결가능성 가드를 생산자에 배선하고 다시 재야 한다. 그 전에 레지스트리에서 지우면
가드 없이 부활한다 — 이 테스트들이 그걸 막는다.
"""
import pytest

from modules.stream_exclusion import RETIRED_LANES, stream_status, apply_stream_exclusion
from modules import model_lane_scan


def test_lane_is_registered_as_killed():
    assert RETIRED_LANES.get("kospi_intraday") == "killed"


def test_retirement_outranks_a_healthy_gate_verdict():
    """게이트가 CONFIRM 을 줘도 은퇴가 이겨야 한다.

    은퇴는 게이트 판정이 아니라 운영자 결정이다. 게이트는 「기대 정합」을 보고 이 레인이 죽은
    이유는 「체결 가능성」이라 축이 아예 다르다. 게이트를 먼저 보면 CONFIRM 이 은퇴를 덮어쓴다."""
    healthy = {"usable": True, "lanes": {"kospi_intraday_t5": {"verdict": "CONFIRM", "n": 99, "fwd_ev": 5.0}}}
    st = stream_status("kospi_intraday", gate_state=healthy, strict=True)
    assert st["excluded"] is True
    assert st["reason"] == "lane_killed"


def test_killed_lane_gets_a_note_that_says_why():
    row = {}
    apply_stream_exclusion(row, "kospi_intraday",
                           gate_state={"usable": True, "lanes": {"kospi_intraday_t5": {"verdict": "CONFIRM"}}})
    note = " ".join(str(v) for v in row.values())
    assert "죽은 레인" in note and "체결" in note


def test_scanner_refuses_to_run_the_lane():
    """스캔 자체가 안 돌아야 한다 — 발행 직전에 막는 것으로는 원장이 계속 쌓인다."""
    out = model_lane_scan.run_model_lane_scan("KOSPI", "INTRADAY", route=False)
    assert out["picks"] == [] and out["routed"] == 0
    assert out["error"] == "lane_killed: kospi_intraday"


def test_other_lanes_are_untouched():
    """죽인 것은 한 레인이다. 나머지는 은퇴 레지스트리에 들어가면 안 된다.

    2026-09-05: `kosdaq_intraday` 를 이 목록에 되돌렸다. 09-03 에 「서빙 모델 auc 0.478」을
    근거로 정지시켰으나 **그 모델은 이 레인의 것이 아니었다** — phase25 는 `quant_analysis`
    스코어링의 tilt 모델이고, 이 레인은 `train_kosdaq_1500_bundle.py` 가 일일 재학습하는
    자기 번들로 돈다. 전진 원장에서도 유일하게 CI 하한이 0 을 넘는 레인이다.
    """
    for lane in ("kospi_swing", "kosdaq_swing", "kosdaq_intraday", "nasdaq_swing"):
        assert lane not in RETIRED_LANES


def test_a_lane_is_only_halted_on_its_own_producer():
    """🔴 2026-09-05 회귀 방지 — 레인을 세울 때 **그 레인의 생산자**를 봤는지 확인한다.

    조정관이 남의 모델(phase25 스코어링 tilt)의 성적으로 이 레인을 세웠다. 두 어휘
    (`kosdaq_intraday` / `kosdaq_intraday_3d_t5_vwap_guard`) 를 다 막아서 스캐너 단계까지
    조용히 죽었고, 하필 그 레인이 전진 원장에서 유일하게 유의 양수였다.
    """
    for lane in ("kosdaq_intraday", "kosdaq_intraday_3d_t5_vwap_guard"):
        st = stream_status(lane, gate_state={"usable": True,
                                             "lanes": {"kosdaq_intraday_t10": {"verdict": "CONFIRM"}}},
                           strict=True)
        assert st["excluded"] is False, f"{lane} 이 근거 없이 막혀 있다"


def test_lane_stays_in_LANES_for_history():
    """LANES 에서 지우면 ledger="" 가 되어 디렉터리를 열고 /api/picks 가 죽는다(과거 사고).

    은퇴는 발행을 막는 것이지 과거 픽 해석을 막는 것이 아니다."""
    from web.backend.services import LANES
    assert "kospi_intraday" in LANES
    assert LANES["kospi_intraday"]["ledger"]


def test_daily_ops_no_longer_invokes_the_producer():
    import pathlib
    src = pathlib.Path("multi_agent/tools/run_daily_ops.sh").read_text(encoding="utf-8")
    assert "python3 multi_agent/tools/report_kospi_intraday_swing.py" not in src
    assert "[SKIP] report_kospi_intraday_swing" in src
