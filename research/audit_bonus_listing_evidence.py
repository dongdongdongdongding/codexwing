"""Verify six fixed exchange bonus-listing notices and listing-day instrument trades.

No strategy selections, returns or touch labels are read. Exchange listing and
instrument trading do not prove a particular account's unrestricted share credit.
"""
import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.run_lowliq_touch10_reconstruction import save_json
from research.audit_nominal_entitlement_schedule import PLAN_SHA256

SCHEDULE_SHA256 = '925eec68875db61b61db6b6702d782c8301d90dacf2ac087b2de66b8c2beab7f'
AS_OF = '2026-10-07'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_listing(text, expected_code):
    text = ' '.join(text.split())
    if '무상증자' not in text:
        raise ValueError('not_bonus_listing')
    rows = re.findall(r'보통주\s+A(\d{6})\s+([\d,]+)', text)
    if rows:
        if len(rows) != 1 or rows[0][0] != expected_code:
            raise ValueError('listing_security_identity_mismatch')
        quantity = int(rows[0][1].replace(',', ''))
    else:
        codes = re.findall(r'단축코드\s*:\s*A(\d{6})', text)
        quantities = re.findall(r'기명식\s*보통주\s+([\d,]+)주', text)
        isin = re.findall(r'표준코드\s*:\s*(KR[0-9A-Z]+)', text)
        if codes != [expected_code] or len(quantities) != 1 or len(isin) != 1 or expected_code not in isin[0]:
            raise ValueError('listing_security_identity_mismatch')
        quantity = int(quantities[0].replace(',', ''))
    dates = re.findall(r'(?:⑥\s*상장일\s*:|5\.\s*상장일)\s*(\d{4})[-년]\s*(\d{1,2})[-월]\s*(\d{1,2})(?:일)?(?=\s|$)', text)
    if len(dates) != 1 or quantity <= 0:
        raise ValueError('ambiguous_listing_date_or_quantity')
    listing = date(*map(int, dates[0])).isoformat()
    restrictions = []
    for keyword in ('의무보유', '의무예탁'):
        if keyword in text:
            restrictions.append(keyword)
    return {'code': expected_code, 'listing_date': listing, 'additional_common_shares': quantity,
            'restriction_types_in_notice': restrictions,
            'account_unrestricted_credit_verified': False}


def _verify_body(captures, key):
    base = captures/key
    receipt = json.loads(base.with_suffix('.json').read_text())
    body = base.with_suffix('.html').read_bytes()
    text = base.with_suffix('.txt').read_bytes()
    if (receipt['status'] != 200 or len(body) != receipt['bytes']
            or hashlib.sha256(body).hexdigest() != receipt['sha256']
            or hashlib.sha256(text).hexdigest() != receipt['text_sha256']):
        raise ValueError('changed_listing_body')
    return text.decode('utf-8'), receipt


def run(root):
    audit = root/'runtime_state/audit'
    schedule_path = audit/'nominal_entitlement_schedule_20261007/result.json'
    plan_path = audit/'kr_exrights_basis_20261007/plan.json'
    if digest(schedule_path) != SCHEDULE_SHA256 or digest(plan_path) != PLAN_SHA256:
        raise ValueError('changed_parent_evidence')
    schedule = json.loads(schedule_path.read_text())
    plan = json.loads(plan_path.read_text())
    corpus = audit/'kr_remaining_action_documents_20261007'
    corpus_path = corpus/'first_result.json'
    prices_plan_path = audit/'lowliq_krx_comparison_20261007/plan.json'
    if (digest(corpus_path) != plan['corpus_result_sha256']
            or digest(prices_plan_path) != plan['price_plan_sha256']):
        raise ValueError('changed_corpus_or_prices_plan')
    corpus_result = json.loads(corpus_path.read_text())
    price_plan = json.loads(prices_plan_path.read_text())
    rows = []
    inputs = {}
    for original in schedule['events']:
        code = original['code']
        groups = [r for r in corpus_result['results'] if r['code'] == code]
        if len(groups) != 1:
            raise ValueError('ambiguous_company_record')
        documents = [d for d in groups[0]['documents'] if d['title'] == '추가상장(무상증자)']
        if len(documents) != 1 or len(documents[0]['body_keys']) != 1:
            raise ValueError('ambiguous_listing_notice')
        document = documents[0]
        key = document['body_keys'][0]
        text, receipt = _verify_body(corpus/'captures', key)
        parsed = parse_listing(text, code)
        published = datetime.fromisoformat(document['published_at']).replace(tzinfo=ZoneInfo('Asia/Seoul'))
        if published.date().isoformat() > AS_OF:
            raise ValueError('notice_after_audit_cutoff')
        item = {**parsed, 'ex_date': original['effective_date'], 'bonus_ratio': original['ratio'],
                'planned_date_in_captured_decision': original['planned_listing_date'],
                'matches_captured_decision_date': parsed['listing_date'] == original['planned_listing_date'],
                'notice_published_at': published.isoformat(),
                'notice_available_on_ex_date': published.date().isoformat() <= original['effective_date'],
                'source_url': receipt['request']['url'], 'body_sha256': receipt['sha256'],
                'text_sha256': receipt['text_sha256'], 'exchange_notice_verified': True,
                'instrument_traded_on_listing_date': None, 'instrument_volume': None}
        inputs[key] = {'receipt_sha256': digest((corpus/'captures'/key).with_suffix('.json')),
                       'body_sha256': receipt['sha256'], 'text_sha256': receipt['text_sha256']}
        if parsed['listing_date'] > AS_OF:
            item['state'] = 'FUTURE_ANNOUNCED'
        else:
            price_path = audit/'lowliq_krx_source_20261007/responses'/(code+'_nominal.json')
            if digest(price_path) != price_plan['response_sha256'][code+'_nominal']:
                raise ValueError('changed_nominal_price_capture')
            price = json.loads(price_path.read_text())
            if price['code'] != code or price['request']['adjusted'] is not False:
                raise ValueError('nominal_price_identity_mismatch')
            matches = [r for r in price['payload']['output2']
                       if r.get('stck_bsop_date') == parsed['listing_date'].replace('-', '')]
            if len(matches) != 1:
                raise ValueError('missing_or_duplicate_listing_bar')
            volume = int(matches[0]['acml_vol'])
            if volume < 0:
                raise ValueError('invalid_listing_volume')
            item.update(instrument_traded_on_listing_date=volume > 0, instrument_volume=volume,
                        state='LISTED_INSTRUMENT_TRADED' if volume > 0 else 'NO_INSTRUMENT_TRADE_OBSERVED',
                        nominal_price_capture_sha256=digest(price_path))
        rows.append(item)
    if len(rows) != 6 or len({r['code'] for r in rows}) != 6:
        raise ValueError('changed_six_event_cohort')
    result = {'as_of': AS_OF, 'schedule_sha256': SCHEDULE_SHA256, 'source_plan_sha256': PLAN_SHA256,
              'implementation_sha256': digest(Path(__file__)), 'listing_inputs': inputs, 'events': rows,
              'exchange_notices_verified': len(rows),
              'listing_day_instrument_trades_verified': sum(r['instrument_traded_on_listing_date'] is True for r in rows),
              'future_listings': sum(r['state'] == 'FUTURE_ANNOUNCED' for r in rows),
              'account_unrestricted_credit_verified': False,
              'complete_action_coverage_verified': False, 'point_in_time_information_for_exdate': False,
              'strategy_outcomes_computed': False, 'source_certified': False, 'publication_allowed': False}
    save_json(audit/'bonus_listing_evidence_20261007/result.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    args = p.parse_args()
    result = run(args.root)
    print(json.dumps({k:v for k,v in result.items() if k not in ('listing_inputs','events')}, indent=2))
