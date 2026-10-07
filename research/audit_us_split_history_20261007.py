"""Read-only full-history extension of the fixed 22-symbol KIS basis audit.

No raw replacement, quarantine release, model fitting or outcome selection.
The saved plan and immutable page receipts make interrupted captures resumable.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modules.kis_openapi import KISConfig, KISOpenAPIClient
from modules.us_symbol_lineage import UNVERIFIED_SPLIT_BASIS
from multi_agent.tools.backfill_kr_intraday import request_deadline
from multi_agent.tools.intraday_cache_journal import save_json


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate_page(payload, symbol, end, seen):
    if payload.get('rt_cd') != '0':
        raise ValueError('provider_error')
    header = payload['output1']
    rows = payload['output2']
    if header.get('rsym') != 'DNAS' + symbol or int(header['nrec']) != len(rows):
        raise ValueError('response_identity_or_count_mismatch')
    dates = [r['xymd'] for r in rows]
    for d in dates:
        if len(d) != 8 or datetime.strptime(d, '%Y%m%d').strftime('%Y%m%d') != d:
            raise ValueError('invalid_date')
    if dates != sorted(set(dates), reverse=True) or any(d > end for d in dates):
        raise ValueError('unordered_duplicate_or_future_date')
    if set(dates) & seen:
        raise ValueError('overlapping_pages')
    return dates


def freeze(root, out, cache):
    path = out / 'plan.json'
    if path.exists():
        plan = json.loads(path.read_text())
        if plan['implementation_sha256'] != sha(__file__):
            raise ValueError('capture_implementation_changed')
        for row in plan['symbols']:
            if sha(row['baseline']) != row['baseline_sha256'] or sha(row['source']) != row['baseline_sha256']:
                raise ValueError('frozen_baseline_changed')
        return plan
    seed = root / 'runtime_state/audit/us_split_basis_crosscheck_20261007'
    old = json.loads((seed / 'plan.json').read_text())
    symbols = sorted(set(UNVERIFIED_SPLIT_BASIS) | {'ADBE'})
    if symbols != sorted(old['symbols']):
        raise ValueError('fixed_cohort_changed')
    receipts = {Path(r['file']).name: r for r in json.loads((seed / 'summary.json').read_text())['records']}
    rows = []
    (out / 'baseline').mkdir(exist_ok=True)
    (out / 'pages').mkdir(exist_ok=True)
    with (cache / '.daily_refresh.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for symbol in symbols:
            source = cache / 'raw_ohlcv' / f'{symbol}.parquet'
            raw = source.read_bytes()
            baseline = out / 'baseline' / source.name
            with baseline.open('xb') as fh:
                fh.write(raw)
            digest = hashlib.sha256(raw).hexdigest()
            if sha(source) != digest or sha(baseline) != digest:
                raise ValueError('source_changed_during_snapshot')
            frame = pd.read_parquet(baseline, columns=['date'])
            start = max(pd.Timestamp('2018-01-01'), pd.to_datetime(frame.date).min()).strftime('%Y%m%d')
            first = {}
            for basis in [0, 1]:
                p = seed / f'{symbol}_MODP{basis}.json'
                record = receipts[p.name]
                if record['status'] != 'OBSERVED' or sha(p) != record['sha256']:
                    raise ValueError('seed_response_hash_mismatch')
                first[str(basis)] = {'path': str(p), 'sha256': sha(p), 'observed_at': record['observed_at']}
            rows.append({'symbol': symbol, 'start': start, 'source': str(source),
                         'baseline': str(baseline), 'baseline_sha256': digest, 'seed': first})
    plan = {'created_at': datetime.now(timezone.utc).isoformat(), 'end': '20261005',
            'implementation_sha256': sha(__file__), 'symbols': rows,
            'scope': 'Fixed 21 quarantined symbols plus ADBE control; independent source coverage, not alpha or replacement authorization.'}
    save_json(path, plan)
    return plan


def page(client, out, symbol, basis, end):
    path = out / 'pages' / f'{symbol}_MODP{basis}_{end}.json'
    receipt = path.with_suffix('.receipt.json')
    request = {'symbol': symbol, 'adjusted': bool(basis), 'exchange': 'NAS', 'end_date': end}
    if path.exists() or receipt.exists():
        saved = json.loads(receipt.read_text())
        if saved['request'] != request or sha(path) != saved['sha256']:
            raise ValueError('saved_response_changed')
        return json.loads(path.read_text()), saved
    started = datetime.now(timezone.utc).isoformat()
    with request_deadline(12):
        payload = client.overseas_daily_bars(**request)
    save_json(path, payload)
    record = {'request': request, 'started_at': started, 'observed_at': datetime.now(timezone.utc).isoformat(),
              'path': str(path), 'sha256': sha(path)}
    save_json(receipt, record)
    return payload, record


def run(root, out, cache, budget):
    from dotenv import load_dotenv
    plan = freeze(root, out, cache)
    load_dotenv(root / '.env.local')
    os.environ['KIS_LIVE_RETRY_COUNT'] = '0'
    client = KISOpenAPIClient(replace(KISConfig.from_env(), live_network_allowed=True), timeout=10)
    started = time.monotonic()
    results = []
    for row in plan['symbols']:
        symbol = row['symbol']
        for basis in [0, 1]:
            seen, pages, end, reason, error = set(), [], plan['end'], None, None
            seed = row['seed'][str(basis)]
            try:
                if sha(seed['path']) != seed['sha256']:
                    raise ValueError('seed_changed')
                payload = json.loads(Path(seed['path']).read_text())
                record = seed
                for _ in range(60):
                    dates = validate_page(payload, symbol, end, seen)
                    pages.append(record)
                    seen.update(dates)
                    if not dates:
                        reason = 'source_exhausted'
                        break
                    if min(dates) <= row['start']:
                        reason = 'requested_start_reached'
                        break
                    end = (pd.Timestamp(min(dates)) - pd.Timedelta(days=1)).strftime('%Y%m%d')
                    if time.monotonic() - started >= budget:
                        reason = 'budget_exhausted'
                        break
                    payload, record = page(client, out, symbol, basis, end)
                else:
                    reason = 'page_limit'
            except Exception as exc:
                reason, error = 'error', type(exc).__name__
            result = {'symbol': symbol, 'basis': basis, 'rows': len(seen),
                      'first': min(seen, default=None), 'last': max(seen, default=None),
                      'stop_reason': reason, 'error_type': error, 'pages': pages}
            results.append(result)
            save_json(out / f'{symbol}_MODP{basis}_result.json', result)
            print(json.dumps({k: v for k, v in result.items() if k != 'pages'}), flush=True)
    unchanged = all(sha(r['source']) == r['baseline_sha256'] for r in plan['symbols'])
    terminal = sum(r['stop_reason'] in {'source_exhausted', 'requested_start_reached'} for r in results)
    save_json(out / 'summary.json', {'checked_at': datetime.now(timezone.utc).isoformat(),
              'terminal': terminal, 'planned': len(results), 'raw_unchanged': unchanged,
              'elapsed_seconds': time.monotonic() - started, 'results': results})
    return 0 if unchanged and terminal == len(results) else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=Path.home() / 'research_cache/us_daily/NASDAQ')
    parser.add_argument('--budget-seconds', type=float, default=600)
    args = parser.parse_args()
    if args.budget_seconds <= 0:
        parser.error('budget must be positive')
    args.audit.mkdir(parents=True, exist_ok=True)
    with (args.audit / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run(args.root.resolve(), args.audit.resolve(), args.cache.resolve(), args.budget_seconds)


if __name__ == '__main__':
    raise SystemExit(main())
