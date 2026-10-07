"""Inventory reference-factor disagreements in the fixed historical review cohort."""
import argparse
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
import sys

import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_lowliq_history_references import signed_reference
from research.compare_indexed_lowliq_history import indexed_receipt
from research.recover_lowliq_history_request import digest
from research.run_lowliq_touch10_reconstruction import save_json

SOURCE_SHA='4d2c43d653140c39daed2f38f1f0c302f95ba16d84d75c9ad7f3162d56414256'
INDEX_SHA='a5397baf779dc4a8fbe0c5a5c786cd403d80874cf7d30d8c471e393855e21e95'
QUEUE_SHA='4570ccfb8912cf849078a488b8d4eda66c5be9551c9d70b91c7efe9a9ade2763'


def inventory_code(raw,quotes):
    if raw.date.duplicated().any() or len(set(raw.code))!=1:raise ValueError('invalid_source_identity')
    raw=raw.sort_values('date');code=str(raw.code.iloc[0]);rows=raw.to_dict('records')
    source_dates={str(r['date'].date()) for r in rows}
    if set(quotes)-source_dates:raise ValueError('provider_date_absent_in_source')
    counts=Counter();events=[];unpaired=[];unsupported=[];nontraded=[]
    for i,row in enumerate(rows):
        day=str(row['date'].date())
        if day not in quotes:continue
        quote=quotes[day];counts['scoped_rows']+=1
        for field,key in [('close','stck_clpr'),('volume','acml_vol'),('amount','acml_tr_pbmn')]:
            if F(str(row[field]))!=F(quote[key]):raise ValueError('nominal_source_disagreement')
        previous=rows[i-1] if i else None
        prior_day=str(previous['date'].date()) if previous else None
        if previous is None or prior_day not in quotes:
            counts['unpaired_scope_boundary']+=1;unpaired.append({'code':code,'date':day,'prior_date':prior_day});continue
        base={'code':code,'date':day,'prior_date':prior_day,'prior_close':previous['close'],
              'close':row['close'],'open':row['open'],'volume':row['volume'],
              'before_factor':previous['adj_factor'],'after_factor':row['adj_factor'],
              'before_stocks':int(previous['stocks']),'after_stocks':int(row['stocks'])}
        if row['volume']<=0:
            counts['nontraded_rows']+=1
            if any(previous[k]!=row[k] for k in ['adj_factor','stocks','close']):nontraded.append(base)
            continue
        counts['traded_rows']+=1
        try:reference=signed_reference(quote)
        except ValueError as exc:
            counts['unsupported_quote']+=1;unsupported.append({**base,'reason':str(exc),'quote':quote});continue
        prior=F(str(previous['close']));before=F(str(previous['adj_factor']));after=F(str(row['adj_factor']))
        if min(prior,before,after)<=0:raise ValueError('nonpositive_source_boundary')
        expected=prior/F(reference);observed=after/before;relative=abs(observed-expected)/expected
        counts['signed_reference_rows']+=1
        if relative==0:
            counts['exact_factor_agreement']+=1;continue
        category='ARITHMETIC_RESIDUAL' if relative<=F(1,10**12) else 'PRIMARY_REVIEW_REQUIRED'
        counts[category]+=1
        events.append({**base,'reference_price':reference,'provider_prtt_rate':quote.get('prtt_rate'),
            'provider_flag':quote.get('flng_cls_code'),'expected_factor_ratio':str(expected),
            'observed_factor_ratio':str(observed),'relative_disagreement_exact':str(relative),
            'relative_disagreement':float(relative),'classification':category})
    return {'code':code,'counts':dict(counts),'events':events,'unpaired_boundaries':unpaired,
            'unsupported_quotes':unsupported,'nontraded_boundaries':nontraded}


def run(root):
    a=root/'runtime_state/audit';source=a/'kr_verified_events_v11_20261008/panel.parquet'
    index_path=a/'lowliq_history_coverage_indices/index_20261007T150309767417.json'
    scope_path=a/'lowliq_history_scope_20261007/plan.json'
    queue_path=a/'lowliq_history_indexed_comparison_v11_20261008/source_review_queue.json'
    for path,sha in [(source,SOURCE_SHA),(index_path,INDEX_SHA),(queue_path,QUEUE_SHA)]:
        if digest(path)!=sha:raise ValueError('changed_frozen_input')
    scope=json.loads(scope_path.read_text());index=json.loads(index_path.read_text());queue=json.loads(queue_path.read_text())
    scope_sha=digest(scope_path)
    if scope_sha!=index['scope_plan_sha256']:raise ValueError('changed_scope')
    codes=sorted(r['code'] for r in queue['worst_examples'])
    if len(codes)!=213 or len(set(codes))!=213:raise ValueError('changed_review_cohort')
    entries={e['request_id']:e for e in index['entries']};quotes={c:{} for c in codes};names={c:set() for c in codes}
    hashes={str(source):SOURCE_SHA,str(index_path):INDEX_SHA,str(queue_path):QUEUE_SHA,str(scope_path):scope_sha}
    for q in scope['requests']:
        code=q['code']
        if code not in quotes or q['basis']!='nominal':continue
        if q['id'] not in entries:raise ValueError('incomplete_code_scope')
        e=entries[q['id']];item=indexed_receipt(e,q,scope_sha,a/'lowliq_history_capture_20261007')
        if item['inspection']['status']!='CAPTURED':raise ValueError('unavailable_provider_scope')
        hashes[e['effective_path']]=e['effective_sha256'];names[code].add(item['payload']['output1'].get('hts_kor_isnm',''))
        for row in item['payload']['output2']:
            day=pd.Timestamp(row['stck_bsop_date']).strftime('%Y-%m-%d')
            if day in q['expected_dates']:
                if day in quotes[code]:raise ValueError('overlapping_provider_dates')
                quotes[code][day]=row
    raw=pd.read_parquet(source,filters=[('code','in',codes)]);results=[];counts=Counter()
    for code,group in raw.groupby('code',sort=True):
        result=inventory_code(group,quotes[code]);result['provider_names']=sorted(names[code]);results.append(result);counts.update(result['counts'])
    if len(results)!=len(codes):raise ValueError('missing_source_code')
    candidates=[{**e,'provider_names':r['provider_names']} for r in results for e in r['events'] if e['classification']=='PRIMARY_REVIEW_REQUIRED']
    summary={'codes':len(codes),'counts':dict(counts),'candidate_codes':len({e['code'] for e in candidates}),
        'candidate_events':len(candidates),'nontraded_boundaries':sum(len(r['nontraded_boundaries']) for r in results),
        'source_certified':False,'publication_allowed':False,'strategy_outcomes_computed':False}
    out=a/'historical_reference_inventory_20261008'
    save_json(out/'manifest.json',{'input_sha256':hashes,'implementation_sha256':digest(Path(__file__)),
        'dependencies':{n:digest(ROOT/n) for n in ['research/audit_lowliq_history_references.py',
            'research/compare_indexed_lowliq_history.py','research/capture_lowliq_krx_source.py']},
        'scope':'All 213 codes in the pinned review queue, all captured nominal dates; no source repair or outcome selection.',
        'arithmetic_split':'Relative 1e-12 separates arithmetic-sized diagnostics only; not a source acceptance tolerance.'})
    save_json(out/'by_code.json',results);save_json(out/'primary_review_events.json',candidates);save_json(out/'summary.json',summary)
    print(json.dumps(summary,indent=2));return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
