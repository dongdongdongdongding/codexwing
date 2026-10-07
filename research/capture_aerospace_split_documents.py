"""Capture the earlier Aerospace split identified in the fixed historical comparison."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.capture_kr_action_documents import Capture, capture_code, HOST, KEYWORDS
from research.capture_kr_suspended_references import capture_extra
from research.recover_lowliq_history_request import digest
from research.run_lowliq_touch10_reconstruction import save_json

WINDOWS=[{'key':'aerospace_202409','code':'012450','name':'한화에어로스페이스','begin':'2024-08-01','end':'2024-10-31'}]
CODES={'012450'}
QUEUE_SHA='fc2ecd482c820ab18abf7901e1c9d0603620fae0ea2a6165b778c2aaf70cf7b4'



def run(root):
    audit=root/'runtime_state/audit';summary=audit/'lowliq_history_indexed_comparison_v10_20261008/source_review_queue.json'
    if digest(summary)!=QUEUE_SHA or not CODES.issubset({r['code'] for r in json.loads(summary.read_text())['worst_examples']}):
        raise ValueError('changed_fixed_source_cohort')
    out=audit/'aerospace_split_documents_20261008';out.mkdir(parents=True,exist_ok=True)
    plan={'windows':WINDOWS,'diagnostic_sha256':QUEUE_SHA,'security_codes':sorted(CODES),'keywords':KEYWORDS,
          'extra_keywords':['기준가격','액면','매매거래','거래정지'],
          'implementation_sha256':digest(Path(__file__)),
          'dependencies':{name:digest(ROOT/name) for name in ['research/capture_kr_action_documents.py',
            'research/capture_kr_suspended_references.py','research/run_lowliq_touch10_reconstruction.py']},
          'scope':'Fixed source discrepancies, all matching action disclosures within the fixed August-October 2024 window. '
                  'No strategy outcomes, whole-source or economic certification.'}
    with (out/'capture.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);save_json(out/'plan.json',plan)
        session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0',
            'Referer':HOST+'/disclosure/details.do?method=searchDetailsMain','X-Requested-With':'XMLHttpRequest'})
        results=[];calls=0
        for target in WINDOWS:
            capture=Capture(out/target['key'],session,600)
            capture.fetch('search_main',HOST+'/disclosure/details.do',params={'method':'searchDetailsMain'})
            result=capture_code(capture,target,target['begin'],target['end'])
            extras=[r for r in result['records'] if not r['selected'] and any(w in r['title'] for w in plan['extra_keywords'])]
            for record in extras:result['documents'].append(capture_extra(capture,target['code'],record))
            result['expanded_selected_count']=result['selected_count']+len(extras)
            result['window_key']=target['key'];save_json(out/(target['key']+'_result.json'),result)
            results.append(result);calls+=capture.requests
            print(json.dumps({'window':target['key'],'status':result['status'],'disclosures':result['total_disclosures'],
                  'selected':result['expanded_selected_count'],'network_calls':capture.requests}),flush=True)
        complete=all(r['status']=='complete' and len(r['documents'])==r['expanded_selected_count'] for r in results)
        final={'status':'captured' if complete else 'partial','results':results,'source_certified':False,
               'publication_allowed':False,'strategy_outcomes_computed':False}
        save_json(out/'result.json',final);print(json.dumps({'status':final['status'],'network_calls':calls}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
