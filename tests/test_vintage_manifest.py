from pathlib import Path
import pandas as pd
from multi_agent.tools import write_vintage_manifest as V


def test_archived_permission_failure_does_not_erase_active_inventory(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "TRACKED", {"active.parquet": "date"})
    pd.DataFrame({"date": [pd.Timestamp("2026-10-06")]}).to_parquet(tmp_path / "active.parquet")
    original = Path.stat
    def denied(path, *args, **kwargs):
        if "S" in path.parts:
            raise PermissionError("archived volume unavailable")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", denied)
    report = V.build_manifest(tmp_path)
    assert report["status"] == "ok"
    assert report["inputs"]["active.parquet"]["max_date"] == "2026-10-06"
    archived = report["inputs"]["S/picks_top20.parquet"]
    assert archived["status"] == "error" and not archived["required"]
    assert "PermissionError" in archived["error"]


def test_active_missing_or_corrupt_input_fails_with_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(V, "TRACKED", {"active.parquet": "date"})
    report = V.build_manifest(tmp_path)
    assert report["status"] == "failed" and report["failed_inputs"] == ["active.parquet"]
    (tmp_path / "active.parquet").write_text("broken parquet")
    report = V.build_manifest(tmp_path)
    assert report["status"] == "failed"
    assert report["inputs"]["active.parquet"]["error"]
