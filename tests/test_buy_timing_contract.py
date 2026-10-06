import pandas as pd
from web.backend import services as S
from modules import market_sessions as M


def setup(monkeypatch, missing=False, stale=False):
    days = pd.bdate_range("2026-09-01", periods=8)
    px = pd.DataFrame({"code": "000001", "date": days,
                       "adj_open": 200., "adj_high": 204., "adj_close": 202.,
                       "adj_factor": 2., "volume": 1000.})
    # A second ticker preserves the market session when our ticker is missing.
    other = px.assign(code="000002")
    if missing:
        px = px.drop(index=2)
    monkeypatch.setattr(pd, "read_parquet", lambda *a, **kw: pd.concat([px, other]))
    observed = [str(d.date()) for d in days] + (["2026-09-14"] if stale else [])
    monkeypatch.setattr(M, "price_sessions", lambda *a: (observed, "fixture"))
    monkeypatch.setattr(S, "LANES", {"kospi_swing": {
        "ledger": "fixture", "label": "swing", "kind": "SWING", "badge": "A"}})
    monkeypatch.setattr(S, "_read_ledger", lambda *a: [{"date": "2026-09-01", "ticker": "000001.KS",
        "market": "KOSPI", "close": 100, "contract_h": 10, "contract_tp": .07}])
    monkeypatch.setattr(S, "prices", lambda *a: {"000001": {"price": 101}})
    monkeypatch.setattr(S, "_lane_forward_ev", lambda: {})
    monkeypatch.setattr(S, "resolve_any_name", lambda x: x)


def test_h10_survives_seven_sessions_and_uses_adjusted_price_scale(monkeypatch):
    setup(monkeypatch)
    p = S.buy_timing(days=10)["picks"][0]
    assert p["contract_h"] == 10 and p["sessions_left"] == 3
    assert p["ref"] == 100 and p["target"] == 107
    assert p["trail"][0]["left"] == 10
    assert p["state"] != "EXPIRED"


def test_missing_symbol_bar_never_compresses_contract_or_says_buy(monkeypatch):
    setup(monkeypatch, missing=True)
    p = S.buy_timing(days=10)["picks"][0]
    assert p["sessions_left"] == 3
    assert p["state"] == "UNKNOWN"
    assert p.get("today_best") is not True


def test_delayed_adjusted_panel_cannot_authorize_today_entry(monkeypatch):
    setup(monkeypatch, stale=True)
    p = S.buy_timing(days=10)["picks"][0]
    assert p["state"] == "UNKNOWN"
    assert "지연" in p["contract_data_error"]
