import pandas as pd
import pytest
from modules import market_sessions as M
from multi_agent.tools import report_research_recursion_gate as G
from web.backend import services as S


def test_prices_count_nonfiring_days_and_exclude_holiday_and_today(tmp_path, monkeypatch):
    path = tmp_path / "px_long.parquet"
    pd.DataFrame({"date": pd.to_datetime(["2026-10-01", "2026-10-02", "2026-10-06", "2026-10-07"])}).to_parquet(path)
    monkeypatch.setattr(M, "price_source", lambda market: path)
    monkeypatch.setattr(G, "LANES", {})  # market calendar must survive zero picks
    assert G.trading_days("KR", "2026-10-07") == ["2026-10-01", "2026-10-02", "2026-10-06"]
    assert S._trading_days_between("2026-10-01", "2026-10-02") == 1


def test_calendar_refresh_does_not_require_process_restart(tmp_path, monkeypatch):
    path = tmp_path / "px_long.parquet"
    monkeypatch.setattr(M, "price_source", lambda market: path)
    pd.DataFrame({"date": pd.to_datetime(["2026-10-01"])}).to_parquet(path)
    assert len(M.price_sessions("KR", "2026-10-07")[0]) == 1
    pd.DataFrame({"date": pd.to_datetime(["2026-10-01", "2026-10-02"])}).to_parquet(path)
    assert len(M.price_sessions("KR", "2026-10-07")[0]) == 2


def test_invalid_calendar_fails_instead_of_understating_gap(tmp_path, monkeypatch):
    path = tmp_path / "px_long.parquet"
    pd.DataFrame({"date": ["2026-10-01", "bad"]}).to_parquet(path)
    monkeypatch.setattr(M, "price_source", lambda market: path)
    with pytest.raises(ValueError, match="invalid dates"):
        M.price_sessions("KR", "2026-10-07")


def test_unknown_market_does_not_fall_back_to_korea():
    with pytest.raises(ValueError, match="unsupported session market"):
        M.price_source("NYSE_TYPO")
