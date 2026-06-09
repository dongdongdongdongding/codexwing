from ui.archive_data import fetch_market_scan_archive_rows


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeMarketScanQuery:
    def __init__(self, rows):
        self._rows = rows
        self.ranges = []

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, start, end):
        self.ranges.append((start, end))
        self._start = start
        self._end = end
        return self

    def execute(self):
        return _FakeResponse(self._rows[self._start : self._end + 1])


class _FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def table(self, name):
        assert name == "market_scan_results"
        query = _FakeMarketScanQuery(self.rows)
        self.queries.append(query)
        return query


class _FakeDB:
    def __init__(self, client):
        self.client = client


def test_fetch_market_scan_archive_rows_pages_real_db_and_merges_local_artifacts():
    db_rows = [
        {"run_id": "RUN-1", "ticker": "005930.KS", "created_at": "2026-06-09T00:00:00Z"},
        {"run_id": "RUN-1", "ticker": "000660.KS", "created_at": "2026-06-09T00:00:00Z"},
        {"run_id": "RUN-2", "ticker": "035420.KS", "created_at": "2026-06-08T00:00:00Z"},
        {"run_id": "RUN-3", "ticker": "035720.KS", "created_at": "2026-06-07T00:00:00Z"},
    ]
    local_rows = [
        {"run_id": "RUN-1", "ticker": "005930.KS", "source_ref": "local_artifact:duplicate"},
        {"run_id": "RUN-LOCAL", "ticker": "123456.KQ", "source_ref": "local_artifact:new"},
    ]
    client = _FakeClient(db_rows)

    rows, meta = fetch_market_scan_archive_rows(
        max_rows=3,
        batch_size=2,
        include_local_fallback=True,
        local_limit_runs=10,
        db_factory=lambda: _FakeDB(client),
        local_loader=lambda **_kwargs: local_rows,
    )

    assert [row["ticker"] for row in rows] == ["005930.KS", "000660.KS", "035420.KS", "123456.KQ"]
    assert meta["source"] == "supabase+local_artifact"
    assert meta["db_available"] is True
    assert meta["db_rows"] == 3
    assert meta["local_rows"] == 2
    assert meta["rows"] == 4


def test_fetch_market_scan_archive_rows_uses_local_when_supabase_unavailable():
    local_rows = [{"run_id": "RUN-LOCAL", "ticker": "123456.KQ", "source_ref": "local_artifact:new"}]

    rows, meta = fetch_market_scan_archive_rows(
        max_rows=100,
        batch_size=50,
        include_local_fallback=True,
        local_limit_runs=10,
        db_factory=lambda: _FakeDB(None),
        local_loader=lambda **_kwargs: local_rows,
    )

    assert rows == local_rows
    assert meta["source"] == "local_artifact"
    assert meta["db_available"] is False
    assert meta["warnings"] == ["supabase_client_unavailable"]


def test_fetch_market_scan_archive_rows_can_skip_supabase_for_fast_ui_path():
    local_rows = [{"run_id": "RUN-LOCAL", "ticker": "123456.KQ", "source_ref": "local_artifact:new"}]
    called = {"db": False}

    def _db_factory():
        called["db"] = True
        return _FakeDB(_FakeClient([]))

    rows, meta = fetch_market_scan_archive_rows(
        max_rows=100,
        batch_size=50,
        include_supabase=False,
        include_local_fallback=True,
        local_limit_runs=10,
        db_factory=_db_factory,
        local_loader=lambda **_kwargs: local_rows,
    )

    assert rows == local_rows
    assert called["db"] is False
    assert meta["source"] == "local_artifact"
    assert meta["supabase_enabled"] is False
    assert meta["warnings"] == []
