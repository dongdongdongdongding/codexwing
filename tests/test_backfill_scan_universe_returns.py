from multi_agent.tools.backfill_scan_universe_returns import _compute_return_payload, build_updates


def test_compute_return_payload_uses_future_trading_days_and_preserves_existing_values():
    row = {
        "base_trade_date": "2026-05-20",
        "entry_reference_price": 10000,
        "return_1d_pct": None,
        "return_3d_pct": 99.0,
        "return_5d_pct": None,
    }
    bars = [
        {"date": "2026-05-20", "close": 10000, "high": 10100, "low": 9900},
        {"date": "2026-05-21", "close": 10200, "high": 10300, "low": 9800},
        {"date": "2026-05-22", "close": 10100, "high": 10400, "low": 10000},
        {"date": "2026-05-25", "close": 10500, "high": 10600, "low": 10100},
        {"date": "2026-05-26", "close": 10700, "high": 10800, "low": 10400},
        {"date": "2026-05-27", "close": 11000, "high": 11200, "low": 10600},
    ]

    payload = _compute_return_payload(row, bars, overwrite=False)

    assert payload["return_1d_pct"] == 2.0
    assert "return_3d_pct" not in payload
    assert payload["return_5d_pct"] == 10.0
    assert payload["max_high_return_5d_pct"] == 12.0
    assert payload["min_low_return_5d_pct"] == -2.0
    assert payload["target_hit_5d"] is True
    assert payload["target_before_stop_5d"] is True
    assert payload["first_touch_5d"] == "target"
    assert payload["outcome_available"] is True


def test_compute_return_payload_can_fill_from_entry_close_when_entry_missing():
    row = {"base_trade_date": "2026-05-20", "entry_reference_price": None}
    bars = [
        {"date": "2026-05-20", "close": 5000, "high": 5100, "low": 4950},
        {"date": "2026-05-21", "close": 5500, "high": 5600, "low": 5450},
    ]

    payload = _compute_return_payload(row, bars, overwrite=False)

    assert payload["entry_reference_price"] == 5000.0
    assert payload["return_1d_pct"] == 10.0
    assert payload["max_high_return_1d_pct"] == 12.0
    assert payload["min_low_return_1d_pct"] == 9.0
    assert "alpha_score" in payload["feature_missing_keys"]


def test_compute_return_payload_marks_actual_flow_asof():
    row = {
        "base_trade_date": "2026-05-20",
        "entry_reference_price": 1000,
        "foreigner_1d": 100,
        "institution_1d": 50,
        "foreigner_3d": 120,
        "institution_3d": 80,
        "retail_1d": -150,
    }
    bars = [
        {"date": "2026-05-20", "close": 1000, "high": 1000, "low": 1000},
        {"date": "2026-05-21", "close": 1010, "high": 1020, "low": 990},
    ]

    payload = _compute_return_payload(row, bars, overwrite=False)

    assert payload["has_actual_flow"] is True
    assert payload["flow_source"] == "scan_universe_snapshot"
    assert payload["flow_asof"] == "2026-05-20"
    assert payload["flow_consensus_buying"] is True
    assert payload["whale_trend"] == "accumulation"


def test_build_updates_repairs_missing_base_date_from_run_index():
    class Provider:
        fetch_counts = {"fixture": 1}
        fetch_failures = {}

        def fetch(self, ticker, start, end):
            assert ticker == "000001.KS"
            assert start == "2026-05-17"
            return [
                {"date": "2026-05-20", "close": 1000, "high": 1010, "low": 990},
                {"date": "2026-05-21", "close": 1100, "high": 1120, "low": 980},
            ]

    result = build_updates(
        [
            {
                "id": 1,
                "snapshot_key": "RUN-X:000001.KS",
                "run_id": "RUN-X",
                "ticker": "000001.KS",
                "market": "KOSPI",
                "row_role": "rejected",
                "base_trade_date": None,
                "entry_reference_price": 1000,
                "return_1d_pct": None,
                "return_3d_pct": None,
                "return_5d_pct": None,
                "max_high_return_1d_pct": None,
                "max_high_return_3d_pct": None,
                "max_high_return_5d_pct": None,
            }
        ],
        provider=Provider(),
        overwrite=False,
        max_tickers=0,
        run_date_index={"RUN-X": "2026-05-20"},
    )

    assert result["repaired_base_date_candidates"] == 1
    assert result["updates"][0]["base_trade_date"] == "2026-05-20"
    assert result["updates"][0]["return_1d_pct"] == 10.0
    assert result["updates"][0]["stop_hit_1d"] is False


def test_compute_return_payload_marks_stop_before_target_conservatively():
    row = {"base_trade_date": "2026-05-20", "entry_reference_price": 1000}
    bars = [
        {"date": "2026-05-20", "close": 1000, "high": 1000, "low": 1000},
        {"date": "2026-05-21", "close": 960, "high": 1060, "low": 940},
    ]

    payload = _compute_return_payload(row, bars, overwrite=False, target_pct=5.0, stop_pct=5.0)

    assert payload["target_hit_1d"] is True
    assert payload["stop_hit_1d"] is True
    assert payload["target_before_stop_1d"] is False
    assert payload["stop_before_target_1d"] is True
    assert payload["first_touch_1d"] == "same_bar_stop_first"
