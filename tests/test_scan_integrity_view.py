import json

from ui.scan_integrity_view import load_scan_context_for_run, scan_integrity_report_for_context


def test_scan_integrity_context_loads_artifact_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    artifact_dir = tmp_path / "runtime_state" / "artifacts" / "RUN-X"
    artifact_dir.mkdir(parents=True)
    scanner_path = artifact_dir / "scanner_handoff.json"
    integrity_path = artifact_dir / "scan_integrity_report.json"
    scanner_path.write_text(
        json.dumps({"summary": {"market_gate": {"gate": "GREEN", "msg": "OK"}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    integrity_path.write_text(json.dumps({"feature_completeness": 0.8}, ensure_ascii=False), encoding="utf-8")
    (artifact_dir / "scan_pipeline_summary.json").write_text(
        json.dumps(
            {
                "artifact_dir": str(artifact_dir),
                "manifest_paths": {
                    "scanner_handoff": str(scanner_path),
                    "scan_integrity_report": str(integrity_path),
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    context = load_scan_context_for_run("RUN-X")
    report = scan_integrity_report_for_context(context)

    assert context["market_gate"]["gate"] == "GREEN"
    assert report["feature_completeness"] == 0.8


def test_scan_integrity_report_prefers_embedded_summary_report():
    context = {
        "summary": {
            "scan_integrity": {
                "report": {
                    "feature_completeness": 0.95,
                    "quality_flags": [],
                }
            }
        }
    }

    assert scan_integrity_report_for_context(context)["feature_completeness"] == 0.95
