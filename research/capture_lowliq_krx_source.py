"""Read-only independent price capture for every frozen test-universe code.

No test labels/returns and no modification of live caches. Capture completeness is
not price-basis certification or evidence of strategy qualification.
"""
import argparse
from collections import Counter
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
from research.audit_kr_adjustment_asof import digest
from research.audit_kr_touch10_price_source import parse_bars
from research.run_lowliq_touch10_reconstruction import save_json, prepare
from multi_agent.tools.backfill_kr_intraday import request_deadline


def payload_sha(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def inspect_payload(payload, request, expected):
    if not isinstance(payload, dict):
        return {'status': 'INVALID_RESPONSE', 'validation_error_type': 'NotMapping'}
    if payload.get('rt_cd') != '0':
        return {'status': 'PROVIDER_ERROR'}
    if payload.get('output2') == []:
        return {'status': 'EMPTY_PROVIDER', 'missing_existing_dates': expected}
    try:
        bars = parse_bars(payload, request['start_date'], request['end_date'])
    except (ValueError, KeyError, TypeError) as exc:
        return {'status': 'INVALID_RESPONSE', 'validation_error_type': type(exc).__name__}
    observed = sorted(str(day.date()) for day in bars.date)
    missing = sorted(set(expected)-set(observed))
    extra = sorted(set(observed)-set(expected))
    return {'status': 'PARTIAL' if missing else 'CAPTURED', 'rows': len(bars),
            'missing_existing_dates': missing, 'additional_provider_dates': extra,
            'first_date': observed[0], 'last_date': observed[-1]}


def plan(root):
    spec, paths, parent, manifest = prepare(root)
    complete_path = parent/'scores_complete.json'
    complete = json.loads(complete_path.read_text())
    assert complete['test_outcomes_computed'] is False and complete['publication_allowed'] is False
    dates = sorted((parent/'scores').glob('*.json'))
    if len(dates) != complete['dates']:
        raise ValueError('incomplete_score_calendar')
    codes = set(); universes = {}
    for path in dates:
        receipt = json.loads(path.read_text()); parquet = path.with_suffix('.parquet')
        sha = digest(parquet)
        if sha != receipt['universe_sha256']:
            raise ValueError('changed_score_universe')
        codes.update(pd.read_parquet(parquet, columns=['code']).code)
        universes[path.stem] = sha
    raw = pd.read_parquet(paths['panel'], columns=['code','date'])
    raw = raw.loc[raw.code.isin(codes) & raw.date.between('2026-06-30','2026-10-02')]
    expected = {code: sorted(str(day.date()) for day in group.date)
                for code, group in raw.groupby('code')}
    if set(expected) != codes:
        raise ValueError('missing_source_code')
    return {'parent_manifest': manifest, 'parent_complete_sha256': digest(complete_path),
            'universes': universes, 'expected_dates': expected,
            'request': {'start_date': '20260630', 'end_date': '20261002',
                        'market_div': 'J', 'period': 'D'},
            'bases': ['adjusted','nominal'], 'code_sha256': digest(Path(__file__)),
            'publication_allowed': False,
            'scope': 'All frozen test-universe codes, both KRX bases, no selected-only filtering. '
                     'JSON provider payloads, not raw HTTP bytes. No outcomes or source certification. '
                     'Adjusted responses reflect provider basis at actual capture time; not historical PIT.'}


def collect(spec, audit, client, budget):
    began = time.monotonic(); calls = 0; results = {}; hashes = {}
    spec_hash = digest(audit/'plan.json')
    requests = [(code, basis) for code in sorted(spec['expected_dates']) for basis in spec['bases']]
    for code, basis in requests:
        key = f'{code}_{basis}'; path = audit/'responses'/f'{key}.json'
        request = {**spec['request'], 'adjusted': basis == 'adjusted'}
        if path.exists():
            item = json.loads(path.read_text())
            if item['plan_sha256'] != spec_hash or item['code'] != code or item['request'] != request:
                raise ValueError('changed_capture_identity')
            if 'payload' in item:
                if payload_sha(item['payload']) != item['payload_sha256']:
                    raise ValueError('changed_provider_payload')
                rebuilt = inspect_payload(item['payload'], request, spec['expected_dates'][code])
                if item['inspection'] != rebuilt:
                    raise ValueError('changed_source_inspection')
        else:
            if time.monotonic()-began >= budget:
                break
            item = {'code': code, 'request': request, 'plan_sha256': spec_hash,
                    'requested_at': datetime.now(timezone.utc).isoformat()}
            try:
                calls += 1
                with request_deadline(20):
                    payload = client.daily_bars(code, **request)
                item.update(payload=payload, payload_sha256=payload_sha(payload))
                item['inspection'] = inspect_payload(payload, request, spec['expected_dates'][code])
            except Exception as exc:
                item.update(inspection={'status': 'REQUEST_ERROR'}, error_type=type(exc).__name__)
            item['received_at'] = datetime.now(timezone.utc).isoformat()
            save_json(path, item)
            if calls % 100 == 0:
                print('captured requests', calls, 'of', len(requests), flush=True)
        results[key] = item['inspection']; hashes[key] = digest(path)
    summary = {'status': 'CAPTURE_ATTEMPTS_COMPLETE' if len(results) == len(requests) else 'BUDGET_EXHAUSTED',
               'completed_attempts': len(results), 'target_requests': len(requests),
               'network_calls': calls, 'elapsed_seconds': time.monotonic()-began,
               'status_counts': dict(Counter(r['status'] for r in results.values())),
               'results': results, 'response_sha256': hashes, 'publication_allowed': False,
               'test_outcomes_computed': False}
    save_json(audit/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json'), summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['results','response_sha256']}), flush=True)
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--budget', type=float, default=600)
    args = ap.parse_args()
    if not 0 < args.budget <= 3600:
        ap.error('budget must be positive and at most 3600 seconds')
    audit = args.root/'runtime_state/audit/lowliq_krx_source_20261007'
    audit.mkdir(parents=True, exist_ok=True)
    with (audit/'capture.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        spec = plan(args.root)
        save_json(audit/'plan.json', spec)
        from dotenv import load_dotenv
        from modules.kis_openapi import KISOpenAPIClient
        load_dotenv(args.root/'.env.local')
        os.environ['KIS_ENABLE_LIVE_CALLS'] = '1'
        os.environ['KIS_LIVE_RETRY_COUNT'] = '0'
        collect(spec, audit, KISOpenAPIClient(timeout=10), args.budget)
