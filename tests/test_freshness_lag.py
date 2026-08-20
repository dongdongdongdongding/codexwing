"""신선도가 한 종목 표본이 아니라 캐시 전체를 보고, 지연을 거래일로 말하는지 고정한다.

원 결함(2026-08-20 실측): `sorted(glob)[:1]` 이 알파벳 첫 파일 `000020.parquet`(08-19)만 읽어
`085620.parquet`(08-20)이 있는데도 분봉을 08-19 로 보고했다 — **한 종목의 지연이
캐시 전체의 신선도로 나갔다.**
"""
import os
import pandas as pd
import pytest
import web.backend.services as sv


@pytest.fixture
def cache(tmp_path, monkeypatch):
    """일봉 달력 + 분봉 캐시. 알파벳 첫 파일이 일부러 뒤처져 있다."""
    sessions = ["2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20"]
    pd.DataFrame({"date": pd.to_datetime(sessions)}).to_parquet(tmp_path / "px_long.parquet")
    day = tmp_path / "intraday"
    day.mkdir()

    def bars(path, last):
        idx = pd.to_datetime([f"{last} 09:0{i}:00" for i in range(3)])
        pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=idx).to_parquet(path)

    bars(day / "000020.parquet", "2026-08-19")   # 알파벳 첫 파일 — 하루 뒤처져 있다
    bars(day / "085620.parquet", "2026-08-20")   # 실제 최신
    os.utime(day / "085620.parquet", (2_000_000_000, 2_000_000_000))
    os.utime(day / "000020.parquet", (1_000_000_000, 1_000_000_000))
    monkeypatch.setattr(sv, "RESEARCH", str(tmp_path))
    return tmp_path


def test_minute_freshness_reads_the_whole_cache_not_the_first_file(cache):
    assert sv.freshness()["minute"] == "2026-08-20"


def test_lag_is_reported_in_trading_days(cache):
    lag = sv.freshness()["_lag"]
    assert lag["daily"] == 0
    assert lag["minute"] == 0


def test_a_lagging_cache_is_reported_as_lagging(cache, monkeypatch):
    """분봉만 하루 밀리면 1거래일 지연으로 나와야 한다 — 날짜만으로는 안 보인다."""
    os.remove(cache / "intraday" / "085620.parquet")
    lag = sv.freshness()["_lag"]
    assert lag["minute"] == 1, "휴장일이 아니라 거래일로 센다"


def test_weekend_does_not_inflate_the_lag(cache):
    """일봉 원장을 달력으로 쓰므로 주말·휴장일은 지연으로 세지 않는다."""
    fr = sv.freshness()
    assert fr["_lag"]["daily"] == 0


def test_lag_never_replaces_the_date_values(cache):
    """기존 항목을 객체로 바꾸면 값을 그대로 그리는 화면이 깨진다."""
    fr = sv.freshness()
    for k in ("daily", "minute"):
        assert isinstance(fr[k], str)
    assert isinstance(fr["_lag"], dict)
