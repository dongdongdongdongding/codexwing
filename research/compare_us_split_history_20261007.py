"""Verify captured KIS pages and measure full-date replacement prerequisites.

Full date coverage and positive prices are necessary, not sufficient, for release.
No price arithmetic in this audit is written into the production data pipeline.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.audit_us_split_history_20261007 import sha, validate_page
from modules.ohlcv_quality import bar_issues
from multi_agent.tools.intraday_cache_journal import save_json


FIELDS = ['open', 'high', 'low', 'close']


def read_series(result, end, start):
    rows, seen = [], set()
    for record in result['pages']:
        path = Path(record['path'])
        if sha(path) != record['sha256']:
            raise ValueError('response_hash_changed')
        payload = json.loads(path.read_text())
        dates = validate_page(payload, result['symbol'], end, seen)
        rows.extend(payload['output2'])
        seen.update(dates)
        if dates:
            end = (pd.Timestamp(min(dates)) - pd.Timedelta(days=1)).strftime('%Y%m%d')
    if len(seen) != result['rows']:
        raise ValueError('capture_count_mismatch')
    frame = pd.DataFrame(rows).rename(columns={'xymd': 'date', 'clos': 'close', 'tvol': 'volume'})
    frame['date'] = pd.to_datetime(frame.date, format='%Y%m%d')
    frame = frame.loc[frame.date.ge(pd.Timestamp(start))].set_index('date').sort_index()
    # Keep original numeric strings for independent decimal ratio checks.
    return frame[FIELDS + ['volume']]


def basis_diagnostics(raw, adjusted):
    common = raw.index.intersection(adjusted.index)
    unequal_volume = []
    inconsistent, invalid, factors = [], [], Counter()
    for day in common:
        a, b = raw.loc[day], adjusted.loc[day]
        values = [Decimal(str(v)) for v in [*a[FIELDS], *b[FIELDS]]]
        if any(not v.is_finite() or v <= 0 for v in values):
            invalid.append(str(day.date()))
            continue
        close_raw, close_adj = Decimal(a['close']), Decimal(b['close'])
        factor = close_adj / close_raw
        factors[str(factor.quantize(Decimal('.000001')))] += 1
        # Four-decimal quote precision propagated without treating float equality
        # or a close-only ratio as certification of an adjustment methodology.
        for field in FIELDS:
            x, y = Decimal(a[field]), Decimal(b[field])
            tolerance = Decimal('.0001') * (abs(x) + abs(y) + abs(close_raw) + abs(close_adj))
            if abs(y * close_raw - x * close_adj) > tolerance:
                inconsistent.append(str(day.date()))
                break
        if Decimal(a['volume']) != Decimal(b['volume']):
            unequal_volume.append(str(day.date()))
    return {'common_dates': len(common), 'invalid_price_dates': invalid,
            'inconsistent_OHLC_factor_dates': inconsistent,
            'different_volume_dates': unequal_volume,
            'close_factor_counts_rounded_6dp': dict(factors)}


def run(audit):
    plan = json.loads((audit / 'plan.json').read_text())
    captured = json.loads((audit / 'summary.json').read_text())
    results = {(r['symbol'], r['basis']): r for r in captured['results']}
    rows = []
    for row in plan['symbols']:
        symbol = row['symbol']
        if sha(row['baseline']) != row['baseline_sha256'] or sha(row['source']) != row['baseline_sha256']:
            raise ValueError('raw_baseline_changed')
        old = pd.read_parquet(row['baseline']).set_index('date')
        old = old.loc[(old.index >= pd.Timestamp(row['start'])) & (old.index <= pd.Timestamp(plan['end']))]
        series = {basis: read_series(results[(symbol, basis)], plan['end'], row['start']) for basis in [0, 1]}
        entry = {'symbol': symbol, 'baseline_dates': len(old), 'basis': {}}
        for basis, strings in series.items():
            frame = strings.apply(pd.to_numeric, errors='coerce')
            issues = bar_issues(frame)
            common = old.index.intersection(frame.index)
            missing = old.index.difference(frame.index)
            added = frame.index.difference(old.index)
            entry['basis'][str(basis)] = {
                'stop_reason': results[(symbol, basis)]['stop_reason'],
                'observed_dates': len(frame), 'missing_dates': missing.strftime('%Y-%m-%d').tolist(),
                'extra_dates': added.strftime('%Y-%m-%d').tolist(),
                'structural_issues': issues[issues.ne('')].value_counts().to_dict(),
                'zero_volume_dates': frame.index[frame.volume.eq(0)].strftime('%Y-%m-%d').tolist(),
                'baseline_raw_close_matches': int(np.isclose(old.loc[common, 'raw_close'], frame.loc[common, 'close'],
                                                            rtol=1e-8, atol=.00011).sum()),
                'common_dates': len(common),
            }
            strings.to_csv(audit / f'{symbol}_MODP{basis}_verified.csv')
        entry['basis_consistency'] = basis_diagnostics(series[0], series[1])
        # Deliberately a prerequisite, never a permission to replace or unquarantine.
        entry['coverage_and_structure_pass'] = all(
            b['stop_reason'] in {'source_exhausted', 'requested_start_reached'} and
            not b['missing_dates'] and not b['structural_issues'] for b in entry['basis'].values())
        entry['replacement_authorized'] = False
        rows.append(entry)
    result = {'scope': 'Full-history source prerequisites only. Corporate actions, dividends, volume adjustment and venue/session comparability need separate certification.',
              'raw_unchanged': True, 'symbols': rows,
              'coverage_and_structure_pass': [r['symbol'] for r in rows if r['coverage_and_structure_pass']],
              'replacement_authorized': False}
    save_json(audit / 'comparison.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'symbols'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    run(parser.parse_args().audit)
