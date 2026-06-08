from __future__ import annotations

from datetime import date

import pandas as pd

from multi_agent.tools.backfill_kis_sidecar_to_scan_universe_snapshots import (
    BackfillOptions,
    build_daily_quote_proxy,
    build_updates,
    fetch_snapshot_rows,
    summarize_candidate_rows,
    verify_existing_sidecars,
    write_updates,
)


def _daily_payload() -> dict:
    return {
        "output2": [
            {
                "stck_bsop_date": "20260527",
                "stck_oprc": "9500",
                "stck_hgpr": "10200",
                "stck_lwpr": "9400",
                "stck_clpr": "10000",
                "acml_vol": "100000",
                "acml_tr_pbmn": "1000000000",
            },
            {
                "stck_bsop_date": "20260528",
                "stck_oprc": "10000",
                "stck_hgpr": "11000",
                "stck_lwpr": "9900",
                "stck_clpr": "10500",
                "acml_vol": "150000",
                "acml_tr_pbmn": "1575000000",
            },
        ]
    }


class FakeKISClient:
    def __init__(self) -> None:
        self.calls = {
            "daily_bars": 0,
            "investor_flow_snapshot": 0,
            "vi_status": 0,
            "stock_info": 0,
            "financial_ratio": 0,
            "news_titles": 0,
        }

    def daily_bars(self, *_args, **_kwargs):
        self.calls["daily_bars"] += 1
        return _daily_payload()

    def investor_flow_snapshot(self, *_args, **_kwargs):
        self.calls["investor_flow_snapshot"] += 1
        return {
            "source_status": "ok",
            "flow_asof": "20260528",
            "flow_unit": "KRW",
            "foreigner_1d": 100,
            "institution_1d": 200,
            "retail_1d": -300,
            "foreigner_3d": 300,
            "institution_3d": 600,
            "retail_3d": -900,
            "foreigner_10d": 1000,
            "institution_10d": 2000,
            "retail_10d": -3000,
        }

    def vi_status(self, *_args, **_kwargs):
        self.calls["vi_status"] += 1
        return {"output": []}

    def stock_info(self, *_args, **_kwargs):
        self.calls["stock_info"] += 1
        return {
            "output": {
                "pdno": "000001",
                "prdt_name": "테스트",
                "mket_id_cd": "STK",
                "mket_id_cd_name": "KOSPI",
                "lstg_stqt": "10000000",
            }
        }

    def financial_ratio(self, *_args, **_kwargs):
        self.calls["financial_ratio"] += 1
        return {
            "output": {
                "stac_yymm": "202512",
                "roe_val": "12.5",
                "per": "9.1",
                "pbr": "1.2",
            }
        }

    def news_titles(self, *_args, **kwargs):
        self.calls["news_titles"] += 1
        symbol = kwargs.get("symbol") or "005930"
        return {
            "output": [
                {
                    "mksc_shrn_iscd": str(symbol).split(".")[0],
                    "hts_pbnt_titl_cntt": "AI 반도체 공급 계약 수주",
                    "data_dt": "20260528",
                    "data_tm": "090000",
                    "dorg": "KIS",
                }
            ]
        }


def test_daily_quote_proxy_uses_real_daily_bar_fields():
    frame = pd.DataFrame(
        [
            {"Date": pd.Timestamp("2026-05-27"), "Open": 9500, "High": 10200, "Low": 9400, "Close": 10000, "Volume": 100000},
            {"Date": pd.Timestamp("2026-05-28"), "Open": 10000, "High": 11000, "Low": 9900, "Close": 10500, "Volume": 150000},
        ]
    ).set_index("Date")

    quote = build_daily_quote_proxy(symbol="000001.KS", base_date=date(2026, 5, 28), daily_bars=frame, value_traded=1575000000)

    assert quote["last_price"] == 10500
    assert quote["day_change_pct"] == 5.0
    assert quote["value_traded"] == 1575000000
    assert quote["source"] == "kis_openapi_daily_backfill"
    assert "quote_snapshot_reconstructed_from_kis_daily_bars" in quote["warnings"]


def test_build_updates_dedupes_same_ticker_and_merges_feature_snapshot():
    client = FakeKISClient()
    rows = [
        {
            "id": 1,
            "snapshot_key": "RUN-A:000001.KS:emitted",
            "run_id": "RUN-A",
            "ticker": "000001.KS",
            "market": "KOSPI",
            "row_role": "emitted",
            "base_trade_date": "2026-05-28",
            "feature_snapshot": {"legacy_feature": 1},
        },
        {
            "id": 2,
            "snapshot_key": "RUN-A:000001.KS:rejected",
            "run_id": "RUN-A",
            "ticker": "000001.KS",
            "market": "KOSPI",
            "row_role": "rejected",
            "base_trade_date": "2026-05-28",
            "feature_snapshot": {"legacy_feature": 2},
        },
    ]

    built = build_updates(rows, client=client, options=BackfillOptions(include_vi=True))
    updates = built["updates"]

    assert len(updates) == 2
    assert built["unique_keys"] == 1
    assert client.calls["daily_bars"] == 1
    assert client.calls["vi_status"] == 1
    assert client.calls["stock_info"] == 1
    assert client.calls["financial_ratio"] == 1
    snapshot = updates[0]["feature_snapshot"]
    assert snapshot["legacy_feature"] == 1
    assert snapshot["kis_sidecar"]["feature_origin"] == "kis_openapi_backfill"
    assert snapshot["kis_sidecar"]["asof_policy"]["no_dummy_data"] is True
    assert snapshot["kis_model_candidate_features"]["kis_current_price"] == 10500.0
    assert snapshot["kis_model_candidate_features"]["kis_daily_bar_count"] == 2
    assert snapshot["kis_sidecar_backfill"]["no_dummy_data"] is True
    assert snapshot["kis_theme_news_evidence"]["no_dummy_data"] is True
    assert snapshot["kis_theme_news_evidence"]["kis_backed"] is True


def test_build_updates_supports_bounded_parallel_workers():
    client = FakeKISClient()
    rows = [
        {
            "id": 2,
            "snapshot_key": "RUN-A:000002.KS:rejected",
            "run_id": "RUN-A",
            "ticker": "000002.KS",
            "market": "KOSPI",
            "row_role": "rejected",
            "base_trade_date": "2026-05-28",
            "feature_snapshot": {},
        },
        {
            "id": 1,
            "snapshot_key": "RUN-A:000001.KS:emitted",
            "run_id": "RUN-A",
            "ticker": "000001.KS",
            "market": "KOSPI",
            "row_role": "emitted",
            "base_trade_date": "2026-05-28",
            "feature_snapshot": {},
        },
    ]

    built = build_updates(rows, client=client, options=BackfillOptions(include_vi=False, max_workers=2))

    assert built["max_workers"] == 2
    assert built["unique_keys"] == 2
    assert built["sidecar_keys_built"] == 2
    assert [item["id"] for item in built["updates"]] == [1, 2]
    assert client.calls["daily_bars"] == 2


def test_existing_sidecar_is_skipped_without_overwrite():
    client = FakeKISClient()
    rows = [
        {
            "id": 1,
            "snapshot_key": "RUN-A:000001.KS:emitted",
            "run_id": "RUN-A",
            "ticker": "000001.KS",
            "market": "KOSPI",
            "row_role": "emitted",
            "base_trade_date": "2026-05-28",
            "feature_snapshot": {"kis_sidecar": {"feature_origin": "existing"}},
        }
    ]

    built = build_updates(rows, client=client, options=BackfillOptions(overwrite=False))

    assert built["updates"] == []
    assert built["skipped_existing_rows"] == 1
    assert client.calls["daily_bars"] == 0


def test_news_only_existing_sidecar_backfills_news_without_rebuilding_sidecar():
    client = FakeKISClient()
    row = {
        "id": 1,
        "snapshot_key": "RUN-A:000001.KS:emitted",
        "run_id": "RUN-A",
        "ticker": "000001.KS",
        "market": "KOSPI",
        "row_role": "emitted",
        "base_trade_date": "2026-05-28",
        "feature_snapshot": {
            "theme_context": {"primary_theme": "AI반도체"},
            "kis_sidecar": {
                "feature_origin": "kis_openapi_backfill",
                "coverage": {"quote_snapshot": True, "daily_ohlcv": True, "stock_info": True},
                "stock_info_contract": {"checked": True, "sector_name": "반도체", "standard_industry_code": "C261"},
                "model_candidate_features": {
                    "kis_current_price": 10500.0,
                    "kis_stock_sector_name": "반도체",
                    "kis_stock_standard_industry_code": "C261",
                },
            },
        },
    }

    built = build_updates([row], client=client, options=BackfillOptions(news_only_existing_sidecar=True))
    snapshot = built["updates"][0]["feature_snapshot"]

    assert built["sidecar_keys_built"] == 1
    assert client.calls["daily_bars"] == 0
    assert client.calls["news_titles"] == 1
    assert snapshot["kis_sidecar"]["coverage"]["news_titles"] is True
    assert snapshot["kis_sidecar"]["news_contract"]["news_count"] == 1
    assert snapshot["kis_model_candidate_features"]["kis_news_title_count"] == 1.0
    assert snapshot["kis_theme_news_evidence"]["news"]["news_count"] == 1
    assert "contract_order" in snapshot["kis_theme_news_evidence"]["news"]["positive_tags"]
    assert snapshot["kis_theme_news_evidence"]["no_dummy_data"] is True


def test_missing_outcome_label_only_skips_when_required():
    client = FakeKISClient()
    row = {
        "id": 1,
        "snapshot_key": "RUN-A:000001.KS:emitted",
        "run_id": "RUN-A",
        "ticker": "000001.KS",
        "market": "KOSPI",
        "row_role": "emitted",
        "base_trade_date": "2026-05-28",
        "return_5d_pct": None,
        "max_high_return_5d_pct": None,
        "target_before_stop_5d": None,
        "feature_snapshot": {},
    }

    unrestricted = build_updates([row], client=client, options=BackfillOptions())
    restricted = build_updates([row], client=FakeKISClient(), options=BackfillOptions(require_outcome_label=True))

    assert len(unrestricted["updates"]) == 1
    assert restricted["updates"] == []
    assert restricted["skipped_missing_outcome_label_rows"] == 1


def test_verify_existing_sidecars_counts_label_ready_rows():
    rows = [
        {
            "id": 1,
            "snapshot_key": "RUN-A:000001.KS:emitted",
            "ticker": "000001.KS",
            "market": "KOSPI",
            "row_role": "emitted",
            "base_trade_date": "2026-05-28",
            "return_5d_pct": 7.5,
            "feature_snapshot": {
                "kis_sidecar": {"feature_origin": "kis_openapi_backfill"},
                "kis_theme_news_evidence": {
                    "kis_backed": True,
                    "evidence_strength_level": "strong",
                    "news": {"checked": True},
                },
            },
        },
        {
            "id": 2,
            "snapshot_key": "RUN-A:000002.KS:emitted",
            "ticker": "000002.KS",
            "market": "KOSPI",
            "row_role": "emitted",
            "base_trade_date": "2026-05-28",
            "return_5d_pct": None,
            "feature_snapshot": {"kis_sidecar": {"feature_origin": "kis_openapi_sidecar"}},
        },
    ]

    summary = verify_existing_sidecars(rows)

    assert summary["checked_rows"] == 2
    assert summary["kis_sidecar_rows"] == 2
    assert summary["kis_sidecar_outcome_label_rows"] == 1
    assert summary["kis_sidecar_origins"]["kis_openapi_backfill"] == 1
    assert summary["kis_theme_news_evidence_rows"] == 1
    assert summary["kis_theme_news_kis_backed_rows"] == 1
    assert summary["kis_theme_news_news_checked_rows"] == 1
    assert summary["kis_theme_news_levels"] == {"strong": 1}


def test_summarize_candidate_rows_reports_date_distribution():
    rows = [
        {
            "id": 10,
            "snapshot_key": "A",
            "ticker": "000001.KS",
            "market": "KOSPI",
            "row_role": "emitted",
            "base_trade_date": "2026-05-28",
            "return_5d_pct": 1.0,
            "feature_snapshot": {},
        },
        {
            "id": 12,
            "snapshot_key": "B",
            "ticker": "000002.KQ",
            "market": "KOSDAQ",
            "row_role": "rejected",
            "base_trade_date": "2026-05-29",
            "max_high_return_5d_pct": 6.0,
            "feature_snapshot": {"kis_sidecar": {"feature_origin": "existing"}},
        },
    ]

    summary = summarize_candidate_rows(rows)

    assert summary["candidate_rows"] == 2
    assert summary["unique_base_dates"] == 2
    assert summary["candidate_rows_by_base_date"] == {"2026-05-28": 1, "2026-05-29": 1}
    assert summary["id_min"] == 10
    assert summary["id_max"] == 12
    assert summary["sample_candidate_rows"][1]["has_kis_sidecar"] is True


def test_fetch_snapshot_rows_retries_statement_timeout(monkeypatch):
    calls = {"limit": []}
    rows = [
        {
            "id": 1,
            "ticker": "000001.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "base_trade_date": "2026-05-28",
            "return_5d_pct": 1.0,
            "feature_snapshot": {},
        },
        {
            "id": 2,
            "ticker": "000002.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "base_trade_date": "2026-05-28",
            "return_5d_pct": 2.0,
            "feature_snapshot": {},
        },
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

        def lte(self, _field, _value):
            return self

        def gte(self, _field, _value):
            return self

        def eq(self, _field, _value):
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
        market="ALL",
        scan_mode="ALL",
        page_size=1000,
        limit=0,
        min_id=0,
        max_id=0,
        base_date="",
        min_base_date="",
        max_base_date="",
        overwrite=False,
        only_outcome_available=False,
        require_outcome_label=False,
    )

    assert [row["id"] for row in got] == [1, 2]
    assert calls["limit"][:2] == [1000, 500]


def test_fetch_snapshot_rows_retries_statement_timeout_below_100(monkeypatch):
    calls = {"limit": []}
    rows = [
        {
            "id": 1,
            "ticker": "000001.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "base_trade_date": "2026-05-28",
            "return_5d_pct": 1.0,
            "feature_snapshot": {},
        }
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

        def lte(self, _field, _value):
            return self

        def gte(self, _field, _value):
            return self

        def eq(self, _field, _value):
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
        limit=0,
        min_id=0,
        max_id=0,
        base_date="",
        min_base_date="",
        max_base_date="",
        overwrite=False,
        only_outcome_available=False,
        require_outcome_label=False,
    )

    assert [row["id"] for row in got] == [1]
    assert calls["limit"][:2] == [100, 50]


def test_fetch_snapshot_rows_can_filter_client_side(monkeypatch):
    calls = {"eq": []}
    rows = [
        {
            "id": 1,
            "ticker": "000001.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "base_trade_date": "2026-05-22",
            "return_5d_pct": 1.0,
            "feature_snapshot": {},
        },
        {
            "id": 2,
            "ticker": "000002.KQ",
            "market": "KOSDAQ",
            "scan_mode": "SWING",
            "base_trade_date": "2026-05-22",
            "return_5d_pct": 1.0,
            "feature_snapshot": {},
        },
        {
            "id": 3,
            "ticker": "000003.KS",
            "market": "KOSPI",
            "scan_mode": "INTRADAY",
            "base_trade_date": "2026-05-22",
            "return_5d_pct": 1.0,
            "feature_snapshot": {},
        },
        {
            "id": 4,
            "ticker": "000004.KS",
            "market": "KOSPI",
            "scan_mode": "SWING",
            "base_trade_date": "2026-05-29",
            "return_5d_pct": 1.0,
            "feature_snapshot": {},
        },
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

        def lte(self, _field, _value):
            return self

        def gte(self, _field, _value):
            return self

        def eq(self, field, value):
            calls["eq"].append((field, value))
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
        limit=0,
        min_id=0,
        max_id=0,
        base_date="",
        min_base_date="2026-05-22",
        max_base_date="2026-05-28",
        overwrite=False,
        only_outcome_available=False,
        require_outcome_label=True,
        client_filter=True,
    )

    assert [row["id"] for row in got] == [1]
    assert calls["eq"] == []


def test_write_updates_reduces_upsert_batch_on_timeout(monkeypatch):
    calls = {"batch_lengths": [], "conflicts": []}

    class Result:
        data = []

    class Query:
        def __init__(self):
            self._payload = []

        def upsert(self, payload, **kwargs):
            self._payload = list(payload)
            calls["conflicts"].append(kwargs.get("on_conflict"))
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
                "snapshot_key": f"RUN:{idx:06d}.KS",
                "run_id": "RUN",
                "ticker": f"{idx:06d}.KS",
                "market": "KOSPI",
                "row_role": "rejected",
                "base_trade_date": "2026-05-28",
                "feature_snapshot": {"kis_sidecar": {"idx": idx}},
                "updated_at": "2026-06-06T00:00:00+00:00",
            }
            for idx in range(1, 51)
        ],
        batch_size=50,
    )

    assert written == 50
    assert calls["batch_lengths"] == [50, 25, 25]
    assert calls["conflicts"] == ["snapshot_key", "snapshot_key", "snapshot_key"]
