from __future__ import annotations

import os
from datetime import datetime, timedelta

from modules import market_data

# 픽스처 날짜는 오늘 기준 동적 생성 — 하드코딩 시 "최근 1개월" 필터 창에서 밀려나
# 시간이 지나면 테스트가 스스로 부패한다 (2026-07-07 확인된 사전 부채).
_D = [(datetime.now() - timedelta(days=n)).strftime("%Y%m%d") for n in (4, 3, 2, 1)]


class FakeKISClient:
    def daily_bars(self, symbol, *, start_date, end_date, period="D", adjusted=True, market_div="J"):
        return {
            "output2": [
                {
                    "stck_bsop_date": _D[0],
                    "stck_oprc": "100",
                    "stck_hgpr": "110",
                    "stck_lwpr": "95",
                    "stck_clpr": "105",
                    "acml_vol": "1000",
                },
                {
                    "stck_bsop_date": _D[1],
                    "stck_oprc": "106",
                    "stck_hgpr": "112",
                    "stck_lwpr": "101",
                    "stck_clpr": "111",
                    "acml_vol": "1200",
                },
            ]
        }

    def today_minute_bars(self, symbol, *, input_hour="153000", include_past=True):
        return {
            "output2": [
                {
                    "stck_bsop_date": _D[1],
                    "stck_cntg_hour": "090000",
                    "stck_prpr": "100",
                    "stck_oprc": "100",
                    "stck_hgpr": "101",
                    "stck_lwpr": "99",
                    "cntg_vol": "10",
                },
                {
                    "stck_bsop_date": _D[1],
                    "stck_cntg_hour": "090100",
                    "stck_prpr": "102",
                    "stck_oprc": "101",
                    "stck_hgpr": "102",
                    "stck_lwpr": "100",
                    "cntg_vol": "20",
                },
            ]
        }


class FakePagedKISClient:
    def __init__(self):
        self.calls = []

    def daily_bars(self, symbol, *, start_date, end_date, period="D", adjusted=True, market_div="J"):
        self.calls.append({"start_date": start_date, "end_date": end_date})
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        rows = []
        for offset in range(100):
            dt = end_dt - timedelta(days=offset)
            price = 1000 + len(self.calls) + offset
            rows.append(
                {
                    "stck_bsop_date": dt.strftime("%Y%m%d"),
                    "stck_oprc": str(price),
                    "stck_hgpr": str(price + 10),
                    "stck_lwpr": str(price - 10),
                    "stck_clpr": str(price + 1),
                    "acml_vol": "1000",
                }
            )
        return {"output2": rows}


class FakeIntradayKISClient:
    def __init__(self):
        self.calls = []

    def today_minute_bars(self, symbol, *, input_hour="153000", include_past=True):
        self.calls.append(("today", input_hour))
        return {
            "output2": [
                {
                    "stck_bsop_date": _D[3],
                    "stck_cntg_hour": "090000",
                    "stck_prpr": "100",
                    "stck_oprc": "100",
                    "stck_hgpr": "101",
                    "stck_lwpr": "99",
                    "cntg_vol": "10",
                },
                {
                    "stck_bsop_date": _D[3],
                    "stck_cntg_hour": "100000",
                    "stck_prpr": "102",
                    "stck_oprc": "101",
                    "stck_hgpr": "103",
                    "stck_lwpr": "100",
                    "cntg_vol": "20",
                },
            ]
        }

    def daily_minute_bars(self, symbol, *, trade_date, input_hour="153000", include_past=True):
        self.calls.append(("daily", trade_date, input_hour))
        return {
            "output2": [
                {
                    "stck_bsop_date": trade_date,
                    "stck_cntg_hour": hour,
                    "stck_prpr": str(100 + idx),
                    "stck_oprc": str(99 + idx),
                    "stck_hgpr": str(101 + idx),
                    "stck_lwpr": str(98 + idx),
                    "cntg_vol": str(100 + idx),
                }
                for idx, hour in enumerate(["090000", "100000", "110000", "120000", "130000", "140000"])
            ]
        }


class FakeKISIndexClient:
    def industry_daily_bars(self, *, index_code, start_date, end_date, period="D", market_div="U"):
        assert index_code == "1001"
        assert market_div == "U"
        return {
            "output2": [
                {
                    "stck_bsop_date": _D[2],
                    "bstp_nmix_oprc": "1032.91",
                    "bstp_nmix_hgpr": "1065.90",
                    "bstp_nmix_lwpr": "1032.29",
                    "bstp_nmix_prpr": "1049.73",
                    "acml_vol": "622960",
                }
            ]
        }


def test_fetch_kis_history_daily_returns_normalized_ohlcv():
    frame = market_data._fetch_kis_history("005930.KS", period="1mo", interval="1d", client=FakeKISClient())

    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert float(frame["Close"].iloc[-1]) == 111.0
    assert frame.attrs["source_provider"] == "kis_openapi"


def test_fetch_kis_index_history_returns_normalized_ohlcv():
    frame = market_data._fetch_kis_index_history("^KQ11", period="1mo", interval="1d", client=FakeKISIndexClient())

    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert float(frame["Close"].iloc[-1]) == 1049.73
    assert frame.attrs["source_provider"] == "kis_openapi"


def test_fetch_kis_history_daily_paginates_kis_100_row_pages(monkeypatch):
    monkeypatch.setenv("AG_KIS_DAILY_MAX_CHUNKS", "4")
    client = FakePagedKISClient()

    frame = market_data._fetch_kis_history("005930.KS", period="1y", interval="1d", client=client)

    assert len(client.calls) >= 3
    assert len(frame) > 200
    assert frame.index.is_monotonic_increasing
    assert frame.attrs["source_provider"] == "kis_openapi"


def test_fetch_kis_history_intraday_builds_multi_day_kis_minutes(monkeypatch):
    monkeypatch.setenv("AG_KIS_INTRADAY_INPUT_HOUR", "101500")
    monkeypatch.setenv("AG_KIS_INTRADAY_LOOKBACK_DAYS", "5")
    monkeypatch.setenv("AG_KIS_INTRADAY_MIN_BARS", "8")
    client = FakeIntradayKISClient()

    frame = market_data._fetch_kis_history("005930.KS", period="60d", interval="1h", client=client)

    assert len(frame) >= 8
    assert frame.attrs["source_provider"] == "kis_openapi"
    assert ("today", "101500") in client.calls
    assert any(call[0] == "daily" and call[2] == "153000" for call in client.calls)


def test_get_history_kis_only_does_not_fallback_for_kr_when_kis_empty(monkeypatch):
    monkeypatch.setenv("AG_KR_MARKET_DATA_PROVIDER", "kis_only")
    monkeypatch.setattr(market_data, "_fetch_kis_history", lambda *args, **kwargs: market_data.pd.DataFrame())

    frame = market_data.get_history("005930.KS", period="1mo", interval="1d")

    assert frame.empty
    assert os.environ["AG_KR_MARKET_DATA_PROVIDER"] == "kis_only"
