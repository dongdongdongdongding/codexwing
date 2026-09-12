"""`docs/LANE_DATA_MAP.md` 가 코드와 어긋나면 깨진다.

왜 있나: 한 세션에서 조정관이 모델·데이터를 다섯 번 혼동했고 둘은 라이브에 닿았다
(phase25 를 코스닥 장중 레인 모델로 착각해 레인 정지 → 철회 `e9ed2b0`;
`_base_prob` 을 스윙 레인 성분으로 착각 → 스윙 파일에 grep 0건).
원인은 **이름이 비슷한 것들이 서로 다른 파이프라인에 있는데 경계가 안 적혀 있던 것**이다.

문서를 쓰는 것만으로는 다시 낡는다. **갱신을 약속이 아니라 관문으로 만든다.**
"""
from pathlib import Path

import pytest

DOC = Path(__file__).resolve().parents[1] / "docs" / "LANE_DATA_MAP.md"


@pytest.fixture(scope="module")
def doc() -> str:
    assert DOC.exists(), f"{DOC} 가 없다 — 레인 지도는 선택이 아니다"
    return DOC.read_text(encoding="utf-8")


def test_every_published_lane_is_documented(doc):
    """레인을 추가하고 문서를 안 고치면 여기서 걸린다."""
    from web.backend.services import LANES
    missing = [k for k in LANES if f"`{k}`" not in doc]
    assert not missing, f"문서에 없는 발행 레인: {missing} — docs/LANE_DATA_MAP.md §1 에 추가해라"


def test_every_retired_lane_is_marked(doc):
    """은퇴·정지는 게이트보다 우선한다. 문서가 그것을 말하지 않으면 다음 사람이 살아 있다고 읽는다."""
    from modules.stream_exclusion import RETIRED_LANES
    for lane in RETIRED_LANES:
        assert f"`{lane}`" in doc, f"은퇴/정지 레인 {lane} 이 문서에 없다"


def test_contract_constants_match_the_document(doc):
    """계약을 바꾸고 문서를 안 고치면 걸린다 — 화면·연구·운영이 서로 다른 계약을 말하게 된다."""
    import multi_agent.tools.report_kr_swing_candidate as swc
    tp = swc.CONTRACT_TP
    tp_map = tp if isinstance(tp, dict) else {m: tp for m in swc.CONTRACT_H}
    for mkt, h in swc.CONTRACT_H.items():
        pct = int(round(float(tp_map[mkt]) * 100))
        assert f"TP{pct} / H{h}" in doc, (
            f"{mkt} 계약이 TP{pct}/H{h} 인데 문서에 그 표기가 없다 "
            f"(문서 §1 의 계약 칸을 고쳐라)")
    for mkt, k in swc.TOP_K.items():
        assert f"top-{k}" in doc, f"{mkt} 발행 깊이 top-{k} 가 문서에 없다"


def test_the_model_sourcing_split_is_stated(doc):
    """이 문서의 존재 이유 그 자체 — **어느 레인이 저장 모델을 쓰고 어느 레인이 매번 적합하는가.**

    조정관이 틀린 지점이 정확히 여기다. 코드에서 다시 확인해 문서와 대조한다.
    """
    root = Path(__file__).resolve().parents[1]
    swing = (root / "multi_agent/tools/report_kr_swing_candidate.py").read_text(encoding="utf-8")
    intraday = (root / "multi_agent/tools/report_kosdaq_intraday_vwap_guard.py").read_text(encoding="utf-8")

    # 스윙: 저장 모델을 로드하지 않고 매 실행 적합한다.
    assert "lgb.LGBMClassifier(" in swing
    assert "joblib.load" not in swing, (
        "스윙 레인이 저장 모델을 로드하기 시작했다 — 문서 §1 의 「매 실행 자체 적합」이 거짓이 된다")
    assert "매 실행 자체 적합" in doc

    # 장중: 저장 번들을 로드한다.
    assert "joblib.load" in intraday
    from modules.kosdaq_intraday_vwap_guard import MODEL_PATH
    assert str(MODEL_PATH) in doc, f"장중 레인 번들 경로({MODEL_PATH})가 문서와 다르다"


def test_phase25_is_not_claimed_as_a_lane_model(doc):
    """phase25 는 `quant_analysis` 스캔 경로의 것이지 발행 레인의 모델이 아니다.

    이것을 혼동해 레인 하나를 근거 없이 정지시켰다. 코드가 그대로인지 확인한다.
    """
    root = Path(__file__).resolve().parents[1]
    for name in ("report_kr_swing_candidate.py", "report_kosdaq_intraday_vwap_guard.py",
                 "report_nasdaq_session_tape.py"):
        src = (root / "multi_agent/tools" / name).read_text(encoding="utf-8")
        assert "phase25" not in src, (
            f"{name} 이 phase25 를 쓰기 시작했다 — 문서 §1 의 경계 설명을 고쳐라")
    assert "quant_analysis" in doc and "별개 파이프라인" in doc


def test_the_unadjusted_panel_warning_survives(doc):
    """`px_long` 의 OHLC 는 미조정이다. 이 경고가 사라지면 다일 경로 연구가 조용히 틀린다."""
    assert "px_long" in doc and "미조정" in doc
    assert "px_delisted" in doc and "adj_factor" in doc
