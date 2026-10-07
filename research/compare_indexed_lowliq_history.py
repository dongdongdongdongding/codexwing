"""Compare a frozen historical capture index to a pinned corrected source.

Only fully attempted, usable codes are compared. Missing and unavailable scope
remains explicit; no strategy outcome or source-certification verdict is emitted.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import json
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.recover_lowliq_history_request import digest, resolve_response
from research.capture_lowliq_krx_source import payload_sha, inspect_payload
from research.compare_lowliq_krx_source import compare_code, index_payload, FIELDS, PRICE
from research.run_lowliq_touch10_reconstruction import save_json, save_frame

TABLE_COLUMNS={
    'nominal_differences':['code','date','field','panel','kis_nominal','nontraded_zero_ohl_convention'],
    'adjusted_differences':['code','date','field','scaled_panel','kis_adjusted','absolute_difference',
                            'exceeds_one_krw','nontraded_zero_ohl_convention'],
    'provider_basis_differences':['code','date','different_fields','close_basis_ratio','nominal_volume',
        'adjusted_volume','inverse_price_volume_error_shares','volume_diff','amount_diff',
        'provider_prtt_rate_nominal','provider_prtt_rate_adjusted'],
    'by_code':['code','rows','anchor_date','constant_scale','nominal_cells','adjusted_cells',
               'nominal_diff_cells','adjusted_diff_cells','adjusted_diff_cells_over_one_krw'],
}


def indexed_receipt(entry,request,scope_sha,capture):
    original=capture/'responses'/(request['id']+'.json')
    if Path(entry['original_path']).resolve()!=original.resolve():raise ValueError('unexpected_original_path')
    provenance=entry['provenance']
    if digest(original)!=provenance['original_sha256']:raise ValueError('changed_original_response')
    item=json.loads(original.read_text())
    identity={'code':request['code'],'market_div':'J','period':'D','start_date':request['start_date'],
              'end_date':request['end_date'],'adjusted':request['basis']=='adjusted'}
    if item['request']!=identity or item['plan_sha256']!=scope_sha or item['inspection']['status']!=entry['original_status']:
        raise ValueError('changed_original_identity')
    effective=Path(entry['effective_path'])
    if provenance['kind']=='original':
        if effective.resolve()!=original.resolve():raise ValueError('unexpected_effective_path')
    elif provenance['kind']=='reviewed_supplement':
        if effective.name!='response.json':raise ValueError('unexpected_supplement_path')
        resolved=resolve_response(original,effective.parent,expected_plan_sha256=provenance['supplement_plan_sha256'])
        if resolved['provenance']!=provenance:raise ValueError('changed_supplement_provenance')
        item=resolved['receipt']
    else:raise ValueError('unknown_response_provenance')
    if digest(effective)!=entry['effective_sha256']:raise ValueError('changed_effective_response')
    if item['request']!=identity or item['inspection']['status']!=entry['effective_status']:raise ValueError('changed_effective_identity')
    if 'payload' in item:
        if payload_sha(item['payload'])!=item['payload_sha256']:raise ValueError('changed_payload')
        if inspect_payload(item['payload'],identity,request['expected_dates'])!=item['inspection']:raise ValueError('changed_inspection')
    elif item['inspection']!={'status':'REQUEST_ERROR'}:raise ValueError('unexplained_missing_payload')
    return item


def load_snapshot(scope_path,index_path,capture,expected_index_sha):
    if digest(index_path)!=expected_index_sha:raise ValueError('changed_frozen_index')
    scope=json.loads(scope_path.read_text());scope_sha=digest(scope_path);index=json.loads(index_path.read_text())
    if index['scope_plan_sha256']!=scope_sha or digest(capture/'manifest.json')!=index['capture_manifest_sha256']:
        raise ValueError('changed_scope_or_manifest')
    requests={r['id']:r for r in scope['requests']};entries={e['request_id']:e for e in index['entries']}
    if len(requests)!=len(scope['requests']) or len(entries)!=len(index['entries']):raise ValueError('duplicate_identity')
    if set(entries)-set(requests):raise ValueError('receipt_outside_scope')
    if (index['target_requests']!=len(requests) or index['snapshot_receipts']!=len(entries)
            or index['unvisited_at_snapshot']!=len(requests)-len(entries)):raise ValueError('changed_coverage_counts')
    original=Counter(e['original_status'] for e in entries.values());effective=Counter(e['effective_status'] for e in entries.values())
    supplements=sorted(k for k,e in entries.items() if e['provenance']['kind']=='reviewed_supplement')
    if dict(original)!=index['original_status_counts'] or dict(effective)!=index['effective_status_counts'] or supplements!=index['reviewed_supplements_used']:
        raise ValueError('changed_coverage_statuses')
    grouped=defaultdict(list)
    for request in requests.values():grouped[request['code']].append(request)
    available={};partial=[];unavailable=[];extras=[]
    for code,rs in sorted(grouped.items()):
        missing=[r['id'] for r in rs if r['id'] not in entries]
        if missing:
            partial.append({'code':code,'unvisited_requests':missing});continue
        bases={'nominal':{},'adjusted':{}};bad=[]
        for request in rs:
            item=indexed_receipt(entries[request['id']],request,scope_sha,capture)
            if item['inspection']['status']!='CAPTURED':
                bad.append({'id':request['id'],'status':item['inspection']['status']});continue
            rows=index_payload(item['payload']);expected=set(request['expected_dates'])
            if len(expected)!=len(request['expected_dates']):raise ValueError('duplicate_expected_date')
            extra=sorted(set(rows)-expected)
            if extra:extras.append({'id':request['id'],'additional_dates':extra})
            target=bases[request['basis']]
            if set(target)&expected:raise ValueError('overlapping_scope_windows')
            target.update({day:rows[day] for day in expected})
        if bad:unavailable.append({'code':code,'requests':bad});continue
        if set(bases['nominal'])!=set(bases['adjusted']):raise ValueError('different_basis_scope')
        available[code]=bases
    return available,{'target_codes':len(grouped),'fully_attempted_codes':len(grouped)-len(partial),
        'usable_codes':len(available),'partial_codes':partial,'unavailable_codes':unavailable,
        'additional_provider_dates':extras,'indexed_requests':len(entries),'target_requests':len(requests),
        'unvisited_requests':len(requests)-len(entries),'supplements':supplements}


def zero_ohl_representation(left,right,left_close,right_close,source,provider):
    values=[Decimal(str(v)) for v in [left,right,left_close,right_close,source['volume'],source['amount'],
                                      provider['acml_vol'],provider['acml_tr_pbmn']]]
    if not all(v.is_finite() for v in values) or any(v!=0 for v in values[4:]):return False
    a,b,ac,bc=values[:4]
    return (a==0 and b==bc and b>0) or (b==0 and a==ac and a>0)


def compare_frame(raw,available):
    groups={str(code):g for code,g in raw.groupby('code')};nominal=[];adjusted=[];basis=[];counts=[]
    for code,sources in sorted(available.items()):
        if code not in groups:raise ValueError('source_code_absent')
        g=groups[code];g=g.loc[g.date.dt.strftime('%Y-%m-%d').isin(sources['nominal'])]
        n,a,b,c=compare_code(code,g,sources['nominal'],sources['adjusted'])
        source_rows={str(r['date'].date()):r for r in g.to_dict('records')}
        for row in n:
            r=sources['nominal'][row['date']];s=source_rows[row['date']]
            row['nontraded_zero_ohl_convention']=(row['field'] in ['open','high','low'] and
                zero_ohl_representation(row['panel'],row['kis_nominal'],s['close'],r['stck_clpr'],s,r))
        for row in a:
            r=sources['adjusted'][row['date']];s=source_rows[row['date']]
            row['nontraded_zero_ohl_convention']=(row['field'] in ['open','high','low'] and
                zero_ohl_representation(row['scaled_panel'],row['kis_adjusted'],
                    Decimal(str(s['adj_close']))*Decimal(c['constant_scale']),r['stck_clpr'],s,r))
        nominal.extend(n);adjusted.extend(a);basis.extend(b);counts.append(c)
    comparable=[r for r in adjusted if not r['nontraded_zero_ohl_convention']]
    summary={'compared_codes':len(counts),'compared_rows':sum(r['rows'] for r in counts),
        'nominal_cells':sum(r['nominal_cells'] for r in counts),'nominal_diff_cells':len(nominal),
        'nominal_diff_fields':dict(Counter(r['field'] for r in nominal)),
        'nominal_nonconventional_diff_cells':sum(not r['nontraded_zero_ohl_convention'] for r in nominal),
        'adjusted_diff_cells':len(adjusted),'comparable_adjusted_diff_cells':len(comparable),
        'codes_without_traded_anchor':[r['code'] for r in counts if r['anchor_date'] is None],
        'comparable_codes_over_one_krw':sorted({r['code'] for r in comparable if r['exceeds_one_krw']}),
        'nonfinite_comparable_differences':sum(not Decimal(r['absolute_difference']).is_finite() for r in comparable),
        'max_comparable_difference':str(max((Decimal(r['absolute_difference']) for r in comparable
            if Decimal(r['absolute_difference']).is_finite()),default=Decimal(0))),
        'source_certified':False,'publication_allowed':False,'strategy_outcomes_computed':False}
    return {'nominal_differences':nominal,'adjusted_differences':adjusted,
            'provider_basis_differences':basis,'by_code':counts},summary


def run(scope,index,capture,source,out,*,index_sha,source_sha):
    available,coverage=load_snapshot(scope,index,capture,index_sha)
    if digest(source)!=source_sha:raise ValueError('changed_source')
    dependencies={name:digest(ROOT/name) for name in ['research/compare_lowliq_krx_source.py',
        'research/capture_lowliq_krx_source.py','research/recover_lowliq_history_request.py']}
    save_json(out/'plan.json',{'index_sha256':index_sha,'scope_sha256':digest(scope),'source_sha256':source_sha,
        'implementation_sha256':digest(Path(__file__)),'dependencies':dependencies,
        'scope':'All fully attempted and usable codes of the fixed index; missing/unavailable scope retained. '
          'Exact nominal comparison and last-traded-anchor adjusted diagnostics, never certification.'})
    raw=pd.read_parquet(source,columns=['code','date',*FIELDS,*['adj_'+p for p in PRICE]],
                        filters=[('code','in',list(available))]) if available else pd.DataFrame(columns=['code'])
    tables,summary=compare_frame(raw,available)
    for name,rows in tables.items():save_frame(out/(name+'.parquet'),pd.DataFrame(rows,columns=TABLE_COLUMNS[name]))
    save_json(out/'coverage.json',coverage);save_json(out/'summary.json',summary)
    return {**summary,**{k:v for k,v in coverage.items() if k not in ['partial_codes','unavailable_codes','additional_provider_dates']}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ['scope','index','capture','source','out']:p.add_argument('--'+arg,type=Path,required=True)
    for arg in ['index-sha','source-sha']:p.add_argument('--'+arg,required=True)
    args=p.parse_args()
    print(json.dumps(run(args.scope,args.index,args.capture,args.source,args.out,
                        index_sha=args.index_sha,source_sha=args.source_sha),indent=2))
