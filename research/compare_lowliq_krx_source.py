"""Compare immutable KRX source evidence without any strategy outcomes.

Exact nominal field differences and adjusted-path differences are diagnostics,
not automatic repair authority. A common last-traded close only removes constant
currency scaling; it does not establish corporate-action correctness or PIT data.
"""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.capture_lowliq_krx_source import payload_sha
from research.run_lowliq_touch10_reconstruction import save_json, save_frame

FIELDS = {'open':'stck_oprc','high':'stck_hgpr','low':'stck_lwpr',
          'close':'stck_clpr','volume':'acml_vol','amount':'acml_tr_pbmn'}
PRICE = ['open','high','low','close']
def D(value):
    return Decimal('NaN') if value is None else Decimal(str(value))


def positive(value):
    value = D(value)
    return value.is_finite() and value > 0


def index_payload(payload):
    if payload['rt_cd'] != '0':
        raise ValueError('provider_error')
    rows = {pd.Timestamp(row['stck_bsop_date']).strftime('%Y-%m-%d'):row
            for row in payload['output2']}
    if len(rows) != len(payload['output2']):
        raise ValueError('duplicate_provider_date')
    return rows


def compare_code(code, raw, nominal, adjusted):
    source = {str(row['date'].date()):row for row in raw.to_dict('records')}
    if len(source) != len(raw) or set(source) != set(nominal) or set(source) != set(adjusted):
        raise ValueError('source_date_coverage_mismatch')
    anchor_days = [day for day,row in source.items() if
        positive(row['volume']) and positive(nominal[day]['acml_vol']) and
        positive(row['adj_close']) and positive(adjusted[day]['stck_clpr'])]
    anchor = max(anchor_days) if anchor_days else None
    scale = D(adjusted[anchor]['stck_clpr']) / D(source[anchor]['adj_close']) if anchor else None
    nominal_diffs, adjusted_diffs, basis_diffs = [], [], []
    comparisons = Counter()
    for day, row in sorted(source.items()):
        nom, adj = nominal[day], adjusted[day]
        for name, field in FIELDS.items():
            old, new = D(row[name]), D(nom[field])
            comparisons['nominal_cells'] += 1
            if not old.is_finite() or not new.is_finite() or old != new:
                nominal_diffs.append({'code':code,'date':day,'field':name,
                                      'panel':str(old),'kis_nominal':str(new)})
        if scale is not None:
            for name in PRICE:
                old, new = D(row['adj_'+name])*scale, D(adj[FIELDS[name]])
                comparisons['adjusted_cells'] += 1
                error = abs(old-new)
                if not error.is_finite() or error > D('0.000001'):
                    adjusted_diffs.append({'code':code,'date':day,'field':name,
                        'scaled_panel':str(old),'kis_adjusted':str(new),
                        'absolute_difference':str(error),'exceeds_one_krw':bool(error.is_finite() and error>1)})
        changed = [name for name,field in FIELDS.items() if D(nom[field]) != D(adj[field])]
        if changed:
            p = D(adj['stck_clpr'])/D(nom['stck_clpr']) if D(nom['stck_clpr'])>0 else None
            err = D(adj['acml_vol'])-D(nom['acml_vol'])/p if p is not None and p>0 else None
            basis_diffs.append({'code':code,'date':day,'different_fields':','.join(changed),
                'close_basis_ratio':str(p) if p is not None else None,
                'nominal_volume':nom['acml_vol'],'adjusted_volume':adj['acml_vol'],
                'inverse_price_volume_error_shares':str(err) if err is not None else None,
                'volume_diff': 'volume' in changed, 'amount_diff':'amount' in changed,
                'provider_prtt_rate_nominal':nom.get('prtt_rate'),
                'provider_prtt_rate_adjusted':adj.get('prtt_rate')})
    return nominal_diffs, adjusted_diffs, basis_diffs, {
        'code':code,'rows':len(raw),'anchor_date':anchor,'constant_scale':str(scale),
        **comparisons,'nominal_diff_cells':len(nominal_diffs),
        'adjusted_diff_cells':len(adjusted_diffs),
        'adjusted_diff_cells_over_one_krw':sum(r['exceeds_one_krw'] for r in adjusted_diffs)}


def run(root):
    capture = root/'runtime_state/audit/lowliq_krx_source_20261007'
    source = root/'runtime_state/audit/kr_adjustment_asof_20261007/final/panel.parquet'
    plan_path = capture/'plan.json';plan = json.loads(plan_path.read_text())
    if digest(source) != plan['parent_manifest']['sources']['panel']:
        raise ValueError('changed_frozen_panel')
    runs = [json.loads(p.read_text()) for p in sorted((capture/'runs').glob('*.json'))]
    complete = [r for r in runs if r['completed_attempts']==r['target_requests']]
    if not complete:
        raise ValueError('incomplete_capture')
    receipt = complete[-1]; plan_hash = digest(plan_path)
    out = root/'runtime_state/audit/lowliq_krx_comparison_20261007'
    save_json(out/'plan.json', {'capture_plan_sha256':plan_hash,'panel_sha256':digest(source),
        'code_sha256':digest(Path(__file__)), 'response_sha256':receipt['response_sha256'],
        'nominal_comparison':'Exact Decimal OHLCV and traded amount on every existing source date.',
        'adjusted_comparison':'Scale frozen full-panel adjusted OHLC to last common traded KIS adjusted close. '
          'Report abs differences >1e-6 and >1KRW as diagnostics, not certification thresholds.',
        'scope':'June30-Oct2 only; no feature lookback, historical publication/PIT or final H10 coverage certificate.',
        'publication_allowed':False,'test_outcomes_computed':False})
    frame = pd.read_parquet(source, columns=['code','date',*FIELDS,*['adj_'+p for p in PRICE]],
                            filters=[('date','>=',pd.Timestamp('2026-06-30')),
                                     ('date','<=',pd.Timestamp('2026-10-02'))])
    groups = {code:g for code,g in frame.loc[frame.code.isin(plan['expected_dates'])].groupby('code')}
    nominal_diffs, adjusted_diffs, basis_diffs, counts = [], [], [], []
    for code in sorted(plan['expected_dates']):
        bases = {}
        for basis in ['nominal','adjusted']:
            key=f'{code}_{basis}';path=capture/'responses'/f'{key}.json'
            if digest(path)!=receipt['response_sha256'][key]:raise ValueError('changed_response')
            item=json.loads(path.read_text())
            if (item['plan_sha256']!=plan_hash or item['code']!=code or
                item['request']!={**plan['request'],'adjusted':basis=='adjusted'} or
                payload_sha(item['payload'])!=item['payload_sha256']):raise ValueError('changed_source_identity')
            bases[basis]=index_payload(item['payload'])
            if sorted(bases[basis])!=plan['expected_dates'][code]:raise ValueError('changed_source_calendar')
        nom,adj,bas,count=compare_code(code,groups[code],bases['nominal'],bases['adjusted'])
        nominal_diffs.extend(nom);adjusted_diffs.extend(adj);basis_diffs.extend(bas);counts.append(count)
    for name,rows in [('nominal_differences',nominal_diffs),('adjusted_differences',adjusted_diffs),
                      ('provider_basis_differences',basis_diffs),('by_code',counts)]:
        save_frame(out/(name+'.parquet'),pd.DataFrame(rows))
    summary={'codes':len(counts),'rows':sum(r['rows'] for r in counts),
        'nominal_cells':sum(r['nominal_cells'] for r in counts),
        'nominal_diff_cells':len(nominal_diffs),'nominal_diff_rows':len({(r['code'],r['date']) for r in nominal_diffs}),
        'nominal_diff_codes':len({r['code'] for r in nominal_diffs}),
        'nominal_diff_fields':dict(Counter(r['field'] for r in nominal_diffs)),
        'adjusted_cells':sum(r.get('adjusted_cells',0) for r in counts),
        'codes_without_traded_anchor':[r['code'] for r in counts if r['anchor_date'] is None],
        'adjusted_diff_cells':len(adjusted_diffs),'adjusted_diff_codes':len({r['code'] for r in adjusted_diffs}),
        'adjusted_cells_over_one_krw':sum(r['exceeds_one_krw'] for r in adjusted_diffs),
        'provider_volume_diff_rows':sum(r['volume_diff'] for r in basis_diffs),
        'provider_amount_diff_rows':sum(r['amount_diff'] for r in basis_diffs),
        'source_basis_certified':False,'test_outcomes_computed':False,'publication_allowed':False}
    save_json(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    return summary


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True)
    run(ap.parse_args().root)
