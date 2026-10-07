import json
from pathlib import Path
from types import SimpleNamespace

from modules.scanner_runtime import run_parallel_scan
from multi_agent.tools import run_primary_market_session_ops as ops
from multi_agent.tools import run_us_full_universe_research as us


def test_runtime_aggregate_already_counts_both_error_types():
    def worker(symbol):
        if symbol == "worker":
            return {"error": "failed"}
        if symbol == "executor":
            raise ValueError("failed")
        return {"ticker": symbol}

    result = run_parallel_scan(ticker_list=["ok", "worker", "executor"], max_scan=3, worker_fn=worker)
    result.update(worker_error_count=1, executor_exception_count=1)
    health = us.summarize_health([result], 3, 1)
    assert result["error_count"] == health["total_errors"] == 2
    assert health["status"] == "degraded" and health["exit_code"] == 2
    assert health["scan_coverage_complete"]


def test_counter_disagreement_and_missing_scans_are_not_ok():
    summary = {"run_id": "one", "total_scans": 2, "error_count": 0, "worker_error_count": 1}
    health = us.summarize_health([summary], 3, 2)
    assert health["total_errors"] == 1
    assert health["error_count_mismatch_run_ids"] == ["one"]
    assert not health["scan_coverage_complete"]
    assert health["status"] == "degraded"


def prepare_main(tmp_path, monkeypatch, scan):
    monkeypatch.setattr(us.quant_analysis.QuantStrategy, "get_market_tickers", lambda market: {"A": "A", "B": "B"})
    monkeypatch.setattr(us, "run_non_ui_scan_pipeline", scan)
    monkeypatch.setattr("sys.argv", ["scan", "--market", "NASDAQ", "--batch-size", "1", "--output-dir", str(tmp_path)])
    monkeypatch.setenv("US_RESEARCH_RECEIPT_PATH", str(tmp_path / "receipt.json"))


def test_partial_error_exit_and_durable_receipt(tmp_path, monkeypatch):
    calls = []
    def scan(**kwargs):
        calls.append(kwargs["tickers"])
        errors = int(kwargs["tickers"] == "B")
        return {"run_id": kwargs["tickers"], "total_scans": 1, "error_count": errors, "worker_error_count": errors}
    prepare_main(tmp_path, monkeypatch, scan)
    assert us.main() == 2
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    report = json.loads(Path(receipt["json_path"]).read_text())
    assert calls == ["A", "B"]
    assert report["total_errors"] == 1 and receipt["status"] == "degraded"
    assert report["completed_batch_count"] == 2
    assert "batch_summaries" not in receipt


def test_batch_exception_preserves_completed_work_without_retry(tmp_path, monkeypatch):
    calls = []
    def scan(**kwargs):
        calls.append(kwargs["tickers"])
        if kwargs["tickers"] == "B":
            raise RuntimeError("interrupted batch")
        return {"run_id": "A", "total_scans": 1, "error_count": 0}
    prepare_main(tmp_path, monkeypatch, scan)
    assert us.main() == 2
    receipt = json.loads((tmp_path / "receipt.json").read_text())
    assert calls == ["A", "B"]
    assert receipt["status"] == "failed" and receipt["completed_batch_count"] == 1
    assert receipt["batch_failure"]["batch_index"] == 2
    assert receipt["run_ids"] == ["A"]


def test_complete_clean_scan_returns_zero(tmp_path, monkeypatch):
    prepare_main(tmp_path, monkeypatch, lambda **kw: {"total_scans": 1, "error_count": 0})
    assert us.main() == 0
    assert json.loads((tmp_path / "receipt.json").read_text())["status"] == "ok"


def test_session_links_receipt_even_when_stdout_is_truncated(tmp_path, monkeypatch):
    monkeypatch.setattr(ops, "PROJECT_ROOT", tmp_path)
    def run(argv, **kwargs):
        us._write_json(Path(kwargs["env"]["US_RESEARCH_RECEIPT_PATH"]), {
            "status": "degraded", "total_errors": 1, "json_path": "durable-report.json"})
        return SimpleNamespace(returncode=2, stdout="x" * 10000, stderr="")
    monkeypatch.setattr(ops.subprocess, "run", run)
    result = ops._run_command({"name": "nasdaq_full_universe_scan", "argv": ["python"]}, dry_run=False)
    artifact = result["step_artifacts"]["us_full_universe_scan"]
    assert artifact["status"] == "degraded" and artifact["total_errors"] == 1
    assert artifact["json_path"] == "durable-report.json" and artifact["sha256"]
    assert result["returncode"] == 2
