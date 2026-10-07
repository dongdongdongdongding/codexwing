"""Verify five fixed ex-rights references and one actual resumption auction."""
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

SOURCE_SHA='f9360da33359799941f906f68a2aba172e9d456c7494edec687ec173a1ba0979'
INDEX_SHA='f2c4b3d6831ae9e370cc8b82e2619dd8c71f3520bc97383c00fd1beeb7c54c8d'
# code, date, actual reference, previous close, event close, provider name,
# official company name, class, window, document, receipt SHA, method
EVENTS=[
 ('000880','2026-08-25',100600,83800,118100,'한화','한화','보통주식','hanwha_202608',
  '000880_20260824000446_20260824001208_body_0','4c6b028677f06ed5a36ea6300eada5fb552099dee72734adb7df037c47a1cd68','auction'),
 ('012450','2025-05-22',837000,850000,833000,'한화에어로스페이스','한화에어로스페이스','보통주식','aerospace_202505',
  '012450_20250521000338_20250521001035_body_0','986ac3bc62b63dfd7b7967ce5238348cfe972274e82550b825715dcb052103a6','fixed'),
 ('011790','2026-04-06',89200,94900,89900,'SKC','SKC','보통주식','skc_202604',
  '011790_20260403001016_20260403001862_body_0','e368a2a9acd51b52e7365f0127d23119a41fe985501592028456cec7da952b22','fixed'),
 ('003670','2025-06-16',123200,127100,118500,'포스코퓨처엠','포스코퓨처엠','보통주식','posco_202506',
  '003670_20250613000420_20250613000969_body_0','ceb007bc69ea95380677c6649f605287c4d0bd1047ef8facea2a3318f2068fc7','fixed'),
 ('006400','2025-04-10',168100,171700,177200,'삼성SDI','삼성SDI','보통주식','sdi_202504',
  '006400_20250409000386_20250409001094_body_0','d355ae72fbb12213c0433bc9cc2b60e8e0920c29eb41885a3e1fc141972a0a48','fixed'),
 ('006405','2025-04-10',95800,99400,103600,'삼성SDI우','삼성SDI','1우선주','sdi_202504',
  '006400_20250409000394_20250409001101_body_0','c486b9fde78e968de2af0087b3283719fad9d2fa7c44d3d417beafa4ddc30c49','fixed'),
]


def verify_event(spec,raw,quote,text):
    code,day,reference,prior,close,name,company,share_class,window,stem,sha,method=spec
    if set(raw.code)!={code} or raw.date.duplicated().any():raise ValueError('wrong_source_identity')
    text=' '.join(text.split())
    if not all(v in text for v in [company,share_class,day]):raise ValueError('wrong_official_identity')
    pair=raw[raw.date.le(day)].sort_values('date').tail(2)
    if len(pair)!=2 or pair.date.iloc[-1]!=pd.Timestamp(day):raise ValueError('missing_event_boundary')
    previous,current=pair.iloc[0],pair.iloc[1]
    if (previous.close!=prior or current.close!=close or current.volume<=0
        or F(quote['stck_clpr'])!=close or F(quote['acml_vol'])!=F(str(current.volume))
        or signed_reference(quote)!=reference):raise ValueError('quote_disagreement')
    before,old=float(previous.adj_factor),float(current.adj_factor)
    if before<=0 or old<=0:raise ValueError('invalid_source_factor')
    if method=='fixed':
        if not all(v in text for v in ['기준가격(원)',f'{reference:,}','권리락(유상증자)']):
            raise ValueError('wrong_fixed_reference')
        if old!=before:raise ValueError('changed_missing_factor')
        if quote['flng_cls_code']!='01' or F(quote['prtt_rate'])>=0:raise ValueError('missing_exrights_quote')
    elif method=='auction':
        if not all(v in text for v in ['평가가격(원)','83,800','167,600','41,900','회사분할',
                '단일가격에 의한 매매방식으로 결정된 최초가격이 기준가격이 됨']):
            raise ValueError('wrong_auction_method')
        if (current.open!=reference or F(quote['stck_oprc'])!=reference or not 41900<=reference<=167600
            or reference==83800):raise ValueError('unproved_actual_auction')
        if abs(old/before-prior/close)>1e-12:raise ValueError('changed_close_based_factor')
        if previous.stocks!=70507919 or current.stocks!=53328897:raise ValueError('changed_split_share_counts')
    else:raise ValueError('unknown_method')
    multiplier=F(str(before))/F(str(old))*F(prior)/F(reference)
    return {'id':code+'_'+day,'code':code,'date':day,'kind':method,'reference_price':reference,
        'prior_close':prior,'first_close':close,'before_factor':before,'old_event_factor':old,
        'multiplier_numerator':multiplier.numerator,'multiplier_denominator':multiplier.denominator,
        'primary_document':stem,'interpretation':'Price-reference continuity only; paid rights, split assets and account availability unresolved.'}


def run(root):
    audit=root/'runtime_state/audit';source=audit/'kr_verified_events_v9_20261007/panel.parquet'
    index_path=audit/'lowliq_history_coverage_indices/index_20261007T141833378696.json'
    scope_path=audit/'lowliq_history_scope_20261007/plan.json';corpus=audit/'large_gap_reference_documents_20261008'
    if digest(source)!=SOURCE_SHA or digest(index_path)!=INDEX_SHA:raise ValueError('changed_frozen_inputs')
    index=json.loads(index_path.read_text());scope=json.loads(scope_path.read_text());scope_sha=digest(scope_path)
    if scope_sha!=index['scope_plan_sha256']:raise ValueError('changed_scope')
    hashes={str(source):SOURCE_SHA,str(index_path):INDEX_SHA,str(scope_path):scope_sha}
    entries={e['request_id']:e for e in index['entries']};codes={s[0] for s in EVENTS}
    nominal={c:{} for c in codes};names={c:set() for c in codes}
    for q in scope['requests']:
        code=q['code']
        if code not in codes or q['basis']!='nominal':continue
        entry=entries[q['id']];item=indexed_receipt(entry,q,scope_sha,audit/'lowliq_history_capture_20261007')
        if item['inspection']['status']!='CAPTURED':raise ValueError('incomplete_provider_scope')
        hashes[entry['effective_path']]=entry['effective_sha256'];names[code].add(item['payload']['output1']['hts_kor_isnm'])
        for row in item['payload']['output2']:
            day=pd.Timestamp(row['stck_bsop_date']).strftime('%Y-%m-%d')
            if day in q['expected_dates']:
                if day in nominal[code]:raise ValueError('overlapping_provider_scope')
                nominal[code][day]=row
    raw=pd.read_parquet(source,filters=[('code','in',sorted(codes))]);events=[]
    for spec in EVENTS:
        code,day,_,_,_,name,_,_,window,stem,sha,_=spec
        if names[code]!={name}:raise ValueError('wrong_provider_identity')
        if digest(corpus/window/'captures'/(stem+'.json'))!=sha:raise ValueError('changed_official_receipt')
        text=body_text(corpus,window,stem,hashes)
        events.append(verify_event(spec,raw[raw.code.eq(code)],nominal[code][day],text))
    listing_stem='000880_20260820000527_20260820001274_body_0'
    listing=body_text(corpus,'hanwha_202608',listing_stem,hashes)
    if not all(v in listing for v in ['A000880','KR7000880005','70,507,919','53,328,897','2026년08월25일','회사분할(존속)']):
        raise ValueError('wrong_final_split_listing')
    result={'source_sha256':SOURCE_SHA,'events':events,'input_sha256':hashes,
        'implementation_sha256':digest(Path(__file__)),
        'dependencies':{n:digest(ROOT/n) for n in ['research/audit_lowliq_history_references.py',
            'research/compare_indexed_lowliq_history.py','research/capture_lowliq_krx_source.py']},
        'ownership_limitations':['Paid-right subscription cash, right sales, dilution and availability not modeled.',
            'Hanwha split transfers assets into another security; one surviving-share price path is not portfolio wealth.',
            'Published documents and present captures do not establish historical availability at every signal date.'],
        'source_certified':False,'portfolio_return_certified':False,'point_in_time_certified':False,
        'publication_allowed':False,'strategy_outcomes_computed':False}
    out=audit/'large_gap_reference_evidence_20261008';save_json(out/'verification.json',result)
    print(json.dumps({'events':len(events),'verification_sha256':digest(out/'verification.json')}));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
