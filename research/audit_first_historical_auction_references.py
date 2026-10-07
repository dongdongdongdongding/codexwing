"""Verify actual opening references in fourteen captured auction notices."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import re
import sys

from bs4 import BeautifulSoup
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_first_historical_fixed_references import run as verify_fixed, INDEX_SHA
from research.audit_lowliq_history_references import body_text, signed_reference
from research.compare_indexed_lowliq_history import indexed_receipt
from research.recover_lowliq_history_request import digest
from research.run_lowliq_touch10_reconstruction import save_json

SOURCE_SHA='508f84d6b43c2e6a7d19d4057ef613d8791fcbe1435d87e6405fa648bf88265b'
FIXED_SHA='f4614a90458804f7beffb235be31da7616661580863f7b4cf6042d39c140d49b'
NAME_CHANGES={'001340':('백광산업','PKC'),'002880':('대유에이텍','디와이에이')}
# Reviewed listing chains describe outstanding shares; they are not a
# shareholder entitlement ratio or proof of actual account availability.
LISTINGS={
 ('001140','2024-02-02'):('001140_20240130000167_20240130000511_body_0',12589769,12589769,
     ['KR7001140003','국보보통주','12,589,769주(제 1~32회) → 125,897,690주',
      '125,897,690주 → 12,589,769주','액면분할','감자(주식병합)']),
 ('001230','2026-05-29'):('001230_20260526000550_20260526001314_body_0',31800483,155507715,
     ['KR7001230002','동국홀딩스보통주','31,800,483주 → 31,101,543주',
      '31,101,543주 → 155,507,715주','감자(주식소각)','액면가액 감액','액면분할']),
 ('002070','2026-05-06'):('002070_20260429000184_20260429000378_body_0',45196077,1499940,
     ['KR7002070001','비비안보통주','45,196,077주 → 1,499,940주','감자(주식병합)']),
 ('002880','2023-12-20'):('002880_20231215000152_20231215000259_body_0',116190898,38730299,
     ['KR7002880003','대유에이텍보통주','116,190,898주 → 38,730,299주','감자(주식병합)']),
 ('003060','2024-04-16'):('003060_20240411000113_20240411000338_body_0',665754689,66575468,
     ['KR7003060001','에이프로젠바이오로직스보통주','665,754,689주 → 66,575,468주','감자(주식병합)']),
 ('003060','2026-05-08'):('003060_20260504000651_20260504001416_body_0',198407845,13227189,
     ['KR7003060001','에이프로젠바이오로직스보통주','198,407,845주 → 13,227,189주','감자(주식병합)']),
 ('003620','2025-05-09'):('003620_20250502000182_20250502000410_body_0',196404254,202356634,
     ['KR7003620002','케이지모빌리티보통주','5,952,380주','국내CB전환',
      '202,356,634주 (변경사항 없음)','액면가액 : 5,000원 → 1,000원']),
 ('004710','2025-09-26'):('004710_20250923000066_20250923000113_body_0',32109878,32109878,
     ['KR7004710000','한솔테크닉스보통주','32,109,878주 (변경사항 없음)',
      '액면가액 : 5,000원 → 1,000원']),
 ('004800','2024-07-29'):('004800_20240724000063_20240724000142_body_0',20466334,16740407,
     ['KR7004800009','효성보통주','20,466,334주 → 16,740,407주','회사분할(존속)']),
 ('006740','2026-05-29'):('006740_20260526000129_20260526000247_body_0',56975588,4747965,
     ['KR7006740005','블루산업개발 보통주','56,975,588주 → 4,747,965주','감자(주식병합)']),
}


def parse_auction(text):
    text=' '.join(text.split())
    if not re.match(r'^:: (99326|99328|99332|99403|99409)_',text):return None
    pattern=(r'1\. 회사명 (?P<company>.+?) 2\. 주권종류와 가격 주권종류 평가가격\(원\) '
        r'최고호가\(원\) 최저호가\(원\) (?P<share_class>보통주식) '
        r'(?P<evaluated>[\d,]+) (?P<upper>[\d,]+) (?P<lower>[\d,]+) '
        r'3\. 기준가격\s?결정\s?방법 (?P<method>.+?) 4\. 매매방법 .+? '
        r'5\. 사유 (?P<reason>.+?) 6\. 적용일 (?P<date>\d{4}-\d{2}-\d{2}) 7\. 근거규정')
    m=re.search(pattern,text)
    if not m:raise ValueError('unsupported_auction_template')
    n=m.groupdict()
    if '단일가격에 의한 매매방식으로 결정된 최초가격이 기준가격이 됨' not in n['method']:
        raise ValueError('unproved_opening_auction_method')
    for field in ['evaluated','upper','lower']:n[field]=int(n[field].replace(',',''))
    if not 0<n['lower']<=n['evaluated']<=n['upper']:raise ValueError('invalid_auction_bounds')
    return n


def verify_identity(code,notice,record_company,viewer_html,provider_name):
    header=BeautifulSoup(viewer_html,'html.parser').select_one('h1.ttl')
    if header is None or header.get_text(' ',strip=True)!=f'{record_company} ({code})':
        raise ValueError('wrong_official_security_code')
    if notice['company']!=record_company and NAME_CHANGES.get(code)!=(notice['company'],record_company):
        raise ValueError('unproved_historical_issuer_identity')
    if provider_name!=record_company:
        if (code,record_company,provider_name)!=('001140','국보',None):
            raise ValueError('wrong_provider_security_identity')
    return {'official_company_at_notice':notice['company'],'official_viewer_company':record_company,
        'provider_security_name':provider_name,'provider_name_unavailable':provider_name is None,
        'identity_basis':'Official viewer code/body binding and indexed nominal request identity; historical names retained.'}


def verify_listing(code,day,text,before_stocks,after_stocks):
    spec=LISTINGS[(code,day)];text=' '.join(text.split())
    date=pd.Timestamp(day).strftime('%Y년%m월%d일')
    if (before_stocks!=spec[1] or after_stocks!=spec[2] or date not in text
        or not re.search(r'단축코드\s*:\s*A'+code+r'\)',text)
        or not all(token in text for token in spec[3])):raise ValueError('wrong_final_listing_boundary')
    if code=='003620' and after_stocks-before_stocks!=5952380:raise ValueError('wrong_concurrent_cb_listing')


def verify_auction(code,raw,quote,notice,candidate,listing_text=None):
    day=notice['date']
    if set(raw.code)!={code} or raw.date.duplicated().any():raise ValueError('wrong_source_identity')
    pair=raw[raw.date.le(day)].sort_values('date').tail(2)
    if len(pair)!=2 or pair.date.iloc[-1]!=pd.Timestamp(day):raise ValueError('missing_source_boundary')
    before,current=pair.iloc[0],pair.iloc[1]
    if (candidate['code']!=code or candidate['date']!=day or candidate['prior_date']!=str(before.date.date())
        or before.close!=candidate['prior_close'] or current.close!=candidate['close']):
        raise ValueError('changed_nominal_inventory_boundary')
    actual=signed_reference(quote)
    if (actual!=candidate['reference_price'] or actual!=F(quote['stck_oprc'])
        or actual!=F(str(current.open)) or F(quote['stck_clpr'])!=F(str(current.close))
        or F(quote['acml_vol'])!=F(str(current.volume)) or current.volume<=0
        or not notice['lower']<=actual<=notice['upper']):raise ValueError('unproved_actual_opening_reference')
    if (code,day) in LISTINGS:
        verify_listing(code,day,listing_text or '',before.stocks,current.stocks)
    elif notice['reason']!='매매거래재개' or before.stocks!=current.stocks:
        raise ValueError('missing_capital_change_listing')
    multiplier=F(str(before.adj_factor))/F(str(current.adj_factor))*F(str(before.close))/actual
    return {'id':code+'_'+day,'code':code,'date':day,'kind':'auction','reference_price':int(actual),
        'prior_close':float(before.close),'first_close':float(current.close),'before_factor':float(before.adj_factor),
        'old_event_factor':float(current.adj_factor),'before_stocks':int(before.stocks),'after_stocks':int(current.stocks),
        'multiplier_numerator':multiplier.numerator,'multiplier_denominator':multiplier.denominator,
        'evaluated_price':notice['evaluated'],'auction_lower':notice['lower'],'auction_upper':notice['upper'],
        'reason':notice['reason'],'interpretation':'Verified price reference only; original stocks retained. '
            'Outstanding-share changes are not investor entitlements or total-wealth returns.'}


def run(root):
    a=root/'runtime_state/audit';corpus=a/'historical_reference_documents_20261008'
    source=a/'kr_verified_events_v12_20261008/panel.parquet'
    fixed_path=a/'first_historical_fixed_evidence_v2_20261008/verification.json'
    if digest(source)!=SOURCE_SHA or digest(fixed_path)!=FIXED_SHA:raise ValueError('changed_frozen_inputs')
    fixed=verify_fixed(root)
    hashes={**fixed['input_sha256'],str(fixed_path):FIXED_SHA,str(source):SOURCE_SHA}
    for p,h in hashes.items():
        if digest(Path(p))!=h:raise ValueError('changed_supporting_evidence')
    plan=json.loads((corpus/'plan.json').read_text())
    run_receipt=json.loads((corpus/'runs/fac472514bb0438180ae74dc2a683ee9.json').read_text())
    candidates={(e['code'],e['date']):e for e in json.loads((a/'historical_reference_inventory_20261008/primary_review_events.json').read_text())}
    notices={}
    for r in run_receipt['results']:
        if r['status']!='complete':continue
        window=r['window'];result=json.loads((corpus/(window+'_result.json')).read_text());code=result['window']['code']
        for doc in result['documents']:
            for stem in doc['body_keys']:
                notice=parse_auction(body_text(corpus,window,stem,hashes))
                if notice is None:continue
                key=(code,notice['date'])
                if key not in candidates or key in notices:raise ValueError('changed_auction_scope')
                if doc['published_at'][:10]>notice['date']:raise ValueError('late_auction_method')
                viewer=code+'_'+doc['acptno']+'_viewer';body_text(corpus,window,viewer,hashes)
                item={'notice':notice,'doc':doc,'window':window,'stem':stem,
                    'viewer_html':(corpus/window/'captures'/(viewer+'.html')).read_bytes(),'listing':None}
                if key in LISTINGS:
                    listing_stem=LISTINGS[key][0]
                    selected=[d for d in result['documents'] if listing_stem in d['body_keys']]
                    if len(selected)!=1 or selected[0]['published_at'][:10]>notice['date']:raise ValueError('unavailable_final_listing')
                    item['listing']=body_text(corpus,window,listing_stem,hashes)
                notices[key]=item
    if len(notices)!=14 or len({k[0] for k in notices})!=13:raise ValueError('incomplete_auction_scope')
    scope_path=a/'lowliq_history_scope_20261007/plan.json';scope=json.loads(scope_path.read_text());scope_sha=digest(scope_path)
    index_path=a/'lowliq_history_coverage_indices/index_20261007T150309767417.json'
    if digest(index_path)!=INDEX_SHA:raise ValueError('changed_index')
    index=json.loads(index_path.read_text());entries={e['request_id']:e for e in index['entries']}
    if scope_sha!=index['scope_plan_sha256']:raise ValueError('changed_scope')
    quotes={};names={}
    for q in scope['requests']:
        keys=[k for k in notices if k[0]==q['code'] and k[1] in q['expected_dates']]
        if not keys or q['basis']!='nominal':continue
        entry=entries[q['id']];receipt=indexed_receipt(entry,q,scope_sha,a/'lowliq_history_capture_20261007')
        if receipt['inspection']['status']!='CAPTURED':raise ValueError('unavailable_nominal_quote')
        hashes[entry['effective_path']]=entry['effective_sha256']
        for quote in receipt['payload']['output2']:
            key=(q['code'],pd.Timestamp(quote['stck_bsop_date']).strftime('%Y-%m-%d'))
            if key in keys:
                if key in quotes:raise ValueError('duplicate_nominal_quote')
                quotes[key]=quote;names[key]=receipt['payload']['output1'].get('hts_kor_isnm')
    raw=pd.read_parquet(source,filters=[('code','in',sorted({k[0] for k in notices}))]);events=[]
    for key,item in sorted(notices.items()):
        identity=verify_identity(key[0],item['notice'],item['doc']['company'],item['viewer_html'],names[key])
        event=verify_auction(key[0],raw[raw.code.eq(key[0])],quotes[key],item['notice'],candidates[key],item['listing'])
        event.update(identity);event['primary_method']={'window':item['window'],'stem':item['stem'],'acptno':item['doc']['acptno']}
        event['listing_stem']=LISTINGS[key][0] if key in LISTINGS else None;events.append(event)
    result={'events':events,'input_sha256':hashes,'implementation_sha256':digest(Path(__file__)),
        'dependencies':{n:digest(ROOT/n) for n in ['research/audit_first_historical_fixed_references.py',
            'research/audit_lowliq_history_references.py','research/compare_indexed_lowliq_history.py']},
        'complete_windows_revalidated':fixed['complete_windows_revalidated'],
        'deferred_windows':fixed['deferred_windows'],'unvisited_windows':run_receipt['unvisited_windows'],
        'source_certified':False,'point_in_time_certified':False,'portfolio_return_certified':False,
        'publication_allowed':False,'strategy_outcomes_computed':False}
    out=a/'first_historical_auction_evidence_20261008';save_json(out/'verification.json',result)
    print(json.dumps({'events':len(events),'codes':len({e['code'] for e in events}),
        'verification_sha256':digest(out/'verification.json')}));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
