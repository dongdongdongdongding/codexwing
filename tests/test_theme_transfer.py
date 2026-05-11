import json
from pathlib import Path

from modules.theme_transfer import (
    ARTIFACT_PATH,
    _canonical_kr_theme_id,
    build_transfer_artifact,
    load_transfer_artifact,
    project_kr_priors,
)


def test_build_transfer_artifact_has_required_fields(tmp_path):
    artifact = build_transfer_artifact(archive_csv=tmp_path / "missing.csv", version="test-v1")
    assert artifact["version"] == "test-v1"
    assert artifact["source_market"] == "US"
    assert artifact["target_market"] == "KR"
    assert "generated_at" in artifact
    assert isinstance(artifact["edges"], list)
    assert len(artifact["edges"]) > 0
    for edge in artifact["edges"]:
        assert {"source_theme_id", "target_theme_id", "relationship", "confidence"}.issubset(edge.keys())
        assert 0.0 <= float(edge["confidence"]) <= 1.0
        assert edge["relationship"] in {"CO_MOVE", "INVERSE"}


def test_artifact_round_trip(tmp_path):
    artifact = build_transfer_artifact(archive_csv=tmp_path / "missing.csv", version="round-trip")
    out = tmp_path / "theme_transfer.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
    loaded = load_transfer_artifact(out)
    assert loaded["version"] == "round-trip"
    assert len(loaded["edges"]) == len(artifact["edges"])


def test_canonical_kr_theme_id_maps_korean_name_to_id():
    assert _canonical_kr_theme_id("반도체") == "semiconductor"
    assert _canonical_kr_theme_id("semiconductor") == "semiconductor"
    assert _canonical_kr_theme_id("") == ""


def test_project_kr_priors_co_move_propagates_direction():
    artifact = {
        "edges": [
            {"source_theme_id": "semiconductor", "target_theme_id": "semiconductor",
             "relationship": "CO_MOVE", "confidence": 0.8},
        ]
    }
    priors = project_kr_priors(
        [{"theme_id": "semiconductor", "direction": "BENEFICIARY", "strength_score": 50.0}],
        artifact,
    )
    assert priors["semiconductor"]["direction"] == "BENEFICIARY"
    assert priors["semiconductor"]["strength_score"] > 0


def test_project_kr_priors_inverse_flips_direction():
    artifact = {
        "edges": [
            {"source_theme_id": "high_yield_risk_off", "target_theme_id": "semiconductor",
             "relationship": "INVERSE", "confidence": 0.7},
        ]
    }
    priors = project_kr_priors(
        [{"theme_id": "high_yield_risk_off", "direction": "BENEFICIARY", "strength_score": 60.0}],
        artifact,
    )
    assert priors["semiconductor"]["direction"] == "HEADWIND"


def test_project_kr_priors_skips_neutral_or_zero_strength():
    artifact = {
        "edges": [
            {"source_theme_id": "semiconductor", "target_theme_id": "semiconductor",
             "relationship": "CO_MOVE", "confidence": 0.8},
        ]
    }
    priors = project_kr_priors(
        [{"theme_id": "semiconductor", "direction": "NEUTRAL", "strength_score": 50.0}],
        artifact,
    )
    assert priors == {}

    priors = project_kr_priors(
        [{"theme_id": "semiconductor", "direction": "BENEFICIARY", "strength_score": 0.0}],
        artifact,
    )
    assert priors == {}


def test_artifact_matches_jsonschema():
    schema_path = Path("multi_agent/schemas/theme_transfer.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    required_top = set(schema.get("required", []))
    edge_required = set(schema["properties"]["edges"]["items"]["required"])

    artifact = build_transfer_artifact(archive_csv=Path("nonexistent.csv"), version="schema-check")
    assert required_top.issubset(artifact.keys())
    for edge in artifact["edges"]:
        assert edge_required.issubset(edge.keys())
