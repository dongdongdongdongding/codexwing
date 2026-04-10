from __future__ import annotations

import contextlib
import io
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd


def _period_to_start(period: str) -> Optional[datetime]:
    p = str(period or "").strip().lower()
    if not p or p == "max":
        return datetime.now() - timedelta(days=3650)
    if p.endswith("d"):
        try:
            days = int(p[:-1])
            return datetime.now() - timedelta(days=max(days, 1))
        except Exception:
            return datetime.now() - timedelta(days=30)
    if p.endswith("mo"):
        try:
            months = int(p[:-2])
            return datetime.now() - timedelta(days=max(months, 1) * 30)
        except Exception:
            return datetime.now() - timedelta(days=90)
    if p.endswith("y"):
        try:
            years = int(p[:-1])
            return datetime.now() - timedelta(days=max(years, 1) * 365)
        except Exception:
            return datetime.now() - timedelta(days=365)
    return datetime.now() - timedelta(days=365)


def _to_fdr_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip()
    if not raw:
        return raw
    upper = raw.upper()
    mapping = {
        "^GSPC": "US500",
        "^KS11": "KS11",
        "^KQ11": "KQ11",
        "^VIX": "VIX",
        "^TNX": "US10YT",
        "KRW=X": "USD/KRW",
    }
    if upper in mapping:
        return mapping[upper]
    if upper.endswith(".KS") or upper.endswith(".KQ"):
        return upper.split(".")[0]
    return raw


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        try:
            out.columns = out.columns.droplevel(1)
        except Exception:
            pass

    col_map = {}
    for col in out.columns:
        low = str(col).strip().lower()
        if low == "open":
            col_map[col] = "Open"
        elif low == "high":
            col_map[col] = "High"
        elif low == "low":
            col_map[col] = "Low"
        elif low == "close":
            col_map[col] = "Close"
        elif low == "volume":
            col_map[col] = "Volume"
    out = out.rename(columns=col_map)

    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in out.columns]
    if not keep:
        return pd.DataFrame()
    out = out[keep].copy()

    if "Date" in out.columns and not isinstance(out.index, pd.DatetimeIndex):
        try:
            out["Date"] = pd.to_datetime(out["Date"])
            out = out.set_index("Date")
        except Exception:
            pass

    if isinstance(out.index, pd.RangeIndex):
        return pd.DataFrame()

    if not isinstance(out.index, pd.DatetimeIndex):
        try:
            out.index = pd.to_datetime(out.index)
        except Exception:
            return pd.DataFrame()
    if out.index.tz is not None:
        out.index = out.index.tz_localize(None)

    return out.dropna(how="all")


def get_history(
    symbol: str,
    *,
    period: str = "1mo",
    interval: str = "1d",
    timeout: int = 8,
) -> pd.DataFrame:
    """Fetch OHLCV with market-aware fallback ordering.

    For KRX daily bars and KRX macro proxies, prefer FinanceDataReader first to avoid
    noisy Yahoo `Invalid Crumb` / 401 failures in KR scan paths.
    """

    upper_symbol = str(symbol or "").strip().upper()
    is_kr_symbol = upper_symbol.endswith(".KS") or upper_symbol.endswith(".KQ") or upper_symbol in {"^KS11", "^KQ11", "KRW=X"}
    is_daily_like = interval in ("1d", "1wk", "1mo")

    # 1) FinanceDataReader first for KR daily-like paths
    if is_kr_symbol and is_daily_like:
        try:
            import FinanceDataReader as fdr

            start = _period_to_start(period)
            fdr_symbol = _to_fdr_symbol(symbol)
            fdr_df = fdr.DataReader(fdr_symbol, start) if start else fdr.DataReader(fdr_symbol)
            fdr_df = _normalize_ohlcv(fdr_df)
            if not fdr_df.empty:
                return fdr_df
        except Exception:
            pass

    # 2) yfinance (supports intraday and non-KR fallbacks)
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yf_df = ticker.history(period=period, interval=interval, timeout=timeout)
        yf_df = _normalize_ohlcv(yf_df)
        if not yf_df.empty:
            return yf_df
    except Exception:
        pass

    # 3) FinanceDataReader (daily fallback for non-KR or secondary fallback)
    if interval not in ("1d", "1wk", "1mo"):
        return pd.DataFrame()

    try:
        import FinanceDataReader as fdr

        start = _period_to_start(period)
        fdr_symbol = _to_fdr_symbol(symbol)
        fdr_df = fdr.DataReader(fdr_symbol, start) if start else fdr.DataReader(fdr_symbol)
        fdr_df = _normalize_ohlcv(fdr_df)
        if not fdr_df.empty:
            return fdr_df
    except Exception:
        pass

    return pd.DataFrame()
