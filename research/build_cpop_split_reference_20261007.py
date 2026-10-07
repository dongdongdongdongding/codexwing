"""Freeze exact supported rows for the source-audited CPOP split history.

No returns, model scores, selection outcomes or strategy metrics are read.
Unsupported observations are retained as explicit deferred rows.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.us_split_basis import reference

CHAINS = {
    'CPOP': [('2023-10-27', 10), ('2026-07-13', 10), ('2026-09-14', 15)],
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(root, output):
    audit = root / 'runtime_state/audit/us_split_full_kis_20261007'
    dest = root / 'runtime_state/audit/cpop_basis_repair_20261007'
    official = root / 'runtime_state/audit/us_full_history_baseline_20261007/official'
    plan = json.loads((audit / 'plan.json').read_text())
    fields = reference()['fields']
    reports = []
    output.mkdir(parents=True, exist_ok=True)
    for symbol, chain in CHAINS.items():
        entry = next(r for r in plan['symbols'] if r['symbol'] == symbol)
        assert digest(entry['baseline']) == digest(entry['source']) == entry['baseline_sha256']
        base = pd.read_parquet(entry['baseline']).set_index('date')
        boundary, ratio = chain[-1]
        base = base.loc[base.index < pd.Timestamp(boundary)]
        raw = pd.read_csv(audit / f'{symbol}_MODP0_verified.csv', parse_dates=['date']).set_index('date')
        adj = pd.read_csv(audit / f'{symbol}_MODP1_verified.csv', parse_dates=['date']).set_index('date')
        assert base.index.isin(raw.index).all() and base.index.isin(adj.index).all()
        proof = []
        for basis in [0, 1]:
            result = json.loads((audit / f'{symbol}_MODP{basis}_result.json').read_text())
            for record in result['pages']:
                assert digest(record['path']) == record['sha256']
                proof.append({k: record[k] for k in ['path', 'sha256', 'observed_at']})
        sources = [json.loads((official / f'{symbol}.json').read_text())]
        assert sources[0]['status'] == 200 and digest(official / f'{symbol}.html') == sources[0]['sha256']
        for tag in ['prior_2023', 'prior_2026']:
            prior = json.loads((dest / f'{symbol}_{tag}.json').read_text())
            assert prior['status'] == 200 and digest(dest / f'{symbol}_{tag}.html') == prior['sha256']
            sources.append(prior)
        verified, nominal, deferred = {}, {}, {}
        for day, row in base.iterrows():
            date = str(day.date())
            a, b = raw.loc[day], adj.loc[day]
            cumulative = np.prod([f for effective, f in chain if date < effective])
            assert all(np.isclose(a[f] * cumulative, b[f], rtol=.005, atol=.0001)
                       for f in ['open', 'high', 'low', 'close']), (symbol, date, 'KIS_official_factor')
            assert a['volume'] == b['volume']
            old = {f: float(row[f]) for f in fields}
            assert old['adj_factor'] == 1 and old['raw_close'] == old['close'] == old['adj_close']
            ready = all(np.isclose(old[f], b[f], rtol=.005, atol=.0001) for f in ['open', 'high', 'low', 'close'])
            missing = all(np.isclose(old[f] * ratio, b[f], rtol=.005, atol=.0001) for f in ['open', 'high', 'low', 'close'])
            if ready == missing:
                deferred[date] = {'values': [old[f] for f in fields],
                                  'reason': 'cross_provider_unresolved_price_units'}
                continue
            new = dict(old)
            if missing:
                for f in ['open', 'high', 'low', 'close', 'raw_close', 'adj_close']:
                    new[f] *= ratio
                new['volume'] /= ratio
                new['dollar_volume'] = new['close'] * new['volume']
            if not np.isclose(new['volume'], a['volume'] / cumulative, rtol=.05, atol=1):
                deferred[date] = {'values': [old[f] for f in fields],
                                  'reason': 'cross_provider_adjusted_volume_difference',
                                  'candidate_volume': new['volume'], 'independent_volume': a['volume'] / cumulative}
                continue
            verified[date] = [new[f] for f in fields]
            if missing:
                nominal[date] = [old[f] for f in fields]
        record = {'schema': 1, 'symbol': symbol, 'provider': 'yfinance', 'effective': boundary, 'ratio': ratio,
                  'official_chain': chain, 'official_sources': sources, 'baseline_sha256': entry['baseline_sha256'],
                  'independent_pages': proof, 'fields': fields, 'known_nominal_rows': nominal,
                  'verified_adjusted_rows': verified, 'unverified_rows': deferred,
                  'scope': 'Exact observed rows only. Unsupported price or volume observations remain unchanged and quarantined. This verifies split basis, not exact exchange prices, source completeness or strategy qualification.',
                  'audit_tolerances': {'price_rtol': .005, 'price_atol': .0001, 'volume_rtol': .05, 'volume_atol': 1}}
        path = output / f'{symbol.lower()}_split_basis_20261007.json'
        body = json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + '\n'
        if path.exists():
            assert path.read_text() == body
        else:
            path.write_text(body)
        reports.append({'symbol': symbol, 'pre_rows': len(base), 'verified': len(verified),
                        'corrected': len(nominal), 'deferred': len(deferred), 'path': str(path), 'sha256': digest(path)})
    (dest / 'references.json').write_text(json.dumps(reports, indent=2))
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.root, args.output)
