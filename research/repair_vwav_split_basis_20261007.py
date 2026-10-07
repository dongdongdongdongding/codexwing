"""Stage or apply the exact audited VWAV repair under the US writer lock."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.us_split_basis import normalize_known_split_rows, reference, verified_split_rows
from modules.us_symbol_lineage import daily_bar_issues
from multi_agent.tools.intraday_cache_journal import digest, save_json
from multi_agent.tools.us_daily_session_refresh import _store


def repair(source, audit, apply=False):
    before = pd.read_parquet(source)
    before_sha = digest(source)
    ref = reference()
    if before.date.duplicated().any() or not before.symbol.eq('VWAV').all() or not before.source.eq('yfinance').all():
        raise ValueError('unexpected_raw_identity')
    after = normalize_known_split_rows(before)
    mask = pd.to_datetime(after.date).lt(ref['effective'])
    dates = set(pd.to_datetime(after.loc[mask, 'date']).dt.strftime('%Y-%m-%d'))
    if dates != set(ref['verified_adjusted_rows']) or not verified_split_rows(after)[mask.to_numpy()].all():
        raise ValueError('uncertified_vwav_history')
    if daily_bar_issues(after).ne('').any():
        raise ValueError('remaining_invalid_source_bar')
    changed = ~(before.eq(after) | (before.isna() & after.isna())).all(axis=1)
    changed_days = pd.to_datetime(before.loc[changed, 'date']).dt.strftime('%Y-%m-%d').tolist()
    if changed_days and (before_sha != ref['baseline_sha256'] or set(changed_days) != set(ref['known_nominal_rows'])):
        raise ValueError('source_differs_from_verified_baseline')
    staged = audit / 'staged.parquet'
    if staged.exists():
        pd.testing.assert_frame_equal(pd.read_parquet(staged), after)
    else:
        after.to_parquet(staged, index=False)
        pd.testing.assert_frame_equal(pd.read_parquet(staged), after)
    report = {'before_sha256': before_sha, 'rows': len(before), 'changed_dates': changed_days,
              'verified_pre_split_rows': int(mask.sum()), 'staged_sha256': digest(staged),
              'applied': False, 'source': str(source), 'scope': 'Exact source normalization; no model or issued-contract mutation.'}
    if digest(source) != before_sha:
        raise ValueError('source_changed_after_validation')
    save_json(audit / ('apply_plan.json' if apply else 'stage_plan.json'), report)
    if apply:
        report['applied'] = _store(source, after, audit / 'storage')
        pd.testing.assert_frame_equal(pd.read_parquet(source), after)
        report['after_sha256'] = digest(source)
        save_json(audit / 'applied.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path.home() / 'research_cache/us_daily/NASDAQ')
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    args.audit.mkdir(parents=True, exist_ok=True)
    with (args.cache / '.daily_refresh.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print(json.dumps(repair(args.cache / 'raw_ohlcv/VWAV.parquet', args.audit, args.apply), indent=2))
