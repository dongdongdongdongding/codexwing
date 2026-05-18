import pandas as pd

import modules.quant_analysis as quant_analysis
from modules.quant_analysis import QuantStrategy


def test_kr_investor_flow_prefers_pykrx_trading_value(monkeypatch):
    class FakeStock:
        @staticmethod
        def get_market_trading_value_by_date(start, end, code):
            return pd.DataFrame(
                {
                    "기관합계": [100_000_000, 200_000_000],
                    "외국인합계": [300_000_000, -100_000_000],
                    "개인": [-400_000_000, -100_000_000],
                }
            )

    monkeypatch.setattr(quant_analysis, "HAS_PYKRX", True)
    monkeypatch.setattr(quant_analysis, "stock", FakeStock)

    flow = QuantStrategy("005930.KS").get_investor_flows()

    assert flow["valid"] is True
    assert flow["flow_source"] == "pykrx_value"
    assert flow["flow_unit"] == "KRW"
    assert flow["institution"] == 300_000_000
    assert flow["foreigner"] == 200_000_000
    assert flow["retail"] == -500_000_000
    assert flow["whale_score"] > 50
    assert flow["warnings"] == []


def test_kr_investor_flow_falls_back_to_naver_when_pykrx_fails(monkeypatch):
    class BadStock:
        @staticmethod
        def get_market_trading_value_by_date(start, end, code):
            raise RuntimeError("krx unavailable")

    class FakeResponse:
        text = """
        <html><body>
          <table class="type2"><tr><td>dummy</td></tr></table>
          <table class="type2">
            <tr><td colspan="3">dummy</td></tr>
            <tr><th>날짜</th><th>순매매량</th><th>순매매량.1</th></tr>
            <tr><td>2026.05.18</td><td>1,000</td><td>2,000</td></tr>
            <tr><td>2026.05.15</td><td>-500</td><td>1,500</td></tr>
          </table>
        </body></html>
        """

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(quant_analysis, "HAS_PYKRX", True)
    monkeypatch.setattr(quant_analysis, "stock", BadStock)
    monkeypatch.setattr("requests.get", fake_get)

    flow = QuantStrategy("005930.KS").get_investor_flows()

    assert flow["valid"] is True
    assert flow["flow_source"] == "naver"
    assert flow["flow_unit"] == "shares"
    assert flow["institution"] == 500
    assert flow["foreigner"] == 3500
    assert flow["retail"] == -4000
    assert flow["warnings"] == ["pykrx_flow_failed:krx unavailable"]
