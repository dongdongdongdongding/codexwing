"""Bounded, resumable read-only capture of the frozen historical audit scope."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.capture_lowliq_krx_source import inspect_payload, payload_sha
from research.run_lowliq_touch10_reconstruction import save_json
from multi_agent.tools.backfill_kr_intraday import request_deadline


def collect(plan, audit, client, *, budget, max_calls, interval=0.35):
    if budget <= 0 or max_calls < 0 or interval < 0:
        raise ValueError('invalid_capture_limits')
    began = time.monotonic()
    counts = Counter(); calls = 0; reused = 0; last_call = None
    for request in plan['requests']:
        path = audit/'responses'/(request['id']+'.json')
        identity = {'code': request['code'], 'market_div': 'J', 'period': 'D',
                    'start_date': request['start_date'], 'end_date': request['end_date'],
                    'adjusted': request['basis'] == 'adjusted'}
        if path.exists():
            item = json.loads(path.read_text())
            if item['request'] != identity or item['plan_sha256'] != plan['plan_sha256']:
                raise ValueError('changed_capture_identity')
            if 'payload' in item:
                if payload_sha(item['payload']) != item['payload_sha256']:
                    raise ValueError('changed_provider_payload')
                if inspect_payload(item['payload'], identity, request['expected_dates']) != item['inspection']:
                    raise ValueError('changed_capture_inspection')
            elif item['inspection'] != {'status': 'REQUEST_ERROR'}:
                raise ValueError('invalid_error_receipt')
            reused += 1
        else:
            if calls >= max_calls or time.monotonic()-began >= budget:
                break
            if last_call is not None:
                delay = max(0, interval-(time.monotonic()-last_call))
                if time.monotonic()-began+delay >= budget:
                    break
                time.sleep(delay)
            item = {'request': identity, 'plan_sha256': plan['plan_sha256'],
                    'requested_at': datetime.now(timezone.utc).isoformat()}
            last_call = time.monotonic(); calls += 1
            try:
                with request_deadline(20):
                    payload = client.daily_bars(identity['code'], **{k: v for k, v in identity.items() if k != 'code'})
                item.update(payload=payload, payload_sha256=payload_sha(payload),
                            inspection=inspect_payload(payload, identity, request['expected_dates']))
            except Exception as exc:
                item.update(inspection={'status': 'REQUEST_ERROR'}, error_type=type(exc).__name__)
            item['received_at'] = datetime.now(timezone.utc).isoformat()
            save_json(path, item)
            if calls % 100 == 0:
                print(json.dumps({'new_requests': calls, 'reused': reused,
                                  'elapsed_seconds': time.monotonic()-began}), flush=True)
        counts[item['inspection']['status']] += 1
    processed = calls + reused
    result = {'status': 'ATTEMPTS_COMPLETE' if processed == len(plan['requests']) else 'BUDGET_EXHAUSTED',
              'plan_sha256': plan['plan_sha256'], 'target_requests': len(plan['requests']),
              'processed_receipts': processed, 'network_calls': calls, 'reused': reused,
              'status_counts': dict(counts), 'elapsed_seconds': time.monotonic()-began,
              'publication_allowed': False, 'source_certified': False, 'test_outcomes_computed': False,
              'retry_policy': 'Preserve every attempt including errors. A reviewed new capture epoch is required to retry errors.'}
    save_json(audit/'runs'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json'), result)
    print(json.dumps(result), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--scope', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--budget', type=float, default=600)
    parser.add_argument('--max-calls', type=int, default=1000)
    parser.add_argument('--interval', type=float, default=0.35)
    args = parser.parse_args()
    if not 0 < args.budget <= 3600 or not 0 <= args.max_calls <= 10000 or args.interval < 0.2:
        parser.error('budget 0..3600, max-calls 0..10000 and interval >=0.2 required')
    scope = json.loads((args.scope/'plan.json').read_text())
    for name, field in [('footprint.parquet','footprint_sha256'), ('signal_keys.parquet','signal_keys_sha256')]:
        if digest(args.scope/name) != scope[field]:
            raise ValueError('changed_scope_artifact')
    if scope['publication_allowed'] or scope['test_outcomes_computed']:
        raise ValueError('invalid_scope_state')
    # Pin request identity and every parser/client/deadline dependency separately
    # from the already-frozen scope producer.
    manifest = {'scope_plan_sha256': digest(args.scope/'plan.json'),
                'dependencies': {name: digest(ROOT/name) for name in [
                    'research/capture_lowliq_history.py', 'research/capture_lowliq_krx_source.py',
                    'research/audit_kr_touch10_price_source.py', 'modules/kis_openapi.py',
                    'multi_agent/tools/backfill_kr_intraday.py',
                    'research/run_lowliq_touch10_reconstruction.py']},
                'request_count': len(scope['requests']), 'response_format': 'parsed provider JSON, not raw HTTP bytes',
                'publication_allowed': False, 'source_certified': False}
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out/'capture.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save_json(args.out/'manifest.json', manifest)
        scope['plan_sha256'] = digest(args.scope/'plan.json')
        from dotenv import load_dotenv
        from modules.kis_openapi import KISOpenAPIClient
        load_dotenv(args.root/'.env.local')
        os.environ['KIS_ENABLE_LIVE_CALLS'] = '1'
        os.environ['KIS_LIVE_RETRY_COUNT'] = '0'
        collect(scope, args.out, KISOpenAPIClient(timeout=10), budget=args.budget,
                max_calls=args.max_calls, interval=args.interval)


if __name__ == '__main__':
    main()
