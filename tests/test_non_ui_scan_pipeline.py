import json

from multi_agent.workflows import non_ui_scan_pipeline as pipeline
from multi_agent.workflows.non_ui_scan_pipeline import _generate_top_deep_reports_for_run, _pipeline_source


def test_pipeline_source_marks_discord_executor():
    assert _pipeline_source("discord-full-kr-v1", "discord-scan-executor-v1") == "discord_scan_executor"
    assert _pipeline_source("legacy-cli-v1", "non-ui-scan-v1") == "non_ui_scan_pipeline"


def test_manual_kospi_tickers_are_exchange_qualified(monkeypatch):
    def fake_market_tickers(market):
        assert market == "KOSPI"
        return {
            "005930.KS": "삼성전자",
            "000660.KS": "SK하이닉스",
            "035420.KS": "NAVER",
        }

    monkeypatch.setattr(pipeline.quant_analysis.QuantStrategy, "get_market_tickers", staticmethod(fake_market_tickers))

    ticker_map = pipeline._resolve_ticker_map("KOSPI", "005930,000660,035420")

    assert list(ticker_map.keys()) == ["005930.KS", "000660.KS", "035420.KS"]
    assert ticker_map["005930.KS"] == "삼성전자"
    assert ticker_map["000660.KS"] == "SK하이닉스"


def test_manual_kosdaq_ticker_falls_back_to_market_suffix(monkeypatch):
    monkeypatch.setattr(pipeline.quant_analysis.QuantStrategy, "get_market_tickers", staticmethod(lambda _market: {}))

    ticker_map = pipeline._resolve_ticker_map("KOSDAQ", "123456")

    assert ticker_map == {"123456.KQ": "123456.KQ"}


def test_non_ui_top_deep_keeps_profile_exception_when_raw_results_empty(tmp_path, monkeypatch):
    from modules import top_deep_report

    report_dir = tmp_path / "top_deep"
    shared_dir = tmp_path / "shared"
    shared_dir.mkdir()
    planner_path = shared_dir / "planner_handoff.json"
    profile_path = shared_dir / "profile_diagnostics.json"
    planner_path.write_text(json.dumps({"decisions": [], "watchlist_meta": []}), encoding="utf-8")
    profile_path.write_text(
        json.dumps(
            {
                "exception_leaders": {
                    "watchlist_meta": [
                        {
                            "ticker": "000660.KS",
                            "stock_name": "SK하이닉스",
                            "decision": "EXCEPTION_LEADER",
                            "decision_bucket": "exception_leader",
                            "risk_label": "EXCEPTION_LEADER",
                            "Decision Score": 93.0,
                            "expected_edge_score": 7.5,
                            "loss_risk_score": 35.0,
                        }
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("AG_TOP_DEEP_WRITE_DB", "0")
    monkeypatch.setattr(top_deep_report, "LOCAL_REPORT_DIR", report_dir)
    monkeypatch.setattr(
        top_deep_report,
        "_fetch_price_snapshot",
        lambda _ticker: {
            "warnings": [],
            "current_price": 100.0,
            "day_change_pct": 0.5,
            "ma5": 99.0,
            "ma20": 96.0,
            "prior_20d_high": 104.0,
            "return_5d_pct": 3.0,
            "return_20d_pct": 8.0,
            "return_60d_pct": 20.0,
            "pct_from_52w_high": -12.0,
            "volume_ratio_20d": 1.3,
            "ohlcv_tail": [],
        },
    )
    monkeypatch.setattr(
        top_deep_report,
        "_fetch_news_snapshot",
        lambda _ticker, _stock_name: {"status": "OK", "headlines": [], "warnings": []},
    )
    monkeypatch.setattr(
        top_deep_report,
        "_fetch_investor_flow_snapshot",
        lambda _ticker, _row, _trace: {"valid": False, "warnings": ["test_flow_unavailable"]},
    )

    result = _generate_top_deep_reports_for_run(
        results=[],
        manifest_paths={"planner_handoff": str(planner_path), "profile_diagnostics": str(profile_path)},
        run_id="RUN-DISCORD-ZERO",
        market="KOSPI",
        scan_mode="SWING",
    )

    saved = json.loads((report_dir / "RUN-DISCORD-ZERO.json").read_text(encoding="utf-8"))
    assert result["count"] == 1
    assert result["local_path"].endswith("RUN-DISCORD-ZERO.json")
    assert saved[0]["ticker"] == "000660.KS"
    assert saved[0]["selection_alignment"]["analysis_section"] == "Exception Leader"
