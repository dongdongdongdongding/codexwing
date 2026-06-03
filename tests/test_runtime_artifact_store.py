import json

from modules import runtime_artifact_store as store


class FakeDB:
    def __init__(self):
        self.client = object()
        self.rows = []

    def upsert_runtime_artifact(self, payload):
        self.rows.append(dict(payload))
        return 1

    def fetch_runtime_artifact(self, run_id, artifact_key):
        for row in reversed(self.rows):
            if row.get("run_id") == run_id and row.get("artifact_key") == artifact_key:
                return row
        return {}

    def list_runtime_artifacts(self, *, artifact_key=None, market=None, run_id=None, limit=100):
        rows = list(reversed(self.rows))
        if artifact_key:
            rows = [row for row in rows if row.get("artifact_key") == artifact_key]
        if market:
            rows = [row for row in rows if row.get("market") == market]
        if run_id:
            rows = [row for row in rows if row.get("run_id") == run_id]
        return rows[:limit]


def test_upsert_and_load_runtime_artifact_payload(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(store, "_db_manager", lambda: fake)

    result = store.upsert_runtime_artifact_payload(
        run_id="RUN-X",
        artifact_key="raw_scan_results",
        payload={"results_sorted": [{"ticker": "005930.KS"}]},
        market="KOSPI",
        scan_mode="SWING",
        source="test",
    )

    assert result["ok"] is True
    assert fake.rows[0]["payload_rows"] == 1
    payload = store.load_runtime_artifact_payload("RUN-X", "raw_scan_results")
    assert payload["results_sorted"][0]["ticker"] == "005930.KS"


def test_load_runtime_artifact_payload_falls_back_to_local_path(tmp_path, monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(store, "_db_manager", lambda: fake)
    path = tmp_path / "planner_handoff.json"
    path.write_text(json.dumps({"decisions": [{"ticker": "000660.KS"}]}), encoding="utf-8")

    payload = store.load_runtime_artifact_payload("RUN-MISSING", "planner_handoff", local_path=path)

    assert payload["decisions"][0]["ticker"] == "000660.KS"


def test_persist_run_runtime_artifacts_collects_standard_paths(tmp_path, monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(store, "_db_manager", lambda: fake)
    artifact_dir = tmp_path / "runtime_state" / "artifacts" / "RUN-Z"
    artifact_dir.mkdir(parents=True)
    summary = {
        "run_id": "RUN-Z",
        "market": "KOSDAQ",
        "scan_mode": "SWING",
        "manifest_paths": {},
    }
    (artifact_dir / "scan_pipeline_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (artifact_dir / "raw_scan_results.json").write_text(
        json.dumps({"results_sorted": [{"ticker": "035900.KQ"}]}),
        encoding="utf-8",
    )

    result = store.persist_run_runtime_artifacts(
        run_id="RUN-Z",
        market="KOSDAQ",
        scan_mode="SWING",
        artifact_dir=artifact_dir,
        summary=summary,
        source="test",
    )

    assert result["ok"] is True
    assert {row["artifact_key"] for row in fake.rows} == {"scan_pipeline_summary", "raw_scan_results"}
