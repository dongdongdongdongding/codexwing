"""Add explicit missing titles and issuer-scope queries without rewriting base captures."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import requests
from research.audit_kr_adjustment_asof import digest
from research.run_lowliq_touch10_reconstruction import save_json
from research.capture_kr_action_documents import Capture, HOST, document_numbers, body_paths, capture_code


def capture_document(capture, code, record):
    stem=code+'_'+record['acptno']
    viewer=capture.fetch(stem+'_viewer',HOST+'/common/disclsviewer.do',params={'method':'search','acptno':record['acptno']})
    numbers=document_numbers(viewer);bodies=[]
    for number in numbers:
        prefix=stem+'_'+number
        route=capture.fetch(prefix+'_routing',HOST+'/common/disclsviewer.do',params={'method':'searchContents','docNo':number})
        for i,path in enumerate(body_paths(route)):
            key=prefix+'_body_'+str(i);capture.fetch(key,HOST+path);bodies.append(key)
    return {**record,'query_code':code,'document_numbers':numbers,'body_keys':bodies}


def run(root):
    base=root/'runtime_state/audit/kr_remaining_action_documents_20261007'
    out=base/'supplement';out.mkdir(exist_ok=True)
    first=base/'first_result.json'
    if not first.exists():save_json(first,json.loads((base/'result.json').read_text()))
    original=json.loads(first.read_text());extra=[]
    for item in original['results']:
        failed={r['acptno'] for r in item.get('document_errors',[])}
        for record in item.get('records',[]):
            if record['acptno'] in failed or (not record['selected'] and any(w in record['title'] for w in ['액면','기준가격'])):
                extra.append({'code':item['code'],'record':record,'reason':'retry_failed_public_document' if record['acptno'] in failed else 'expanded_title_coverage'})
    plan={'base_result_sha256':digest(first),'base_plan_sha256':digest(base/'plan.json'),
        'implementation_sha256':digest(Path(__file__)),'capture_implementation_sha256':digest(ROOT/'research/capture_kr_action_documents.py'),
        'documents':extra,'issuer_scope_queries':[{'code':'000880','name':'한화','security_under_review':'00088K'}],
        'scope':'Additional public source capture. Issuer query is a hypothesis, not an automatic preferred-share alias or economic certificate.'}
    with (out/'capture.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);save_json(out/'plan.json',plan)
        session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0','Referer':HOST+'/disclosure/details.do?method=searchDetailsMain','X-Requested-With':'XMLHttpRequest'})
        capture=Capture(out,session,600)
        capture.fetch('search_main',HOST+'/disclosure/details.do',params={'method':'searchDetailsMain'})
        results=[]
        for item in extra:
            try:result={'status':'captured','reason':item['reason'],'document':capture_document(capture,item['code'],item['record'])}
            except Exception as exc:result={'status':'failed','request':item,'error_type':type(exc).__name__,'reason':str(exc)[:250]}
            results.append(result)
        issuer_results=[]
        for target in plan['issuer_scope_queries']:
            issuer_results.append(capture_code(capture,target,'2026-06-01','2026-10-07'))
        result={'documents':results,'issuer_scope_results':issuer_results,'requests':capture.requests,'source_certified':False}
        save_json(out/'result.json',result)
        print(json.dumps({'extra_documents':len(results),'statuses':{s:sum(r['status']==s for r in results) for s in {r['status'] for r in results}},'issuer_results':[{k:v for k,v in r.items() if k not in ['records','documents']} for r in issuer_results],'requests':capture.requests},ensure_ascii=False),flush=True)
        return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    run(parser.parse_args().root)
