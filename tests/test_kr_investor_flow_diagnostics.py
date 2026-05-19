from modules.kr_investor_flow_diagnostics import (
    build_pykrx_investor_flow_investigation,
    classify_pykrx_warning,
    source_decision,
)


def test_classify_pykrx_empty_warning():
    diagnostic = classify_pykrx_warning(["pykrx_flow_failed:pykrx_empty_investor_flow"])
    assert diagnostic["class"] == "empty_dataframe"
    assert diagnostic["severity"] == "warning"
    assert any("no rows" in item for item in diagnostic["likely_causes"])


def test_source_decision_marks_naver_as_pykrx_fallback_when_warning_exists():
    decision = source_decision("naver", ["pykrx_flow_failed:pykrx_empty_investor_flow"])
    assert decision["usable_for_buy_signal"] is True
    assert decision["required_warning"] == "PYKRX_FAILED_NAVER_FALLBACK"
    assert decision["pykrx_warning_class"] == "empty_dataframe"


def test_investigation_summarizes_observed_sources_and_warnings():
    report = build_pykrx_investor_flow_investigation(
        [
            {"flow_source": "naver", "warnings": ["pykrx_flow_failed:pykrx_empty_investor_flow"]},
            {"flow_source": "pykrx_value", "warnings": []},
        ]
    )
    assert report["version"] == "pykrx_investor_flow_diagnostic_v1"
    assert report["source_counts"] == {"naver": 1, "pykrx_value": 1}
    assert report["warning_class_counts"]["empty_dataframe"] == 1
    assert "score-only rows must not claim foreigner/institution direction" in report["required_runtime_behavior"]
