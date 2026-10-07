"""Reconcile captured ex-right references, entitlements and rounded provider prices.

An offline source diagnostic only: no source replacement or strategy labels.
"""
import argparse
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.run_lowliq_touch10_reconstruction import save_json

D = Decimal
FIELDS = {'open':'stck_oprc', 'high':'stck_hgpr', 'low':'stck_lwpr', 'close':'stck_clpr'}


def parse_notice(query_code, title, text):
    text = ' '.join(text.split())
    date = re.search(r'2026-\d{2}-\d{2}', text)
    kind = 'bonus' if '무상증자' in text else 'rights' if '유상증자' in text else None
    if query_code == '012200' and '계양전기우' in title:
        code = '012205'
        if '1우선주' not in text:
            raise ValueError('preferred_class_not_proved')
    else:
        code = query_code
    match = re.search(r'A' + re.escape(code) + r' ([\d,]+) 2026-', text)
    if not match:
        match = re.search(r'(?:보통주식|1우선주) ([\d,]+) 3\. 사유', text)
    if not date or not kind or not match:
        raise ValueError('unresolved_exrights_notice')
    return {'code':code, 'query_code':query_code, 'date':date.group(),
            'kind':kind, 'reference_price':match.group(1).replace(',', ''),
            'identity_basis':'direct_short_code' if 'A'+code in text else 'issuer_name_and_stock_class'}


def project_price(nominal, rates, *, round_each=False):
    value = D(nominal)
    for rate in rates:
        value *= D(1) + D(rate) / D(100)
        if round_each:
            value = value.to_integral_value(rounding=ROUND_DOWN)
    return value.to_integral_value(rounding=ROUND_DOWN)


def load_capture(corpus, key):
    base = corpus/'captures'/key
    receipt = json.loads(base.with_suffix('.json').read_text())
    if (receipt['status'] != 200 or digest(base.with_suffix('.html')) != receipt['sha256']
            or digest(base.with_suffix('.txt')) != receipt['text_sha256']):
        raise ValueError('changed_official_capture')
    return base.with_suffix('.txt').read_text(), receipt


def run(root):
    audit = root/'runtime_state/audit'; corpus = audit/'kr_remaining_action_documents_20261007'
    base = json.loads((corpus/'first_result.json').read_text())
    events=[]; hashes={}; entitlements={}
    for item in base['results']:
        for doc in item['documents']:
            if '권리락' not in doc['title']:
                continue
            key = doc['body_keys'][-1]; text, receipt = load_capture(corpus, key)
            event = parse_notice(item['code'], doc['title'], text)
            event.update({'acptno':doc['acptno'], 'body_key':key,
                          'source_url':receipt['request']['url'], 'title':doc['title']})
            hashes[key] = receipt['sha256']; events.append(event)
    events.sort(key=lambda e:(e['code'], e['date']))
    if len(events) != 18 or len({e['code'] for e in events}) != 17:
        raise ValueError('changed_fixed_notice_scope')
    bonus_codes={e['code'] for e in events if e['kind']=='bonus'}
    for item in base['results']:
        if item['code'] not in bonus_codes:
            continue
        decisions=[d for d in item['documents'] if '무상증자' in d['title'] and '결정' in d['title']]
        if len(decisions) != 1:
            raise ValueError('ambiguous_bonus_decision')
        key=decisions[0]['body_keys'][-1];text,receipt=load_capture(corpus,key)
        ratios=re.findall(r'1주당 신주배정 주식수 보통주식 \(주\) ([0-9.]+)', ' '.join(text.split()))
        if len(set(ratios)) != 1:
            raise ValueError('ambiguous_bonus_entitlement')
        entitlements[item['code']]={'new_shares_per_share':ratios[0], 'body_key':key,
                                   'source_url':receipt['request']['url']}
        hashes[key]=receipt['sha256']
    price_plan_path=audit/'lowliq_krx_comparison_20261007/plan.json'
    price_plan=json.loads(price_plan_path.read_text()); providers={}; provider_hashes={}
    for code in sorted({e['code'] for e in events}):
        providers[code]={}
        for basis in ['nominal','adjusted']:
            path=audit/'lowliq_krx_source_20261007/responses'/f'{code}_{basis}.json'
            expected=price_plan['response_sha256'][code+'_'+basis]
            if digest(path)!=expected:
                raise ValueError('changed_provider_capture')
            rows=json.loads(path.read_text())['payload']['output2']
            if len(rows)!=len({r['stck_bsop_date'] for r in rows}):
                raise ValueError('duplicate_provider_date')
            providers[code][basis]={r['stck_bsop_date']:r for r in rows}
            provider_hashes[code+'_'+basis]=expected
        if set(providers[code]['nominal']) != set(providers[code]['adjusted']):
            raise ValueError('provider_date_scope_disagreement')
    out=audit/'kr_exrights_basis_20261007';out.mkdir(exist_ok=True)
    plan={'events':events,'entitlements':entitlements,'official_body_hashes':hashes,
          'provider_response_hashes':provider_hashes,'price_plan_sha256':digest(price_plan_path),
          'corpus_result_sha256':digest(corpus/'first_result.json'),'implementation_sha256':digest(Path(__file__)),
          'hypotheses':['Decimal reported-rate product then truncate once','Decimal reported-rate product with truncation after each event'],
          'source_certified':False,'scope':'All 18 captured ex-right notices; all available nominal/adjusted OHLC dates for 17 exact securities. Missing pre-event evidence remains explicit.'}
    save_json(out/'plan.json',plan)
    event_checks=[]
    for event in events:
        code=event['code'];nominal=providers[code]['nominal'];adjusted=providers[code]['adjusted'];dt=event['date'].replace('-','')
        earlier=sorted(d for d in nominal if d<dt)
        row={**event, 'entitlement':entitlements.get(code) if event['kind']=='bonus' else None}
        if not earlier or dt not in adjusted:
            row.update({'status':'outside_captured_provider_window', 'prior_price_verified':False})
        else:
            prior=nominal[earlier[-1]];close=D(prior['stck_clpr']);ref=D(event['reference_price'])
            actual=D(adjusted[dt]['prtt_rate']);reference_pct=(ref/close-D(1))*100
            row.update({'status':'compared','prior_date':earlier[-1], 'prior_nominal_close':str(close),
                        'reference_backward_coefficient':str(ref/close), 'reference_forward_factor':str(close/ref),
                        'reference_percent_exact':str(reference_pct),
                        'reference_percent_rounded_2dp':str(reference_pct.quantize(D('.01'),rounding=ROUND_HALF_UP)),
                        'reported_provider_percent':str(actual),
                        'provider_matches_rounded_reference_percent':actual==reference_pct.quantize(D('.01'),rounding=ROUND_HALF_UP)})
        event_checks.append(row)
    comparisons=[];summaries=[]
    for code,pair in providers.items():
        nominal=pair['nominal'];adjusted=pair['adjusted'];dates=sorted(nominal)
        rate_events=[(dt,r['prtt_rate']) for dt,r in sorted(adjusted.items()) if D(r['prtt_rate'])!=0]
        start=len(comparisons)
        for dt in dates:
            rates=[rate for when,rate in rate_events if when>dt]
            for field,key in FIELDS.items():
                actual=D(adjusted[dt][key]);n=nominal[dt][key]
                once=project_price(n,rates);each=project_price(n,rates,round_each=True)
                comparisons.append({'code':code,'date':dt,'field':field,'nominal':n,
                                    'provider_adjusted':str(actual),'projected_round_once':str(once),
                                    'projected_round_each':str(each),'once_exact':once==actual,'each_exact':each==actual,
                                    'once_error':str(abs(once-actual)), 'rates':rates})
        part=comparisons[start:]
        summaries.append({'code':code,'dates':len(dates),'cells':len(part),'rate_events':rate_events,
                          'round_once_exact':sum(r['once_exact'] for r in part),
                          'round_each_exact':sum(r['each_exact'] for r in part),
                          'max_abs_round_once_error':str(max(D(r['once_error']) for r in part))})
    save_json(out/'comparison_cells.json',comparisons)
    result={'event_checks':event_checks,'provider_checks':summaries,
            'notices':len(events),'securities':len(providers),'cells':len(comparisons),
            'round_once_exact_cells':sum(r['once_exact'] for r in comparisons),
            'round_each_exact_cells':sum(r['each_exact'] for r in comparisons),
            'source_certified':False,'normalization_applied':False,'strategy_outcomes_computed':False}
    save_json(out/'result.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='event_checks'},ensure_ascii=False),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    run(parser.parse_args().root)
