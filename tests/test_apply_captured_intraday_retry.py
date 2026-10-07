import json
from pathlib import Path

import pandas as pd
import pytest

from multi_agent.tools import apply_captured_intraday_retry as m
from multi_agent.tools.intraday_cache_journal import restore_state


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def setup(tmp_path, monkeypatch, *, conflicting=False, missing_checkpoint=False):
    monkeypatch.setattr(m.backfill, "legacy_writers", lambda *a, **kw: [])
    evidence, cache = tmp_path / "evidence", tmp_path / "cache"
    out = cache / "intraday"
    out.mkdir(parents=True)
    errors, files = [], []
    for code in ("000001", "000002"):
        q = {"code": code, "day": "20261002", "hour": "153000", "error": "KISOpenAPIError"}
        errors.append(q)
        old = pd.DataFrame({"Open": [100.], "High": [102.], "Low": [99.], "Close": [101.],
                            "Volume": [10.], "code": [code]}, index=pd.to_datetime(["2026-10-02 15:29"]))
        old.to_parquet(out / (code + ".parquet"))
        st = (out / (code + ".parquet")).stat()
        state = {"identity": [st.st_mtime_ns, st.st_size], "days": {q["day"]: {
            "successful_hours": ["100000", "113000", "133000"], "status": "PARTIAL_OR_EMPTY", "retry_after": 9999999999}}}
        if missing_checkpoint and code == "000002":
            state["days"] = {}
        write(out / ".backfill" / (code + ".json"), state)
        payload = {"rt_cd": "0", "output2": [{"stck_bsop_date": q["day"], "stck_cntg_hour": time,
            "stck_oprc": "100", "stck_hgpr": "102", "stck_lwpr": "99", "stck_prpr": "101", "cntg_vol": "10"}
            for time in ("152900", "153000")]}
        if conflicting and code == "000002":
            payload["output2"][0]["stck_oprc"] = "99"
        path = evidence / (code + ".json")
        write(path, {"request": q, "status": "VALID", "payload": payload})
        files.append({"path": path.name, "sha256": m.digest(path)})
    receipt = evidence / "original_receipt.json"
    write(receipt, {"market_div": "J", "request_errors": errors})
    write(evidence / "apply_manifest.json", {"receipt_sha256": m.digest(receipt), "files": files})
    return evidence, cache


def test_missing_only_repair_checkpoints_backups_and_repeat(tmp_path, monkeypatch):
    evidence, cache = setup(tmp_path, monkeypatch)
    before = m.digest(cache / "intraday/000001.parquet")
    dry = m.run(evidence, cache)
    assert sum(r["added"] for r in dry["rows"]) == 2
    assert m.digest(cache / "intraday/000001.parquet") == before
    result = m.run(evidence, cache, apply=True)
    assert result["session_completeness"] == "NOT_ESTABLISHED"
    for row in result["rows"]:
        state = json.loads((cache / "intraday/.backfill" / (row["code"] + ".json")).read_text())
        cell = state["days"]["20261002"]
        assert cell["status"] == "REQUESTED_ALL_SLICES" and cell["session_complete"] is None
        assert "retry_after" not in cell
    journal = next((Path(result["audit"]) / "cache_journal").glob("*.json"))
    assert len(restore_state(json.loads(journal.read_text())["recovery"]["before_state"])) == 1
    repeat = m.run(evidence, cache, apply=True)
    assert all(r["added"] == 0 and not r["checkpoint_changed"] for r in repeat["rows"])


@pytest.mark.parametrize("option,error", [("conflicting", "overlapping_prices_changed"),
                                        ("missing_checkpoint", "invalid_existing_checkpoint")])
def test_all_preflight_before_first_write(tmp_path, monkeypatch, option, error):
    evidence, cache = setup(tmp_path, monkeypatch, **{option: True})
    path = cache / "intraday/000001.parquet"
    before = m.digest(path)
    with pytest.raises(ValueError, match=error):
        m.run(evidence, cache, apply=True)
    assert m.digest(path) == before


def test_capture_tampering_fails(tmp_path, monkeypatch):
    evidence, cache = setup(tmp_path, monkeypatch)
    path = evidence / "000002.json"
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="capture_hash_mismatch"):
        m.run(evidence, cache, apply=True)


def test_manifest_cannot_silently_drop_failed_requests(tmp_path, monkeypatch):
    evidence, cache = setup(tmp_path, monkeypatch)
    path = evidence / "apply_manifest.json"
    data = json.loads(path.read_text());data["files"] = data["files"][:1];write(path, data)
    with pytest.raises(ValueError, match="capture_cohort_incomplete"):
        m.run(evidence, cache)


def test_empty_request_preserves_partial_checkpoint(tmp_path, monkeypatch):
    evidence, cache = setup(tmp_path, monkeypatch)
    path = evidence / "000002.json"
    item = json.loads(path.read_text());item.update(status="EMPTY", payload={"rt_cd": "0", "output2": []});write(path, item)
    manifest_path = evidence / "apply_manifest.json"
    manifest = json.loads(manifest_path.read_text());manifest["files"][1]["sha256"] = m.digest(path);write(manifest_path, manifest)
    state_path = cache / "intraday/.backfill/000002.json";before = m.digest(state_path)
    r = m.run(evidence, cache, apply=True)
    assert len(r["unresolved"]) == 1 and m.digest(state_path) == before


def test_zero_open_is_rejected_not_filled_from_close(tmp_path, monkeypatch):
    evidence, _ = setup(tmp_path, monkeypatch)
    p = json.loads((evidence / "000001.json").read_text())["payload"]
    p["output2"][0]["stck_oprc"] = "0"
    with pytest.raises(ValueError, match="invalid_minute_OHLCV"):
        m.strict_frame(p, "20261002")
