"""Metadata/date-only preflight of the two frozen, source-rejected lowliq arms.

This command has NO outcome loading or evaluation mode. New accepted source
requires an explicit new study; changing a report flag cannot repair this study.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.lowliq_fixed_window_evaluation import preflight
from research.run_lowliq_touch10_reconstruction import save_json

REJECTION_SHA256 = '9d62452e046ab618d6928dd70a9e8c1870d3e1be70f7d365d86e459f376c6fc6'
MANIFEST_SHA256 = '210e94abc9769a10a68429073a55833ee3ea41b7006d10eca51b811e9b0809e7'


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def run(root):
    audit = root/'runtime_state/audit'
    rejected = audit/'lowliq_corporate_actions_20261007/source_verdict.json'
    manifest_path = audit/'lowliq_touch10_20261007/manifest.json'
    if digest(rejected) != REJECTION_SHA256 or digest(manifest_path) != MANIFEST_SHA256:
        raise ValueError('changed_frozen_evidence')
    verdict = json.loads(rejected.read_text())
    if verdict['source_verdict'] != 'INPUT_REJECTED_FOR_QUALIFICATION':
        raise ValueError('rejected_study_requires_new_epoch')
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest['code'].items():
        if digest(root/name) != expected:
            raise ValueError('changed_frozen_implementation')
    source = audit/'kr_adjustment_asof_20261007/final/panel.parquet'
    if digest(source) != manifest['sources']['panel']:
        raise ValueError('changed_frozen_source')
    # Read DATE ONLY. Never select OHLC, adjusted prices, model outcomes or labels.
    dates = pd.read_parquet(source, columns=['date']).date
    calendar = sorted(pd.to_datetime(dates).dt.strftime('%Y-%m-%d').unique().tolist())
    results = []
    for folder, spec_name in [('lowliq_touch10_20261007','prereg_lowliq_touch10_20261007.json'),
                              ('lowliq_touch10_cumulative_20261007','prereg_lowliq_touch10_cumulative_20261007.json')]:
        spec_path = root/'research'/spec_name
        spec = json.loads(spec_path.read_text())
        frozen_spec = audit/folder/'prereg.json'
        if digest(spec_path) != digest(frozen_spec):
            raise ValueError('changed_frozen_spec')
        if spec['source']['panel_sha256'] != manifest['sources']['panel']:
            raise ValueError('wrong_source_epoch')
        complete = json.loads((audit/folder/'scores_complete.json').read_text())
        fixed = [d for d in calendar if spec['test_signal_start'] <= d <= spec['test_signal_end']]
        if complete['dates'] != len(fixed) or complete['test_outcomes_computed'] is not False:
            raise ValueError('changed_score_completion')
        proof = {'source_verdict':verdict['source_verdict'], 'source_sha256':manifest['sources']['panel'],
                 'source_observed_through':calendar[-1], 'as_of':'2026-10-07', 'fixed_signal_dates':fixed,
                 # No source qualification is created by a metadata preflight.
                 'calendar_verified':False, 'contract_verified':False,
                 'complete_universe_verified':False, 'model_score_replay_verified':False}
        checked = preflight(spec,calendar,proof)
        if checked['ready'] or checked['outcomes_loaded']:
            raise ValueError('rejected_study_became_evaluable')
        results.append({'study':folder, 'spec_sha256':digest(spec_path), **checked,
                        'fixed_sessions':len(fixed), 'source_last_date':calendar[-1],
                        'observed_sessions_after_last_signal':sum(d > fixed[-1] for d in calendar),
                        'scope':'Date/source-rejection preflight only; evidence flags are not a new score audit.'})
    output = {'results':results, 'rejection_sha256':REJECTION_SHA256,
              'source_sha256':manifest['sources']['panel'], 'manifest_sha256':MANIFEST_SHA256,
              'implementation_sha256':digest(Path(__file__)),
              'statistics_sha256':digest(ROOT/'research/lowliq_fixed_window_evaluation.py'),
              'test_outcomes_loaded_or_computed':False, 'publication_allowed':False}
    epoch = hashlib.sha256((output['implementation_sha256']+output['statistics_sha256']).encode()).hexdigest()[:12]
    save_json(audit/'lowliq_evaluation_preflight_20261007'/('result_'+epoch+'.json'),output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    output = run(args.root)
    print(json.dumps({'studies':[{'study':r['study'],'ready':r['ready'],'reasons':r['reasons'],
                                 'fixed_sessions':r['fixed_sessions'],
                                 'observed_sessions_after_last_signal':r['observed_sessions_after_last_signal']}
                                for r in output['results']],
                      'test_outcomes_loaded_or_computed':False}, indent=2))
