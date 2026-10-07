"""Capture primary disclosures around fixed historical price discontinuities.

The cohort is fixed from prefix972 source diagnostics, not strategy performance.
Common-company search keys for preferred shares are search hypotheses; only a
matching security code/ISIN in a body can establish the affected share class.
"""
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
from research.capture_kr_action_documents import Capture,capture_code,HOST,KEYWORDS
from research.capture_kr_suspended_references import capture_extra

COHORT=[
    {'key':'krmotors_202403','code':'000040','name':'KR모터스','affected':['000040'],'begin':'2023-12-01','end':'2024-04-15'},
    {'key':'samyang_202511','code':'000070','name':'삼양홀딩스','affected':['000070'],'begin':'2025-10-01','end':'2025-12-15'},
    {'key':'yuhan_202312','code':'000100','name':'유한양행','affected':['000100','000105'],'begin':'2023-11-01','end':'2024-02-15'},
    {'key':'hite_202401','code':'000140','name':'하이트진로홀딩스','affected':['000145'],'begin':'2023-12-01','end':'2024-02-15'},
    {'key':'dhauto_202601','code':'000300','name':'DH오토넥스','affected':['000300'],'begin':'2025-11-01','end':'2026-02-15'},
    {'key':'noru_202503','code':'000320','name':'노루홀딩스','affected':['000325'],'begin':'2025-02-01','end':'2025-04-15'},
    {'key':'noru_202609','code':'000320','name':'노루홀딩스','affected':['000325'],'begin':'2026-08-01','end':'2026-09-30'},
    {'key':'gaon_202606','code':'000500','name':'가온전선','affected':['000500'],'begin':'2026-05-01','end':'2026-07-31'},
]
EXTRA=('기준가격','액면','매매거래','거래정지')


def run(root,budget):
    audit=root/'runtime_state/audit';prefix=audit/'lowliq_history_capture_20261007/diagnostics/prefix_972'
    diagnostic=json.loads((prefix/'comparable_diagnostics.json').read_text())
    expected=sorted({c for target in COHORT for c in target['affected']})
    if diagnostic['comparable_codes_over_one_krw_plus_float']!=expected:
        raise ValueError('changed_fixed_cohort')
    out=audit/'lowliq_history_actions_20261007';out.mkdir(parents=True,exist_ok=True)
    plan={'cohort':COHORT,'base_keywords':KEYWORDS,'extra_keywords':EXTRA,
          'diagnostic_sha256':digest(prefix/'comparable_diagnostics.json'),
          'prefix_plan_sha256':digest(prefix/'plan.json'),
          'implementation_sha256':digest(Path(__file__)),
          'dependencies':{name:digest(ROOT/name) for name in ['research/capture_kr_action_documents.py',
              'research/capture_kr_suspended_references.py','research/run_lowliq_touch10_reconstruction.py']},
          'scope':'Fixed windows around observed price-basis discontinuities, all matching disclosures in each window. '
                  'Not complete company history, proof of no corporate action, preferred identity or historical PIT.',
          'source_certified':False,'publication_allowed':False,'test_outcomes_computed':False}
    with (out/'capture.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);save_json(out/'plan.json',plan)
        session=requests.Session();session.headers.update({'User-Agent':'Mozilla/5.0',
            'Referer':HOST+'/disclosure/details.do?method=searchDetailsMain','X-Requested-With':'XMLHttpRequest'})
        results=[];calls=0
        for target in COHORT:
            capture=Capture(out/target['key'],session,budget)
            capture.fetch('search_main',HOST+'/disclosure/details.do',params={'method':'searchDetailsMain'})
            result=capture_code(capture,target,target['begin'],target['end'])
            extras=[r for r in result['records'] if not r['selected'] and any(word in r['title'] for word in EXTRA)]
            for record in extras:
                result['documents'].append(capture_extra(capture,target['code'],record))
            result['additional_reference_titles']=extras
            result['expanded_selected_count']=result['selected_count']+len(extras)
            result['window_key']=target['key']
            save_json(out/(target['key']+'_result.json'),result);results.append(result);calls+=capture.requests
            print(json.dumps({'window':target['key'],'status':result['status'],'disclosures':result['total_disclosures'],
                              'selected':result['expanded_selected_count'],'network_calls':capture.requests}),flush=True)
        complete=all(r['status']=='complete' and len(r['documents'])==r['expanded_selected_count'] for r in results)
        result={'status':'captured' if complete else 'partial','results':results,
                'source_certified':False,'publication_allowed':False,'test_outcomes_computed':False}
        save_json(out/'result.json',result)
        print(json.dumps({'status':result['status'],'network_calls':calls,'windows':len(results)}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--budget-per-window',type=float,default=300);args=p.parse_args()
    if not 0<args.budget_per_window<=900:p.error('window budget must be 0..900 seconds')
    run(args.root,args.budget_per_window)
