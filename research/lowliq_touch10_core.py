"""Causal feature, maturity and cadence primitives for the fixed research study."""
import numpy as np
import pandas as pd

from research.audit_kr_adjustment_asof import index_features

FEATS = ['ret_1d','ret_3d','ret_5d','ret_10d','ret_20d','ret_60d','ma5_dist','ma20_dist','ma60_dist',
         'ma120_dist','ma20_slope','ma60_slope','rsi14','rsi_slope','accel','consec_up','dist_hi20',
         'dist_hi60','dist_hi120','dist_lo20','dist_lo60','pos20','bb_pctb','bb_bw','atr_pct','vol20',
         'close_loc','gap','vol_ratio','vol_trend','turn_z','obv_slope','cmf20','idx_mom20','idx_vol20']


def eligible(frame):
    return (frame.market.isin(['KOSPI', 'KOSDAQ']) & frame.liq.ge(5e8) & frame.liq.lt(3e9)
            & frame.volume.gt(0) & frame[FEATS[:6]].notna().all(axis=1))


def stock_features(frame, last_only=False):
    """Rolling inputs only. Last-only optimization retains an exact up-run count."""
    full_close = frame.adj_close.to_numpy()
    up_full = np.r_[False, full_close[1:] > full_close[:-1]]
    consecutive = len(up_full) - 1 - np.flatnonzero(~up_full)[-1]
    d = frame.iloc[-130:].copy() if last_only else frame
    c, o, h, l, v = [d[k] for k in ['adj_close', 'adj_open', 'adj_high', 'adj_low', 'volume']]
    f = pd.DataFrame(index=d.index)
    for n in [1, 3, 5, 10, 20, 60]:
        f[f'ret_{n}d'] = c.pct_change(n) * 100
    for n in [5, 20, 60, 120]:
        f[f'ma{n}_dist'] = (c / c.rolling(n).mean() - 1) * 100
    f['ma20_slope'] = (c.rolling(20).mean() / c.rolling(20).mean().shift(5) - 1) * 100
    f['ma60_slope'] = (c.rolling(60).mean() / c.rolling(60).mean().shift(10) - 1) * 100
    change = c.diff()
    strength = change.clip(lower=0).rolling(14).mean() / (-change.clip(upper=0).rolling(14).mean() + 1e-9)
    f['rsi14'] = 100 - 100 / (1 + strength)
    f['rsi_slope'] = f.rsi14 - f.rsi14.shift(5)
    f['accel'] = c.pct_change(5) * 100 - c.pct_change(5).shift(5) * 100
    up = c.gt(c.shift(1)).astype(int)
    f['consec_up'] = up.groupby(up.ne(up.shift()).cumsum()).cumsum() * up
    if last_only:
        f.loc[f.index[-1], 'consec_up'] = consecutive
    for n in [20, 60, 120]:
        f[f'dist_hi{n}'] = (c / h.rolling(n).max() - 1) * 100
    for n in [20, 60]:
        f[f'dist_lo{n}'] = (c / l.rolling(n).min() - 1) * 100
    f['pos20'] = (c - l.rolling(20).min()) / (h.rolling(20).max() - l.rolling(20).min() + 1e-9)
    average, std = c.rolling(20).mean(), c.rolling(20).std()
    f['bb_pctb'] = (c - (average - 2 * std)) / (4 * std + 1e-9)
    f['bb_bw'] = 4 * std / (average + 1e-9) * 100
    tr = pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    f['atr_pct'] = tr.rolling(14).mean() / c * 100
    f['vol20'] = c.pct_change().rolling(14).std() * 100
    f['close_loc'] = (c-l) / (h-l+1e-9)
    f['gap'] = (o/c.shift()-1)*100
    f['vol_ratio'] = v/v.rolling(20).mean()
    f['vol_trend'] = v.rolling(5).mean()/v.rolling(20).mean()
    f['turn_z'] = (v-v.rolling(60).mean())/(v.rolling(60).std()+1e-9)
    signed = (np.sign(c.diff()) * v).fillna(0)
    f['obv_slope'] = signed.rolling(10).sum()/(v.rolling(20).mean()*10+1e-9)
    mfm = ((c-l)-(h-c))/(h-l+1e-9)
    f['cmf20'] = (mfm*v).rolling(20).sum()/(v.rolling(20).sum()+1e-9)
    f['liq'] = d.amount.rolling(20).mean()
    for column in ['date', 'code', 'market', 'volume']:
        f[column] = d[column]
    return f.iloc[-1:].copy() if last_only else f


def feature_frame(raw, prices, *, start=None, only_date=None, progress=None):
    """Caller supplies a date-limited adjusted snapshot with identical row keys."""
    raw = raw.reset_index(drop=True)
    prices = prices.reset_index(drop=True)
    pd.testing.assert_frame_equal(raw[['code', 'date']], prices[['code', 'date']])
    if only_date is not None and raw.date.max() > pd.Timestamp(only_date):
        raise ValueError('future_input_in_prediction')
    context = index_features(raw, prices.adj_close)
    merged = raw[['code', 'date', 'market', 'volume', 'amount']].copy()
    for column in ['adj_open', 'adj_high', 'adj_low', 'adj_close']:
        merged[column] = prices[column].to_numpy()
    outputs = []
    for i, (code, group) in enumerate(merged.groupby('code', sort=False), 1):
        if only_date is not None and group.date.iloc[-1] != pd.Timestamp(only_date):
            continue
        f = stock_features(group, last_only=only_date is not None)
        for market in f.market.unique():
            mask = f.market.eq(market)
            for field in ['idx_mom20', 'idx_vol20']:
                f.loc[mask, field] = f.loc[mask, 'date'].map(context[market][field]).to_numpy()
        if start is not None:
            f = f.loc[f.date.ge(start)]
        f = f.loc[eligible(f)].copy()
        f[FEATS] = f[FEATS].astype(np.float32)
        outputs.append(f)
        if progress and i % 500 == 0:
            progress(f'feature codes {i}')
    if not outputs:
        return pd.DataFrame(columns=['date','code','market','volume','liq']+FEATS)
    return pd.concat(outputs, ignore_index=True).sort_values(['date','code']).reset_index(drop=True)


def training_labels(bars, sessions, horizon=10):
    """Whole-horizon availability, strict calendar alignment, no invented fills.

    Returns a target only for resolved entries. The test universe never uses it.
    Missing/invalid bars, unfilled entries and suspended terminal exits retain
    explicit statuses. This is a label primitive, not a P&L settlement engine.
    """
    calendar = pd.DatetimeIndex(sessions)
    if not calendar.is_unique or not calendar.is_monotonic_increasing:
        raise ValueError('invalid_market_calendar')
    if bars.date.duplicated().any():
        raise ValueError('duplicate_symbol_date')
    positions = calendar.get_indexer(pd.to_datetime(bars.date))
    if (positions < 0).any():
        raise ValueError('source_date_outside_calendar')
    aligned = bars.set_index('date').reindex(calendar)
    fields = ['adj_open','adj_high','adj_low','adj_close','volume']
    values = aligned[fields].to_numpy(dtype=float)
    n = len(bars)
    target = np.full(n, np.nan)
    status = np.full(n, 'pending_maturity', dtype=object)
    maturity = np.full(n, np.datetime64('NaT'), dtype='datetime64[ns]')
    complete = positions + horizon < len(calendar)
    where = np.flatnonzero(complete)
    if not len(where):
        return pd.DataFrame({'date':bars.date.to_numpy(), 'target':target, 'label_available_date':maturity, 'status':status})
    future = positions[where, None] + np.arange(1, horizon+1)
    window = values[future]
    o, h, l, c, v = [window[:,:,k] for k in range(5)]
    valid = np.isfinite(window).all(axis=2) & (window >= 0).all(axis=2)
    traded = v > 0
    valid &= ~traded | ((np.minimum.reduce([o,h,l,c]) > 0) &
                        (h >= np.maximum.reduce([o,l,c])) & (l <= np.minimum.reduce([o,h,c])))
    all_valid = valid.all(axis=1)
    fillable = (v[:,0] > 0) & (o[:,0] > 0)
    touch = ((h >= o[:,0,None]*1.05) & traded).any(axis=1)
    exit_ok = (v[:,-1] > 0) & (o[:,-1] > 0) & (c[:,-1] > 0)
    result = np.full(len(where), 'data_error', dtype=object)
    result[valid[:,0] & ~fillable] = 'unfilled_entry'
    result[all_valid & fillable & ~touch & ~exit_ok] = 'pending_exit'
    resolved = all_valid & fillable & (touch | exit_ok)
    result[resolved] = 'resolved'
    target[where[resolved]] = touch[resolved].astype(float)
    status[where] = result
    maturity[where] = calendar.to_numpy()[positions[where]+horizon]
    return pd.DataFrame({'date':bars.date.to_numpy(), 'target':target, 'label_available_date':maturity, 'status':status})


def rank_and_cap(frame, calendar, prior):
    """Three original slots and first three firing dates per rolling five sessions."""
    if frame.empty:
        return frame.copy(), frame.copy()
    day = pd.Timestamp(frame.date.iloc[0])
    if frame.date.nunique() != 1:
        raise ValueError('multiple_signal_dates')
    dates = [pd.Timestamp(d) for d in calendar if pd.Timestamp(d) <= day]
    if not dates or dates[-1] != day:
        raise ValueError('signal_not_in_calendar')
    required = dates[-5:-1]
    if any(str(d.date()) not in prior for d in required):
        raise ValueError('missing_prior_cadence_record')
    selected = frame.sort_values(['score','code'], ascending=[False,True]).head(3).copy()
    allowed = sum(bool(prior[str(d.date())]) for d in required) < 3
    return selected, selected if allowed else selected.iloc[:0].copy()
