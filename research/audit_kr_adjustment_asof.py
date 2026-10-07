"""Compare reviewed KR price adjustment on full history and fixed date prefixes.

No model, performance labels, prices or production artifacts are changed.
The original builder is hash-pinned and only its numerical adjustment block runs.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

BUILDER_SHA = 'a44b3733a59886d75de676a466fb90d0c9aa5480f3f8cca3e2d9cb044db113da'
CUTOFFS = ['2026-03-31', '2026-06-30', '2026-07-31', '2026-08-31', '2026-09-30']
FIELDS = ['adj_factor', 'adj_open', 'adj_high', 'adj_low', 'adj_close']
RETURNS = [1, 3, 5, 10, 20, 60]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def adjustment_block(builder):
    if digest(builder) != BUILDER_SHA:
        raise ValueError('unreviewed_adjustment_builder')
    source = Path(builder).read_text()
    start = source.index('# ---------------- event detection ----------------')
    end = source.index('# ---------------- delisting join ----------------')
    return compile(source[start:end], str(builder), 'exec')


def rebuild(raw, block):
    columns = ['code', 'date', 'open', 'high', 'low', 'close', 'volume', 'stocks']
    df = raw[columns].copy().reset_index(drop=True)
    if df.empty or df.duplicated(['code', 'date']).any():
        raise ValueError('empty_or_duplicate_source')
    if not df.equals(df.sort_values(['code', 'date']).reset_index(drop=True)):
        raise ValueError('source_must_be_sorted')
    scope = {'df': df, 'pd': pd, 'np': np, 'print': lambda *a, **k: None}
    exec(block, scope)
    result = scope['df'][['code', 'date'] + FIELDS].copy()
    result['event_factor'] = scope['factor']
    result['same_day_rule'] = scope['same_day']
    result['admin_rule'] = scope['admin']
    result['limit_rule'] = scope['limit_viol']
    result['lag_rule'] = (result.event_factor.ne(1) & ~result.same_day_rule &
                          ~result.admin_rule & ~result.limit_rule)
    return result


def asof_adjustment(raw, cutoff, block):
    """Date-limited reconstruction, not a certificate of historical publication.

    Future rows are removed before every adjustment decision. Raw provider
    revisions and the economic validity of heuristic factors remain unaudited.
    """
    day = pd.Timestamp(cutoff)
    if pd.isna(day) or day.tzinfo is not None or day != day.normalize():
        raise ValueError('expected_naive_signal_date')
    if pd.to_datetime(raw.date).isna().any():
        raise ValueError('invalid_source_date')
    prefix = raw.loc[pd.to_datetime(raw.date).le(day)].copy()
    result = rebuild(prefix, block)
    assert result.date.max() <= day
    return result


def changed(a, b):
    return ~np.isclose(a, b, rtol=1e-12, atol=0, equal_nan=True)


def index_features(raw, prices):
    """Legacy internal market context; no current weights or external index."""
    returns = prices.groupby(raw.code, sort=False).pct_change()
    weights = raw.groupby('code', sort=False).marcap.shift(1)
    usable = returns.notna() & weights.notna()
    keys = [raw.loc[usable, 'market'], raw.loc[usable, 'date']]
    weighted = (returns[usable] * weights[usable]).groupby(keys).sum()
    total = weights[usable].groupby(keys).sum()
    result = {}
    for market, series in (weighted / total).groupby(level=0):
        series = series.droplevel(0).sort_index()
        level = (1 + series).cumprod()
        result[market] = pd.DataFrame({'idx_mom20': (level.pct_change(20) * 100).shift(1),
                                       'idx_vol20': (series.rolling(20).std() * 100 * np.sqrt(20)).shift(1)})
    return result


def audit(panel, builder, output):
    output.mkdir(parents=True, exist_ok=False)
    inputs = {}
    for name, source in [('panel.parquet', panel), ('builder.py.txt', builder)]:
        sha = digest(source)
        shutil.copyfile(source, output / name)
        assert sha == digest(output / name) == digest(source)
        inputs[name] = {'path': str(source), 'sha256': sha}
    plan = {'cutoffs': CUTOFFS, 'inputs': inputs,
            'selection': 'Fixed quarter/month ends before any prefix comparison; all observed codes; no outcome or model-based selection.'}
    (output / 'plan.json').write_text(json.dumps(plan, indent=2))
    block = adjustment_block(output / 'builder.py.txt')
    source = pd.read_parquet(output / 'panel.parquet').sort_values(['code', 'date']).reset_index(drop=True)
    full = rebuild(source, block)
    for field in FIELDS:
        # Full reconstruction must explain the actual preserved consumer input.
        np.testing.assert_array_equal(full[field].to_numpy(), source[field].to_numpy())
    print('full source reproduced exactly', len(full), flush=True)
    reports = []
    for cutoff in CUTOFFS:
        mask = source.date.le(cutoff)
        raw = source.loc[mask].reset_index(drop=True)
        observed = full.loc[mask].reset_index(drop=True)
        prefix = asof_adjustment(source, cutoff, block)
        pd.testing.assert_frame_equal(prefix[['code', 'date']], observed[['code', 'date']])
        differs = np.zeros(len(prefix), dtype=bool)
        counts = {}
        for field in FIELDS:
            selected = changed(prefix[field], observed[field])
            counts[field] = int(selected.sum())
            differs |= selected
        event_changed = changed(prefix.event_factor, observed.event_factor)
        event_columns = ['code', 'date', 'event_factor', 'same_day_rule', 'admin_rule', 'limit_rule', 'lag_rule']
        examples = observed.loc[event_changed, event_columns].copy()
        examples['prefix_event_factor'] = prefix.loc[event_changed, 'event_factor']
        examples['prefix_limit_rule'] = prefix.loc[event_changed, 'limit_rule']
        examples.to_csv(output / f'events_{cutoff}.csv', index=False)
        liq = raw.groupby('code', sort=False).amount.transform(lambda s: s.rolling(20).mean())
        signal = raw.date.eq(cutoff) & raw.volume.gt(0) & liq.ge(5e8) & liq.lt(30e8)
        prefix_eligible = np.ones(len(prefix), dtype=bool)
        for n in RETURNS:
            prefix_eligible &= prefix.groupby('code', sort=False).adj_close.pct_change(n).notna().to_numpy()
        signal &= prefix_eligible
        feature_counts = {}
        example_frames = []
        for n in RETURNS:
            old = observed.groupby('code', sort=False).adj_close.pct_change(n) * 100
            prior = prefix.groupby('code', sort=False).adj_close.pct_change(n) * 100
            difference = changed(old, prior)
            on_signal = signal.to_numpy() & difference
            feature_counts[f'ret_{n}d'] = {'all_prefix_rows': int(difference.sum()),
                                         'same_cutoff_lowliq_signal_rows': int(on_signal.sum())}
            sample = raw.loc[on_signal, ['code', 'date']].copy()
            sample['feature'] = f'ret_{n}d'
            sample['full_history_value'] = old.loc[on_signal]
            sample['prefix_value'] = prior.loc[on_signal]
            example_frames.append(sample)
        pd.concat(example_frames, ignore_index=True).to_csv(output / f'features_{cutoff}.csv', index=False)
        full_index = index_features(raw, observed.adj_close)
        prefix_index = index_features(raw, prefix.adj_close)
        index_changes = []
        for market in full_index:
            for field in ['idx_mom20', 'idx_vol20']:
                a = full_index[market].loc[pd.Timestamp(cutoff), field]
                b = prefix_index[market].loc[pd.Timestamp(cutoff), field]
                if changed(a, b):
                    index_changes.append({'market': market, 'feature': field, 'full_history_value': float(a),
                                          'prefix_value': float(b),
                                          'affected_eligible_signal_rows': int((signal & raw.market.eq(market)).sum())})
        record = {'cutoff': cutoff, 'prefix_rows': len(prefix),
                  'adjusted_price_or_factor_changed_rows': int(differs.sum()),
                  'changed_codes': int(raw.loc[differs, 'code'].nunique()),
                  'field_counts': counts, 'event_factor_changed_rows': int(event_changed.sum()),
                  'feature_counts': feature_counts, 'market_context_changes': index_changes}
        reports.append(record)
        print(json.dumps(record), flush=True)
        del raw, observed, prefix, examples, old, prior, sample, example_frames
        gc.collect()
    for name, source_path in [('panel.parquet', panel), ('builder.py.txt', builder)]:
        assert digest(source_path) == inputs[name]['sha256'] == digest(output / name)
    result = {'verdict': 'HISTORICAL_INPUT_NOT_ASOF_STABLE' if any(r['adjusted_price_or_factor_changed_rows'] for r in reports) else 'NO_CHANGE_AT_FIXED_CUTOFFS',
              'source_rows': len(full), 'full_reconstruction_exact': True, 'cutoffs': reports,
              'scope': 'Algorithm/data provenance, not official corporate-action correctness or strategy outcome attribution.',
              'inputs': inputs, 'source_unchanged': True, 'model_fit_or_scoring': False}
    (output / 'audit.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--panel', type=Path, required=True)
    p.add_argument('--builder', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    audit(args.panel, args.builder, args.output)
