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
        {"date": "2026-05-20", "close": 10000, "high": 10100},
        {"date": "2026-05-21", "close": 10200, "high": 10300},
        {"date": "2026-05-22", "close": 10100, "high": 10400},
        {"date": "2026-05-25", "close": 10500, "high": 10600},
        {"date": "2026-05-26", "close": 10700, "high": 10800},
        {"date": "2026-05-27", "close": 11000, "high": 11200},
    ]

    payload = _compute_return_payload(row, bars, overwrite=False)

    assert payload["return_1d_pct"] == 2.0
    assert "return_3d_pct" not in payload
    assert payload["return_5d_pct"] == 10.0
    assert payload["max_high_return_5d_pct"] == 12.0
    assert payload["outcome_available"] is True


def test_compute_return_payload_can_fill_from_entry_close_when_entry_missing():
    row = {"base_trade_date": "2026-05-20", "entry_reference_price": None}
    bars = [
        {"date": "2026-05-20", "close": 5000, "high": 5100},
        {"date": "2026-05-21", "close": 5500, "high": 5600},
    ]

    payload = _compute_return_payload(row, bars, overwrite=False)

    assert payload["entry_reference_price"] == 5000.0
    assert payload["return_1d_pct"] == 10.0
    assert payload["max_high_return_1d_pct"] == 12.0


def test_build_updates_repairs_missing_base_date_from_run_index():
    class Provider:
        fetch_counts = {"fixture": 1}
        fetch_failures = {}

        def fetch(self, ticker, start, end):
            assert ticker == "000001.KS"
            assert start == "2026-05-17"
            return [
                {"date": "2026-05-20", "close": 1000, "high": 1010},
                {"date": "2026-05-21", "close": 1100, "high": 1120},
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
