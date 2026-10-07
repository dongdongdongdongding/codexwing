"""Recheck the entire frozen provider cohort after guarded repairs, with no strategy labels."""
import argparse
from collections import Counter
from decimal import Decimal as D, localcontext
import json
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.capture_lowliq_krx_source import payload_sha
from research.compare_lowliq_krx_source import compare_code,index_payload,FIELDS,PRICE
from research.run_lowliq_touch10_reconstruction import save_json,save_frame



def coefficient_interval(cells):
    """Intersect exact Decimal constraints a <= adjusted_source*k < a+1.

    Empty intervals remain empty, including tiny floating-storage disagreements.
    Bounds describe compatibility with truncation, never source certification.
    """
    with localcontext() as ctx:
        ctx.prec=60
        lower=D(0);upper=D('Infinity');lower_cell=None;upper_cell=None;count=0
        for cell in cells:
            raw=D(str(cell['source']));adjusted=D(str(cell['provider']))
            if not raw.is_finite() or raw<=0 or not adjusted.is_finite() or adjusted<0:
                raise ValueError('invalid_interval_price')
            lo=adjusted/raw;hi=(adjusted+1)/raw
            if lo>lower:lower=lo;lower_cell=cell
            if hi<upper:upper=hi;upper_cell=cell
            count+=1
        if not count:raise ValueError('empty_interval_scope')
        return {'cells':count,'lower_inclusive':str(lower),'upper_exclusive':str(upper),
                'nonempty_half_open':lower<upper,'closed_bounds_overlap':lower<=upper,
                'relative_gap':str(max(D(0),lower-upper)/max(abs(lower),abs(upper))),
                'lower_binding_cell':lower_cell,'upper_binding_cell':upper_cell}


def run(root, source, out, expected_sha256):
    audit=root/'runtime_state/audit';capture=audit/'lowliq_krx_source_20261007'
    original=audit/'lowliq_krx_comparison_20261007';out.mkdir(parents=True,exist_ok=True)
    if digest(source)!=expected_sha256:raise ValueError('changed_corrected_source')
    plan_path=capture/'plan.json';plan=json.loads(plan_path.read_text());plan_sha=digest(plan_path)
    original_plan=json.loads((original/'plan.json').read_text())
    if original_plan['capture_plan_sha256']!=plan_sha:raise ValueError('changed_capture_plan')
    codes=sorted(plan['expected_dates'])
    if len(codes)!=1310:raise ValueError('changed_cohort')
    frame=pd.read_parquet(source,filters=[('code','in',codes),('date','>=',pd.Timestamp('2026-06-30')),
        ('date','<=',pd.Timestamp('2026-10-02'))])
    groups={c:g for c,g in frame.groupby('code')};nominal_diffs=[];adjusted_diffs=[];basis_diffs=[];counts=[];intervals=[]
    compared_hashes={};comparable=Counter();traded_diffs=[]
    for code in codes:
        bases={}
        for basis in ['nominal','adjusted']:
            key=code+'_'+basis;path=capture/'responses'/(key+'.json');sha=digest(path)
            if sha!=original_plan['response_sha256'][key]:raise ValueError('changed_provider_response')
            item=json.loads(path.read_text())
            if (item['plan_sha256']!=plan_sha or item['code']!=code or
                item['request']!={**plan['request'],'adjusted':basis=='adjusted'} or
                payload_sha(item['payload'])!=item['payload_sha256']):raise ValueError('changed_provider_identity')
            bases[basis]=index_payload(item['payload']);compared_hashes[key]=sha
            if sorted(bases[basis])!=plan['expected_dates'][code]:raise ValueError('changed_calendar')
        g=groups[code];nom,adj,bas,count=compare_code(code,g,bases['nominal'],bases['adjusted'])
        nominal_diffs+=nom;adjusted_diffs+=adj;basis_diffs+=bas;counts.append(count)
        valid={};constraint_cells=[]
        for r in g.to_dict('records'):
            day=str(r['date'].date());n=bases['nominal'][day];a=bases['adjusted'][day]
            for field in PRICE:
                if r['volume']==0 and field!='close':
                    if r[field]!=0 or r['amount']!=0:raise ValueError('unexpected_nontrade_convention')
                    comparable['nontrade_ohl_preserved']+=1;continue
                if D(str(r[field]))!=D(n[FIELDS[field]]):raise ValueError('raw_price_disagreement')
                valid[(day,field)]=True;comparable['adjusted_comparable_cells']+=1
                constraint_cells.append({'date':day,'field':field,'source':str(r['adj_'+field]),'provider':a[FIELDS[field]]})
        traded_diffs.extend(r for r in adj if (r['date'],r['field']) in valid)
        intervals.append({'code':code,**coefficient_interval(constraint_cells)})
    if len(frame)!=85104:raise ValueError('changed_total_dates')
    # The new panel must leave nominal data and provider-basis diagnostics exact.
    for name,rows in [('nominal_differences',nominal_diffs),('provider_basis_differences',basis_diffs)]:
        pd.testing.assert_frame_equal(pd.DataFrame(rows),pd.read_parquet(original/(name+'.parquet')),check_exact=True)
    for name,rows in [('nominal_differences',nominal_diffs),('adjusted_differences',adjusted_diffs),
                      ('provider_basis_differences',basis_diffs),('by_code',counts),('comparable_adjusted_differences',traded_diffs)]:
        save_frame(out/(name+'.parquet'),pd.DataFrame(rows))
    save_json(out/'intervals.json',intervals)
    hashes={str(p):digest(p) for p in [original/'plan.json',original/'nominal_differences.parquet',
        original/'provider_basis_differences.parquet',ROOT/'research/compare_lowliq_krx_source.py',
        ROOT/'research/capture_lowliq_krx_source.py']}
    save_json(out/'plan.json',{'source_path':str(source),'source_sha256':expected_sha256,'capture_plan_sha256':plan_sha,
        'response_sha256':compared_hashes,'input_sha256':hashes,'implementation_sha256':digest(Path(__file__)),
        'scope':'All original 1310 codes and 85104 dates, June30-Oct2. Nontrade zero OHL separated; all close/volume/amount retained. No source or performance certification.'})
    summary={'codes':len(codes),'rows':len(frame),'nominal_cells':sum(r['nominal_cells'] for r in counts),
        'nominal_diff_cells':len(nominal_diffs),'nominal_differences_unchanged':True,
        'provider_basis_differences_unchanged':True,'adjusted_cells':sum(r['adjusted_cells'] for r in counts),
        **comparable,'comparable_difference_cells':len(traded_diffs),
        'comparable_difference_codes':len({r['code'] for r in traded_diffs}),
        'comparable_difference_cells_over_one_krw':sum(r['exceeds_one_krw'] for r in traded_diffs),
        'codes_over_one_krw':sorted({r['code'] for r in traded_diffs if r['exceeds_one_krw']}),
        'max_comparable_difference':str(max(D(r['absolute_difference']) for r in traded_diffs)),
        'nonempty_half_open_interval_codes':sum(r['nonempty_half_open'] for r in intervals),
        'closed_bounds_overlap_codes':sum(r['closed_bounds_overlap'] for r in intervals),
        'empty_half_open_interval_codes':[r['code'] for r in intervals if not r['nonempty_half_open']],
        'max_interval_relative_gap':str(max(D(r['relative_gap']) for r in intervals)),
        'source_certified':False,'publication_allowed':False,'strategy_outcomes_computed':False}
    save_json(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--expected-sha256',required=True);args=p.parse_args()
    run(args.root,args.source,args.out,args.expected_sha256)
