"""Structural bar validation; never repairs or drops source observations."""
import numpy as np
import pandas as pd


def bar_issues(frame: pd.DataFrame, *, require_volume: bool = True) -> pd.Series:
    prices = frame.reindex(columns=['open', 'high', 'low', 'close']).apply(pd.to_numeric, errors='coerce')
    reason = pd.Series('', index=frame.index, dtype=object)
    invalid = (~np.isfinite(prices)).any(axis=1) | (prices <= 0).any(axis=1)
    reason.loc[invalid] = 'invalid_prices'
    order = (prices.high < prices.max(axis=1)) | (prices.low > prices.min(axis=1))
    reason.loc[reason.eq('') & order] = 'invalid_OHLC_order'
    if require_volume:
        volume = pd.to_numeric(frame.get('volume', pd.Series(np.nan, index=frame.index)), errors='coerce')
        reason.loc[reason.eq('') & (~np.isfinite(volume) | volume.lt(0))] = 'invalid_volume'
    return reason
