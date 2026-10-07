"""Collect the complete fixed traded-reference review inventory in bounded runs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sys
import time
import uuid

import pandas as pd
import requests
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.capture_kr_action_documents import Capture, capture_code, HOST, KEYWORDS
from research.capture_kr_suspended_references import capture_extra
from research.recover_lowliq_history_request import digest
from research.run_lowliq_touch10_reconstruction import save_json

EVENTS_SHA='a080aa9cf180216445580658c9df2c23af28d14c10244123061554d5112be3c9'
EXTRA=('기준가격','액면','매매거래','거래정지')


def windows_for(events):
    keys=[(e['code'],e['date']) for e in events]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate_event')
    windows=[]
    for code in sorted({e['code'] for e in events}):
        selected=sorted([e for e in events if e['code']==code],key=lambda e:e['date'])
        names=sorted({n for e in selected for n in e['provider_names'] if n})
        if len(names)>1:raise ValueError('ambiguous_security_name')
        for e in selected:
            date=pd.Timestamp(e['date']);begin=date-pd.Timedelta(days=45);end=date+pd.Timedelta(days=45)
            if windows and windows[-1]['code']==code and begin<=pd.Timestamp(windows[-1]['end']):
                windows[-1]['end']=str(max(end,pd.Timestamp(windows[-1]['end'])).date());windows[-1]['event_dates'].append(e['date'])
            else:windows.append({'code':code,'name':names[0] if names else '',
                'begin':str(begin.date()),'end':str(end.date()),'event_dates':[e['date']]})
    for w in windows:w['key']=w['code']+'_'+w['begin'].replace('-','')+'_'+w['end'].replace('-','')
    return windows


def run(root,budget,max_new_windows):
    if budget<=0 or max_new_windows<=0:raise ValueError('positive_budget_required')
    audit=root/'runtime_state/audit';events_path=audit/'historical_reference_inventory_20261008/primary_review_events.json'
    if digest(events_path)!=EVENTS_SHA:raise ValueError('changed_event_inventory')
    events=json.loads(events_path.read_text());windows=windows_for(events)
    if len(events)!=287 or len({e['code'] for e in events})!=187:raise ValueError('changed_capture_scope')
    out=audit/'historical_reference_documents_20261008';out.mkdir(parents=True,exist_ok=True)
    plan={'events_sha256':EVENTS_SHA,'windows':windows,'keywords':KEYWORDS,'extra_keywords':EXTRA,
        'implementation_sha256':digest(Path(__file__)),
        'dependencies':{n:digest(ROOT/n) for n in ['research/capture_kr_action_documents.py',
            'research/capture_kr_suspended_references.py','research/run_lowliq_touch10_reconstruction.py']},
        'scope':'All fixed traded-reference candidate events, overlapping per-code ±45-calendar-day windows merged. '
            'Absent names retain ticker-only queries. Empty, partial and unvisited windows are unresolved; no price or outcome inference.'}
    with (out/'capture.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);save_json(out/'plan.json',plan)
        session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0',
            'Referer':HOST+'/disclosure/details.do?method=searchDetailsMain','X-Requested-With':'XMLHttpRequest'})
        started=datetime.now(timezone.utc).isoformat();deadline=time.monotonic()+budget
        results=[];calls=0;new_windows=0;stop='ALL_WINDOWS_ATTEMPTED';failure=None
        for w in windows:
            dest=out/(w['key']+'_result.json');is_new=not dest.exists()
            if is_new and (new_windows>=max_new_windows or time.monotonic()>=deadline):
                stop='BUDGET_EXHAUSTED';break
            capture=Capture(out/w['key'],session,deadline-time.monotonic())
            try:
                capture.fetch('search_main',HOST+'/disclosure/details.do',params={'method':'searchDetailsMain'})
                result=capture_code(capture,w,w['begin'],w['end'])
                extras=[r for r in result['records'] if not r['selected'] and any(k in r['title'] for k in EXTRA)]
                for record in extras:result['documents'].append(capture_extra(capture,w['code'],record))
                result['expanded_selected_count']=result['selected_count']+len(extras)
                result['window']=w
                save_json(dest,result);results.append({'window':w['key'],'status':result['status'],
                    'disclosures':result['total_disclosures'],'selected':result['expanded_selected_count']})
                new_windows+=int(is_new)
                print(json.dumps({**results[-1],'network_calls':capture.requests}),flush=True)
            except TimeoutError:
                stop='BUDGET_EXHAUSTED';break
            except Exception as exc:
                stop='CAPTURE_FAILED';failure={'window':w['key'],'error_type':type(exc).__name__,'reason':str(exc)[:250]};break
            finally:calls+=capture.requests
        summary={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'status':stop,
            'target_windows':len(windows),'processed_windows':len(results),'new_windows':new_windows,
            'unvisited_windows':len(windows)-len(results),'network_calls':calls,'failure':failure,
            'statuses':dict(Counter(r['status'] for r in results)),'results':results,
            'source_certified':False,'publication_allowed':False,'strategy_outcomes_computed':False}
        save_json(out/'runs'/(uuid.uuid4().hex+'.json'),summary)
        print(json.dumps({k:v for k,v in summary.items() if k!='results'}),flush=True);return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--budget',type=float,default=1800);p.add_argument('--max-new-windows',type=int,default=1000)
    args=p.parse_args();run(args.root,args.budget,args.max_new_windows)
