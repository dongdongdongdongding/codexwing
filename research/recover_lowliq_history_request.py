"""One reviewed retry epoch for a fixed failed historical request, never overwrite.

The active collector and its dependency pins are unchanged. Downstream comparison
must explicitly opt into resolve_response with this plan's trusted digest.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.capture_lowliq_krx_source import inspect_payload, payload_sha
from research.run_lowliq_touch10_reconstruction import save_json
from multi_agent.tools.backfill_kr_intraday import request_deadline

REQUEST_ID = '004310_20260602_20260830_nominal'
FAILED_SHA256 = '454e5d0a9b7a5cc26cade0059e0ed5e581ea37184ff5adde3a2e839affbe03e4'
PAIRED_SHA256 = 'e096743da7751cc35bf386e4e1cd779ecc298ada214cd61624061d071b99de6c'
SCOPE_SHA256 = '096169882e8f3ef773516d7dbec19c90fb1acde8047f1df54b1e45970f35636a'
SOURCE_SHA256 = '2a5cf80053751670294f253c68ad67c68219e84a26df9291c15d5882e720e02e'
FIELDS = {'open':'stck_oprc','high':'stck_hgpr','low':'stck_lwpr','close':'stck_clpr',
          'volume':'acml_vol','amount':'acml_tr_pbmn'}


def digest(path):
    sha=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):sha.update(block)
    return sha.hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def normalized(payload):
    rows=[]
    for row in payload['output2']:
        day=datetime.strptime(row['stck_bsop_date'],'%Y%m%d').date().isoformat()
        values={k:Decimal(row[v]) for k,v in FIELDS.items()}
        if any(not v.is_finite() or v<0 for v in values.values()):
            raise ValueError('invalid_numeric_response')
        rows.append({'date':day,**{k:str(v) for k,v in values.items()}})
    if len({r['date'] for r in rows})!=len(rows):raise ValueError('duplicate_response_date')
    return sorted(rows,key=lambda r:r['date'])


def compare_rows(actual, expected):
    a={r['date']:r for r in actual};e={r['date']:r for r in expected}
    if len(a)!=len(actual) or len(e)!=len(expected) or set(a)!=set(e):
        return {'matched':False,'reason':'reference_date_mismatch'}
    differences=[{'date':d,'field':k,'actual':a[d][k],'expected':e[d][k]}
                 for d in sorted(a) for k in FIELDS if Decimal(a[d][k])!=Decimal(e[d][k])]
    return {'matched':not differences,'rows':len(a),'cells':len(a)*len(FIELDS),'differences':differences}


def verify_receipt(plan, receipt):
    if (receipt['request']!=plan['request'] or receipt['parent_failure_sha256']!=plan['parent_failure_sha256']
            or receipt['scope_plan_sha256']!=plan['scope_plan_sha256']):
        raise ValueError('changed_supplement_identity')
    if 'payload' not in receipt:
        if receipt['inspection']!={'status':'REQUEST_ERROR'}:raise ValueError('invalid_error_receipt')
        return {'accepted':False,'reason':'retry_request_error','source_certified':False}
    if payload_sha(receipt['payload'])!=receipt['payload_sha256']:raise ValueError('changed_retry_payload')
    inspection=inspect_payload(receipt['payload'],plan['request'],plan['expected_dates'])
    if inspection!=receipt['inspection']:raise ValueError('changed_retry_inspection')
    if inspection['status']!='CAPTURED':
        return {'accepted':False,'reason':'retry_not_complete','inspection':inspection,'source_certified':False}
    rows=normalized(receipt['payload'])
    reference=compare_rows(rows,plan['reference_rows'])
    paired=compare_rows(rows,plan['paired_rows'])
    return {'accepted':reference['matched'] and paired['matched'],'reference':reference,'paired':paired,
            'source_certified':False,'publication_allowed':False,'strategy_outcomes_computed':False}


def capture_retry(plan, out, client):
    save_json(out/'plan.json',plan)
    path=out/'response.json'
    calls=0
    if path.exists():
        receipt=json.loads(path.read_text())
    else:
        receipt={'request':plan['request'],'parent_failure_sha256':plan['parent_failure_sha256'],
                 'scope_plan_sha256':plan['scope_plan_sha256'],'requested_at':utc()}
        try:
            calls+=1
            with request_deadline(20):
                payload=client.daily_bars(plan['request']['code'],**{k:v for k,v in plan['request'].items() if k!='code'})
            receipt.update(payload=payload,payload_sha256=payload_sha(payload),
                           inspection=inspect_payload(payload,plan['request'],plan['expected_dates']))
        except Exception as exc:
            receipt.update(inspection={'status':'REQUEST_ERROR'},error_type=type(exc).__name__)
        receipt['received_at']=utc()
        save_json(path,receipt)
    validation=verify_receipt(plan,receipt)
    save_json(out/'validation.json',{'plan_sha256':digest(out/'plan.json'),
                                   'response_sha256':digest(path),**validation})
    return {'network_calls':calls,**validation}


def resolve_response(parent_path, supplement, *, expected_plan_sha256):
    """Opt-in resolver, preserving the failed attempt and both provenance digests."""
    if digest(supplement/'plan.json')!=expected_plan_sha256:raise ValueError('untrusted_supplement_plan')
    plan=json.loads((supplement/'plan.json').read_text())
    if digest(parent_path)!=plan['parent_failure_sha256']:raise ValueError('changed_original_failure')
    parent=json.loads(parent_path.read_text())
    if (parent.get('inspection')!={'status':'REQUEST_ERROR'} or 'payload' in parent
            or parent['request']!=plan['request'] or parent['plan_sha256']!=plan['scope_plan_sha256']):
        raise ValueError('supplement_cannot_replace_this_parent')
    receipt=json.loads((supplement/'response.json').read_text())
    validation=verify_receipt(plan,receipt)
    frozen=json.loads((supplement/'validation.json').read_text())
    expected={'plan_sha256':expected_plan_sha256,'response_sha256':digest(supplement/'response.json'),**validation}
    if frozen!=expected:raise ValueError('changed_supplement_validation')
    if validation.get('accepted') is not True:raise ValueError('supplement_not_accepted')
    return {'receipt':receipt,'provenance':{'kind':'reviewed_supplement',
        'original_status':'REQUEST_ERROR','original_sha256':plan['parent_failure_sha256'],
        'supplement_plan_sha256':expected_plan_sha256,'response_sha256':expected['response_sha256']},
        'source_certified':False,'publication_allowed':False}


def prepare(root):
    audit=root/'runtime_state/audit';parent=audit/'lowliq_history_capture_20261007'
    scope_path=audit/'lowliq_history_scope_20261007/plan.json'
    original=parent/'responses'/(REQUEST_ID+'.json')
    paired_path=parent/'responses'/REQUEST_ID.replace('_nominal','_adjusted')
    paired_path=paired_path.with_suffix('.json')
    source=audit/'kr_verified_events_v8_20261007/panel.parquet'
    for path,sha in [(scope_path,SCOPE_SHA256),(original,FAILED_SHA256),(paired_path,PAIRED_SHA256),(source,SOURCE_SHA256)]:
        if digest(path)!=sha:raise ValueError('changed_reviewed_source:'+path.name)
    parent_manifest=json.loads((parent/'manifest.json').read_text())
    for name,sha in parent_manifest['dependencies'].items():
        if digest(root/name)!=sha:raise ValueError('changed_parent_dependency')
    scope=json.loads(scope_path.read_text())
    requests=[r for r in scope['requests'] if r['id']==REQUEST_ID]
    if len(requests)!=1:raise ValueError('changed_reviewed_request')
    requested=requests[0];failed=json.loads(original.read_text());paired=json.loads(paired_path.read_text())
    identity={'code':requested['code'],'market_div':'J','period':'D','start_date':requested['start_date'],
              'end_date':requested['end_date'],'adjusted':False}
    if (failed['request']!=identity or failed['inspection']!={'status':'REQUEST_ERROR'}
            or failed['error_type']!='KISOpenAPIError' or 'payload' in failed):
        raise ValueError('not_reviewed_failure')
    if paired['request']!={**identity,'adjusted':True} or payload_sha(paired['payload'])!=paired['payload_sha256']:
        raise ValueError('changed_paired_identity')
    if inspect_payload(paired['payload'],paired['request'],requested['expected_dates'])!=paired['inspection']:
        raise ValueError('changed_paired_inspection')
    rows=pd.read_parquet(source,columns=['date',*FIELDS],filters=[('code','==',requested['code']),
        ('date','>=',pd.Timestamp(requested['start_date'])),('date','<=',pd.Timestamp(requested['end_date']))])
    reference=[{'date':pd.Timestamp(r['date']).date().isoformat(),**{k:str(r[k]) for k in FIELDS}}
               for r in rows.sort_values('date').to_dict('records')]
    pair_rows=normalized(paired['payload'])
    if not compare_rows(pair_rows,reference)['matched'] or [r['date'] for r in reference]!=requested['expected_dates']:
        raise ValueError('paired_reference_does_not_support_review')
    return original,{'request_id':REQUEST_ID,'request':identity,'scope_plan_sha256':SCOPE_SHA256,
        'parent_failure_sha256':FAILED_SHA256,'paired_response_sha256':PAIRED_SHA256,
        'reference_source_sha256':SOURCE_SHA256,'expected_dates':requested['expected_dates'],
        'reference_rows':reference,'paired_rows':pair_rows,'implementation_sha256':digest(Path(__file__)),
        'dependencies':parent_manifest['dependencies'],'maximum_network_attempts':1,
        'reason':'Reviewed request failed without payload; later one-shot same-identity supplement. '
                 'Original root cause unknown; no automatic replacement or certification.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();out=args.root/'runtime_state/audit/lowliq_history_request_recovery_20261007'
    out.mkdir(parents=True,exist_ok=True)
    with (out/'recovery.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        original,plan=prepare(args.root)
        client=None
        if not (out/'response.json').exists():
            from dotenv import load_dotenv
            from modules.kis_openapi import KISOpenAPIClient
            load_dotenv(args.root/'.env.local')
            os.environ['KIS_ENABLE_LIVE_CALLS']='1';os.environ['KIS_LIVE_RETRY_COUNT']='0'
            client=KISOpenAPIClient(timeout=10)
        result=capture_retry(plan,out,client)
        if result['accepted']:
            resolved=resolve_response(original,out,expected_plan_sha256=digest(out/'plan.json'))
            save_json(out/'resolved_provenance.json',resolved['provenance'])
        print(json.dumps(result,indent=2))
