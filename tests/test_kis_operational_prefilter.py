from __future__ import annotations

from modules.kis_operational_prefilter import (
    KISOperationalPrefilterConfig,
    build_kis_operational_prefilter,
    selected_ticker_arg,
    selected_ticker_symbols,
)


class FakeKISClient:
    def __init__(self) -> None:
        self.quote_calls = []
        self.flow_calls = []

    def volume_rank(self, *, market: str = "ALL"):
        return {
            "rt_cd": "0",
            "output": [
                {"mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자", "data_rank": "1"},
                {"mksc_shrn_iscd": "000660", "hts_kor_isnm": "SK하이닉스", "data_rank": "2"},
            ],
        }

    def fluctuation_rank(self, *, market: str = "ALL", sort: str = "up"):
        return {
            "rt_cd": "0",
            "output": [
                {"mksc_shrn_iscd": "000660", "hts_kor_isnm": "SK하이닉스", "data_rank": "1"},
                {"mksc_shrn_iscd": "001234", "hts_kor_isnm": "주의종목", "data_rank": "2"},
            ],
        }

    def volume_power_rank(self, *, market: str = "ALL"):
        return {"rt_cd": "0", "output": [{"mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자", "data_rank": "3"}]}

    def vi_status(self, *, market: str = "ALL", trade_date: str):
        return {"rt_cd": "0", "output": [{"mksc_shrn_iscd": "000660", "hts_kor_isnm": "SK하이닉스"}]}

    def quote_snapshot(self, symbol: str):
        self.quote_calls.append(symbol)
        code = symbol[:6]
        rows = {
            "005930": {
                "ticker": code,
                "source_status": "ok",
                "last_price": "81200",
                "day_change_pct": "1.5",
                "volume": "1234567",
                "value_traded": "100000000000",
                "prev_volume_ratio": "180.0",
                "market_cap": "480000000",
            },
            "000660": {
                "ticker": code,
                "source_status": "ok",
                "last_price": "205000",
                "day_change_pct": "3.0",
                "volume": "2345678",
                "value_traded": "250000000000",
                "prev_volume_ratio": "220.0",
                "market_cap": "300000000",
            },
            "001234": {
                "ticker": code,
                "source_status": "ok",
                "last_price": "1000",
                "day_change_pct": "12.0",
                "volume": "3456789",
                "value_traded": "5000000000",
                "prev_volume_ratio": "300.0",
                "status_warning": "investment_warning",
            },
        }
        return rows[code]

    def investor_flow_snapshot(self, symbol: str, *, trade_date: str, market_div: str = "J"):
        self.flow_calls.append(symbol)
        return {
            "source_status": "ok",
            "flow_unit": "KRW",
            "foreigner_1d": 100,
            "institution_1d": 50,
            "retail_1d": -150,
            "foreigner_3d": 200,
            "institution_3d": 100,
            "retail_3d": -300,
            "foreigner_10d": 300,
            "institution_10d": 200,
            "retail_10d": -500,
        }


def test_kis_prefilter_unions_rank_sources_and_excludes_blocked_status():
    client = FakeKISClient()

    report = build_kis_operational_prefilter(
        client,
        KISOperationalPrefilterConfig(
            markets=("KOSPI",),
            max_candidates_per_market=2,
            rank_limit_per_source=5,
            quote_limit_per_market=3,
            sleep_sec=0,
        ),
    )

    market = report["markets"]["KOSPI"]
    assert market["seed_count"] == 3
    assert market["selected_count"] == 2
    assert "001234.KS" not in market["selected_tickers"]
    assert "001234.KS" in [row["ticker"] for row in market["rejected_sample"]]
    assert set(market["selected_tickers"]) == {"005930.KS", "000660.KS"}
    assert len(client.quote_calls) == 3
    assert report["summary"]["selected_total"] == 2


def test_kis_prefilter_selected_ticker_arg_preserves_names_and_suffix():
    report = build_kis_operational_prefilter(
        FakeKISClient(),
        KISOperationalPrefilterConfig(markets=("KOSPI",), max_candidates_per_market=1, sleep_sec=0),
    )

    ticker_arg = selected_ticker_arg(report, "KOSPI")

    assert ticker_arg.endswith(".KS=SK하이닉스") or ticker_arg.endswith(".KS=삼성전자")
    assert ticker_arg.count(",") == 0
    assert "=" not in selected_ticker_symbols(report, "KOSPI")


def test_kis_prefilter_can_fetch_flow_without_fabricating_values():
    client = FakeKISClient()

    report = build_kis_operational_prefilter(
        client,
        KISOperationalPrefilterConfig(
            markets=("KOSPI",),
            max_candidates_per_market=2,
            flow_limit_per_market=1,
            fetch_flow=True,
            sleep_sec=0,
            trade_date="20260605",
        ),
    )

    selected = report["markets"]["KOSPI"]["selected"]
    assert len(client.flow_calls) == 1
    assert any(row.get("flow", {}).get("flow_source") == "kis_openapi" for row in selected)
    assert all(row["is_dummy_data"] is False for row in selected)


def test_kis_prefilter_rejects_zero_activity_rank_rows():
    class ZeroActivityClient(FakeKISClient):
        def quote_snapshot(self, symbol: str):
            code = symbol[:6]
            return {
                "ticker": code,
                "source_status": "ok",
                "last_price": "1000",
                "day_change_pct": "0",
                "volume": "0",
                "value_traded": "0",
            }

    report = build_kis_operational_prefilter(
        ZeroActivityClient(),
        KISOperationalPrefilterConfig(markets=("KOSPI",), max_candidates_per_market=2, sleep_sec=0),
    )

    market = report["markets"]["KOSPI"]
    assert market["selected_count"] == 0
    assert {row["reject_reason"] for row in market["rejected_sample"]} == {"quote_activity_missing"}
    assert "KOSPI:no_prefilter_candidates_selected" in report["warnings"]


def test_kis_prefilter_skips_non_numeric_rank_codes_before_deep_scan():
    class AlphaCodeClient(FakeKISClient):
        def fluctuation_rank(self, *, market: str = "ALL", sort: str = "up"):
            return {
                "rt_cd": "0",
                "output": [
                    {"mksc_shrn_iscd": "0001A0", "hts_kor_isnm": "비보통주", "data_rank": "1"},
                    {"mksc_shrn_iscd": "005930", "hts_kor_isnm": "삼성전자", "data_rank": "2"},
                ],
            }

        def volume_power_rank(self, *, market: str = "ALL"):
            return {"rt_cd": "0", "output": []}

    report = build_kis_operational_prefilter(
        AlphaCodeClient(),
        KISOperationalPrefilterConfig(markets=("KOSPI",), max_candidates_per_market=5, sleep_sec=0),
    )

    market = report["markets"]["KOSPI"]
    all_seed_tickers = {row["ticker"] for row in market["selected"] + market["rejected_sample"]}
    assert "0001A0.KS" not in all_seed_tickers
