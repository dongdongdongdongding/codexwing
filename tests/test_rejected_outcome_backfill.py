from modules.rejected_outcome_backfill import backfill_reject_outcomes, compute_forward_returns, dedupe_reject_rows


def test_dedupe_reject_rows_keeps_kr_rows_with_base_date():
    rows = dedupe_reject_rows(
        [
            {"run_id": "RUN-1", "ticker": "000001.KS", "base_trade_date": "2026-05-12", "stage": "liquidity_gate"},
            {"run_id": "RUN-1", "ticker": "000001.KS", "base_trade_date": "2026-05-12", "stage": "liquidity_gate"},
            {"run_id": "RUN-2", "ticker": "AAPL", "base_trade_date": "2026-05-12", "stage": "liquidity_gate"},
            {"run_id": "RUN-3", "ticker": "000002.KQ", "base_trade_date": "", "stage": "liquidity_gate"},
        ]
    )

    assert len(rows) == 1
    assert rows[0]["market"] == "KOSPI"
    assert rows[0]["emitted"] is False

    with_reason = dedupe_reject_rows(
        [{"run_id": "RUN-1", "ticker": "000003.KS", "base_trade_date": "2026-05-12", "reject_reasons": "LIQUIDITY_FILTER_FAIL"}]
    )
    assert with_reason[0]["reject_reason"] == "LIQUIDITY_FILTER_FAIL"


def test_compute_forward_returns_uses_entry_and_future_closes():
    row = {"ticker": "000001.KS", "base_trade_date": "2026-05-12", "entry_reference_price": 100.0}
    result = compute_forward_returns(
        row,
        [
            {"date": "2026-05-12", "close": 100, "high": 101},
            {"date": "2026-05-13", "close": 105, "high": 106},
            {"date": "2026-05-14", "close": 103, "high": 107},
            {"date": "2026-05-15", "close": 112, "high": 113},
            {"date": "2026-05-18", "close": 110, "high": 114},
            {"date": "2026-05-19", "close": 116, "high": 118},
        ],
    )

    assert result["outcome_available"] is True
    assert result["return_1d_pct"] == 5.0
    assert result["return_3d_pct"] == 12.0
    assert result["return_5d_pct"] == 16.0
    assert result["max_high_return_5d_pct"] == 18.0


def test_backfill_reject_outcomes_uses_price_provider():
    def provider(ticker, start, end):
        assert ticker == "000001.KS"
        assert start == "2026-05-12"
        return [
            {"date": "2026-05-12", "close": 100, "high": 100},
            {"date": "2026-05-13", "close": 107, "high": 108},
        ]

    rows = backfill_reject_outcomes(
        [{"run_id": "RUN-1", "ticker": "000001.KS", "base_trade_date": "2026-05-12", "curr_price": 100}],
        price_provider=provider,
    )

    assert len(rows) == 1
    assert rows[0]["return_1d_pct"] == 7.0
    assert rows[0]["outcome_available"] is True
