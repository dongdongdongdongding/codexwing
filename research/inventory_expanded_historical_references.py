"""Reconcile the expanded v14 review cohort without replacing the v11 inventory."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.compare_indexed_lowliq_history import indexed_receipt
from research.inventory_historical_reference_gaps import inventory_code
from research.recover_lowliq_history_request import digest
from research.run_lowliq_touch10_reconstruction import save_json

PINS = {
    'kr_verified_events_v14_20261008/panel.parquet':
        '700903bde57d828f77a0a01df4d1d62e620c2cf0bd6df8fc050c36fc6910d069',
    'lowliq_history_coverage_indices/index_20261007T164015205007.json':
        '3573f9cf558c9c733e0fa4b1c63127a080bf6b89554ca78696150d2980cbefd7',
    'lowliq_history_indexed_comparison_v14_expanded_20261008/source_review_queue.json':
        'e5583edcf124d94bd1b4584222518ea6d450db4c64ec92c281d35f073cbebcb3',
    'lowliq_history_indexed_comparison_v14_20261008/source_review_queue.json':
        '1c321217aff960d235e79674f522a87160913c91100efab2cfffeb55f4da7e67',
    'historical_reference_inventory_20261008/primary_review_events.json':
        'a080aa9cf180216445580658c9df2c23af28d14c10244123061554d5112be3c9',
    'historical_reference_inventory_20261008/by_code.json':
        'c2533415fbbfaf20050742dce863fee8e57f3555cb81b43f52d8f4adf86ce2c9',
}
FROZEN_INVENTORY_SHA = 'aad39f20b643774ded861dc288a3b8256707c5952d5a8676cff1b001c7a55afc'


def reconcile_old_events(old_events, groups, quotes):
    """Re-evaluate each old event, including codes absent from the new queue."""
    seen = set()
    rows = []
    for old in old_events:
        code, day = old['code'], old['date']
        key = (code, day)
        if key in seen:
            raise ValueError('duplicate_old_event')
        seen.add(key)
        group = groups[code].sort_values('date')
        pair = group.loc[group.date.le(day)].tail(2)
        dates = pair.date.dt.strftime('%Y-%m-%d').tolist()
        if dates != [old['prior_date'], day] or any(d not in quotes[code] for d in dates):
            raise ValueError('unverified_old_event_scope')
        before, after = pair.to_dict('records')
        # A vanished diagnostic must not conceal changed nominal input.
        for value, expected in [(before['close'], old['prior_close']),
                                (after['close'], old['close']),
                                (after['open'], old['open']),
                                (after['volume'], old['volume']),
                                (before['stocks'], old['before_stocks']),
                                (after['stocks'], old['after_stocks'])]:
            if value != expected:
                raise ValueError('changed_old_event_nominal')
        result = inventory_code(pair, {d: quotes[code][d] for d in dates})
        if result['counts'].get('signed_reference_rows') != 1:
            raise ValueError('old_event_no_longer_comparable')
        current = result['events'][0] if result['events'] else None
        if current and current['reference_price'] != old['reference_price']:
            raise ValueError('changed_old_event_reference')
        rows.append({'code': code, 'date': day, 'prior_date': old['prior_date'],
                     'old_classification': old['classification'],
                     'current_classification': current['classification'] if current else 'EXACT_FACTOR_AGREEMENT',
                     'old_relative_disagreement_exact': old['relative_disagreement_exact'],
                     'current_relative_disagreement_exact': current['relative_disagreement_exact'] if current else '0'})
    return rows


def summarize(results):
    counts = Counter()
    for result in results:
        counts.update(result['counts'])
    events = [e for r in results for e in r['events'] if e['classification'] == 'PRIMARY_REVIEW_REQUIRED']
    return {'codes': len(results), 'counts': dict(counts), 'candidate_events': len(events),
            'candidate_codes': len({e['code'] for e in events}),
            'nontraded_boundaries': sum(len(r['nontraded_boundaries']) for r in results)}


def run(root):
    audit = root / 'runtime_state/audit'
    hashes = {}
    for name, sha in PINS.items():
        path = audit / name
        if digest(path) != sha:
            raise ValueError('changed_frozen_input:' + name)
        hashes[str(path)] = sha
    frozen = ROOT / 'research/inventory_historical_reference_gaps.py'
    if digest(frozen) != FROZEN_INVENTORY_SHA:
        raise ValueError('changed_frozen_inventory')
    names = list(PINS)
    source = audit / names[0]
    index = json.loads((audit / names[1]).read_text())
    queue = json.loads((audit / names[2]).read_text())
    prior_queue = json.loads((audit / names[3]).read_text())
    old_events = json.loads((audit / names[4]).read_text())
    old_results = json.loads((audit / names[5]).read_text())
    current_codes = {r['code'] for r in queue['worst_examples']}
    prior_codes = {r['code'] for r in prior_queue['worst_examples']}
    old_codes = {r['code'] for r in old_results}
    if (len(current_codes) != 316 or len(queue['worst_examples']) != 316 or
            len(prior_codes) != 192 or len(old_codes) != 213 or len(old_events) != 287 or
            not prior_codes <= current_codes or not prior_codes <= old_codes or
            current_codes & old_codes != prior_codes):
        raise ValueError('changed_cohort')
    codes = sorted(current_codes | old_codes)
    scope_path = audit / 'lowliq_history_scope_20261007/plan.json'
    scope = json.loads(scope_path.read_text())
    scope_sha = digest(scope_path)
    capture = audit / 'lowliq_history_capture_20261007'
    if scope_sha != index['scope_plan_sha256'] or digest(capture / 'manifest.json') != index['capture_manifest_sha256']:
        raise ValueError('changed_capture_scope')
    hashes[str(scope_path)] = scope_sha
    hashes[str(capture / 'manifest.json')] = index['capture_manifest_sha256']
    entries = {e['request_id']: e for e in index['entries']}
    if len(entries) != len(index['entries']):
        raise ValueError('duplicate_index_request')
    quotes = {c: {} for c in codes}
    provider_names = {c: set() for c in codes}
    used_requests = []
    for request in scope['requests']:
        code = request['code']
        if code not in quotes or request['basis'] != 'nominal':
            continue
        entry = entries[request['id']]
        item = indexed_receipt(entry, request, scope_sha, capture)
        if item['inspection']['status'] != 'CAPTURED':
            raise ValueError('unavailable_provider_scope')
        used_requests.append(request['id'])
        hashes[entry['original_path']] = entry['provenance']['original_sha256']
        hashes[entry['effective_path']] = entry['effective_sha256']
        provider_names[code].add(item['payload']['output1'].get('hts_kor_isnm', ''))
        expected = set(request['expected_dates'])
        scoped = {}
        for row in item['payload']['output2']:
            day = pd.Timestamp(row['stck_bsop_date']).strftime('%Y-%m-%d')
            if day in expected:
                if day in quotes[code] or day in scoped:
                    raise ValueError('overlapping_provider_dates')
                scoped[day] = row
        if set(scoped) != expected:
            raise ValueError('missing_provider_dates')
        quotes[code].update(scoped)
    raw = pd.read_parquet(source, filters=[('code', 'in', codes)])
    groups = {str(code): group for code, group in raw.groupby('code', sort=True)}
    if set(groups) != set(codes) or any(not q for q in quotes.values()):
        raise ValueError('missing_source_or_quote_code')
    results = []
    for code in codes:
        result = inventory_code(groups[code], quotes[code])
        result['provider_names'] = sorted(provider_names[code], key=lambda name: (name is None, str(name)))
        result['in_expanded_review_queue'] = code in current_codes
        result['in_original_v11_inventory'] = code in old_codes
        results.append(result)
    reconciliation = reconcile_old_events(old_events, groups, quotes)
    candidates = [{**e, 'provider_names': r['provider_names']} for r in results for e in r['events']
                  if e['classification'] == 'PRIMARY_REVIEW_REQUIRED']
    old_keys = {(e['code'], e['date']) for e in old_events}
    new_keys = {(e['code'], e['date']) for e in candidates}
    summary = {
        'expanded_review_queue': summarize([r for r in results if r['code'] in current_codes]),
        'prior_v11_cohort_rechecked': summarize([r for r in results if r['code'] in old_codes]),
        'newly_added_codes': summarize([r for r in results if r['code'] not in old_codes]),
        'all_rechecked': summarize(results), 'nominal_requests': len(used_requests),
        'old_event_reconciliation': dict(Counter(r['current_classification'] for r in reconciliation)),
        'new_primary_events_in_old_codes': sorted([list(k) for k in new_keys - old_keys if k[0] in old_codes]),
        'codes_retained_outside_current_queue': sorted(old_codes - current_codes),
        'source_certified': False, 'point_in_time_certified': False,
        'portfolio_return_certified': False, 'publication_allowed': False, 'strategy_outcomes_computed': False,
    }
    out = audit / 'expanded_historical_reference_inventory_20261009'
    save_json(out / 'manifest.json', {
        'input_sha256': hashes, 'implementation_sha256': digest(Path(__file__)),
        'dependencies': {n: digest(ROOT / n) for n in [
            'research/inventory_historical_reference_gaps.py', 'research/audit_lowliq_history_references.py',
            'research/compare_indexed_lowliq_history.py', 'research/recover_lowliq_history_request.py',
            'research/capture_lowliq_krx_source.py', 'research/run_lowliq_touch10_reconstruction.py']},
        'used_nominal_requests': used_requests,
        'scope': '316 expanded queue codes plus all prior 213 codes; v14 source and fixed 46520-receipt index.',
        'arithmetic_split': 'Relative 1e-12 is a diagnostic classification, never an acceptance tolerance.',
    })
    save_json(out / 'by_code.json', results)
    save_json(out / 'primary_review_events.json', candidates)
    save_json(out / 'old_event_reconciliation.json', reconciliation)
    save_json(out / 'summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    run(parser.parse_args().root)
