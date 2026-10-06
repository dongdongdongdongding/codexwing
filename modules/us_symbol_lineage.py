"""Narrow, evidence-backed corrections for current-provider daily series.

This is not a complete security master or a certification of historical prices.
CBIO here means Yahoo's current Crescent/GLYC series, not an old issued Catalyst
contract. Do not apply listing_symbols to arbitrary historical ticker records.
Sources and captured response hashes: docs/research/NASDAQ_SOURCE_AUDIT_2026-10-07.md.
"""
import numpy as np
import pandas as pd

from modules.ohlcv_quality import bar_issues

CBIO_RENAME = pd.Timestamp('2025-06-16')
CBIO_LAST_BAD_DIVIDEND = pd.Timestamp('2023-01-13')


def listing_symbols(frame: pd.DataFrame) -> pd.Index:
    """Lookup aliases for current-provider price rows; keep input order/identity.

    Nasdaq ECA2025-303: GLYC (CUSIP 38000Q102) -> CBIO (38000Q201),
    effective June 16 2025. Old Catalyst CBIO is a different security.
    Snapshot availability rules still apply; no listing gaps are backfilled.
    """
    symbols = frame['symbol'].astype(str).to_numpy(copy=True)
    dates = pd.to_datetime(frame['date'], errors='coerce')
    symbols[(symbols == 'CBIO') & (dates < CBIO_RENAME).to_numpy()] = 'GLYC'
    return pd.Index(symbols)


def daily_bar_issues(frame: pd.DataFrame, *, require_volume: bool = True) -> pd.Series:
    """Structural checks plus a known cross-issuer dividend contamination.

    Yahoo attaches Catalyst's 2022-09-21 / 2023-01-13 dividends to the
    GLYC-derived CBIO series. GLYC SEC filings state no cash dividends.
    Before the last event, non-unit (or unknown) adjustment is incompatible.
    Preserve source values and dates; consumers quarantine instead of inventing
    replacement prices. A unit adjustment does not certify the OHLC themselves.
    """
    issues = bar_issues(frame, require_volume=require_volume)
    if not {'date', 'symbol', 'source'}.issubset(frame.columns):
        return issues
    affected = (frame['symbol'].eq('CBIO') & frame['source'].eq('yfinance')
                & pd.to_datetime(frame['date'], errors='coerce').lt(CBIO_LAST_BAD_DIVIDEND))
    raw = pd.to_numeric(frame.get('raw_close', pd.Series(np.nan, index=frame.index)), errors='coerce')
    adjusted = pd.to_numeric(frame.get('adj_close', pd.Series(np.nan, index=frame.index)), errors='coerce')
    unit = np.isclose(adjusted, raw, rtol=1e-6, atol=0) & np.isfinite(raw) & raw.gt(0)
    # Keep a more immediate structural error when both reasons apply.
    issues.loc[affected & ~unit & issues.eq('')] = 'incompatible_issuer_dividend_adjustment'
    return issues
