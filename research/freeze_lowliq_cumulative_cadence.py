"""Freeze a preregistered timing correction using original immutable scores.

No labels, returns, model fitting, or publication. The original run is preserved.
The complete original calendar must be frozen before this derivative is written.
"""
from datetime import datetime, timezone
import argparse
import fcntl
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.lowliq_touch10_core import rank_and_cap
from research.run_lowliq_touch10_reconstruction import prepare, replay_record, save_json, publish
from research.audit_kr_adjustment_asof import digest


def cumulative_rank_and_cap(day, frame, calendar, prior):
    dates = [str(pd.Timestamp(d).date()) for d in calendar]
    if len(dates) != len(set(dates)) or dates != sorted(dates) or day not in dates:
        raise ValueError('invalid_cadence_calendar')
    n = dates.index(day) + 1
    if set(prior) != set(dates[:n-1]):
        raise ValueError('incomplete_prior_calendar')
    if not frame.empty and (frame.date.nunique() != 1 or
                            pd.Timestamp(frame.date.iloc[0]) != pd.Timestamp(day)):
        raise ValueError('wrong_signal_date')
    original, picks = rank_and_cap(frame, calendar, prior)
    if sum(bool(v) for v in prior.values()) + 1 > (3*n)//5:
        picks = picks.iloc[:0].copy()
    return original, picks


def derive(calendar, records, frames, hashes):
    """Validate every parent selection before deriving a different calendar."""
    parent_prior = {name: {} for name in hashes}
    amended_prior = {name: {} for name in hashes}
    output = []
    for date, record, frame in zip(calendar, records, frames):
        day = str(pd.Timestamp(date).date())
        if record['date'] != day:
            raise ValueError('parent_calendar_mismatch')
        replay_record(record, frame, calendar, parent_prior, hashes)
        variants = {}
        for name in hashes:
            original, picks = cumulative_rank_and_cap(
                day, frame.assign(score=frame[name]), calendar, amended_prior[name])
            amended_prior[name][day] = bool(len(picks))
            cols = ['code', 'market', 'liq', 'score']
            variants[name] = {'source_picks': original[cols].to_dict('records'),
                              'picks': picks[cols].to_dict('records')}
            assert variants[name]['source_picks'] == record['variants'][name]['source_picks']
        output.append({'date': day, 'kind': 'retrospective_cumulative_cadence_amendment',
                       'parent_universe_sha256': record['universe_sha256'],
                       'model_hashes': hashes, 'variants': variants,
                       'publication_allowed': False})
    if len(output) != len(calendar) or len(records) != len(calendar) or len(frames) != len(calendar):
        raise ValueError('incomplete_parent_scores')
    return output, parent_prior, amended_prior


def freeze(root):
    spec_path = ROOT/'research/prereg_lowliq_touch10_cumulative_20261007.json'
    spec = json.loads(spec_path.read_text())
    parent_spec, paths, parent, manifest = prepare(root)
    if digest(ROOT/spec['amendment']['parent_path']) != spec['amendment']['parent_sha256']:
        raise ValueError('changed_parent_preregistration')
    complete_path = parent/'scores_complete.json'
    if not complete_path.exists():
        raise ValueError('parent_scores_not_complete')
    complete = json.loads(complete_path.read_text())
    assert complete['test_outcomes_computed'] is False and complete['publication_allowed'] is False
    source_dates = pd.read_parquet(paths['panel'], columns=['date']).date
    calendar = sorted(source_dates.loc[source_dates.between(
        parent_spec['test_signal_start'], parent_spec['test_signal_end'])].unique())
    if len(calendar) != complete['dates']:
        raise ValueError('parent_calendar_count_changed')
    hashes = {}
    for kind in ['real', 'noise']:
        for seed in parent_spec['model']['seeds']:
            name = f'{kind}_{seed}'
            receipt = json.loads((parent/'models'/f'{name}.json').read_text())
            sha = digest(parent/'models'/f'{name}.txt')
            if sha != receipt['model_sha256']:
                raise ValueError('parent_model_changed')
            hashes[name] = sha
    records, frames, inputs = [], [], {}
    for date in calendar:
        day = str(pd.Timestamp(date).date())
        path = parent/'scores'/f'{day}.json'
        record = json.loads(path.read_text())
        universe = parent/'scores'/f'{day}.parquet'
        if digest(universe) != record['universe_sha256']:
            raise ValueError('parent_universe_changed')
        records.append(record)
        frames.append(pd.read_parquet(universe))
        inputs[day] = {'record_path': str(path), 'record_sha256': digest(path),
                       'universe_path': str(universe), 'universe_sha256': record['universe_sha256']}
    output, original, amended = derive(calendar, records, frames, hashes)
    audit = root/'runtime_state/audit/lowliq_touch10_cumulative_20261007'
    save_json(audit/'manifest.json', {'spec_sha256': digest(spec_path),
        'code_sha256': digest(Path(__file__)), 'parent_manifest': manifest,
        'parent_complete_sha256': digest(complete_path), 'inputs': inputs, 'models': hashes})
    publish(audit/'prereg.json', spec_path.read_bytes())
    receipt = audit/'created_at.json'
    if not receipt.exists():
        save_json(receipt, {'computed_at': datetime.now(timezone.utc).isoformat()})
    for record in output:
        save_json(audit/'scores'/(record['date']+'.json'), record)
    summary = {'status': 'SCORES_FROZEN_AWAITING_FIXED_H10_WINDOW_AND_SOURCE_REVIEW',
        'dates': len(calendar), 'test_outcomes_computed': False, 'publication_allowed': False,
        'family_size': 4, 'schedule': {}}
    for name in hashes:
        flags = list(amended[name].values())
        summary['schedule'][name] = {'parent_firing_dates': sum(original[name].values()),
            'firing_dates': sum(flags), 'firing_dates_per_five_sessions': 5*sum(flags)/len(calendar),
            'max_full_rolling_five': max(sum(flags[i:i+5]) for i in range(len(flags)-4)),
            'selected_records': sum(len(row['variants'][name]['picks']) for row in output)}
    save_json(audit/'scores_complete.json', summary)
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True, type=Path)
    args = ap.parse_args()
    lock = args.root/'runtime_state/audit/lowliq_touch10_cumulative_20261007.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        freeze(args.root)
