from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from multi_agent.tools import run_kis_full_kr_scanner_batches as batches


def _args(tmp_path: Path, **overrides):
    values = {
        "batch_size": 2,
        "batch_count": 0,
        "workers": 1,
        "limit": 100000,
        "start_batch": 0,
        "max_batches": 0,
        "state_path": str(tmp_path / "state.json"),
        "resume": False,
        "dry_run": False,
        "fail_fast": False,
        "retries": 0,
        "batch_timeout_sec": 0.0,
        "kis_call_sleep_sec": 0.18,
        "sidecar_call_sleep_sec": 0.40,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _universe(count: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Code": [f"{idx:06d}" for idx in range(1, count + 1)],
            "Name": [f"Name {idx}" for idx in range(1, count + 1)],
        }
    )


def test_chunk_rows_and_ticker_arg_keep_requested_batch_size():
    rows = [
        {"Code": "000001", "Name": "Alpha"},
        {"Code": "000002", "Name": "Beta"},
        {"Code": "000003", "Name": "Gamma"},
        {"Code": "000004", "Name": "Delta"},
        {"Code": "000005", "Name": "Epsilon"},
    ]

    chunks = batches._chunk_rows(rows, 2)

    assert [len(chunk) for chunk in chunks] == [2, 2, 1]
    assert batches._ticker_arg(chunks[0]) == "000001=Alpha,000002=Beta"


def test_chunk_rows_by_count_splits_whole_universe_into_requested_batches():
    rows = [{"Code": f"{idx:06d}", "Name": f"Name {idx}"} for idx in range(1, 11)]

    chunks = batches._chunk_rows_by_count(rows, 3)

    assert [len(chunk) for chunk in chunks] == [4, 3, 3]
    assert chunks[0][0]["Code"] == "000001"
    assert chunks[-1][-1]["Code"] == "000010"


def test_load_batch_universe_forces_fdr_provider_and_restores_env(monkeypatch):
    observed = []

    def fake_load(limit):
        observed.append((limit, os.environ.get("AG_KR_UNIVERSE_PROVIDER")))
        return _universe(1)

    monkeypatch.setattr(batches, "_load_kr_universe", fake_load)
    monkeypatch.setenv("AG_KR_UNIVERSE_PROVIDER", "kis_rank")

    frame = batches._load_batch_universe(7)

    assert len(frame) == 1
    assert observed == [(7, "fdr")]
    assert os.environ["AG_KR_UNIVERSE_PROVIDER"] == "kis_rank"


def test_dry_run_writes_checkpoint_for_two_ticker_batches(tmp_path, monkeypatch):
    monkeypatch.setattr(batches, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(batches, "_load_batch_universe", lambda limit: _universe(5))

    state = batches.run(_args(tmp_path, batch_size=2, max_batches=2, dry_run=True))

    state_path = tmp_path / "state.json"
    latest_path = tmp_path / "reports" / "kis_full_scanner_batches_latest.json"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))

    assert state["batch_count"] == 3
    assert persisted["summary"] == {"completed": 0, "failed": 0, "skipped": 2, "pending": 1}
    assert [item["tickers"] for item in persisted["batches"]] == [["000001", "000002"], ["000003", "000004"]]
    assert latest_path.exists()


def test_dry_run_can_split_full_universe_into_three_batches(tmp_path, monkeypatch):
    monkeypatch.setattr(batches, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(batches, "_load_batch_universe", lambda limit: _universe(10))

    state = batches.run(_args(tmp_path, batch_count=3, max_batches=3, dry_run=True))

    assert state["chunk_mode"] == "batch_count"
    assert state["batch_count_requested"] == 3
    assert state["batch_count"] == 3
    assert [item["ticker_count"] for item in state["batches"]] == [4, 3, 3]
    assert state["summary"] == {"completed": 0, "failed": 0, "skipped": 3, "pending": 0}


def test_resume_skips_completed_batch_and_runs_next_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(batches, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(batches, "_load_batch_universe", lambda limit: _universe(4))
    commands = []

    def fake_run_with_retries(command, *, env, retries, timeout_sec):
        commands.append((command, env, retries, timeout_sec))
        return {"returncode": 0, "elapsed_sec": 0.01, "timeout": False, "output_tail": ["ok"], "attempts": []}

    monkeypatch.setattr(batches, "_run_with_retries", fake_run_with_retries)
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "run_id": "existing",
                "batches": [
                    {"batch_index": 0, "batch_number": 1, "status": "completed", "tickers": ["000001", "000002"]}
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    state = batches.run(_args(tmp_path, batch_size=2, max_batches=1, resume=True))

    assert len(commands) == 1
    assert commands[0][0][-2] == "000003=Name 3,000004=Name 4"
    assert commands[0][0][-1] == "--allow-empty-results"
    assert commands[0][1]["AG_KR_MARKET_DATA_PROVIDER"] == "kis_only"
    assert commands[0][1]["AG_ENABLE_KIS_SIDECAR"] == "1"
    assert commands[0][2] == 0
    assert commands[0][3] == 0.0
    assert state["summary"] == {"completed": 2, "failed": 0, "skipped": 0, "pending": 0}


def test_run_with_retries_records_attempt_accounting(monkeypatch):
    calls = []

    def fake_run_command(command, *, env, timeout_sec):
        calls.append(timeout_sec)
        return {
            "returncode": 1 if len(calls) == 1 else 0,
            "elapsed_sec": 0.01,
            "timeout": False,
            "output_tail": [f"attempt {len(calls)}"],
        }

    monkeypatch.setattr(batches, "_run_command", fake_run_command)

    result = batches._run_with_retries(["scan"], env={"A": "B"}, retries=2, timeout_sec=3.5)

    assert result["returncode"] == 0
    assert result["retry_count"] == 1
    assert [attempt["attempt"] for attempt in result["attempts"]] == [1, 2]
    assert calls == [3.5, 3.5]


def test_scan_exception_reason_marks_batch_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(batches, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(batches, "_load_batch_universe", lambda limit: _universe(2))

    def fake_run_with_retries(command, *, env, retries, timeout_sec):
        return {
            "returncode": 0,
            "elapsed_sec": 0.01,
            "timeout": False,
            "scan_exception_reasons": ["EXCEPTION:ValueError: 1"],
            "output_tail": ["EXCEPTION:ValueError: 1"],
            "attempts": [],
        }

    monkeypatch.setattr(batches, "_run_with_retries", fake_run_with_retries)

    state = batches.run(_args(tmp_path, batch_size=2, max_batches=1))

    assert state["batches"][0]["status"] == "failed"
    assert state["summary"] == {"completed": 0, "failed": 1, "skipped": 0, "pending": 0}
