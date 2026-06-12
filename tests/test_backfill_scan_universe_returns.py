from multi_agent.tools.backfill_scan_universe_returns import (
    BUY_PREMIUM_PATH_LABEL_VERSION,
    PriceHistoryProvider,
    _compute_return_payload,
    build_updates,
    fetch_snapshot_rows,
    write_updates,
)


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
    assert payload["buy_premium_entry_price"] == 10200.0
    assert payload["buy_premium_return_5d_pct"] == 7.843137
    assert payload["buy_premium_max_high_return_5d_pct"] == 9.803922
    assert payload["buy_premium_min_low_return_5d_pct"] == -3.921569
    assert payload["target_hit_5d"] is True
    assert payload["target_before_stop_5d"] is True
    assert payload["first_touch_5d"] == "target"
    assert payload["buy_premium_target_hit_5d"] is True
    assert payload["buy_premium_target_before_stop_5d"] is True
    assert payload["buy_premium_first_touch_5d"] == "target"
    assert payload["buy_premium_path_label_version"] == BUY_PREMIUM_PATH_LABEL_VERSION
    assert payload["outcome_available"] is True


def test_price_history_provider_can_fetch_kis_daily_bars(monkeypatch):
    class FakeKISClient:
        def __init__(self, timeout=8):
            self.timeout = timeout

        def daily_bars(self, symbol, *, start_date, end_date, period="D"):
            assert symbol == "005930.KS"
            assert start_date == "20260520"
            assert end_date == "20260522"
            assert period == "D"
            return {
                "output2": [
                    {
                        "stck_bsop_date": "20260522",
                        "stck_oprc": "1000",
                        "stck_hgpr": "1150",
                        "stck_lwpr": "990",
                        "stck_clpr": "1100",
                        "acml_vol": "1000",
                    },
                    {
                        "stck_bsop_date": "20260520",
                        "stck_oprc": "900",
                        "stck_hgpr": "1010",
                        "stck_lwpr": "880",
                        "stck_clpr": "1000",
                        "acml_vol": "800",
                    },
                ]
            }

    monkeypatch.setattr("modules.kis_openapi.KISOpenAPIClient", FakeKISClient)

    provider = PriceHistoryProvider(provider="kis", fetch_timeout=0)
    bars = provider.fetch("005930.KS", "2026-05-20", "2026-05-22")

    assert provider.fetch_counts["kis"] == 1
    assert [bar["date"] for bar in bars] == ["2026-05-20", "2026-05-22"]
    assert bars[-1]["close"] == 1100.0


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
    assert payload["buy_premium_target_hit_1d"] is False
    assert payload["buy_premium_stop_hit_1d"] is True
    assert payload["buy_premium_target_before_stop_1d"] is False
    assert payload["buy_premium_stop_before_target_1d"] is True
    assert payload["buy_premium_first_touch_1d"] == "stop"


def test_fetch_snapshot_rows_applies_filters_and_retries_timeout(monkeypatch):
    calls = {"limit": [], "eq": [], "gte": [], "lte": []}
    rows = [
        {"id": 1, "ticker": "000001.KS", "market": "KOSPI", "scan_mode": "SWING", "base_trade_date": "2026-05-22"},
        {"id": 2, "ticker": "000002.KS", "market": "KOSPI", "scan_mode": "SWING", "base_trade_date": "2026-05-22"},
    ]

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        failures = 0

        def __init__(self):
            self._last_id = 0
            self._limit = None

        def select(self, _cols):
            return self

        def order(self, _field):
            return self

        def gt(self, _field, value):
            self._last_id = int(value)
            return self

        def limit(self, value):
            self._limit = int(value)
            calls["limit"].append(self._limit)
            return self

        def eq(self, field, value):
            calls["eq"].append((field, value))
            return self

        def gte(self, field, value):
            calls["gte"].append((field, value))
            return self

        def lte(self, field, value):
            calls["lte"].append((field, value))
            return self

        def execute(self):
            if self._limit == 1000 and Query.failures == 0:
                Query.failures += 1
                raise RuntimeError("57014 canceling statement due to statement timeout")
            batch = [row for row in rows if row["id"] > self._last_id][: self._limit]
            return Result(batch)

    class Client:
        def table(self, _table):
            return Query()

    class FakeDB:
        client = Client()

    import modules.db_manager as db_manager

    monkeypatch.setattr(db_manager, "DBManager", lambda: FakeDB())

    got = fetch_snapshot_rows(
        market="KOSPI",
        scan_mode="SWING",
        page_size=1000,
        min_id=0,
        max_id=10,
        base_date="2026-05-22",
        min_base_date="",
        max_base_date="",
        limit=0,
    )

    assert [row["id"] for row in got] == [1, 2]
    assert calls["limit"][:2] == [1000, 500]
    assert ("market", "KOSPI") in calls["eq"]
    assert ("scan_mode", "SWING") in calls["eq"]
    assert ("base_trade_date", "2026-05-22") in calls["eq"]
    assert ("id", 10) in calls["lte"]


def test_fetch_snapshot_rows_retries_timeout_below_100(monkeypatch):
    calls = {"limit": []}
    rows = [
        {"id": 1, "ticker": "000001.KS", "market": "KOSPI", "scan_mode": "SWING", "base_trade_date": "2026-05-22"}
    ]

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        failures = 0

        def __init__(self):
            self._last_id = 0
            self._limit = None

        def select(self, _cols):
            return self

        def order(self, _field):
            return self

        def gt(self, _field, value):
            self._last_id = int(value)
            return self

        def limit(self, value):
            self._limit = int(value)
            calls["limit"].append(self._limit)
            return self

        def eq(self, _field, _value):
            return self

        def gte(self, _field, _value):
            return self

        def lte(self, _field, _value):
            return self

        def execute(self):
            if self._limit == 100 and Query.failures == 0:
                Query.failures += 1
                raise RuntimeError("57014 canceling statement due to statement timeout")
            batch = [row for row in rows if row["id"] > self._last_id][: self._limit]
            return Result(batch)

    class Client:
        def table(self, _table):
            return Query()

    class FakeDB:
        client = Client()

    import modules.db_manager as db_manager

    monkeypatch.setattr(db_manager, "DBManager", lambda: FakeDB())

    got = fetch_snapshot_rows(
        market="ALL",
        scan_mode="ALL",
        page_size=100,
        min_id=0,
        max_id=0,
        base_date="",
        min_base_date="",
        max_base_date="",
        limit=0,
    )

    assert [row["id"] for row in got] == [1]
    assert calls["limit"][:2] == [100, 50]


def test_fetch_snapshot_rows_can_filter_client_side(monkeypatch):
    calls = {"eq": []}
    rows = [
        {"id": 1, "ticker": "000001.KS", "market": "KOSPI", "scan_mode": "SWING", "base_trade_date": "2026-05-22"},
        {"id": 2, "ticker": "000002.KQ", "market": "KOSDAQ", "scan_mode": "SWING", "base_trade_date": "2026-05-22"},
        {"id": 3, "ticker": "000003.KS", "market": "KOSPI", "scan_mode": "INTRADAY", "base_trade_date": "2026-05-22"},
        {"id": 4, "ticker": "000004.KS", "market": "KOSPI", "scan_mode": "SWING", "base_trade_date": "2026-05-29"},
    ]

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self):
            self._last_id = 0
            self._limit = None

        def select(self, _cols):
            return self

        def order(self, _field):
            return self

        def gt(self, _field, value):
            self._last_id = int(value)
            return self

        def limit(self, value):
            self._limit = int(value)
            return self

        def eq(self, field, value):
            calls["eq"].append((field, value))
            return self

        def gte(self, _field, _value):
            return self

        def lte(self, _field, _value):
            return self

        def execute(self):
            batch = [row for row in rows if row["id"] > self._last_id][: self._limit]
            return Result(batch)

    class Client:
        def table(self, _table):
            return Query()

    class FakeDB:
        client = Client()

    import modules.db_manager as db_manager

    monkeypatch.setattr(db_manager, "DBManager", lambda: FakeDB())

    got = fetch_snapshot_rows(
        market="KOSPI",
        scan_mode="SWING",
        page_size=10,
        min_id=0,
        max_id=0,
        base_date="",
        min_base_date="2026-05-22",
        max_base_date="2026-05-28",
        limit=0,
        client_filter=True,
    )

    assert [row["id"] for row in got] == [1]
    assert calls["eq"] == []


def test_write_updates_reduces_upsert_batch_on_timeout(monkeypatch):
    calls = {"batch_lengths": []}

    class Result:
        data = []

    class Query:
        def __init__(self):
            self._payload = []

        def upsert(self, payload, **_kwargs):
            self._payload = list(payload)
            return self

        def execute(self):
            calls["batch_lengths"].append(len(self._payload))
            if len(self._payload) > 25:
                raise RuntimeError("57014 canceling statement due to statement timeout")
            return Result()

    class Client:
        def table(self, _table):
            return Query()

    class FakeDB:
        client = Client()

    import modules.db_manager as db_manager

    monkeypatch.setattr(db_manager, "DBManager", lambda: FakeDB())

    written = write_updates(
        [
            {
                "id": idx,
                "snapshot_key": f"KEY-{idx}",
                "run_id": "RUN",
                "ticker": f"{idx:06d}.KS",
                "row_role": "rejected",
            }
            for idx in range(1, 51)
        ],
        batch_size=50,
        write_method="upsert",
    )

    assert written == 50
    assert calls["batch_lengths"] == [50, 25, 25]
