"""Verify fixed references in complete windows of a pinned interrupted capture."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import re
import sys

import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.capture_kr_action_documents import Capture, capture_code
from research.capture_kr_suspended_references import capture_extra
from research.capture_historical_reference_inventory import EXTRA
from research.compare_indexed_lowliq_history import indexed_receipt
from research.audit_lowliq_history_references import signed_reference, body_text
from research.recover_lowliq_history_request import digest
from research.run_lowliq_touch10_reconstruction import save_json

SOURCE_SHA='4d2c43d653140c39daed2f38f1f0c302f95ba16d84d75c9ad7f3162d56414256'
RUN_SHA='1e28f56b7a6c7b61bd9333ded5e478415c3da0df5059e0170bc45035a6fcec55'
EVENTS_SHA='a080aa9cf180216445580658c9df2c23af28d14c10244123061554d5112be3c9'
INDEX_SHA='a5397baf779dc4a8fbe0c5a5c786cd403d80874cf7d30d8c471e393855e21e95'
PREFERRED={('001060','1우선주'):('001065','JW중외제약우'),
           ('001060','2우선주B'):('001067','JW중외제약2우B'),
           ('006800','1우선주'):('006805','미래에셋증권우'),
           ('006800','2우선주B'):('00680K','미래에셋증권2우B')}


def parse_fixed(text):
    text=' '.join(text.split())
    if not re.match(r'^:: (99301|99302|99311|99321|99322)_',text):return None
    pattern=(r'1\. 회사명 (?P<company>.+?) 2\. (?:주권종류와 가격|주식의 종류와 가격) '
             r'주권종류 기준가격\(원\) (?P<share_class>보통주식|1우선주|2우선주B|3우선주B) '
             r'(?P<reference>[\d,]+) 3\. 사유 (?P<reason>.+?) 4\. 적용일 '
             r'(?P<date>\d{4}-\d{2}-\d{2}) 5\. 근거규정')
    match=re.search(pattern,text)
    if not match:raise ValueError('unsupported_fixed_reference_template')
    result=match.groupdict();result['reference']=int(result['reference'].replace(',',''))
    if result['reference']<=0:raise ValueError('nonpositive_fixed_reference')
    return result


def security_for(issuer,notice):
    if notice['share_class']=='보통주식':return issuer,notice['company']
    if (issuer,notice['share_class']) not in PREFERRED:return None
    return PREFERRED[issuer,notice['share_class']]


def provider_name_for(code,name,identity_text=None):
    if (code,name)!=('001530','디아이동일'):return name
    text=' '.join((identity_text or '').split())
    required=['디아이동일(주)', '상장종목 : DI동일보통주', 'KR7001530005 (단축코드:A001530)']
    if not all(s in text for s in required):raise ValueError('unproved_provider_name_alias')
    return 'DI동일'


def verify_quote_event(candidate,raw,quote,notice):
    code,day=candidate['code'],candidate['date']
    if set(raw.code)!={code} or raw.date.duplicated().any():raise ValueError('wrong_source_identity')
    pair=raw[raw.date.le(day)].sort_values('date').tail(2)
    if len(pair)!=2 or str(pair.date.iloc[-1].date())!=day:raise ValueError('missing_source_boundary')
    previous,current=pair.iloc[0],pair.iloc[1]
    if (str(previous.date.date())!=candidate['prior_date'] or previous.close!=candidate['prior_close']
        or current.close!=candidate['close'] or previous.adj_factor!=candidate['before_factor']
        or current.adj_factor!=candidate['after_factor']):raise ValueError('changed_inventory_boundary')
    reference=notice['reference']
    if (notice['date']!=day or reference!=candidate['reference_price'] or signed_reference(quote)!=reference
        or F(quote['stck_clpr'])!=F(str(current.close)) or F(quote['acml_vol'])!=F(str(current.volume))
        or current.volume<=0):raise ValueError('primary_quote_disagreement')
    multiplier=F(str(previous.adj_factor))/F(str(current.adj_factor))*F(str(previous.close))/F(reference)
    return {'id':code+'_'+day,'code':code,'date':day,'kind':'fixed','reference_price':reference,
        'prior_close':float(previous.close),'first_close':float(current.close),'before_factor':float(previous.adj_factor),
        'old_event_factor':float(current.adj_factor),'multiplier_numerator':multiplier.numerator,
        'multiplier_denominator':multiplier.denominator,'reason':notice['reason'],
        'interpretation':'Explicit class-specific price reference only; entitlement cash, fractions and availability not certified.'}


def run(root):
    a=root/'runtime_state/audit';corpus=a/'historical_reference_documents_20261008'
    source=a/'kr_verified_events_v11_20261008/panel.parquet';run_path=corpus/'runs/fac472514bb0438180ae74dc2a683ee9.json'
    event_path=a/'historical_reference_inventory_20261008/primary_review_events.json'
    index_path=a/'lowliq_history_coverage_indices/index_20261007T150309767417.json';scope_path=a/'lowliq_history_scope_20261007/plan.json'
    hashes={str(p):h for p,h in [(source,SOURCE_SHA),(run_path,RUN_SHA),(event_path,EVENTS_SHA),(index_path,INDEX_SHA)]}
    for p,h in hashes.items():
        if digest(Path(p))!=h:raise ValueError('changed_frozen_input')
    run_receipt=json.loads(run_path.read_text());plan=json.loads((corpus/'plan.json').read_text())
    hashes[str(corpus/'plan.json')]=digest(corpus/'plan.json');windows={w['key']:w for w in plan['windows']}
    candidates={(e['code'],e['date']):e for e in json.loads(event_path.read_text())}
    notices={};deferred=[];searched=0
    for row in run_receipt['results']:
        key=row['window'];window=windows[key];path=corpus/(key+'_result.json');result=json.loads(path.read_text())
        hashes[str(path)]=digest(path)
        if result['status']!=row['status'] or result['window']!=window:raise ValueError('changed_window_identity')
        if result['status']!='complete':deferred.append({'window':key,'status':result['status']});continue
        # A zero time budget and no session ensure this can only read verified
        # existing captures; incomplete evidence cannot trigger a network call.
        capture=Capture(corpus/key,None,0);rebuilt=capture_code(capture,window,window['begin'],window['end'])
        extras=[r for r in rebuilt['records'] if not r['selected'] and any(s in r['title'] for s in EXTRA)]
        for r in extras:rebuilt['documents'].append(capture_extra(capture,window['code'],r))
        rebuilt['expanded_selected_count']=rebuilt['selected_count']+len(extras);rebuilt['window']=window
        if rebuilt!=result:raise ValueError('changed_cached_search_or_documents')
        searched+=1
        for doc in result['documents']:
            for stem in doc['body_keys']:
                text=body_text(corpus,key,stem,hashes);notice=parse_fixed(text)
                if notice is None:continue
                if notice['company']!=doc['company']:raise ValueError('wrong_official_issuer')
                target=security_for(window['code'],notice)
                if target is None:continue
                code,name=target;event_key=(code,notice['date'])
                if event_key not in candidates:continue
                if doc['published_at'][:10]>notice['date']:raise ValueError('late_reference_notice')
                if event_key in notices and notices[event_key]['notice']!=notice:raise ValueError('conflicting_reference_notices')
                item=notices.setdefault(event_key,{'notice':notice,'expected_name':name,'documents':[]})
                item['documents'].append({'window':key,'stem':stem,'issuer_code':window['code'],'acptno':doc['acptno']})
    scope=json.loads(scope_path.read_text());index=json.loads(index_path.read_text());scope_sha=digest(scope_path)
    if scope_sha!=index['scope_plan_sha256']:raise ValueError('changed_scope')
    hashes[str(scope_path)]=scope_sha;entries={e['request_id']:e for e in index['entries']}
    providers={};names={}
    for q in scope['requests']:
        keys=[k for k in notices if k[0]==q['code'] and k[1] in q['expected_dates']]
        if not keys or q['basis']!='nominal':continue
        e=entries[q['id']];receipt=indexed_receipt(e,q,scope_sha,a/'lowliq_history_capture_20261007')
        if receipt['inspection']['status']!='CAPTURED':raise ValueError('unavailable_nominal_quote')
        hashes[e['effective_path']]=e['effective_sha256'];name=receipt['payload']['output1'].get('hts_kor_isnm')
        for quote in receipt['payload']['output2']:
            key=(q['code'],pd.Timestamp(quote['stck_bsop_date']).strftime('%Y-%m-%d'))
            if key in keys:
                if key in providers:raise ValueError('duplicate_nominal_quote')
                providers[key]=quote;names[key]=name
    codes=sorted({k[0] for k in notices});raw=pd.read_parquet(source,filters=[('code','in',codes)]);events=[]
    alias_text=body_text(corpus,'001530_20241112_20250210',
        '001530_20250124000093_20250124000252_body_0',hashes)
    for key,item in sorted(notices.items()):
        if names.get(key)!=provider_name_for(key[0],item['expected_name'],alias_text):
            raise ValueError(f'wrong_provider_security_class: {key}: {names.get(key)!r} != {item["expected_name"]!r}')
        event=verify_quote_event(candidates[key],raw[raw.code.eq(key[0])],providers[key],item['notice'])
        event['official_company']=item['notice']['company'];event['share_class']=item['notice']['share_class']
        event['provider_security_name']=names[key]
        event['primary_documents']=item['documents'];events.append(event)
    result={'events':events,'input_sha256':hashes,'implementation_sha256':digest(Path(__file__)),
        'dependencies':{n:digest(ROOT/n) for n in ['research/capture_kr_action_documents.py',
            'research/capture_kr_suspended_references.py','research/capture_historical_reference_inventory.py',
            'research/compare_indexed_lowliq_history.py','research/audit_lowliq_history_references.py']},
        'complete_windows_revalidated':searched,'deferred_windows':deferred,
        'provider_name_alias_evidence':{'code':'001530','official_company':'디아이동일',
            'provider_security_name':'DI동일','window':'001530_20241112_20250210',
            'stem':'001530_20250124000093_20250124000252_body_0',
            'purpose':'Security identity only; not a point-in-time or entitlement certificate.'},
        'unmatched_candidate_events':[{'code':c,'date':d} for c,d in sorted(set(candidates)-set(notices))],
        'source_certified':False,'portfolio_return_certified':False,'point_in_time_certified':False,
        'publication_allowed':False,'strategy_outcomes_computed':False}
    out=a/'first_historical_fixed_evidence_v2_20261008';save_json(out/'verification.json',result)
    print(json.dumps({'events':len(events),'codes':len(codes),'complete_windows':searched,
        'deferred_windows':len(deferred),'verification_sha256':digest(out/'verification.json')}));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
