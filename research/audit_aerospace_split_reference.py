"""Verify the omitted 2024 Aerospace resumption auction without wealth claims."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_lowliq_history_references import body_text, signed_reference
from research.compare_indexed_lowliq_history import indexed_receipt
from research.recover_lowliq_history_request import digest
from research.run_lowliq_touch10_reconstruction import save_json

SOURCE_SHA='86c7f56e91261f3d8c8c770aaa6b8a5e9079bfa221ef80525e7f490d73b6dd53'
INDEX_SHA='f2c4b3d6831ae9e370cc8b82e2619dd8c71f3520bc97383c00fd1beeb7c54c8d'
DOCUMENTS={
 'method':('012450_20240926000330_20240926000924_body_0','9f2cdd90f348b6178a273572e95307ec0088282a2f9a21330d089e3a3f97bbd5'),
 'listing':('012450_20240924000043_20240924000088_body_0','3da9194989bcf3f91b72503259e1580a49927a1d05a207aaf9b01d8eea45f5a6'),
}


def verify_boundary(raw,quote,texts):
    if set(raw.code)!={'012450'} or raw.date.duplicated().any():raise ValueError('wrong_source_identity')
    if not all(t in texts['method'] for t in ['한화에어로스페이스','보통주식','2024-09-27',
        '평가가격(원)','290,000','580,000','145,000','회사분할',
        '단일가격에 의한 매매방식으로 결정된 최초가격이 기준가격이 됨']):raise ValueError('wrong_auction_method')
    if not all(t in texts['listing'] for t in ['A012450','KR7012450003','50,630,000','45,581,161',
        '2024년09월27일','회사분할(존속)']):raise ValueError('wrong_final_listing')
    pair=raw[raw.date.le('2024-09-27')].sort_values('date').tail(2)
    if len(pair)!=2 or pair.date.iloc[-1]!=pd.Timestamp('2024-09-27'):raise ValueError('missing_boundary')
    previous,current=pair.iloc[0],pair.iloc[1]
    if (previous.close!=290000 or current.close!=317000 or current.open!=300000 or current.volume<=0
        or previous.stocks!=50630000 or current.stocks!=45581161):raise ValueError('changed_boundary')
    if previous.adj_factor!=1 or current.adj_factor!=1:raise ValueError('changed_missing_factor')
    if (F(quote['stck_clpr'])!=317000 or F(quote['stck_oprc'])!=300000 or signed_reference(quote)!=300000
        or F(quote['acml_vol'])!=F(str(current.volume))):raise ValueError('unproved_actual_auction')
    return {'id':'012450_2024-09-27','code':'012450','date':'2024-09-27','kind':'auction',
        'reference_price':300000,'prior_close':290000,'first_close':317000,'before_factor':1.,
        'old_event_factor':1.,'multiplier_numerator':29,'multiplier_denominator':30,
        'interpretation':'Actual resumption auction, not evaluated price or event close; separate split assets unresolved.'}


def run(root):
    a=root/'runtime_state/audit';source=a/'kr_verified_events_v10_20261008/panel.parquet'
    index_path=a/'lowliq_history_coverage_indices/index_20261007T141833378696.json';scope_path=a/'lowliq_history_scope_20261007/plan.json'
    if digest(source)!=SOURCE_SHA or digest(index_path)!=INDEX_SHA:raise ValueError('changed_frozen_inputs')
    scope=json.loads(scope_path.read_text());index=json.loads(index_path.read_text());scope_sha=digest(scope_path)
    if scope_sha!=index['scope_plan_sha256']:raise ValueError('changed_scope')
    hashes={str(source):SOURCE_SHA,str(index_path):INDEX_SHA,str(scope_path):scope_sha};texts={}
    corpus=a/'aerospace_split_documents_20261008'
    for key,(stem,sha) in DOCUMENTS.items():
        if digest(corpus/'aerospace_202409/captures'/(stem+'.json'))!=sha:raise ValueError('changed_primary_receipt')
        texts[key]=body_text(corpus,'aerospace_202409',stem,hashes)
    entries={e['request_id']:e for e in index['entries']};quotes={};names=set()
    for q in scope['requests']:
        if q['code']!='012450' or q['basis']!='nominal':continue
        e=entries[q['id']];item=indexed_receipt(e,q,scope_sha,a/'lowliq_history_capture_20261007')
        if item['inspection']['status']!='CAPTURED':raise ValueError('incomplete_scope')
        hashes[e['effective_path']]=e['effective_sha256'];names.add(item['payload']['output1']['hts_kor_isnm'])
        for row in item['payload']['output2']:
            day=pd.Timestamp(row['stck_bsop_date']).strftime('%Y-%m-%d')
            if day in q['expected_dates']:
                if day in quotes:raise ValueError('overlapping_dates')
                quotes[day]=row
    if names!={'한화에어로스페이스'}:raise ValueError('wrong_provider_identity')
    event=verify_boundary(pd.read_parquet(source,filters=[('code','==','012450')]),quotes['2024-09-27'],texts)
    result={'events':[event],'input_sha256':hashes,'implementation_sha256':digest(Path(__file__)),
        'dependencies':{n:digest(ROOT/n) for n in ['research/audit_lowliq_history_references.py',
            'research/compare_indexed_lowliq_history.py','research/capture_lowliq_krx_source.py']},
        'source_certified':False,'portfolio_return_certified':False,'point_in_time_certified':False,
        'publication_allowed':False,'strategy_outcomes_computed':False,
        'ownership_limitations':'Surviving shares fall from 50,630,000 to 45,581,161; new-company assets, fractions and actual availability are not modeled.'}
    out=a/'aerospace_split_evidence_20261008';save_json(out/'verification.json',result)
    print(json.dumps({'verification_sha256':digest(out/'verification.json'),'events':1}));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
