import pandas as pd

from modules.us_overnight_theme_lead import (
    build_us_overnight_theme_states,
    enrich_kr_intel_with_us_overnight_theme_lead,
)


def _hist(prev_close: float, last_close: float, volumes=None):
    idx = pd.date_range("2026-05-01", periods=6, freq="B")
    closes = [prev_close, prev_close, prev_close, prev_close, prev_close, last_close]
    data = {"Close": closes}
    if volumes is not None:
        data["Volume"] = volumes
    return pd.DataFrame(data, index=idx)


def test_build_us_overnight_theme_states_uses_completed_daily_returns():
    def fake_fetcher(symbol, **_kwargs):
        if symbol in {"SOXX", "SMH", "NVDA"}:
            return _hist(100, 104, [100, 100, 100, 100, 100, 180])
        if symbol in {"AMD", "AVGO", "MU", "TSM", "ASML"}:
            return _hist(100, 103, [100, 100, 100, 100, 100, 120])
        return pd.DataFrame()

    out = build_us_overnight_theme_states(
        fetcher=fake_fetcher,
        baskets={"semiconductor": {"theme_name": "Semiconductor", "symbols": ["SOXX", "SMH", "NVDA", "AMD"]}},
    )

    assert out["status"] == "ok"
    assert out["no_leakage_asof"] == "2026-05-08"
    row = out["theme_states"][0]
    assert row["theme_id"] == "semiconductor"
    assert row["direction"] == "BENEFICIARY"
    assert row["avg_proxy_return_1d_pct"] > 3.0
    assert row["proxy_count"] == 4
    assert any(item["symbol"] == "SOXX" for item in row["leader_proxies"])


def test_enrich_kr_intel_projects_us_quantum_and_semis_to_theme_states():
    def fake_fetcher(symbol, **_kwargs):
        if symbol in {"IONQ", "RGTI", "QBTS", "QTUM", "QUBT"}:
            return _hist(10, 11.2)
        if symbol in {"SOXX", "SMH", "NVDA", "AMD", "AVGO", "MU", "TSM", "ASML"}:
            return _hist(100, 102)
        return pd.DataFrame()

    payload = enrich_kr_intel_with_us_overnight_theme_lead(
        {"theme_states": [], "beneficiary_themes": [], "headwind_themes": []},
        market="KOSDAQ",
        fetcher=fake_fetcher,
    )

    themes = {row["theme_id"]: row for row in payload["theme_states"]}
    assert "quantum" in themes
    assert themes["quantum"]["direction"] == "BENEFICIARY"
    assert "semiconductor" in themes
    assert payload["us_overnight_theme_lead"]["projected_kr_theme_count"] >= 2
    assert payload["beneficiary_themes"]


def test_enrich_kr_intel_is_noop_for_us_market():
    payload = {"theme_states": [{"theme_id": "semiconductor"}]}
    out = enrich_kr_intel_with_us_overnight_theme_lead(payload, market="NASDAQ", fetcher=lambda *_a, **_k: pd.DataFrame())
    assert out is payload
