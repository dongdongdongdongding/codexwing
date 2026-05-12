import pandas as pd

from modules import macro_scheduler
from modules.scan_policy import compute_rank_adjustment


def _hist(prev_close: float, last_close: float):
    idx = pd.date_range("2026-05-01", periods=2, freq="B")
    return pd.DataFrame({"Close": [prev_close, last_close]}, index=idx)


def test_macro_context_includes_us_lead_for_kr(monkeypatch):
    macro_scheduler._macro_cache.clear()
    macro_scheduler._macro_cache_ts.clear()

    changes = {
        "^VIX": (20, 22),
        "^TNX": (4.0, 4.0),
        "KRW=X": (1350, 1350),
        "SPY": (100, 99),
        "^IXIC": (100, 97),
        "QQQ": (100, 97),
        "NQ=F": (100, 98),
        "ES=F": (100, 99),
        "SOXX": (100, 96),
        "EWY": (100, 97),
        "KORU": (100, 91),
        "KS200": (100, 96),
        "069500.KS": (100, 97),
    }

    def fake_history(symbol, **_kwargs):
        prev_close, last_close = changes.get(symbol, (100, 100))
        return _hist(prev_close, last_close)

    monkeypatch.setattr(macro_scheduler, "get_history", fake_history)

    ctx = macro_scheduler.get_macro_context(force_refresh=True, market_group="KOSDAQ")

    assert ctx["qqq_change_1d"] == -3.0
    assert ctx["nq_futures_change_1d"] == -2.0
    assert ctx["soxx_change_1d"] == -4.0
    assert ctx["kospi200_source"] == "KS200"
    assert ctx["kospi200_change_1d"] == -4.0
    assert ctx["kodex200_change_1d"] == -3.0
    assert ctx["kr_derivative_lead_state"] == "RISK_OFF"
    assert ctx["us_lead_state"] == "RISK_OFF"
    assert "US_LEAD_RISK_OFF" in ctx["flags"]
    assert "KR_DERIVATIVE_LEAD_RISK_OFF" in ctx["flags"]


def test_rank_adjustment_uses_macro_and_us_lead_penalty():
    base = compute_rank_adjustment(
        "UP",
        "Rising",
        "Core",
        "T1",
        65,
        1.5,
        volume_confirmed=True,
    )
    stressed = compute_rank_adjustment(
        "UP",
        "Rising",
        "Core",
        "T1",
        65,
        1.5,
        volume_confirmed=True,
        macro_ctx={
            "macro_penalty": 5,
            "us_lead_score": -25,
            "us_lead_state": "RISK_OFF",
        },
    )

    assert stressed == base - 9
