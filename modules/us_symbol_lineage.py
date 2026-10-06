"""Narrow, evidence-backed corrections for current-provider daily series.

This is not a complete security master or a certification of historical prices.
CBIO here means Yahoo's current Crescent/GLYC series, not an old issued Catalyst
contract. Do not apply listing_symbols to arbitrary historical ticker records.
Sources and captured response hashes: docs/research/NASDAQ_SOURCE_AUDIT_2026-10-07.md.
"""
import numpy as np
import pandas as pd

from modules.ohlcv_quality import bar_issues

# Effective trading dates, not legal-name-change or announcement dates.
# Each rule is keyed by the ORIGINAL current-provider symbol: never chain
# GYRE -> historical CBIO -> GLYC, which would cross unrelated issuers.
LISTING_ALIASES = (
    ('CBIO', '2025-06-16', 'GLYC'),  # Nasdaq ECA2025-303
    ('GYRE', '2023-10-31', 'CBIO'),  # Nasdaq ECA2023-623
    ('ASTS', '2021-04-07', 'NPA'),   # Nasdaq ECA2021-59
    ('ATTT', '2026-09-10', 'RAY'),   # SEC 1948443/000121390026098242
    ('GMEX', '2026-03-12', 'FTEL'),  # issuer March 11 announcement + KIS boundary
    ('ITOC', '2026-01-16', 'PTHL'),  # SEC 1970544/000121390026036395
)
# Prior OTC/NYSE American data remain price observations; they do not establish
# membership of the Nasdaq universe. A later snapshot must still confirm it.
NASDAQ_STARTS = {
    'CNL': '2026-08-11',
    'SPRC': '2021-12-22',
    'TLN': '2024-07-10',
}
CBIO_RENAME = pd.Timestamp('2025-06-16')
CBIO_LAST_BAD_DIVIDEND = pd.Timestamp('2023-01-13')

# Independent KIS MODP0/1 observations through 2026-10-05 show mixed nominal
# and split-adjusted units within each of these Yahoo pre-event series. A full
# Yahoo re-download reproduces that mixture; positive OHLC is insufficient.
# Quarantine the uncertified pre-event series, not just the sampled bad dates.
# These are release boundaries, not instructions to multiply prices. Removing
# a quarantine requires a separately verified replacement history.
# Nasdaq ECA2026 IDs are recorded alongside the official effective dates.
UNVERIFIED_SPLIT_BASIS = {
    'AIXI': '2026-09-08',  # 643
    'ALP': '2026-09-09',   # 646
    'BRTX': '2026-09-08',  # 636
    'BTLN': '2026-09-28',  # 676
    'CPOP': '2026-09-14',  # 658
    'DLXY': '2026-09-28',  # 679
    'GMEX': '2026-09-28',  # 675
    'GTBP': '2026-09-08',  # 644
    'HUBC': '2026-09-14',  # 657
    'IMMP': '2026-09-28',  # 681
    'IZM': '2026-09-15',   # 660
    'LRHC': '2026-09-08',  # 641
    'NFE': '2026-09-14',   # 654
    'NRSN': '2026-09-14',  # 656
    'NXXT': '2026-09-14',  # 655
    'SFWL': '2026-09-08',  # 639
    'TNMG': '2026-09-08',  # 640
    'UCAR': '2026-09-09',  # 647
    'VWAV': '2026-09-22',  # 667
    'WCT': '2026-09-08',   # 642
    'WHLR': '2026-09-22',  # 666
}


def listing_symbols(frame: pd.DataFrame) -> pd.Index:
    """Lookup aliases for current-provider price rows; keep input order/identity.

    Nasdaq ECA2025-303: GLYC (CUSIP 38000Q102) -> CBIO (38000Q201),
    effective June 16 2025. Old Catalyst CBIO is a different security.
    Snapshot availability rules still apply; no listing gaps are backfilled.
    """
    original = frame['symbol'].astype(str).to_numpy()
    symbols = original.copy()
    dates = pd.to_datetime(frame['date'], errors='coerce')
    for current, effective, previous in LISTING_ALIASES:
        mask = (original == current) & (dates < pd.Timestamp(effective)).to_numpy()
        symbols[mask] = previous
    return pd.Index(symbols)


def nasdaq_venue_eligible(frame: pd.DataFrame) -> np.ndarray:
    """Known venue boundaries only; not a replacement for observed membership."""
    symbols = frame['symbol'].astype(str).to_numpy()
    dates = pd.to_datetime(frame['date'], errors='coerce')
    eligible = dates.notna().to_numpy()
    for symbol, first in NASDAQ_STARTS.items():
        eligible &= ~((symbols == symbol) & (dates < pd.Timestamp(first)).to_numpy())
    return eligible


def listing_snapshot_eligible(frame: pd.DataFrame, snapshot_dates) -> np.ndarray:
    """A new ticker/venue epoch cannot inherit an older issuer's directory row."""
    symbols = frame['symbol'].astype(str).to_numpy()
    dates = pd.DatetimeIndex(pd.to_datetime(frame['date'], errors='coerce'))
    observed = pd.DatetimeIndex(snapshot_dates)
    eligible = np.asarray(dates.notna() & observed.notna())
    boundaries = [(symbol, effective) for symbol, effective, _ in LISTING_ALIASES]
    boundaries += list(NASDAQ_STARTS.items())
    for symbol, effective in boundaries:
        stamp = pd.Timestamp(effective)
        eligible &= ~((symbols == symbol) & (dates >= stamp) & (observed < stamp))
    return eligible


def daily_bar_issues(frame: pd.DataFrame, *, require_volume: bool = True) -> pd.Series:
    """Structural checks plus independently observed adjustment contamination.

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
    boundaries = pd.to_datetime(frame['symbol'].map(UNVERIFIED_SPLIT_BASIS))
    uncertain = (frame['source'].eq('yfinance') & boundaries.notna()
                 & pd.to_datetime(frame['date'], errors='coerce').lt(boundaries))
    issues.loc[uncertain & issues.eq('')] = 'unverified_mixed_split_basis'
    return issues
