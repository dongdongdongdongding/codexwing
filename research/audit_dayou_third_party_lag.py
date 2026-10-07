"""Verify that a third-party issuance caused a false backdated bonus factor."""
import argparse
from fractions import Fraction as F
import json
import math
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_lowliq_history_references import body_text,signed_reference
from research.compare_indexed_lowliq_history import indexed_receipt
from research.recover_lowliq_history_request import digest
from research.trace_lowliq_adjustment_events import trace
from research.run_lowliq_touch10_reconstruction import save_json

SOURCE_SHA='b574338c410d620dd6802473aa9066254838158dac2604bd57692ea470c28116'
ORIGINAL_SHA='8c6fba2daf8d995be66441d873094928f347618c3a41f208c9286509f4fb1981'
AUCTION_SHA='0b4aa1ab38a5a48cb7ec1ef89de1e924650ca025a769eb530cc214321accca51'
INDEX_SHA='a5397baf779dc4a8fbe0c5a5c786cd403d80874cf7d30d8c471e393855e21e95'
DOCUMENTS={
 'decision':'002880_20231219000480_20231219001332_body_1',
 'payment':'002880_20231226000855_20231226001862_body_0',
 'listing':'002880_20240118000146_20240118000522_body_0',
}


def verify_false_lag(raw,quote,observed,texts):
    required={
        'decision':['회 사 명 : (주)대유에이텍','보통주식 (주) 8,009,151',
            '보통주식 (주) 38,730,299','5. 증자방식 제3자배정증자',
            '(주)동강홀딩스','2,288,329','(주)푸른산수목원','1,716,247',
            '(주)대유하늘','박은희','박은진','1,144,164'],
        'payment':['기명식 보통주식','2. 발행방법 제3자배정 유상증자',
            '실제발행주식수(주) 8,009,151','실제발행금액(원) 6,999,997,974','납입일 2023-12-26'],
        'listing':['대유에이텍 보통주 추가상장','기명식 보통주 8,009,151주',
            '유상증자(제3자배정)','2024년01월19일','KR7002880003 (단축코드:A002880)',
            '(주)동강홀딩스 외 4인','2024년01월19일 ~ 2025년01월18일'],
    }
    if any(not all(token in texts[k] for token in tokens) for k,tokens in required.items()):
        raise ValueError('unproved_third_party_issuance')
    if (observed['code']!='002880' or observed['date']!='2023-12-22' or observed['rule']!='lag'
        or observed['trigger_date']!='2024-01-19' or observed['trigger_stocks_before']!=38730299
        or observed['trigger_stocks_after']!=46739450 or observed['code_rows_between_event_and_trigger']!=17
        or observed['event_factor']!=46739450/38730299):raise ValueError('wrong_algorithm_trigger')
    if set(raw.code)!={'002880'} or raw.date.duplicated().any():raise ValueError('wrong_source_identity')
    pair=raw[raw.date.le('2023-12-22')].sort_values('date').tail(2)
    if len(pair)!=2 or list(pair.date.dt.strftime('%Y-%m-%d'))!=['2023-12-21','2023-12-22']:
        raise ValueError('missing_false_event_boundary')
    before,current=pair.iloc[0],pair.iloc[1]
    if (before.close!=1618 or current.close!=1360 or current.open!=1578 or current.volume!=7009766
        or before.stocks!=38730299 or current.stocks!=38730299):raise ValueError('changed_false_event_boundary')
    if not math.isclose(current.adj_factor/before.adj_factor,observed['event_factor'],rel_tol=1e-15,abs_tol=0):
        raise ValueError('wrong_retained_lag_factor')
    listing_pair=raw[raw.date.le('2024-01-19')].sort_values('date').tail(2)
    if (list(listing_pair.date.dt.strftime('%Y-%m-%d'))!=['2024-01-18','2024-01-19']
        or list(listing_pair.stocks)!=[38730299,46739450]
        or listing_pair.stocks.iloc[1]-listing_pair.stocks.iloc[0]!=8009151):raise ValueError('wrong_final_share_increase')
    if (signed_reference(quote)!=1618 or F(quote['stck_oprc'])!=1578 or F(quote['stck_clpr'])!=1360
        or F(quote['acml_vol'])!=7009766 or F(quote['prtt_rate'])!=0):raise ValueError('wrong_nominal_reference')
    multiplier=F(str(before.adj_factor))/F(str(current.adj_factor))
    return {'id':'002880_2023-12-22','code':'002880','date':'2023-12-22','kind':'false_third_party_lag',
        'reference_price':1618,'prior_close':1618.,'first_close':1360.,
        'before_factor':float(before.adj_factor),'old_event_factor':float(current.adj_factor),
        'multiplier_numerator':multiplier.numerator,'multiplier_denominator':multiplier.denominator,
        'trace':observed,'interpretation':'The 8,009,151 January19 shares were allocated to five named third parties. '
            'Remove only their false December22 bonus factor; retain real December20 auction/consolidation and actual stocks.'}


def run(root):
    a=root/'runtime_state/audit';source=a/'kr_verified_events_v13_20261008/panel.parquet'
    original=a/'kr_adjustment_asof_20261007/final/panel.parquet';proof=a/'first_historical_auction_evidence_20261008/verification.json'
    for p,h in [(source,SOURCE_SHA),(original,ORIGINAL_SHA),(proof,AUCTION_SHA)]:
        if digest(p)!=h:raise ValueError('changed_frozen_input')
    prior=json.loads(proof.read_text());hashes={**prior['input_sha256'],str(source):SOURCE_SHA,str(original):ORIGINAL_SHA,str(proof):AUCTION_SHA}
    for p,h in hashes.items():
        if digest(Path(p))!=h:raise ValueError('changed_primary_provenance')
    for n,h in prior['dependencies'].items():
        if digest(ROOT/n)!=h:raise ValueError('changed_auction_dependency')
    if digest(ROOT/'research/audit_first_historical_auction_references.py')!=prior['implementation_sha256']:
        raise ValueError('changed_auction_verifier')
    builder=ROOT/'research/data/build_px_delisted_20261007.py.txt'
    original_raw=pd.read_parquet(original,filters=[('code','==','002880')])
    traced=trace(original_raw,builder);observed=traced[traced.date.eq('2023-12-22')]
    if len(observed)!=1:raise ValueError('missing_unique_algorithm_trace')
    hashes[str(builder)]=digest(builder)
    corpus=a/'historical_reference_documents_20261008';window='002880_20231105_20240205'
    result=json.loads((corpus/(window+'_result.json')).read_text());texts={}
    if result['status']!='complete':raise ValueError('partial_primary_window')
    for name,stem in DOCUMENTS.items():
        docs=[d for d in result['documents'] if stem in d['body_keys']]
        if len(docs)!=1 or docs[0]['company']!='디와이에이':raise ValueError('wrong_document_identity')
        texts[name]=body_text(corpus,window,stem,hashes)
    scope_path=a/'lowliq_history_scope_20261007/plan.json';scope=json.loads(scope_path.read_text());scope_sha=digest(scope_path)
    index_path=a/'lowliq_history_coverage_indices/index_20261007T150309767417.json'
    if digest(index_path)!=INDEX_SHA:raise ValueError('changed_index')
    index=json.loads(index_path.read_text());entries={e['request_id']:e for e in index['entries']}
    if scope_sha!=index['scope_plan_sha256']:raise ValueError('changed_scope')
    requests=[q for q in scope['requests'] if q['code']=='002880' and q['basis']=='nominal' and '2023-12-22' in q['expected_dates']]
    if len(requests)!=1:raise ValueError('ambiguous_nominal_request')
    q=requests[0];entry=entries[q['id']];receipt=indexed_receipt(entry,q,scope_sha,a/'lowliq_history_capture_20261007')
    if receipt['inspection']['status']!='CAPTURED' or receipt['payload']['output1']['hts_kor_isnm']!='디와이에이':
        raise ValueError('unavailable_nominal_identity')
    hashes[entry['effective_path']]=entry['effective_sha256'];quotes=[r for r in receipt['payload']['output2'] if r['stck_bsop_date']=='20231222']
    if len(quotes)!=1:raise ValueError('ambiguous_nominal_day')
    event=verify_false_lag(pd.read_parquet(source,filters=[('code','==','002880')]),quotes[0],observed.iloc[0].to_dict(),texts)
    evidence={'events':[event],'input_sha256':hashes,'implementation_sha256':digest(Path(__file__)),
        'dependencies':{n:digest(ROOT/n) for n in ['research/trace_lowliq_adjustment_events.py',
            'research/audit_lowliq_history_references.py','research/compare_indexed_lowliq_history.py']},
        'original_code_rows_reproduced':len(original_raw),'original_five_adjusted_fields_exact':True,
        'primary_documents':DOCUMENTS,'allocation_to_existing_holders':False,
        'source_certified':False,'point_in_time_certified':False,'portfolio_return_certified':False,
        'publication_allowed':False,'strategy_outcomes_computed':False}
    out=a/'dayou_third_party_lag_evidence_20261008';save_json(out/'verification.json',evidence)
    print(json.dumps({'events':1,'original_rows_reproduced':len(original_raw),'verification_sha256':digest(out/'verification.json')}));return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
