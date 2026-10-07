"""Test a six-decimal truncation explanation; never waive residual source gaps."""
import argparse
from decimal import Decimal as D, localcontext, ROUND_DOWN
import json
from pathlib import Path
import sys
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.compare_indexed_lowliq_history import indexed_receipt
from research.recover_lowliq_history_request import digest
from research.revalidate_kr_corrected_cohort import coefficient_interval
from research.run_lowliq_touch10_reconstruction import save_json

SOURCE_SHA='86c7f56e91261f3d8c8c770aaa6b8a5e9079bfa221ef80525e7f490d73b6dd53'
INDEX_SHA='f2c4b3d6831ae9e370cc8b82e2619dd8c71f3520bc97383c00fd1beeb7c54c8d'
EVENTS={'000880':('2026-08-25',83800,100600),
        '006400':('2025-04-10',171700,168100),
        '000500':('2026-06-30',343000,190600)}
FIELDS={'open':'stck_oprc','high':'stck_hgpr','low':'stck_lwpr','close':'stck_clpr'}


def run(root):
    a=root/'runtime_state/audit';source=a/'kr_verified_events_v10_20261008/panel.parquet'
    index_path=a/'lowliq_history_coverage_indices/index_20261007T141833378696.json';scope_path=a/'lowliq_history_scope_20261007/plan.json'
    if digest(source)!=SOURCE_SHA or digest(index_path)!=INDEX_SHA:raise ValueError('changed_frozen_inputs')
    scope=json.loads(scope_path.read_text());index=json.loads(index_path.read_text());scope_sha=digest(scope_path)
    if scope_sha!=index['scope_plan_sha256']:raise ValueError('changed_scope')
    hashes={str(source):SOURCE_SHA,str(index_path):INDEX_SHA,str(scope_path):scope_sha};entries={e['request_id']:e for e in index['entries']}
    providers={c:{} for c in EVENTS}
    for q in scope['requests']:
        c=q['code']
        if c not in EVENTS or q['basis']!='adjusted':continue
        e=entries[q['id']];item=indexed_receipt(e,q,scope_sha,a/'lowliq_history_capture_20261007')
        if item['inspection']['status']!='CAPTURED':raise ValueError('incomplete_provider_scope')
        hashes[e['effective_path']]=e['effective_sha256']
        for row in item['payload']['output2']:
            day=pd.Timestamp(row['stck_bsop_date']).strftime('%Y-%m-%d')
            if day in q['expected_dates']:
                if day in providers[c]:raise ValueError('overlapping_dates')
                providers[c][day]=row
    frame=pd.read_parquet(source,filters=[('code','in',list(EVENTS))]);results={}
    with localcontext() as ctx:
        ctx.prec=70
        for code,(event_day,prior,reference) in EVENTS.items():
            exact=D(reference)/D(prior);rounded=exact.quantize(D('.000001'),rounding=ROUND_DOWN)
            cells=[];mismatches=[];float32_mismatches=[];post_mismatches=[];post_cells=0;excluded=0
            for row in frame[frame.code.eq(code)].to_dict('records'):
                day=str(row['date'].date())
                if day not in providers[code]:continue
                quote=providers[code][day]
                for field,provider_field in FIELDS.items():
                    nominal=D(str(row[field]));adjusted=D(quote[provider_field])
                    if (field!='close' and nominal==0 and adjusted==D(quote['stck_clpr']) and adjusted>0
                        and row['volume']==0 and row['amount']==0 and D(quote['acml_vol'])==0 and D(quote['acml_tr_pbmn'])==0):
                        excluded+=1;continue
                    if nominal<=0:raise ValueError('unsupported_nonpositive_price')
                    cell={'date':day,'field':field,'source':str(nominal),'provider':str(adjusted)}
                    if day<event_day:
                        cells.append(cell);predicted=int(nominal*rounded)
                        if predicted!=adjusted:mismatches.append({**cell,'predicted':predicted})
                        float32_prediction=int(np.float32(float(nominal))*np.float32(str(rounded)))
                        if float32_prediction!=adjusted:float32_mismatches.append({**cell,'predicted':float32_prediction})
                    else:
                        post_cells+=1
                        if nominal!=adjusted:post_mismatches.append(cell)
            results[code]={'event_date':event_day,'exact_reference_ratio':str(exact),
                'candidate_six_decimal_truncated_ratio':str(rounded),'pre_cells':len(cells),
                'pre_prediction_mismatches':mismatches,'pre_float32_prediction_mismatches':float32_mismatches,
                'float32_hypothesis':'truncate_integer(float32(nominal_price) * float32(six_decimal_coefficient))',
                'post_cells':post_cells,
                'post_nominal_mismatches':post_mismatches,'excluded_zero_ohl_representations':excluded,
                'pre_coefficient_interval':coefficient_interval(cells)}
    result={'results':results,'input_sha256':hashes,'implementation_sha256':digest(Path(__file__)),
        'dependencies':{n:digest(ROOT/n) for n in ['research/compare_indexed_lowliq_history.py',
            'research/revalidate_kr_corrected_cohort.py']},
        'interpretation':'Compatibility test of an explicit numeric hypothesis; not a verified provider algorithm, tolerance waiver or source certificate.',
        'source_certified':False,'publication_allowed':False,'strategy_outcomes_computed':False}
    save_json(a/'reference_coefficient_rounding_v2_20261008/verification.json',result)
    print(json.dumps({c:{'pre_cells':r['pre_cells'],'pre_mismatches':len(r['pre_prediction_mismatches']),
        'float32_mismatches':len(r['pre_float32_prediction_mismatches']),
        'post_cells':r['post_cells'],'post_mismatches':len(r['post_nominal_mismatches']),
        'coefficient':r['candidate_six_decimal_truncated_ratio'],
        'nonempty_pre_interval':r['pre_coefficient_interval']['nonempty_half_open']} for c,r in results.items()},indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
