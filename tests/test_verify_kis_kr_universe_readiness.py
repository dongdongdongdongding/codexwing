from __future__ import annotations

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "multi_agent" / "tools" / "verify_kis_kr_universe_readiness.py"


def _load_tool_module():
    spec = importlib.util.spec_from_file_location("verify_kis_kr_universe_readiness", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_filter_universe_for_requested_tickers_matches_suffix_and_codes():
    tool = _load_tool_module()
    universe = {
        "KOSPI": {"005930.KS": "Samsung", "267250.KS": "HD Hyundai"},
        "KOSDAQ": {"215200.KQ": "Megastudy Edu"},
    }

    requested = tool._parse_requested_tickers("KOSPI:267250,215200.KQ,999999.KQ")
    selected, missing = tool._filter_universe_for_tickers(universe, requested)

    assert selected == {
        "KOSPI": {"267250.KS": "HD Hyundai"},
        "KOSDAQ": {"215200.KQ": "Megastudy Edu"},
    }
    assert missing == [{"market": "", "ticker": "999999.KQ"}]


def test_write_reports_can_skip_latest_artifacts(tmp_path, monkeypatch):
    tool = _load_tool_module()
    monkeypatch.setattr(tool, "REPORT_DIR", tmp_path)

    artifacts = tool._write_reports(
        {"run_id": "TEST", "tool": "verify_kis_kr_universe_readiness"},
        {"KOSPI": [{"market": "KOSPI", "ticker": "005930.KS", "name": "Samsung", "ok": True}]},
        write_latest=False,
    )

    assert Path(artifacts["json"]).exists()
    assert Path(artifacts["quote_csv"]).exists()
    assert "json_latest" not in artifacts
    assert "quote_csv_latest" not in artifacts
    assert not (tmp_path / "kis_kr_universe_readiness_latest.json").exists()
    assert not (tmp_path / "kis_kr_universe_quote_rows_latest.csv").exists()
