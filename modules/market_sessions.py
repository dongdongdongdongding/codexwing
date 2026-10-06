"""Observed market sessions shared by diagnostics, gate and web.

The calendar comes from prices, never from a strategy's sparse firing dates.
Cache identity includes file mtime so a daily refresh is visible without restart.
"""
from functools import lru_cache
from pathlib import Path
import pandas as pd

CACHE = Path.home() / "research_cache"


def price_source(market):
    if market not in {"KR", "KOSPI", "KOSDAQ", "US", "NASDAQ"}:
        raise ValueError(f"unsupported session market: {market}")
    if market in {"US", "NASDAQ"}:
        files = [p for p in (CACHE / "us_daily/NASDAQ").glob("daily_features_*.parquet")
                 if "_latest_" not in p.name]
        if not files:
            raise FileNotFoundError("NASDAQ session price panel missing")
        return max(files, key=lambda p: p.stat().st_mtime_ns)
    return CACHE / "px_long.parquet"


@lru_cache(maxsize=8)
def _dates(path, mtime_ns):
    p = Path(path)
    frame = pd.read_parquet(p, columns=["date"])
    # Millions of ticker rows share a few thousand dates. Deduplicate before
    # formatting, so a cold web request does not allocate millions of strings.
    dates = pd.to_datetime(frame["date"].drop_duplicates(), errors="coerce")
    if dates.isna().any():
        raise ValueError("price calendar contains invalid dates")
    dates = dates.dt.strftime("%Y-%m-%d")
    if p.stat().st_mtime_ns != mtime_ns:
        raise RuntimeError("price calendar changed during read")
    if dates.empty:
        raise ValueError("price calendar has no valid dates")
    return tuple(sorted(set(dates)))


def price_sessions(market, before):
    before = pd.Timestamp(before).date().isoformat()
    path = price_source(market)
    days = _dates(str(path), path.stat().st_mtime_ns)
    return [d for d in days if d < before], str(path)
