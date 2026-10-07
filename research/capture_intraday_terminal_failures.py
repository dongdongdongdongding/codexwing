"""Read-only, immutable capture for the reviewed October 7 20:55 failure cohort.

Seven exact failed requests plus all four query windows for the three existing
invalid-cache codes. Fresh payloads cannot prove the original unsaved failures.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.recover_lowliq_history_request import digest
from research.capture_lowliq_krx_source import payload_sha
from research.run_lowliq_touch10_reconstruction import save_json
from modules.kis_operational_adapter import normalize_kis_minute_bars
from multi_agent.tools.backfill_kr_intraday import filter_bars, request_deadline, HOURS

REPORT_SHA = '99aef45f30c266c5828b4794d32aef8a4845284ce805057e7a05daf162b303bb'
DEPENDENCIES = {
    'modules/kis_openapi.py':'3d31bea79b3c39c072fc322682786d15ef483a4b2f0a4c126eef62242f257b54',
    'modules/kis_operational_adapter.py':'44cb95cae591316b2be752bdf5fbe607e938fbe9a0f3687cc8dad7014e601f34',
    'multi_agent/tools/backfill_kr_intraday.py':'5f713fbf90aa00a19ece493b8a011cf758f196daf694ec22842d4d67c7843fe8',
}


def request_scope(report):
    if report['run_id'] != '20261007T205547317819':
        raise ValueError('changed_run')
    requests = {(r['code'],r['day'],r['hour']) for r in report['request_errors']}
    if len(requests)!=7 or {r['code'] for r in report['storage_errors']}!={'011230','013000','014130'}:
        raise ValueError('changed_failure_scope')
    requests.update((code,'20260923',hour) for code in ['011230','013000','014130'] for hour in HOURS)
    return [{'code':c,'day':d,'hour':h} for c,d,h in sorted(requests)]


def inspect(request, payload):
    if payload.get('rt_cd')!='0':
        return {'status':'PROVIDER_ERROR'}
    try:
        frame=filter_bars(normalize_kis_minute_bars(request['code'],payload,trade_date=request['day']),request['day'])
    except Exception as exc:
        return {'status':'INVALID_OHLCV'} if str(exc)=='invalid_minute_OHLCV' else {
            'status':'PARSE_ERROR','error_type':type(exc).__name__}
    return {'status':'VALID_SLICE' if len(frame) else 'EMPTY_SLICE','rows':len(frame)}


def capture(plan, out, client, *, pause=time.sleep):
    save_json(out/'plan.json',plan)
    calls=0; statuses={}
    for request in plan['requests']:
        path=out/'responses'/('{code}_{day}_{hour}.json'.format(**request))
        if path.exists():
            item=json.loads(path.read_text())
        else:
            item={'request':request,'plan_sha256':digest(out/'plan.json'),
                  'requested_at':datetime.now(timezone.utc).isoformat()}
            try:
                calls+=1
                with request_deadline(20):
                    payload=client.daily_minute_bars(request['code'],trade_date=request['day'],
                            input_hour=request['hour'],include_past=True)
                item.update(payload=payload,payload_sha256=payload_sha(payload))
                item['inspection']=inspect(request,payload)
            except Exception as exc:
                # Retain any received payload above; never persist exception text
                # that could include tokens or the full request URL.
                item.update(error_type=type(exc).__name__,inspection={'status':'REQUEST_ERROR'})
            item['received_at']=datetime.now(timezone.utc).isoformat()
            save_json(path,item);pause(.35)
        if item['request']!=request or item['plan_sha256']!=digest(out/'plan.json'):
            raise ValueError('changed_capture_identity')
        if 'payload' in item:
            if payload_sha(item['payload'])!=item['payload_sha256']:raise ValueError('changed_capture_payload')
            if inspect(request,item['payload'])!=item['inspection']:raise ValueError('changed_capture_inspection')
        elif item['inspection']!={'status':'REQUEST_ERROR'}:
            raise ValueError('missing_payload')
        status=item['inspection']['status'];statuses[status]=statuses.get(status,0)+1
    summary={'requests':len(plan['requests']),'status_counts':statuses,'cache_modified':False,
             'original_failure_cause_proved':False,'source_certified':False}
    save_json(out/'summary.json',summary)
    return {'network_calls_this_run':calls,**summary}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    args=p.parse_args();audit=args.root/'runtime_state/audit/intraday_terminal_20261007_205547'
    report=audit/'original_report.json';out=audit/'fresh_capture';out.mkdir(parents=True,exist_ok=True)
    with (out/'capture.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if digest(report)!=REPORT_SHA:raise ValueError('changed_terminal_report')
        for name,sha in DEPENDENCIES.items():
            if digest(args.root/name)!=sha:raise ValueError('changed_dependency')
        plan={'source_report_sha256':REPORT_SHA,'dependencies':DEPENDENCIES,
              'implementation_sha256':digest(Path(__file__)),'requests':request_scope(json.loads(report.read_text())),
              'purpose':'Exact failed requests and four query windows for three invalid-cache dates; read-only, one attempt per identity.'}
        client=None
        if any(not (out/'responses'/('{code}_{day}_{hour}.json'.format(**r))).exists() for r in plan['requests']):
            from dotenv import load_dotenv
            from modules.kis_openapi import KISOpenAPIClient
            load_dotenv(args.root/'.env.local');os.environ['KIS_ENABLE_LIVE_CALLS']='1';os.environ['KIS_LIVE_RETRY_COUNT']='0'
            client=KISOpenAPIClient(timeout=10)
        print(json.dumps(capture(plan,out,client),indent=2))
