"""Verify two official DS Dansuk reference prices without certifying wealth."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import sys

import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.recover_lowliq_history_request import digest
from research.compare_indexed_lowliq_history import indexed_receipt
from research.audit_lowliq_history_references import body_text, signed_reference
from research.run_lowliq_touch10_reconstruction import save_json

SOURCE_SHA='2a5cf80053751670294f253c68ad67c68219e84a26df9291c15d5882e720e02e'
INDEX_SHA='f2c4b3d6831ae9e370cc8b82e2619dd8c71f3520bc97383c00fd1beeb7c54c8d'
DOCUMENTS={
 'bonus_reference':('bonus_202411','017860_20241122000304_20241122000873_body_0','28b4b1a907ea7ac4a07a56cad8675dd810487b899f43815147b68492140ba1c6'),
 'bonus_decision':('bonus_202411','017860_20241111000186_20241111000466_body_1','d8fd4ee38b5141020e4245d363f4ae44e530f6ada1f45034ddc0a9210879b19d'),
 'bonus_listing':('bonus_202411','017860_20241219000042_20241219000100_body_0','c1460f4e121a531063dd5084bfcfdd7628fd18065d1fc0a680874c0019967898'),
 'dividend_reference':('stock_dividend_202512','017860_20251226000708_20251226002084_body_0','e9accc540a7e3b0750d47321f099f3bbe86f32ad370d162aa1df10dd9c8f3a3f'),
 'stock_dividend_decision':('stock_dividend_202512','017860_20251216000781_20251127001015_body_0','c6d96baf687d7f621759b3fc356a0708ceace6bc8dbf3df5673aa2aadf1a1f75'),
 'cash_dividend_decision':('stock_dividend_202512','017860_20251216000818_20251127001072_body_0','c3b3bcc1a8aeedd5f42cff9eb31dd07ae85f083a9cc67676805f88759be06d05'),
}
EVENTS=[('2024-11-25',42950,128800,55800,'bonus_reference','권리락(무상증자)'),
        ('2025-12-29',18420,18600,18270,'dividend_reference','주식배당')]


def verify_reference_events(raw,nominal,texts):
    if set(raw.code)!= {'017860'}:raise ValueError('wrong_security')
    if raw.date.duplicated().any():raise ValueError('duplicate_source_dates')
    raw=raw.sort_values('date');events=[]
    for day,reference,prior,close,key,reason in EVENTS:
        text=' '.join(texts[key].split())
        if not all(token in text for token in ['DS단석',day,'보통주식',f'{reference:,}',reason]):
            raise ValueError('wrong_official_reference')
        pair=raw[raw.date.le(day)].tail(2)
        if len(pair)!=2 or pair.date.iloc[-1]!=pd.Timestamp(day):raise ValueError('missing_event_boundary')
        previous,current=pair.iloc[0],pair.iloc[1];quote=nominal[day]
        if (previous.close!=prior or current.close!=close or current.volume<=0
                or F(quote['stck_clpr'])!=close or signed_reference(quote)!=reference):
            raise ValueError('event_quote_disagreement')
        before,old=float(previous.adj_factor),float(current.adj_factor)
        if before<=0 or old<=0:raise ValueError('invalid_source_factor')
        if day=='2024-11-25' and abs(old/before-prior/close)>1e-12:raise ValueError('changed_reviewed_bad_factor')
        if day=='2025-12-29' and old!=before:raise ValueError('changed_missing_event')
        multiplier=F(str(before))/F(str(old))*F(prior)/F(reference)
        events.append({'id':'017860_'+day,'code':'017860','date':day,'kind':'fixed',
            'reference_price':reference,'prior_close':prior,'first_close':close,'before_factor':before,
            'old_event_factor':old,'multiplier_numerator':multiplier.numerator,
            'multiplier_denominator':multiplier.denominator,'primary_document':key,
            'interpretation':'Official price-reference continuity only; not share availability, wealth or PIT certification.'})
    return events


def run(root):
    audit=root/'runtime_state/audit';source=audit/'kr_verified_events_v8_20261007/panel.parquet'
    index_path=audit/'lowliq_history_coverage_indices/index_20261007T141833378696.json'
    scope_path=audit/'lowliq_history_scope_20261007/plan.json';corpus=audit/'ds_reference_documents_20261007'
    if digest(source)!=SOURCE_SHA or digest(index_path)!=INDEX_SHA:raise ValueError('changed_frozen_inputs')
    index=json.loads(index_path.read_text());scope=json.loads(scope_path.read_text());scope_sha=digest(scope_path)
    if scope_sha!=index['scope_plan_sha256']:raise ValueError('changed_scope')
    hashes={str(source):SOURCE_SHA,str(index_path):INDEX_SHA,str(scope_path):scope_sha};texts={}
    for key,(window,stem,sha) in DOCUMENTS.items():
        path=corpus/window/'captures'/(stem+'.json')
        if digest(path)!=sha:raise ValueError('changed_reviewed_document')
        texts[key]=body_text(corpus,window,stem,hashes)
    if not all(s in texts['bonus_listing'] for s in ['A017860','KR7017860008','11,722,808','2024년12월24일','무상증자']):
        raise ValueError('wrong_bonus_listing')
    if not all(s in texts['bonus_decision'] for s in ['1주당 2주','5,861,404','11,722,808']):raise ValueError('wrong_bonus_ratio')
    if not all(s in texts['stock_dividend_decision'] for s in ['0.01','정기주주총회 결과에 따라 변경','현금 지급할 예정']):
        raise ValueError('wrong_dividend_terms')
    if not all(s in texts['cash_dividend_decision'] for s in ['현금배당','보통주식 10','주주총회의 결과에 따라 변경']):
        raise ValueError('wrong_cash_dividend_terms')
    entries={e['request_id']:e for e in index['entries']};nominal={};names=set()
    for request in scope['requests']:
        if request['code']!='017860' or request['basis']!='nominal':continue
        entry=entries[request['id']];item=indexed_receipt(entry,request,scope_sha,audit/'lowliq_history_capture_20261007')
        if item['inspection']['status']!='CAPTURED':raise ValueError('incomplete_provider_scope')
        hashes[entry['effective_path']]=entry['effective_sha256']
        name=item['payload']['output1'].get('hts_kor_isnm')
        if name:names.add(name)
        for row in item['payload']['output2']:
            day=pd.Timestamp(row['stck_bsop_date']).strftime('%Y-%m-%d')
            if day in request['expected_dates']:
                if day in nominal:raise ValueError('overlapping_provider_scope')
                nominal[day]=row
    if names!={'DS단석'}:raise ValueError('wrong_provider_security')
    raw=pd.read_parquet(source,filters=[('code','==','017860')]);events=verify_reference_events(raw,nominal,texts)
    listing=raw[raw.date.eq('2024-12-24')]
    if len(listing)!=1 or listing.iloc[0].volume<=0 or F(nominal['2024-12-24']['acml_vol'])<=0:
        raise ValueError('listing_instrument_activity_unconfirmed')
    dependencies={name:digest(ROOT/name) for name in ['research/compare_indexed_lowliq_history.py',
        'research/audit_lowliq_history_references.py','research/capture_lowliq_krx_source.py']}
    result={'source_sha256':SOURCE_SHA,'events':events,'input_sha256':hashes,'dependencies':dependencies,
        'implementation_sha256':digest(Path(__file__)),
        'ownership_evidence':{'bonus_additional_per_held_share':'2','bonus_final_listing':'2024-12-24',
            'bonus_listing_after_exdate_calendar_days':29,'instrument_traded_on_listing':True,
            'unrestricted_account_credit_certified':False,'stock_dividend_proposed_per_share':'0.01',
            'stock_dividend_fractional_cash_terms_present':True,'separate_proposed_cash_dividend_per_share':'10',
            'stock_dividend_agm_approval_payment_and_availability_verified':False},
        'source_certified':False,'portfolio_return_certified':False,'point_in_time_certified':False,
        'publication_allowed':False,'strategy_outcomes_computed':False}
    out=audit/'ds_price_reference_evidence_20261007';save_json(out/'verification.json',result)
    print(json.dumps({'verified_events':len(events),'verification_sha256':digest(out/'verification.json'),
                      'source_certified':False,'ownership_evidence':result['ownership_evidence']},indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
