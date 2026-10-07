from copy import deepcopy
import json

import pytest

from modules.investor_flow_units import FLOW_VALUE_FIELDS
from multi_agent.tools import repair_flow_snapshot_metadata as repair


def fixture():
    values = {k: 1 for k in FLOW_VALUE_FIELDS}
    owner = {"flow_source": "naver", "flow_unit": "shares", "flow_asof": "2026.05.27", **values}
    projected = {"snapshot_source": "naver", "snapshot_unit": "shares", "snapshot_asof": "2026.05.27",
                 "snapshot_flow": None, **{"snapshot_" + k: "1" for k in values}}
    before = {"flow_source": "scan_universe_snapshot", "flow_unit": "source_units", "flow_asof": "2026-05-28"}
    after = {k: owner[k] for k in repair.META}
    row = {"id": 1, "run_id": "RUN-ONE", "ticker": "005930.KS", **before, **values,
           "feature_snapshot": owner, "return_5d_pct": 12.3, "entry_reference_price": 1000,
           "updated_at": "2026-10-07T00:00:00+00:00"}
    entry = {"id": 1, "run_id": "RUN-ONE", "ticker": "005930.KS", "before": before,
             "after": after, "expected_flow_values": values, "expected_owner": projected}
    return entry, {"row": row, "owner": deepcopy(projected)}


class DB:
    def __init__(self, captured, change=None, lost_response=False):
        self.captured = deepcopy(captured)
        self.calls = 0
        self.change = change
        self.lost_response = lost_response

    def read(self, ids):
        return [deepcopy(self.captured)] if self.captured["row"]["id"] in ids else []

    def cas(self, updates):
        self.calls += 1
        if self.change:
            self.captured["row"].update(self.change)
        for u in updates:
            if self.captured["row"] == u["before"]:
                self.captured["row"].update(u["after"])
        if self.lost_response:
            raise TimeoutError("response lost")
        return [{"id": self.captured["row"]["id"]}]


def test_dry_run_apply_and_replay_preserve_all_other_fields(tmp_path):
    e, captured = fixture()
    db = DB(captured)
    preview = repair.process_batch([e], db, tmp_path, "plan", apply=False)
    assert preview["counts"] == {"eligible": 1} and db.calls == 0
    backup = (tmp_path / "before.json").read_bytes()
    applied = repair.process_batch([e], db, tmp_path, "plan", apply=True)
    assert applied["counts"] == {"applied_verified": 1}
    assert db.captured["row"] == {**captured["row"], **e["after"]}
    repeated = repair.process_batch([e], db, tmp_path, "plan", apply=True)
    assert repeated["counts"] == {"already_correct": 1} and db.calls == 1
    assert (tmp_path / "before.json").read_bytes() == backup


@pytest.mark.parametrize("field,value", [("foreigner_1d", 99), ("return_5d_pct", -4), ("updated_at", "new")])
def test_full_row_cas_rejects_concurrent_numeric_label_and_timestamp_changes(tmp_path, field, value):
    e, captured = fixture()
    db = DB(captured, change={field: value})
    result = repair.process_batch([e], db, tmp_path, "plan", apply=True)
    assert result["counts"] == {"concurrent_or_unexpected_change": 1}
    assert db.captured["row"]["flow_unit"] == "source_units"
    assert db.captured["row"][field] == value


def test_lost_response_is_reconciled_without_duplicate_mutation(tmp_path):
    e, captured = fixture()
    db = DB(captured, lost_response=True)
    result = repair.process_batch([e], db, tmp_path, "plan", apply=True)
    assert result["counts"] == {"applied_verified": 1}
    assert result["transport_error"] == "TimeoutError"
    assert repair.process_batch([e], db, tmp_path, "plan", apply=True)["counts"] == {"already_correct": 1}
    assert db.calls == 1


def test_wrong_or_changed_owner_never_updates(tmp_path):
    e, captured = fixture()
    captured["owner"]["snapshot_unit"] = "KRW"
    db = DB(captured)
    result = repair.process_batch([e], db, tmp_path, "plan", apply=True)
    assert result["counts"] == {"evidence_changed": 1} and db.calls == 0


def test_already_changed_metadata_cannot_justify_itself():
    e, captured = fixture()
    captured["row"].update(e["after"])
    captured["row"]["feature_snapshot"]["flow_unit"] = "KRW"
    assert not repair.matches_evidence(e, captured)


def test_changed_backup_or_plan_fails_closed(tmp_path):
    e, captured = fixture()
    db = DB(captured)
    repair.process_batch([e], db, tmp_path, "plan", apply=False)
    with pytest.raises(ValueError, match="another plan"):
        repair.process_batch([e], db, tmp_path, "other", apply=True)
    p = tmp_path / "before.json"
    p.write_text(p.read_text() + " ")
    with pytest.raises(ValueError, match="hash mismatch"):
        repair.process_batch([e], db, tmp_path, "plan", apply=True)
    assert db.calls == 0


def test_sql_assigns_only_metadata_and_compares_typed_entire_row():
    e, captured = fixture()
    sql = repair.cas_sql([{"before": captured["row"], "after": e["after"]}])
    assignment = sql.split(" t SET ", 1)[1].split(" FROM p", 1)[0]
    assert assignment == ",".join(f"{k}=p.patch->>'{k}'" for k in repair.META)
    assert "to_jsonb(t)=to_jsonb(p.b)" in sql and "t.id=(p.b).id" in sql
    assert "jsonb_populate_record(NULL::public.scan_universe_snapshots" in sql
    with pytest.raises(ValueError):
        repair.cas_sql([{"before": captured["row"], "after": {"return_5d_pct": 100}}])


def test_plan_duplicate_and_missing_guard_are_rejected():
    e, _ = fixture()
    with pytest.raises(ValueError, match="duplicate"):
        repair.validate_plan({"rows": 2, "updates": [e, e]})
    e["expected_flow_values"].pop("retail_10d")
    with pytest.raises(ValueError, match="incomplete"):
        repair.validate_plan({"rows": 1, "updates": [e]})
