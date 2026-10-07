"""One reviewed same-identity recovery for 102460; preserve its original error."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.recover_lowliq_history_request import (
    digest,normalized,compare_rows,capture_retry,resolve_response,FIELDS,SCOPE_SHA256)
from research.capture_lowliq_krx_source import payload_sha,inspect_payload
from research.run_lowliq_touch10_reconstruction import save_json

REQUEST_ID='102460_20250607_20250904_nominal'
FAILED_SHA256='a937a7c60216cf812fd57e975ca904d4141f531d81cf4ed3c653fa0335fc93ac'
PAIRED_SHA256='aad3a6d655df0487eda9468a6c12ec133cdbe15d0b3d4c05f06a09c32585102f'
SOURCE_SHA256='b574338c410d620dd6802473aa9066254838158dac2604bd57692ea470c28116'


def prepare(root):
    audit=root/'runtime_state/audit';parent=audit/'lowliq_history_capture_20261007'
    scope_path=audit/'lowliq_history_scope_20261007/plan.json'
    original=parent/'responses'/(REQUEST_ID+'.json')
    paired_path=parent/'responses'/REQUEST_ID.replace('_nominal','_adjusted')
    paired_path=paired_path.with_suffix('.json')
    source=audit/'kr_verified_events_v13_20261008/panel.parquet'
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
        'dependencies':parent_manifest['dependencies'],
        'retry_protocol_sha256':digest(ROOT/'research/recover_lowliq_history_request.py'),'maximum_network_attempts':1,
        'reason':'Reviewed request failed without payload; later one-shot same-identity supplement. '
                 'Original root cause unknown; no automatic replacement or certification.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();out=args.root/'runtime_state/audit/lowliq_history_102460_recovery_20261008'
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
    sys.exit(0 if result['accepted'] else 2)
