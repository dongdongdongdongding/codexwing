"""Verify nine historical price-reference corrections without applying them."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import sys

import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.capture_lowliq_krx_source import payload_sha,inspect_payload
from research.run_lowliq_touch10_reconstruction import save_json
from research.freeze_lowliq_history_scope import V7_SHA
from research.trace_lowliq_adjustment_events import trace

# Security class is explicit in the official fixed-reference bodies. Preferred
# code/name is independently pinned by its own KIS request and output identity.
EVENTS=[
 ('000040','2024-03-18','auction',1624,'krmotors_202403','000040_20240315000616_20240315002267_body_0','KR모터스','보통주식'),
 ('000040','2024-03-20','fixed',1042,'krmotors_202403','000040_20240319000562_20240319002625_body_0','KR모터스','보통주식'),
 ('000070','2025-11-24','auction',69800,'samyang_202511','000070_20251121000436_20251121001003_body_0','삼양홀딩스','보통주식'),
 ('000100','2023-12-27','fixed',66900,'yuhan_202312','000100_20231226000728_20231226001871_body_0','유한양행','보통주식'),
 ('000105','2023-12-27','fixed',62200,'yuhan_202312','000100_20231226000734_20231226001872_body_0','유한양행','1우선주'),
 ('000500','2026-06-30','fixed',190600,'gaon_202606','000500_20260629000820_20260629001732_body_0','가온전선','보통주식'),
 ('000145','2024-01-18','nontrade_no_rebase',None,None,None,'하이트진로홀딩스우',None),
 ('000325','2025-03-21','nontrade_no_rebase',None,None,None,'노루홀딩스우',None),
 ('000325','2026-09-11','nontrade_no_rebase',None,None,None,'노루홀딩스우',None),
]


def signed_reference(quote):
    close=F(quote['stck_clpr']);change=F(quote['prdy_vrss']);sign=quote['prdy_vrss_sign']
    if (sign not in {'1','2','3','4','5'} or (sign in {'1','2'} and change<=0)
        or (sign in {'4','5'} and change>=0) or (sign=='3' and change!=0)):
        raise ValueError('invalid_quote_sign')
    reference=close-change
    if reference<=0 or reference.denominator!=1:raise ValueError('invalid_quote_reference')
    return int(reference)


def verify_nontrade(previous,current,nominal,adjusted,algorithm_rule):
    reference=signed_reference(nominal)
    if (current['volume']!=0 or current['amount']!=0 or previous['volume']<=0
        or current['stocks']!=previous['stocks'] or reference!=previous['close']
        or F(nominal['acml_vol'])!=0 or F(nominal['stck_clpr'])!=F(str(current['close']))
        or F(adjusted['stck_clpr'])!=F(nominal['stck_clpr'])
        or F(nominal['prtt_rate'])!=0 or algorithm_rule!='admin'):
        raise ValueError('unproved_nontrade_no_rebase')
    return reference


def body_text(corpus,window,key,hashes):
    base=corpus/window/'captures'/key
    receipt=json.loads(base.with_suffix('.json').read_text())
    if receipt['status']!=200:raise ValueError('failed_primary_capture')
    for suffix,field in [('.html','sha256'),('.txt','text_sha256')]:
        p=base.with_suffix(suffix)
        if digest(p)!=receipt[field]:raise ValueError('changed_primary_capture')
        hashes[str(p)]=digest(p)
    hashes[str(base.with_suffix('.json'))]=digest(base.with_suffix('.json'))
    return ' '.join(base.with_suffix('.txt').read_bytes().decode('utf-8').split())


def run(root):
    audit=root/'runtime_state/audit';capture=audit/'lowliq_history_capture_20261007'
    corpus=audit/'lowliq_history_actions_20261007';scope=audit/'lowliq_history_scope_20261007'
    source=audit/'kr_verified_events_v7_20261007/panel.parquet'
    if digest(source)!=V7_SHA:raise ValueError('changed_v7_source')
    plan=json.loads((scope/'plan.json').read_text());plan_sha=digest(scope/'plan.json')
    hashes={str(source):V7_SHA,str(scope/'plan.json'):plan_sha,str(corpus/'plan.json'):digest(corpus/'plan.json')}
    codes=sorted({r[0] for r in EVENTS}|{'000300'})
    raw=pd.read_parquet(source,filters=[('code','in',codes)]).sort_values(['code','date'])
    original=audit/'kr_adjustment_asof_20261007/final/panel.parquet'
    if digest(original)!=plan['parent_manifest']['sources']['panel']:raise ValueError('changed_original_source')
    builder=ROOT/'research/data/build_px_delisted_20261007.py.txt'
    traced=trace(pd.read_parquet(original,filters=[('code','in',codes)]),builder)
    rules={(r.code,r.date):r.rule for r in traced.itertuples()}
    for p in [original,builder,ROOT/'research/trace_lowliq_adjustment_events.py']:hashes[str(p)]=digest(p)
    providers={c:{'nominal':{},'adjusted':{}} for c in codes};identities={} 
    for request in plan['requests']:
        code=request['code']
        if code not in codes:continue
        p=capture/'responses'/(request['id']+'.json');item=json.loads(p.read_text())
        identity={'code':code,'market_div':'J','period':'D','start_date':request['start_date'],
                  'end_date':request['end_date'],'adjusted':request['basis']=='adjusted'}
        if (item['request']!=identity or item['plan_sha256']!=plan_sha
            or payload_sha(item['payload'])!=item['payload_sha256']
            or inspect_payload(item['payload'],identity,request['expected_dates'])!=item['inspection']
            or item['inspection']['status']!='CAPTURED'):
            raise ValueError('changed_provider_capture')
        hashes[str(p)]=digest(p)
        name=item['payload']['output1']['hts_kor_isnm']
        if code in identities and identities[code]!=name:raise ValueError('changed_security_name')
        identities[code]=name
        for row in item['payload']['output2']:
            day=pd.Timestamp(row['stck_bsop_date']).strftime('%Y-%m-%d')
            if day in providers[code][request['basis']]:raise ValueError('duplicate_provider_date')
            providers[code][request['basis']][day]=row
    events=[]
    for code,day,kind,reference,window,key,company,stock_class in EVENTS:
        g=raw[raw.code.eq(code) & raw.date.le(day)]
        previous,current=g.iloc[-2].to_dict(),g.iloc[-1].to_dict()
        if current['date']!=pd.Timestamp(day):raise ValueError('missing_event_row')
        nominal=providers[code]['nominal'][day];adjusted=providers[code]['adjusted'][day]
        if F(nominal['stck_clpr'])!=F(str(current['close'])):raise ValueError('raw_close_disagreement')
        text=None
        if kind=='nontrade_no_rebase':
            reference=verify_nontrade(previous,current,nominal,adjusted,rules.get((code,day)))
            if identities[code]!=company:raise ValueError('wrong_nontrade_security')
            # Every captured nominal/adjusted close of these codes is identical;
            # no inference that absence of a search result proves no action.
            if any(F(r['stck_clpr'])!=F(providers[code]['adjusted'][d]['stck_clpr'])
                   for d,r in providers[code]['nominal'].items()):
                raise ValueError('provider_history_not_same_basis')
        else:
            text=body_text(corpus,window,key,hashes)
            if not all(s in text for s in [company,day,stock_class]):raise ValueError('wrong_primary_scope')
            if not identities[code].startswith(company):raise ValueError('wrong_security_name')
            if signed_reference(nominal)!=reference or current['volume']<=0:
                raise ValueError('reference_quote_disagreement')
            if kind=='auction':
                if ('최초가격이 기준가격이 됨' not in text or current['open']!=reference
                    or F(nominal['stck_oprc'])!=reference):raise ValueError('unproved_auction_reference')
            elif f'{stock_class} {reference:,}' not in text:
                raise ValueError('wrong_official_fixed_reference')
        before=float(previous['adj_factor']);old=float(current['adj_factor'])
        multiplier=F(str(before))/F(str(old))*F(str(previous['close']))/F(str(reference))
        events.append({'id':code+'_'+day,'code':code,'date':day,'kind':kind,
                       'reference_price':reference,'prior_close':int(previous['close']),
                       'first_close':int(current['close']),'before_factor':before,'old_event_factor':old,
                       'multiplier_numerator':multiplier.numerator,'multiplier_denominator':multiplier.denominator,
                       'primary_body':key,'primary_window':window,'security_name':identities[code],
                       'interpretation':'Price-reference continuity only; no wealth/PIT/execution certificate.'})
    unresolved_text=body_text(corpus,'dhauto_202601','000300_20260113000540_20260113001238_body_0',hashes)
    if not all(s in unresolved_text for s in ['2026-01-14','4,200','매매거래정지가 계속됨']):
        raise ValueError('missing_suspended_capital_evidence')
    result={'source_sha256':V7_SHA,'events':events,'input_sha256':hashes,
            'implementation_sha256':digest(Path(__file__)),
            'unresolved':[{'code':'000300','date':'2026-01-14','reason':'Actual 2:1 capital reduction while suspended; '
                          'published 4200 is evaluated price, not executed auction reference. Provider nominal/adjusted '
                          'series do not encode the same ownership change. Do not remove valid share factor merely to '
                          'match provider, invent a fill or count this discrepancy as resolved.'}],
            'publication_allowed':False,'price_source_certified':False,'portfolio_return_certified':False,
            'test_outcomes_computed':False}
    out=audit/'lowliq_history_reference_evidence_20261007';save_json(out/'verification.json',result)
    print(json.dumps({'verified_events':len(events),'codes':len({e['code'] for e in events}),
                      'event_kinds':{kind:sum(e['kind']==kind for e in events) for kind in ['auction','fixed','nontrade_no_rebase']},
                      'unresolved':result['unresolved'],'verification_sha256':digest(out/'verification.json')}),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
