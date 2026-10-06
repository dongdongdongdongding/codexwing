from types import SimpleNamespace

import pytest

from modules import db_manager, top_deep_report as T


@pytest.mark.parametrize("fail_write,fail_cleanup", [(True, False), (False, False), (False, True)])
def test_old_snapshot_is_never_deleted_before_successful_replacement(monkeypatch, fail_write, fail_cleanup):
    events = []
    class Query:
        operation = None
        @property
        def not_(self):
            return self
        def eq(self, key, value):
            assert (key, value) == ("run_id", "RUN")
            return self
        def in_(self, key, value):
            assert key == "report_id" and value == ["RUN-A"]
            return self
        def upsert(self, rows, **kwargs):
            self.operation = "upsert"
            return self
        def delete(self):
            self.operation = "delete_obsolete"
            return self
        def execute(self):
            events.append(self.operation)
            if self.operation == "upsert" and fail_write:
                raise ConnectionError("write failed")
            if self.operation == "delete_obsolete" and fail_cleanup:
                raise ConnectionError("cleanup failed")
            return SimpleNamespace(data=[])
    fake = SimpleNamespace(client=SimpleNamespace(table=lambda _: Query()),
                           _filter_payload_to_existing_columns=lambda _, row: row)
    monkeypatch.setattr(db_manager, "DBManager", lambda: fake)
    result = T.upsert_reports_to_supabase([{"run_id": "RUN", "report_id": "RUN-A", "ticker": "A"}])
    if fail_write:
        assert events == ["upsert"] and result["rows_upserted"] == 0
    else:
        assert events == ["upsert", "delete_obsolete"] and result["rows_upserted"] == 1
        assert ("stale_cleanup_failed" in result["warning"]) == fail_cleanup


def test_lane_does_not_report_routed_when_deep_write_failed(monkeypatch):
    from multi_agent.tools.report_swing_ensemble import _route_live
    monkeypatch.setattr(db_manager, "DBManager", lambda: SimpleNamespace(upsert_scan_result=lambda *a, **k: True))
    monkeypatch.setattr(T, "upsert_reports_to_supabase", lambda rows: {"rows_upserted": 0, "warning": "network"})
    with pytest.raises(RuntimeError, match="persistence failed"):
        _route_live([{"ticker": "A", "market": "KOSPI", "p": .7}], "RUN", "2026-10-06")


def test_strict_scan_write_fails_when_client_is_unavailable():
    db = db_manager.DBManager.__new__(db_manager.DBManager)
    db.client = None
    with pytest.raises(RuntimeError, match="unavailable"):
        db.upsert_scan_result({"ticker": "A"}, strict=True)
    assert db.upsert_scan_result({"ticker": "A"}) is False
