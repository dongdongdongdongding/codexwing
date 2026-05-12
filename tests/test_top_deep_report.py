from unittest.mock import patch

from modules.top_deep_report import build_top_deep_reports


def test_build_top_deep_reports_merges_real_scan_and_planner_trace():
    with patch("modules.top_deep_report._fetch_price_snapshot") as price, patch("modules.top_deep_report._fetch_news_snapshot") as news:
        price.return_value = {
            "warnings": [],
            "current_price": 100.0,
            "day_change_pct": 1.2,
            "volume": 10000,
            "volume_ratio_20d": 1.5,
            "trend": "UP",
            "ohlcv_tail": [{"date": "2026-05-12", "close": 100.0}],
        }
        news.return_value = {
            "status": "OK",
            "sentiment_score": 0.25,
            "headlines": [{"title": "real headline", "score": 0.25}],
            "warnings": [],
        }

        reports = build_top_deep_reports(
            scan_rows=[{"ticker": "005930.KS", "stock_name": "삼성전자", "Decision Score": 88.0}],
            planner_payload={
                "decisions": [
                    {
                        "ticker": "005930.KS",
                        "decision": "PRIORITY_WATCHLIST",
                        "priority_rank": 1,
                        "loss_risk_score": 42.0,
                        "relative_rank_score": 77.5,
                        "expected_return_1d_pct": 1.1,
                        "expected_return_3d_pct": 2.3,
                        "theme_risk": ["LOSS_RISK_SOFT_CAP"],
                    }
                ]
            },
            run_id="RUN-TEST",
            market="KOSPI",
            scan_mode="SWING",
            top_n=5,
        )

    assert len(reports) == 1
    report = reports[0]
    assert report["report_id"] == "RUN-TEST:005930.KS:top_deep_report_v1"
    assert report["signal_label"] == "PRIMARY_BUY"
    assert report["loss_risk_score"] == 42.0
    assert report["buy_score"] == 77.5
    assert report["accuracy"] is not None
    assert report["prediction"]["expected_return_3d_pct"] == 2.3
    assert report["trade_plan"]["target_tp_pct"] is not None
    assert report["trade_plan"]["stop_sl_pct"] is not None
    assert report["trade_plan"]["hold_days"] is not None
    assert report["trade_plan"]["entry_policy"]
    assert report["price"]["trend"] == "UP"
    assert report["news"]["headlines"][0]["title"] == "real headline"
