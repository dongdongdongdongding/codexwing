"""Extract the fixed six bonus schedules, never treating planned listing as credit."""
import argparse
from datetime import date
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.run_lowliq_touch10_reconstruction import save_json

PLAN_SHA256 = '2a9d222a219ba3c764e27352bb77e01c73239cf4a56d654cb32926acc101258f'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_schedule(text):
    text = ' '.join(text.split())
    ratios = set(re.findall(r'1주당 신주배정 주식수 보통주식 \(주\) ([0-9.]+)', text))
    dates = set(re.findall(r'8\.\s*신주의\s*상장\s*예정일\s*(\d{4})[.년]\s*(\d{1,2})[.월]\s*(\d{1,2})[.일]?(?=\s|$)', text))
    if len(ratios) != 1 or len(dates) != 1:
        raise ValueError('ambiguous_bonus_schedule')
    ratio = Fraction(next(iter(ratios)))
    if ratio <= 0:
        raise ValueError('invalid_entitlement')
    y, m, d = map(int, next(iter(dates)))
    return {'ratio': [ratio.numerator, ratio.denominator],
            'planned_listing_date': date(y, m, d).isoformat(),
            'availability_status': 'planned', 'actual_tradeable_date': None}


def run(root):
    audit = root/'runtime_state/audit'
    plan_path = audit/'kr_exrights_basis_20261007/plan.json'
    if digest(plan_path) != PLAN_SHA256:
        raise ValueError('changed_fixed_source_plan')
    plan = json.loads(plan_path.read_text())
    output = []
    captures = audit/'kr_remaining_action_documents_20261007/captures'
    for code, entitlement in sorted(plan['entitlements'].items()):
        key = entitlement['body_key']
        base = captures/key
        receipt = json.loads(base.with_suffix('.json').read_text())
        if (receipt['status'] != 200 or digest(base.with_suffix('.html')) != plan['official_body_hashes'][key]
                or digest(base.with_suffix('.html')) != receipt['sha256']
                or digest(base.with_suffix('.txt')) != receipt['text_sha256']):
            raise ValueError('changed_official_body')
        parsed = parse_schedule(base.with_suffix('.txt').read_bytes().decode('utf-8'))
        if Fraction(*parsed['ratio']) != Fraction(entitlement['new_shares_per_share']):
            raise ValueError('changed_entitlement')
        events = [e for e in plan['events'] if e['code'] == code and e['kind'] == 'bonus']
        if len(events) != 1:
            raise ValueError('ambiguous_effective_event')
        event = events[0]
        notice = captures/event['body_key']
        notice_receipt = json.loads(notice.with_suffix('.json').read_text())
        if (digest(notice.with_suffix('.html')) != plan['official_body_hashes'][event['body_key']]
                or digest(notice.with_suffix('.txt')) != notice_receipt['text_sha256']):
            raise ValueError('changed_exdate_body')
        output.append({'code': code, 'effective_date': event['date'], **parsed,
                       'planned_calendar_delay': (date.fromisoformat(parsed['planned_listing_date'])-
                                                  date.fromisoformat(event['date'])).days,
                       'body_sha256': receipt['sha256'], 'text_sha256': receipt['text_sha256'],
                       'source_url': entitlement['source_url'], 'body_key': key})
    if len(output) != 6:
        raise ValueError('changed_fixed_scope')
    result = {'source_plan_sha256': PLAN_SHA256, 'implementation_sha256': digest(Path(__file__)),
              'events': output, 'source_certified': False, 'strategy_outcomes_computed': False,
              'publication_allowed': False, 'actual_availability_verified': False,
              'meaning': 'Planned listing dates from fixed decision bodies; not final listing/credit evidence. '
                         'No entitlement is made tradeable from this audit.'}
    save_json(audit/'nominal_entitlement_schedule_20261007/result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root), ensure_ascii=False, indent=2))
