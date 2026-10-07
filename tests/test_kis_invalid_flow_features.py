"""Invalid diagnostics must not become supply/demand model evidence."""
from copy import deepcopy

import pytest

from modules.kis_model_features import flatten_kis_model_features
from modules.kis_operational_adapter import build_kis_sidecar_snapshot


SIDECAR_KEYS = ("kis_whale_score", "kis_foreigner_1d", "kis_institution_1d",
                "kis_retail_1d", "kis_whale_flow_3d", "kis_whale_flow_10d")


@pytest.mark.parametrize("status,first", [("ok", None), ("error", 100), ("ok", 0)])
def test_new_sidecar_preserves_invalid_diagnostics_without_numeric_evidence(status, first):
    flow = {"source_status": status, "flow_asof": "20261007", "flow_unit": "KRW_million",
            "foreigner_1d": first, "institution_1d": 0, "retail_1d": 0,
            "foreigner_3d": 900, "foreigner_10d": 1000}
    original = deepcopy(flow)
    sidecar = build_kis_sidecar_snapshot("005930", investor_flow=flow)
    assert sidecar["flow_contract"]["valid"] is False
    assert sidecar["flow_contract"]["foreigner_10d"] == 1000
    assert sidecar["flow_contract"]["whale_score"] > 50
    assert sidecar["coverage"]["investor_flow"] is False
    assert all(sidecar["model_candidate_features"][k] is None for k in SIDECAR_KEYS)
    assert all(flatten_kis_model_features({"kis_sidecar": sidecar})[k] is None for k in SIDECAR_KEYS)
    assert flow == original


@pytest.mark.parametrize("evidence", ["coverage", "flow_contract"])
def test_historical_sidecar_explicit_failure_masks_features_without_rewriting(evidence):
    sidecar = {"model_candidate_features": {k: 123 for k in SIDECAR_KEYS}}
    sidecar[evidence] = {"investor_flow" if evidence == "coverage" else "valid": False}
    row = {"feature_snapshot": {"kis_sidecar": sidecar}}
    original = deepcopy(row)
    flat = flatten_kis_model_features(row)
    assert all(flat[k] is None for k in SIDECAR_KEYS)
    assert row == original


@pytest.mark.parametrize("flag", [None, True])
def test_valid_or_unknown_legacy_sidecar_is_not_reclassified(flag):
    sidecar = {"model_candidate_features": {k: 123 for k in SIDECAR_KEYS}}
    if flag is not None:
        sidecar["coverage"] = {"investor_flow": flag}
        sidecar["flow_contract"] = {"valid": flag}
    flat = flatten_kis_model_features({"kis_sidecar": sidecar})
    assert all(flat[k] == 123 for k in SIDECAR_KEYS)


@pytest.mark.parametrize("evidence", ["flow_ok", "valid"])
def test_invalid_prefilter_masks_flow_evidence_and_keeps_original_selection_history(evidence):
    flow = {"whale_score": 38, "foreigner_1d": 0, "foreigner_10d": -100,
            "flow_source": "kis_openapi", "flow_unit": "shares"}
    prefilter = {"flow": flow, "score_components": {"whale_score": -5.4}, "selection_score": 12}
    if evidence == "valid":
        flow["valid"] = False
    else:
        prefilter["flow_ok"] = False
    row = {"kis_operational_prefilter": prefilter}
    original = deepcopy(row)
    flat = flatten_kis_model_features(row)
    assert flat["kis_prefilter_flow_whale_score"] is None
    assert flat["kis_prefilter_flow_foreigner_1d"] is None
    assert flat["kis_prefilter_flow_foreigner_10d"] is None
    assert flat["kis_prefilter_score_whale_score"] is None
    assert flat["kis_prefilter_selection_score"] == 12
    assert flat["kis_prefilter_flow_unit"] == "shares"
    assert row == original


def test_valid_flow_preserves_real_zero_and_other_numeric_inputs():
    flow = {"source_status": "ok", "foreigner_1d": 0, "institution_1d": 100,
            "retail_1d": -100, "foreigner_3d": 90, "institution_3d": 60,
            "foreigner_10d": 100, "institution_10d": 100}
    sidecar = build_kis_sidecar_snapshot("005930", investor_flow=flow)
    assert sidecar["coverage"]["investor_flow"] is True
    flat = flatten_kis_model_features({"kis_sidecar": sidecar})
    assert flat["kis_foreigner_1d"] == 0
    assert flat["kis_institution_1d"] == 100
    assert flat["kis_whale_flow_3d"] == 150
    assert flat["kis_whale_flow_10d"] == 200
    assert flat["kis_whale_score"] == sidecar["flow_contract"]["whale_score"]
