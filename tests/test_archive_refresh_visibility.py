import json
from pathlib import Path

import pytest

import web.backend.services as S
from multi_agent.tools.export_scan_archive_learning_dataset import atomic_export


def test_replaced_archive_is_visible_without_service_restart(tmp_path,monkeypatch):
    monkeypatch.setattr(S,"REPO",str(tmp_path))
    path = tmp_path/"runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
    path.parent.mkdir(parents=True)
    path.write_text("ticker,return_5d_pct\nX,9\n")
    assert S._archive_df().iloc[0].return_5d_pct == 9
    atomic_export(path,lambda p:p.write_text("ticker,return_5d_pct\nX,-2\n"))
    assert S._archive_df().iloc[0].return_5d_pct == -2


def test_failed_export_preserves_previous_complete_file(tmp_path):
    path = tmp_path/"archive.csv"; path.write_text("complete")
    def broken(temp):
        temp.write_text("partial")
        assert path.read_text() == "complete"
        raise RuntimeError("writer interrupted")
    with pytest.raises(RuntimeError,match="interrupted"):
        atomic_export(path,broken)
    assert path.read_text() == "complete"
    assert list(tmp_path.glob("*.tmp")) == []


def test_gate_ev_refreshes_with_report_replacement(tmp_path,monkeypatch):
    monkeypatch.setattr(S,"REPO",str(tmp_path))
    path = tmp_path/"runtime_state/reports/validation/research_recursion_gate_latest.json"
    path.parent.mkdir(parents=True)
    def payload(ev):
        return json.dumps({"results":[{"lane":"test","fwd_ev":ev,"fwd_win":80,"n":30}]})
    path.write_text(payload(-1))
    assert S._lane_forward_ev()["test"][0] == -1
    atomic_export(path,lambda p:p.write_text(payload(3)))
    assert S._lane_forward_ev()["test"][0] == 3


def test_empty_archive_is_a_valid_empty_state(tmp_path,monkeypatch):
    monkeypatch.setattr(S,"REPO",str(tmp_path))
    path = tmp_path/"runtime_state/reports/archive/scan_archive_learning_dataset_all.csv"
    path.parent.mkdir(parents=True); path.write_text("")
    assert S._archive_df() is None
