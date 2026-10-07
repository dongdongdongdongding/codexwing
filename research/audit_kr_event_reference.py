"""Reconcile listing references with quote-implied bases, without strategy labels.

The quote reference is close minus its signed daily change. Requiring agreement
with the independently sourced nominal opening price avoids substituting the
notice's evaluated price or the first day's closing price for that reference.
"""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path
import re
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.run_lowliq_touch10_reconstruction import save_json

PARENT_SHA = '85bf1a928bdf9a9dd356a97d6dae9df8235cde49fdea3ef9ecd030cd38dcc122'
FIELDS = {'open':'stck_oprc','high':'stck_hgpr','low':'stck_lwpr','close':'stck_clpr'}
# Scope fixed before any correction or strategy outcome calculation.
EVENTS = [
    ('00088K','2026-08-25','supplement','000880_20260824000466_20260824001209_body_0',
     '000880_20260820000527_20260820001274_body_0'),
    ('002630','2026-09-22','supplement','002630_20260921000340_20260921001012_body_0',None),
    ('004870','2026-07-24','supplement','004870_20260723000583_20260723001304_body_0',None),
    ('006490','2026-09-10','supplement','006490_20260909000413_20260909001131_body_0',None),
    ('083660','2026-08-04','','083660_20260730000577_20260730001346_body_0',None),
    ('101000','2026-08-18','','101000_20260812000546_20260812001412_body_0',None),
    ('148780','2026-08-04','','148780_20260730000739_20260730001692_body_0',None),
    ('348080','2026-07-22','','348080_20260716000637_20260716001560_body_0',None),
    ('354200','2026-07-13','','354200_20260708000562_20260708001349_body_0',None),
    ('417310','2026-08-28','','417310_20260827000392_20260827000870_body_0',None),
]
OUTSIDE = [
    ('050110','2026-10-07','supplement','050110_20261006000662_20261006001534_body_0'),
    ('131400','2026-10-07','','131400_20261001000427_20261001001122_body_0'),
]


def quote_reference(row, raw_open, raw_close):
    close = F(row['stck_clpr']); change = F(row['prdy_vrss'])
    sign = row['prdy_vrss_sign']
    if sign not in {'1','2','3','4','5'}:
        raise ValueError('unknown_quote_sign')
    if ((sign in {'1','2'} and change <= 0) or
            (sign in {'4','5'} and change >= 0) or (sign == '3' and change != 0)):
        raise ValueError('inconsistent_quote_sign')
    reference = close - change
    if (reference <= 0 or reference.denominator != 1 or reference != F(row['stck_oprc'])
            or reference != F(str(raw_open)) or close != F(str(raw_close))
            or F(row['acml_vol']) <= 0):
        raise ValueError('unproved_quote_reference')
    return int(reference)


def load_body(corpus, subdir, key, receipts, hashes):
    base = corpus/subdir/'captures'/key
    receipt = json.loads(base.with_suffix('.json').read_text())
    if receipt['status'] != 200:
        raise ValueError('failed_primary_capture')
    for ext, field in [('html','sha256'),('txt','text_sha256')]:
        path = base.with_suffix('.'+ext)
        if digest(path) != receipt[field]:
            raise ValueError('changed_primary_capture')
        hashes[str(path)] = receipt[field]
    receipts[key] = {'subdir':subdir, 'receipt':receipt}
    return ' '.join(base.with_suffix('.txt').read_text().split())


def run(root):
    audit = root/'runtime_state/audit'; corpus = audit/'kr_remaining_action_documents_20261007'
    out = audit/'kr_event_reference_basis_20261007'; out.mkdir(exist_ok=True)
    source = audit/'kr_verified_events_v5_20261007/panel.parquet'
    if digest(source) != PARENT_SHA:
        raise ValueError('changed_parent')
    codes = sorted([r[0] for r in EVENTS]+[r[0] for r in OUTSIDE])
    panel = pd.read_parquet(source, filters=[('code','in',codes),('date','>=',pd.Timestamp('2026-06-30'))])
    plan_path = audit/'lowliq_krx_comparison_20261007/plan.json'
    price_plan = json.loads(plan_path.read_text())
    hashes = {str(source):PARENT_SHA, str(plan_path):digest(plan_path)}
    providers = {}; receipts = {}; events = []; excluded = []; cells = []; summaries = []
    for code in codes:
        providers[code] = {}
        for basis in ['nominal','adjusted']:
            path = audit/'lowliq_krx_source_20261007/responses'/f'{code}_{basis}.json'
            sha = digest(path)
            if sha != price_plan['response_sha256'][code+'_'+basis]:
                raise ValueError('changed_provider')
            hashes[str(path)] = sha
            rows = json.loads(path.read_text())['payload']['output2']
            indexed = {r['stck_bsop_date']:r for r in rows}
            if len(indexed) != len(rows) or len(rows) != 65:
                raise ValueError('changed_provider_scope')
            providers[code][basis] = indexed
        if set(providers[code]['nominal']) != set(providers[code]['adjusted']):
            raise ValueError('inconsistent_provider_dates')
    for code, date, subdir, key, identity_key in EVENTS:
        text = load_body(corpus,subdir,key,receipts,hashes)
        if date not in text:
            raise ValueError('unproved_effective_date')
        method = '최초가격이 기준가격이 됨' in text
        evaluated = None
        if method:
            stock_class = '3우선주B' if code == '00088K' else '보통주식'
            match = re.search(stock_class+r' ([\d,]+)원? ([\d,]+)원? ([\d,]+)원?',text)
            if not match:
                raise ValueError('missing_auction_bounds')
            evaluated, upper, lower = [int(v.replace(',','')) for v in match.groups()]
        elif 'A'+code not in text or '감자(무상)' not in text:
            raise ValueError('unproved_listing_identity')
        if identity_key:
            identity = load_body(corpus,subdir,identity_key,receipts,hashes)
            korean_date = date[:4]+'년'+date[5:7]+'월'+date[8:]+'일'
            if 'KR700088K015' not in identity or 'A00088K' not in identity or korean_date not in identity:
                raise ValueError('unproved_preferred_identity')
        g = panel[panel.code.eq(code)].sort_values('date')
        before = g[g.date.lt(date)].iloc[-1]; first = g[g.date.eq(date)]
        if len(first) != 1:
            raise ValueError('missing_event_row')
        first = first.iloc[0]; row = providers[code]['nominal'][date.replace('-','')]
        reference = quote_reference(row,first['open'],first['close'])
        if method and not lower <= reference <= upper:
            raise ValueError('reference_outside_official_bounds')
        prior = int(before['close'])
        if str(prior) != providers[code]['nominal'][before.date.strftime('%Y%m%d')]['stck_clpr']:
            raise ValueError('unproved_prior_close')
        overlay = F(str(before.adj_factor))*F(prior,reference)/F(str(first.adj_factor))
        events.append({'code':code,'date':date,'body':key,'identity_body':identity_key,
            'body_subdir':subdir,'source_url':receipts[key]['receipt']['request']['url'],
            'official_first_price_method_explicit':method,'evaluated_price':evaluated,
            'reference_price':reference,'prior_date':str(before.date.date()),'prior_close':prior,
            'first_close':int(first['close']),'signed_quote_change':row['prdy_vrss'],
            'before_factor':float(before.adj_factor),'old_event_factor':float(first.adj_factor),
            'overlay_numerator':overlay.numerator,'overlay_denominator':overlay.denominator,
            'basis':'official_notice_plus_KIS_signed_change_and_independent_marcap_open',
            'source_certified':False})
    for code,date,subdir,key in OUTSIDE:
        text = load_body(corpus,subdir,key,receipts,hashes)
        if date not in text or 'A'+code not in text:
            raise ValueError('unproved_outside_event')
        excluded.append({'code':code,'date':date,'body':key,'source_url':receipts[key]['receipt']['request']['url'],
            'status':'after_frozen_source_end_no_overlay','provider_asof_adjustment_includes_later_basis':True})
    for code in codes:
        g = panel[panel.code.eq(code)].sort_values('date'); event = next((e for e in events if e['code']==code),None)
        if len(g)!=65 or set(g.date.dt.strftime('%Y%m%d'))!=set(providers[code]['nominal']):
            raise ValueError('changed_panel_scope')
        factors = [F(str(v)) for v in g.adj_factor]
        if event:
            overlay=F(event['overlay_numerator'],event['overlay_denominator'])
            factors=[v*overlay if dt>=pd.Timestamp(event['date']) else v for v,dt in zip(factors,g.date)]
        last = factors[-1]; start = len(cells); raw_count=0; zero_count=0
        interval_lo = F(0); interval_hi = None
        for i,r in enumerate(g.to_dict('records')):
            day=r['date'].strftime('%Y%m%d');n=providers[code]['nominal'][day];a=providers[code]['adjusted'][day]
            if F(str(r['volume']))!=F(n['acml_vol']): raise ValueError('raw_volume_mismatch')
            for field,k in FIELDS.items():
                if r['volume']==0 and field!='close':
                    if r[field]!=0: raise ValueError('unexpected_nontrade_ohl')
                    zero_count+=1;continue
                raw_count+=1
                if F(str(r[field]))!=F(n[k]):raise ValueError('raw_price_mismatch')
                nominal=F(n[k]);adjusted=F(a[k]);projected=nominal*factors[i]/last
                if nominal<=0:raise ValueError('nonpositive_price')
                interval_lo=max(interval_lo,adjusted/nominal)
                upper=(adjusted+1)/nominal;interval_hi=upper if interval_hi is None else min(interval_hi,upper)
                cells.append({'code':code,'date':day,'field':field,'nominal':n[k],
                    'provider_adjusted':a[k],'projected_numerator':projected.numerator,
                    'projected_denominator':projected.denominator,'abs_difference':float(abs(projected-adjusted))})
        part=cells[start:]
        summaries.append({'code':code,'dates':len(g),'raw_comparable_cells':raw_count,
            'nontrade_ohl_preserved':zero_count,'overlay_proposed':bool(event),
            'projected_max_abs_difference':max(x['abs_difference'] for x in part) if event else None,
            'all_window_constant_provider_coefficient_interval_nonempty':interval_lo<interval_hi,
            'constant_coefficient_lower':[interval_lo.numerator,interval_lo.denominator],
            'constant_coefficient_upper_exclusive':[interval_hi.numerator,interval_hi.denominator]})
    result={'events':events,'outside_events':excluded,'comparisons':summaries,
        'source_certified':False,'portfolio_return_certified':False,'normalization_applied':False,
        'strategy_outcomes_computed':False,'source_sha256':PARENT_SHA,'input_sha256':hashes,
        'implementation_sha256':digest(Path(__file__)),
        'limitations':'Quote-implied price continuity is not shareholder wealth. Five KOSDAQ notices prove changed-listing dates but do not spell out the auction method. Current captured quotes are not historical PIT observations. Earlier histories remain unaudited. Two later events explain an external adjusted scale; no later event is inserted into the as-of source.'}
    save_json(out/'comparison_cells.json',cells);save_json(out/'receipts.json',receipts);save_json(out/'result.json',result)
    print(json.dumps({'events':events,'outside':excluded,'comparisons':summaries},ensure_ascii=False),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    run(parser.parse_args().root)
