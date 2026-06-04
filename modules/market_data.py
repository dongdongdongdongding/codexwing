from __future__ import annotations

import contextlib
import io
import os
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


def _is_kr_symbol(symbol: str) -> bool:
    upper = str(symbol or "").strip().upper()
    return upper.endswith(".KS") or upper.endswith(".KQ") or (upper.isdigit() and len(upper) <= 6)


def _kis_provider_mode() -> str:
    raw = str(os.getenv("AG_KR_MARKET_DATA_PROVIDER") or "").strip().lower()
    if raw in {"kis", "kis_first", "kis_openapi"}:
        return "kis_first"
    if raw in {"kis_only", "kis_openapi_only"}:
        return "kis_only"
    if str(os.getenv("AG_ENABLE_KIS_MARKET_DATA") or "").strip().lower() in {"1", "true", "yes", "on"}:
        return "kis_first"
    return "legacy"


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


def _with_source(frame: pd.DataFrame, source_provider: str) -> pd.DataFrame:
    if frame is not None and not frame.empty:
        frame.attrs["source_provider"] = source_provider
    return frame


def _fetch_kis_daily_history(
    kis_client: object,
    symbol: str,
    *,
    start: datetime,
    end: datetime,
    period: str = "D",
) -> pd.DataFrame:
    from modules.kis_operational_adapter import normalize_kis_daily_bars

    frames = []
    cursor_end = end
    max_chunks = max(1, int(os.getenv("AG_KIS_DAILY_MAX_CHUNKS", "8") or "8"))
    seen_earliest = set()

    for _chunk in range(max_chunks):
        payload = kis_client.daily_bars(
            symbol,
            start_date=start.strftime("%Y%m%d"),
            end_date=cursor_end.strftime("%Y%m%d"),
            period=period,
        )
        frame = _normalize_ohlcv(normalize_kis_daily_bars(symbol, payload))
        if frame.empty:
            break
        frames.append(frame)
        earliest = frame.index.min()
        if earliest is None:
            break
        earliest_key = str(pd.Timestamp(earliest).date())
        if earliest_key in seen_earliest:
            break
        seen_earliest.add(earliest_key)
        if pd.Timestamp(earliest).to_pydatetime() <= start:
            break
        if len(frame) < int(os.getenv("AG_KIS_DAILY_PAGE_SOFT_LIMIT", "95") or "95"):
            break
        cursor_end = pd.Timestamp(earliest).to_pydatetime() - timedelta(days=1)

    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    combined = combined[combined.index >= pd.Timestamp(start)]
    return combined


def _resample_intraday(frame: pd.DataFrame, interval: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    freq_map = {
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "60m": "60min",
        "1h": "1h",
    }
    freq = freq_map.get(str(interval or "").lower())
    if not freq:
        return frame
    return (
        frame.resample(freq)
        .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
        .dropna()
    )


def _fetch_kis_history(
    symbol: str,
    *,
    period: str = "1mo",
    interval: str = "1d",
    timeout: int = 8,
    client: Optional[object] = None,
) -> pd.DataFrame:
    """Fetch KRX OHLCV through KIS and normalize it to the local OHLCV contract."""

    if not _is_kr_symbol(symbol):
        return pd.DataFrame()

    from modules.kis_openapi import KISOpenAPIClient
    from modules.kis_operational_adapter import normalize_kis_daily_bars, normalize_kis_minute_bars

    kis_client = client or KISOpenAPIClient(timeout=timeout)
    today = datetime.now()
    start = _period_to_start(period) or (today - timedelta(days=365))
    interval_key = str(interval or "").strip().lower()
    if interval_key in {"1d", "1wk", "1mo"}:
        frame = _fetch_kis_daily_history(
            kis_client,
            symbol,
            start=start,
            end=today,
            period={"1wk": "W", "1mo": "M"}.get(interval_key, "D"),
        )
        return _with_source(frame, "kis_openapi")

    if interval_key in {"1m", "5m", "15m", "30m", "60m", "1h"}:
        payload = kis_client.today_minute_bars(symbol, input_hour="153000", include_past=True)
        frame = normalize_kis_minute_bars(symbol, payload, trade_date=today.strftime("%Y%m%d"))
        return _with_source(_normalize_ohlcv(_resample_intraday(frame, interval_key)), "kis_openapi")

    return pd.DataFrame()


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
    kis_mode = _kis_provider_mode()

    # 0) Optional KIS-first source replacement for KRX equities.
    if kis_mode in {"kis_first", "kis_only"} and _is_kr_symbol(symbol):
        try:
            kis_df = _fetch_kis_history(symbol, period=period, interval=interval, timeout=timeout)
            if not kis_df.empty:
                return kis_df
        except Exception:
            pass
        if kis_mode == "kis_only":
            return pd.DataFrame()

    # 1) FinanceDataReader first for KR daily-like paths
    if is_kr_symbol and is_daily_like:
        try:
            import FinanceDataReader as fdr

            start = _period_to_start(period)
            fdr_symbol = _to_fdr_symbol(symbol)
            fdr_df = fdr.DataReader(fdr_symbol, start) if start else fdr.DataReader(fdr_symbol)
            fdr_df = _normalize_ohlcv(fdr_df)
            if not fdr_df.empty:
                return _with_source(fdr_df, "finance_data_reader")
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
            return _with_source(yf_df, "yfinance")
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
            return _with_source(fdr_df, "finance_data_reader")
    except Exception:
        pass

    return pd.DataFrame()
