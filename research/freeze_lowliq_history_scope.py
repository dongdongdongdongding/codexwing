"""Freeze a conservative, outcome-independent historical price audit footprint.

This is a source-verification plan, not a new training epoch, evaluator or live
replacement. Full original panels remain the computational source of truth.
"""
import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest, index_features
from research.run_lowliq_touch10_reconstruction import prepare, save_frame, save_json

V7_SHA = '2dca1f0b55a5614a8e6faa076e881d435955775061df6ed8d098622bba36c73a'


def validate_keys(frame):
    if frame[['code', 'date']].isna().any().any() or frame.duplicated(['code', 'date']).any():
        raise ValueError('invalid_source_keys')
    ordered = frame.sort_values(['code', 'date']).reset_index(drop=True)
    pd.testing.assert_frame_equal(frame[['code', 'date']].reset_index(drop=True),
                                  ordered[['code', 'date']])


def history_scope(raw, start, alternate_close=None):
    """All recent rows, 130 prior stock observations, and full up-run boundaries.

    All codes are included regardless of liquidity, training labels or picks.
    Twenty-one prior market dates conservatively cover shifted 20-return context;
    each contributing observation's prior per-code row is included explicitly.
    """
    validate_keys(raw)
    start = pd.Timestamp(start)
    calendar = pd.DatetimeIndex(sorted(raw.date.unique()))
    first = calendar.searchsorted(start)
    if first == len(calendar) or first < 21:
        raise ValueError('insufficient_context_calendar')
    context_start = calendar[first - 21]
    recent = raw.date.ge(context_start).to_numpy()
    flags = recent.astype(np.uint8)
    boundary_extensions = 0
    for _, group in raw.groupby('code', sort=False):
        positions = group.index.to_numpy()
        days = group.date.to_numpy()
        at = days.searchsorted(start.to_datetime64())
        if at < len(group):
            begin = max(0, at - 130)
            for close in [raw.adj_close] + ([] if alternate_close is None else [alternate_close]):
                values = close.iloc[positions].to_numpy()
                # Alternate fit prices are NaN after the fit cutoff. They cannot
                # extend a boundary beyond their observed prefix.
                if np.isfinite(values[at]):
                    up = np.r_[False, values[1:at+1] > values[:at]]
                    last_nonup = np.flatnonzero(~up)[-1]
                    needed = max(0, last_nonup - 1)
                    if needed < begin:
                        boundary_extensions += 1
                        begin = needed
            flags[positions[begin:]] |= 2
        context_positions = np.flatnonzero(recent[positions])
        predecessors = context_positions[context_positions > 0] - 1
        flags[positions[predecessors]] |= 4
    result = raw.loc[flags != 0, ['code', 'date']].copy()
    result['scope_flags'] = flags[flags != 0]
    return result.reset_index(drop=True), {
        'market_context_start': str(context_start.date()),
        'up_run_boundary_extensions': boundary_extensions,
        'flags': {'1': 'all source rows from context start through source end',
                  '2': 'all signal-period codes plus 130 earlier observations and up-run boundary',
                  '4': 'prior observed per-code row for each market-context row'},
    }


def requests_for_scope(scope, width_days=90):
    if not 1 <= width_days <= 90:
        raise ValueError('invalid_request_width')
    requests = []
    for code, group in scope.groupby('code', sort=True):
        dates = pd.DatetimeIndex(group.date).sort_values()
        cursor = dates.min()
        while cursor <= dates.max():
            end = min(cursor + pd.Timedelta(days=width_days-1), dates.max())
            expected = [str(d.date()) for d in dates[(dates >= cursor) & (dates <= end)]]
            if expected:
                for basis in ['nominal', 'adjusted']:
                    requests.append({'id': f'{code}_{cursor:%Y%m%d}_{end:%Y%m%d}_{basis}',
                                     'code': code, 'basis': basis,
                                     'start_date': f'{cursor:%Y%m%d}', 'end_date': f'{end:%Y%m%d}',
                                     'expected_dates': expected})
            cursor = end + pd.Timedelta(days=1)
    return requests


def context_parity(raw, close, start):
    original = index_features(raw, close)
    returns = close.groupby(raw.code, sort=False).pct_change()
    weights = raw.groupby('code', sort=False).marcap.shift(1)
    usable = returns.notna() & weights.notna()
    keys = [raw.loc[usable, 'market'], raw.loc[usable, 'date']]
    ratio = (returns[usable]*weights[usable]).groupby(keys).sum() / weights[usable].groupby(keys).sum()
    result = {}
    for market, block in ratio.groupby(level=0):
        series = block.droplevel(0).sort_index()
        finite = ((1+series).rolling(20).apply(np.prod, raw=True)-1).shift(1)*100
        keep = finite.index >= pd.Timestamp(start)
        a = finite[keep].to_numpy(); b = original[market].idx_mom20.loc[keep].to_numpy()
        same = (a.astype('float32') == b.astype('float32')) | (np.isnan(a) & np.isnan(b))
        if not same.all():
            raise ValueError('finite_context_float32_mismatch:' + market)
        result[market] = {'cells': len(a), 'float32_mismatches': int((~same).sum()),
                          'max_float64_difference': float(np.nanmax(abs(a-b)))}
    return result


def freeze(root, out):
    import json
    spec, paths, parent, manifest = prepare(root)
    receipt = json.loads((parent/'training_receipt.json').read_text())
    for name, field in [('training.parquet', 'training_sha256'),
                        ('training_eligibility.parquet', 'eligibility_sha256')]:
        if digest(parent/name) != receipt[field]:
            raise ValueError('changed_training_artifact')
    complete = json.loads((parent/'scores_complete.json').read_text())
    if complete['test_outcomes_computed'] or complete['publication_allowed']:
        raise ValueError('changed_study_state')
    inputs = {name: digest(parent/name) for name in ['manifest.json', 'training_receipt.json',
              'training.parquet', 'training_eligibility.parquet', 'scores_complete.json']}
    signals = [pd.read_parquet(parent/'training_eligibility.parquet', columns=['code', 'date'])]
    score_paths = sorted((parent/'scores').glob('*.parquet'))
    if len(score_paths) != complete['dates']:
        raise ValueError('missing_score_date')
    for path in score_paths:
        meta = json.loads(path.with_suffix('.json').read_text())
        if digest(path) != meta['universe_sha256']:
            raise ValueError('changed_score_universe')
        signals.append(pd.read_parquet(path, columns=['code', 'date']))
        for artifact in [path, path.with_suffix('.json')]:
            inputs[str(artifact.relative_to(parent))] = digest(artifact)
    for path in sorted((parent/'models').glob('*.json')):
        meta = json.loads(path.read_text())
        if digest(path.with_suffix('.txt')) != meta['model_sha256']:
            raise ValueError('changed_model')
        for artifact in [path, path.with_suffix('.txt')]:
            inputs[str(artifact.relative_to(parent))] = digest(artifact)
    corrected = root/'runtime_state/audit/kr_verified_events_v7_20261007/panel.parquet'
    if digest(corrected) != V7_SHA:
        raise ValueError('changed_v7_source')
    raw = pd.read_parquet(corrected, columns=['code','date','market','marcap','adj_close'])
    raw = raw.sort_values(['code','date']).reset_index(drop=True)
    fit = pd.read_parquet(paths['fit_prices'], columns=['code','date','adj_close'])
    train_raw = raw.loc[raw.date.le(spec['fit_cutoff'])].reset_index(drop=True)
    pd.testing.assert_frame_equal(train_raw[['code','date']], fit[['code','date']])
    alternate = pd.Series(np.nan, index=raw.index)
    alternate.loc[raw.date.le(spec['fit_cutoff'])] = fit.adj_close.to_numpy()
    scope, rules = history_scope(raw, spec['train_signal_start'], alternate)
    keys = pd.concat(signals, ignore_index=True).drop_duplicates().sort_values(['code','date']).reset_index(drop=True)
    covered = pd.MultiIndex.from_frame(scope[['code','date']])
    if (covered.get_indexer(pd.MultiIndex.from_frame(keys)) < 0).any():
        raise ValueError('signal_key_outside_footprint')
    parity = {'v7': context_parity(raw, raw.adj_close, spec['train_signal_start']),
              'fit_snapshot': context_parity(train_raw, fit.adj_close, spec['train_signal_start'])}
    requests = requests_for_scope(scope)
    save_frame(out/'footprint.parquet', scope)
    save_frame(out/'signal_keys.parquet', keys)
    plan = {'schema': 1, 'source_sha256': V7_SHA, 'parent_manifest': manifest,
            'parent_artifact_sha256': inputs, 'code_sha256': digest(Path(__file__)),
            'footprint_sha256': digest(out/'footprint.parquet'),
            'signal_keys_sha256': digest(out/'signal_keys.parquet'),
            'rules': rules, 'context_parity': parity,
            'rows': len(scope), 'codes': int(scope.code.nunique()),
            'signal_rows': len(keys), 'signal_codes': int(keys.code.nunique()),
            'first_date': str(scope.date.min().date()), 'last_date': str(scope.date.max().date()),
            'requests': requests, 'request_count': len(requests),
            'publication_allowed': False, 'test_outcomes_computed': False,
            'source_certified': False,
            'scope': 'Conservative superset for every source code, not selected or resolved-only. '
                     'Includes all training label source dates through fit cutoff and all post-start raw rows, '
                     'including nontrading rows and currently ineligible codes. No labels/returns read from test. '
                     '90 calendar days per request avoids 100-bar truncation. Missing/delisted history remains explicit.',
            'limitations': 'This freezes price/volume/amount verification scope, not a source certificate. '
                          'KIS daily bars do not independently certify marcap, market membership, historical publication '
                          'time, dividends, corporate-action wealth or absent source dates. Full original panels remain '
                          'the computational source: cumulative floating-point history is not replaced by a subset. '
                          'Finite-context parity is empirical on the two pinned snapshots, not a universal identity. '
                          'A changed source requires renewed scope/up-run checks and a separately registered study.'}
    save_json(out/'plan.json', plan)
    print(json.dumps({k: v for k,v in plan.items() if k in ['rows','codes','signal_rows','signal_codes',
                      'first_date','last_date','request_count','context_parity','rules']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    freeze(args.root, args.out)
