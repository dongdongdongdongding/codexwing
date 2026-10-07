"""Freeze captured-response coverage with explicit reviewed supplements.

Read-only index of a snapshot of already published immutable receipt paths. The
collector may continue independently; files appearing after enumeration are
outside this index. This is availability, not economic/source certification.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.recover_lowliq_history_request import digest,resolve_response
from research.capture_lowliq_krx_source import inspect_payload,payload_sha
from research.run_lowliq_touch10_reconstruction import save_json


def build_index(scope_path,capture,*,supplements=()):
    scope=json.loads(scope_path.read_text());scope_sha=digest(scope_path)
    manifest=json.loads((capture/'manifest.json').read_text())
    if manifest['scope_plan_sha256']!=scope_sha:raise ValueError('capture_scope_mismatch')
    requests={r['id']:r for r in scope['requests']}
    if len(requests)!=len(scope['requests']):raise ValueError('duplicate_scope_request')
    # Freeze path membership first, then validate immutable contents. This is not
    # a live directory total and does not claim the current writer has finished.
    paths=sorted((capture/'responses').glob('*.json'))
    supplied={s['request_id']:s for s in supplements}
    if len(supplied)!=len(supplements):raise ValueError('duplicate_supplement')
    if set(supplied)-set(requests):raise ValueError('supplement_outside_scope')
    original_counts=Counter();effective_counts=Counter();rows=[];used=set()
    for path in paths:
        key=path.stem
        if key not in requests:raise ValueError('receipt_outside_frozen_scope')
        request=requests[key]
        identity={'code':request['code'],'market_div':'J','period':'D','start_date':request['start_date'],
                  'end_date':request['end_date'],'adjusted':request['basis']=='adjusted'}
        receipt=json.loads(path.read_text())
        if receipt['request']!=identity or receipt['plan_sha256']!=scope_sha:
            raise ValueError('changed_original_identity')
        original_status=receipt['inspection']['status']
        original_counts[original_status]+=1
        provenance={'kind':'original','original_sha256':digest(path)}
        effective_path=path
        if key in supplied:
            item=supplied[key]
            resolved=resolve_response(path,Path(item['directory']),expected_plan_sha256=item['plan_sha256'])
            receipt=resolved['receipt'];provenance=resolved['provenance']
            effective_path=Path(item['directory'])/'response.json';used.add(key)
        if 'payload' in receipt:
            if payload_sha(receipt['payload'])!=receipt['payload_sha256']:raise ValueError('changed_payload')
            rebuilt=inspect_payload(receipt['payload'],identity,request['expected_dates'])
            if rebuilt!=receipt['inspection']:raise ValueError('changed_inspection')
        elif receipt['inspection']!={'status':'REQUEST_ERROR'}:
            raise ValueError('unexplained_missing_payload')
        effective_status=receipt['inspection']['status'];effective_counts[effective_status]+=1
        rows.append({'request_id':key,'original_path':str(path),'original_status':original_status,
                     'effective_path':str(effective_path),'effective_status':effective_status,
                     'effective_sha256':digest(effective_path),'provenance':provenance})
    if used!=set(supplied):raise ValueError('supplement_parent_not_in_snapshot')
    return {'scope_plan_sha256':scope_sha,'capture_manifest_sha256':digest(capture/'manifest.json'),
            'target_requests':len(requests),'snapshot_receipts':len(paths),
            'unvisited_at_snapshot':len(requests)-len(paths),'original_status_counts':dict(original_counts),
            'effective_status_counts':dict(effective_counts),'reviewed_supplements_used':sorted(used),
            'entries':rows,'source_certified':False,'publication_allowed':False,'strategy_outcomes_computed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--supplement',type=Path)
    p.add_argument('--supplement-plan-sha256')
    args=p.parse_args();audit=args.root/'runtime_state/audit'
    if bool(args.supplement)!=bool(args.supplement_plan_sha256):p.error('supplement and trusted plan digest required together')
    supplements=[]
    if args.supplement:
        plan=json.loads((args.supplement/'plan.json').read_text())
        supplements=[{'request_id':plan['request_id'],'directory':str(args.supplement),
                      'plan_sha256':args.supplement_plan_sha256}]
    result=build_index(audit/'lowliq_history_scope_20261007/plan.json',
                       audit/'lowliq_history_capture_20261007',supplements=supplements)
    result['implementation_sha256']=digest(Path(__file__))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    path=audit/'lowliq_history_coverage_indices'/('index_'+stamp+'.json')
    save_json(path,result)
    print(json.dumps({'path':str(path),'sha256':digest(path),
                      **{k:v for k,v in result.items() if k!='entries'}},indent=2))
