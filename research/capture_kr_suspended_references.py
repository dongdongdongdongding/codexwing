"""Capture the six nontrading-history residual codes revealed by the v6 audit."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.run_lowliq_touch10_reconstruction import save_json
from research.capture_kr_action_documents import Capture,capture_code,document_numbers,body_paths,HOST

CODES=['002210','051360','079190','175250','210120','214330']


def capture_extra(capture,code,record):
    stem=code+'_'+record['acptno']
    viewer=capture.fetch(stem+'_viewer',HOST+'/common/disclsviewer.do',
        params={'method':'search','acptno':record['acptno']})
    numbers=document_numbers(viewer);bodies=[]
    for number in numbers:
        prefix=stem+'_'+number
        routing=capture.fetch(prefix+'_routing',HOST+'/common/disclsviewer.do',
            params={'method':'searchContents','docNo':number})
        for i,path in enumerate(body_paths(routing)):
            key=prefix+'_body_'+str(i);capture.fetch(key,HOST+path);bodies.append(key)
    return {**record,'document_numbers':numbers,'body_keys':bodies}


def run(root,budget):
    audit=root/'runtime_state/audit';out=audit/'kr_suspended_references_20261007';out.mkdir(exist_ok=True)
    comparison=audit/'kr_v6_full_cohort_20261007';intervals=json.loads((comparison/'intervals.json').read_text())
    residual=[r['code'] for r in intervals if float(r['relative_gap'])>1e-12]
    if residual!=CODES:raise ValueError('changed_suspended_residual_scope')
    original=json.loads((audit/'lowliq_krx_comparison_20261007/plan.json').read_text());cohort=[]
    for code in CODES:
        p=audit/'lowliq_krx_source_20261007/responses'/f'{code}_nominal.json'
        if digest(p)!=original['response_sha256'][code+'_nominal']:raise ValueError('changed_identity_source')
        cohort.append({'code':code,'name':json.loads(p.read_text())['payload']['output1']['hts_kor_isnm'],
                       'identity_response_sha256':digest(p)})
    plan={'cohort':cohort,'from':'2026-06-01','through':'2026-10-07',
        'selection':'Original corporate-action keywords plus all reference-price and par-value titles',
        'intervals_sha256':digest(comparison/'intervals.json'),'implementation_sha256':digest(Path(__file__)),
        'capture_helper_sha256':digest(ROOT/'research/capture_kr_action_documents.py'),
        'scope':'Current observed official disclosures for all six nontrading-history residual codes. No correction, historical PIT or performance claim.'}
    with (out/'capture.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);save_json(out/'plan.json',plan)
        session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0',
            'Referer':HOST+'/disclosure/details.do?method=searchDetailsMain','X-Requested-With':'XMLHttpRequest'})
        capture=Capture(out,session,budget)
        for p in (out/'captures').glob('*.json'):capture.verify(p.stem)
        capture.fetch('search_main',HOST+'/disclosure/details.do',params={'method':'searchDetailsMain'})
        results=[]
        for target in cohort:
            result=capture_code(capture,target,plan['from'],plan['through'])
            extras=[r for r in result['records'] if not r['selected'] and any(s in r['title'] for s in ['기준가격','액면'])]
            result['additional_reference_titles']=extras
            for record in extras:result['documents'].append(capture_extra(capture,target['code'],record))
            result['expanded_selected_count']=result['selected_count']+len(extras)
            save_json(out/(target['code']+'_result.json'),result);results.append(result)
            print(json.dumps({'code':target['code'],'status':result['status'],'disclosures':result['total_disclosures'],
                'selected':result['expanded_selected_count'],'requests':capture.requests}),flush=True)
        complete=all(r['status']=='complete' and len(r['documents'])==r['expanded_selected_count'] for r in results)
        result={'status':'captured' if complete else 'partial','results':results,'source_certified':False,
                'strategy_outcomes_computed':False,'implementation_sha256':digest(Path(__file__))}
        save_json(out/'result.json',result)
        print(json.dumps({'status':result['status'],'requests_this_run':capture.requests,
            'codes':len(results),'disclosures':sum(r['total_disclosures'] for r in results),
            'selected':sum(r['expanded_selected_count'] for r in results)}),flush=True)
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--budget',type=float,default=900);args=p.parse_args();run(args.root,args.budget)
