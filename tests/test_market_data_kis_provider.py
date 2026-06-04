from __future__ import annotations

import os

from modules import market_data


class FakeKISClient:
    def daily_bars(self, symbol, *, start_date, end_date, period="D", adjusted=True, market_div="J"):
        return {
            "output2": [
                {
                    "stck_bsop_date": "20260602",
                    "stck_oprc": "100",
                    "stck_hgpr": "110",
                    "stck_lwpr": "95",
                    "stck_clpr": "105",
                    "acml_vol": "1000",
                },
                {
                    "stck_bsop_date": "20260603",
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
                    "stck_bsop_date": "20260603",
                    "stck_cntg_hour": "090000",
                    "stck_prpr": "100",
                    "stck_oprc": "100",
                    "stck_hgpr": "101",
                    "stck_lwpr": "99",
                    "cntg_vol": "10",
                },
                {
                    "stck_bsop_date": "20260603",
                    "stck_cntg_hour": "090100",
                    "stck_prpr": "102",
                    "stck_oprc": "101",
                    "stck_hgpr": "102",
                    "stck_lwpr": "100",
                    "cntg_vol": "20",
                },
            ]
        }


def test_fetch_kis_history_daily_returns_normalized_ohlcv():
    frame = market_data._fetch_kis_history("005930.KS", period="1mo", interval="1d", client=FakeKISClient())

    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert float(frame["Close"].iloc[-1]) == 111.0


def test_get_history_kis_only_does_not_fallback_for_kr_when_kis_empty(monkeypatch):
    monkeypatch.setenv("AG_KR_MARKET_DATA_PROVIDER", "kis_only")
    monkeypatch.setattr(market_data, "_fetch_kis_history", lambda *args, **kwargs: market_data.pd.DataFrame())

    frame = market_data.get_history("005930.KS", period="1mo", interval="1d")

    assert frame.empty
    assert os.environ["AG_KR_MARKET_DATA_PROVIDER"] == "kis_only"
