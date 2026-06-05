from __future__ import annotations

import contextlib
import io
import os
from datetime import datetime, timedelta
from typing import List, Optional

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


def _kis_index_code(symbol: str) -> Optional[str]:
    upper = str(symbol or "").strip().upper()
    mapping = {
        "^KS11": "0001",
        "KS11": "0001",
        "KOSPI": "0001",
        "^KQ11": "1001",
        "KQ11": "1001",
        "KOSDAQ": "1001",
        "KS200": "2001",
        "$KS200": "2001",
        "KOSPI200": "2001",
        "^KS200": "2001",
    }
    return mapping.get(upper)


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


def _normalize_kis_index_bars(payload: object) -> pd.DataFrame:
    rows = []
    source = payload if isinstance(payload, dict) else {}
    raw_rows = source.get("output2") or source.get("output") or []
    if isinstance(raw_rows, dict):
        raw_rows = [raw_rows]
    for raw in raw_rows if isinstance(raw_rows, list) else []:
        if not isinstance(raw, dict):
            continue
        try:
            date_idx = pd.to_datetime(str(raw.get("stck_bsop_date") or ""), format="%Y%m%d")
        except Exception:
            continue
        rows.append(
            {
                "Date": date_idx,
                "Open": raw.get("bstp_nmix_oprc"),
                "High": raw.get("bstp_nmix_hgpr"),
                "Low": raw.get("bstp_nmix_lwpr"),
                "Close": raw.get("bstp_nmix_prpr"),
                "Volume": raw.get("acml_vol"),
            }
        )
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows).set_index("Date").sort_index()
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame.dropna(subset=["Open", "High", "Low", "Close"], how="any")


def _fetch_kis_index_history(
    symbol: str,
    *,
    period: str = "1mo",
    interval: str = "1d",
    timeout: int = 8,
    client: Optional[object] = None,
) -> pd.DataFrame:
    index_code = _kis_index_code(symbol)
    if not index_code:
        return pd.DataFrame()
    interval_key = str(interval or "").strip().lower()
    if interval_key not in {"1d", "1wk", "1mo"}:
        return pd.DataFrame()

    from modules.kis_openapi import KISOpenAPIClient

    kis_client = client or KISOpenAPIClient(timeout=timeout)
    today = datetime.now()
    start = _period_to_start(period) or (today - timedelta(days=365))
    cursor_end = today
    frames = []
    seen_earliest = set()
    max_chunks = max(1, int(os.getenv("AG_KIS_INDEX_DAILY_MAX_CHUNKS", "8") or "8"))
    period_code = {"1wk": "W", "1mo": "M"}.get(interval_key, "D")
    for _chunk in range(max_chunks):
        payload = kis_client.industry_daily_bars(
            index_code=index_code,
            start_date=start.strftime("%Y%m%d"),
            end_date=cursor_end.strftime("%Y%m%d"),
            period=period_code,
        )
        frame = _normalize_kis_index_bars(payload)
        if frame.empty:
            break
        frames.append(frame)
        earliest = frame.index.min()
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
    return _with_source(combined, "kis_openapi")


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


def _fetch_kis_intraday_history(
    kis_client: object,
    symbol: str,
    *,
    today: datetime,
    start: datetime,
    interval: str,
) -> pd.DataFrame:
    from modules.kis_operational_adapter import kis_intraday_input_hour, normalize_kis_minute_bars

    max_days = max(1, int(os.getenv("AG_KIS_INTRADAY_LOOKBACK_DAYS", "15") or "15"))
    min_bars = max(1, int(os.getenv("AG_KIS_INTRADAY_MIN_BARS", "50") or "50"))
    input_hour = kis_intraday_input_hour(now=today)
    frames = []

    def _query_hours(last_hour: str) -> List[str]:
        cleaned = str(last_hour or "153000").strip().replace(":", "")
        if not (cleaned.isdigit() and len(cleaned) >= 4):
            cleaned = "153000"
        cleaned = cleaned.zfill(6)[:6]
        hours = [cleaned]
        for anchor in ("153000", "133000", "113000", "093000"):
            if anchor < cleaned and anchor not in hours:
                hours.append(anchor)
        return hours

    def _append_payload(payload: object, trade_date: str) -> pd.DataFrame:
        frame = normalize_kis_minute_bars(symbol, payload, trade_date=trade_date)
        if frame.empty:
            return pd.DataFrame()
        return _normalize_ohlcv(frame)

    for day_offset in range(max_days):
        trade_dt = today - timedelta(days=day_offset)
        if pd.Timestamp(trade_dt).to_pydatetime() < start:
            break
        trade_date = trade_dt.strftime("%Y%m%d")
        for query_hour in _query_hours(input_hour if day_offset == 0 else "153000"):
            frame = pd.DataFrame()
            if day_offset == 0 and query_hour == input_hour:
                try:
                    payload = kis_client.today_minute_bars(symbol, input_hour=query_hour, include_past=True)
                    frame = _append_payload(payload, trade_date)
                except Exception:
                    frame = pd.DataFrame()
            if frame.empty:
                try:
                    payload = kis_client.daily_minute_bars(
                        symbol,
                        trade_date=trade_date,
                        input_hour=query_hour,
                        include_past=True,
                    )
                    frame = _append_payload(payload, trade_date)
                except Exception:
                    frame = pd.DataFrame()
            if not frame.empty:
                frames.append(frame)
                combined = pd.concat(frames).sort_index()
                combined = combined[~combined.index.duplicated(keep="last")]
                resampled = _normalize_ohlcv(_resample_intraday(combined, interval))
                if len(resampled) >= min_bars:
                    return resampled

            if query_hour == "093000":
                break

    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    return _normalize_ohlcv(_resample_intraday(combined, interval))


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
        frame = _fetch_kis_intraday_history(
            kis_client,
            symbol,
            today=today,
            start=start,
            interval=interval_key,
        )
        return _with_source(frame, "kis_openapi")

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

    # 0) Optional KIS-first source replacement for KRX equities and indices.
    if kis_mode in {"kis_first", "kis_only"} and _kis_index_code(symbol):
        try:
            kis_index_df = _fetch_kis_index_history(symbol, period=period, interval=interval, timeout=timeout)
            if not kis_index_df.empty:
                return kis_index_df
        except Exception:
            pass
        if kis_mode == "kis_only":
            return pd.DataFrame()

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
