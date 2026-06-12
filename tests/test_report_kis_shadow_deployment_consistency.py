from __future__ import annotations

import json
from pathlib import Path

import joblib

from multi_agent.tools import report_kis_shadow_deployment_consistency as tool


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _bundle(identity: dict, gate: dict) -> dict:
    return {
        "market": identity["market"],
        "label": identity["label"],
        "feature_set": identity["feature_set"],
        "model_name": identity["model"],
        "topn": identity["topn"],
        "prob_threshold": identity["prob_threshold"],
        "tail_risk_prob_threshold": identity["tail_risk_prob_threshold"],
        "selection_rule": identity["selection_rule"],
        "kis_model_gate": gate,
    }


def test_deployment_consistency_passes_when_all_surfaces_match(tmp_path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    comparison_path = tmp_path / "comparison.json"
    deployment_path = tmp_path / "deployment.json"
    identity = {
        "market": "KOSPI",
        "label": "touch5_dd10_5d",
        "feature_set": "kis_sidecar_failure_risk_augmented",
        "model": "lightgbm",
        "topn": 1,
        "prob_threshold": 0.3,
        "tail_risk_prob_threshold": 0.9,
        "selection_rule": "top1_p0p3_tail0p9",
    }
    gate = {
        "status": "shadow_ready",
        "production_ready": False,
        "shadow_display_allowed": True,
        "production_blocking_reasons": ["active_days_lt_15"],
    }
    model_path = tool._model_path_from_identity(model_dir, identity)
    joblib.dump(_bundle(identity, gate), model_path)
    joblib.dump(_bundle(identity, gate), tool._alias_path(model_dir, "KOSPI"))
    _write_json(
        comparison_path,
        {"markets": {"KOSPI": {"current_kis_model": {"identity": identity, "kis_model_gate": gate}}}},
    )
    _write_json(
        deployment_path,
        {"deployments": {"KOSPI": {"identity": identity, "model": {"model_path": str(model_path), "kis_model_gate_status": "shadow_ready"}}}},
    )

    report = tool.build_report(
        comparison_path=comparison_path,
        deployment_path=deployment_path,
        model_dir=model_dir,
        required_markets=["KOSPI"],
    )

    assert report["decision"]["deployment_consistent"] is True
    assert report["markets"][0]["status"] == "pass"
    assert report["markets"][0]["issues"] == []


def test_deployment_consistency_fails_on_alias_drift(tmp_path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    comparison_path = tmp_path / "comparison.json"
    deployment_path = tmp_path / "deployment.json"
    identity = {
        "market": "KOSDAQ",
        "label": "touch5_dd10_5d",
        "feature_set": "kis_sidecar_failure_risk_augmented",
        "model": "lightgbm",
        "topn": 1,
        "prob_threshold": 0.75,
        "tail_risk_prob_threshold": 0.85,
        "selection_rule": "top1_p0p75_tail0p85",
    }
    gate = {"status": "shadow_ready", "production_ready": False, "shadow_display_allowed": True}
    model_path = tool._model_path_from_identity(model_dir, identity)
    joblib.dump(_bundle(identity, gate), model_path)
    drifted = {**identity, "selection_rule": "top1_old"}
    joblib.dump(_bundle(drifted, gate), tool._alias_path(model_dir, "KOSDAQ"))
    _write_json(
        comparison_path,
        {"markets": {"KOSDAQ": {"current_kis_model": {"identity": identity, "kis_model_gate": gate}}}},
    )
    _write_json(
        deployment_path,
        {"deployments": {"KOSDAQ": {"identity": identity, "model": {"model_path": str(model_path), "kis_model_gate_status": "shadow_ready"}}}},
    )

    report = tool.build_report(
        comparison_path=comparison_path,
        deployment_path=deployment_path,
        model_dir=model_dir,
        required_markets=["KOSDAQ"],
    )

    assert report["decision"]["deployment_consistent"] is False
    assert "comparison_alias_identity_mismatch" in report["markets"][0]["issues"]


def test_deployment_consistency_fails_on_gate_drift(tmp_path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    comparison_path = tmp_path / "comparison.json"
    deployment_path = tmp_path / "deployment.json"
    identity = {
        "market": "KOSDAQ",
        "label": "touch5_dd10_5d",
        "feature_set": "kis_sidecar_failure_risk_augmented",
        "model": "lightgbm",
        "topn": 1,
        "prob_threshold": 0.75,
        "tail_risk_prob_threshold": 0.85,
        "selection_rule": "top1_p0p75_tail0p85",
    }
    gate = {"status": "shadow_ready", "production_ready": False, "shadow_display_allowed": True}
    stale_gate = {"status": "blocked", "production_ready": False, "shadow_display_allowed": False}
    model_path = tool._model_path_from_identity(model_dir, identity)
    joblib.dump(_bundle(identity, gate), model_path)
    joblib.dump(_bundle(identity, stale_gate), tool._alias_path(model_dir, "KOSDAQ"))
    _write_json(
        comparison_path,
        {"markets": {"KOSDAQ": {"current_kis_model": {"identity": identity, "kis_model_gate": gate}}}},
    )
    _write_json(
        deployment_path,
        {"deployments": {"KOSDAQ": {"identity": identity, "model": {"model_path": str(model_path), "kis_model_gate_status": "blocked"}}}},
    )

    report = tool.build_report(
        comparison_path=comparison_path,
        deployment_path=deployment_path,
        model_dir=model_dir,
        required_markets=["KOSDAQ"],
    )

    assert report["decision"]["deployment_consistent"] is False
    assert "comparison_deployment_gate_mismatch" in report["markets"][0]["issues"]
    assert "comparison_alias_gate_mismatch" in report["markets"][0]["issues"]
