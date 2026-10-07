"""Audit inherited low-liquidity selection without fitting or scoring a model.

Counts describe the frozen current panel, not a reconstruction of the unpinned
August report. Original code, report and panel are preserved; nothing is repaired.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

LEGACY_SHA = '037d2a7b666755555d680c1087e2842af853569ddb12f54c979f67cd8d2ef52b'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def barrier_labels(frame, horizon=5):
    """Independent vectorized reproduction plus the first resolution offset."""
    n = len(frame)
    entry = frame.adj_open.shift(-1).to_numpy()
    high, low, opening, volume = [frame[k].to_numpy() for k in
                                ['adj_high', 'adj_low', 'adj_open', 'volume']]
    label = np.full(n, np.nan)
    offset = np.zeros(n, dtype=int)
    for k in range(1, horizon + 1):
        if k >= n:
            break
        e = entry[:-k]
        upper = high[k:] >= e * 1.05
        lower = low[k:] <= e * .95
        # Legacy only tests volume <= 0; its handling of NaN is reproduced too.
        event = (np.isnan(label[:-k]) & np.isfinite(e) & (e > 0) &
                 ~(volume[k:] <= 0) & (upper | lower))
        positions = np.flatnonzero(event)
        label[positions] = np.where(upper & lower, opening[k:] >= e * .95, upper)[event]
        offset[positions] = k
    return label, offset


def legacy_labels(frame, first_touch, exited):
    entry = frame.adj_open.shift(-1)
    valid = (frame.volume.shift(-1) > 0) & entry.notna() & (entry > 0)
    label = first_touch(entry.to_numpy(), frame.adj_high.to_numpy(),
                        frame.adj_low.to_numpy(), frame.adj_open.to_numpy(),
                        frame.volume.to_numpy(), 5, .05, .05)
    last = frame.adj_close.where(frame.volume > 0).ffill().iloc[-1]
    if exited and np.isfinite(last):
        label[np.isnan(label) & valid.to_numpy()] = 0
    label[~valid.to_numpy()] = np.nan
    return label, valid.to_numpy()


def causal_feature_eligible(frame):
    liq = frame.amount.rolling(20, min_periods=20).mean()
    returns = pd.concat([frame.adj_close.pct_change(n) for n in [1, 3, 5, 10, 20, 60]], axis=1)
    return (liq.ge(5e8) & liq.lt(30e8) & returns.notna().all(axis=1)).to_numpy()


def load_legacy(path):
    if digest(path) != LEGACY_SHA:
        raise ValueError('unreviewed_legacy_source')
    tree = ast.parse(Path(path).read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'first_touch_masked')
    scope = {'np': np}
    # Isolate the reviewed pure function; never execute legacy imports/main/output.
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), scope)
    return scope['first_touch_masked']


def audit(panel, legacy, report, output):
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name, source in [('panel.parquet', panel), ('legacy.py', legacy), ('legacy_report.json', report)]:
        expected = digest(source)
        shutil.copyfile(source, output / name)
        assert digest(output / name) == expected == digest(source)
        hashes[name] = {'source': str(source), 'sha256': expected}
    (output / 'inputs.json').write_text(json.dumps(hashes, indent=2))
    first_touch = load_legacy(output / 'legacy.py')
    cols = ['code', 'date', 'market', 'adj_open', 'adj_high', 'adj_low', 'adj_close', 'volume', 'amount']
    panel_frame = pd.read_parquet(output / 'panel.parquet', columns=cols).sort_values(['code', 'date'])
    end = panel_frame.date.max()
    quarters = list(pd.period_range('2019Q1', '2026Q2', freq='Q'))
    totals = {'source_rows': len(panel_frame), 'source_codes': panel_frame.code.nunique(),
              'prelabel_eligible_rows': 0, 'legacy_retained_rows': 0,
              'fully_observed_valid_entry_no_barrier': 0,
              'nonexited_no_barrier_excluded': 0, 'exited_no_barrier_retained': 0,
              'future_entry_unfilled_excluded': 0, 'legacy_function_rows_verified': 0}
    boundary = {str(q): 0 for q in quarters}
    boundary_examples = {str(q): [] for q in quarters}
    records = []
    for number, (code, original) in enumerate(panel_frame.groupby('code', sort=True), 1):
        f = original.reset_index(drop=True)
        labels, offsets = barrier_labels(f)
        raw = first_touch(f.adj_open.shift(-1).to_numpy(), f.adj_high.to_numpy(),
                          f.adj_low.to_numpy(), f.adj_open.to_numpy(), f.volume.to_numpy(), 5, .05, .05)
        np.testing.assert_array_equal(labels, raw)
        exited = f.date.max() < end - pd.Timedelta(days=14)
        final, entry_valid = legacy_labels(f, first_touch, exited)
        eligible = causal_feature_eligible(f)
        period = f.date.between('2019-01-01', '2026-06-30').to_numpy()
        available = eligible & period
        complete = np.arange(len(f)) + 5 < len(f)
        no_barrier = available & complete & entry_valid & np.isnan(labels)
        totals['prelabel_eligible_rows'] += int(available.sum())
        totals['legacy_retained_rows'] += int((available & ~np.isnan(final)).sum())
        totals['fully_observed_valid_entry_no_barrier'] += int(no_barrier.sum())
        totals['nonexited_no_barrier_excluded'] += int((no_barrier & np.isnan(final)).sum())
        totals['exited_no_barrier_retained'] += int((no_barrier & ~np.isnan(final)).sum())
        totals['future_entry_unfilled_excluded'] += int((available & complete & ~entry_valid).sum())
        totals['legacy_function_rows_verified'] += len(f)
        # A finite barrier label depends on its actual event date, not signal date.
        resolved = f.date.to_numpy()[np.minimum(np.arange(len(f)) + offsets, len(f) - 1)]
        events = eligible & ~np.isnan(final) & (offsets > 0)
        for q in quarters:
            t0 = q.start_time
            leaking = events & f.date.lt(t0).to_numpy() & f.date.ge(t0 - pd.DateOffset(years=2)).to_numpy()
            leaking &= resolved >= t0.to_datetime64()
            boundary[str(q)] += int(leaking.sum())
            if leaking.any() and len(boundary_examples[str(q)]) < 5:
                i = np.flatnonzero(leaking)[0]
                boundary_examples[str(q)].append({'code': str(code), 'signal_date': str(f.date.iloc[i].date()),
                                                  'event_date': str(pd.Timestamp(resolved[i]).date()),
                                                  'label': float(final[i])})
        if no_barrier.any():
            records.append({'code': str(code), 'exited_by_legacy_rule': bool(exited),
                            'fully_observed_no_barrier': int(no_barrier.sum()),
                            'first_example': str(f.loc[no_barrier, 'date'].iloc[0].date())})
        if number % 500 == 0:
            print('audited codes', number, flush=True)
    totals = {k: int(v) for k, v in totals.items()}
    assert totals['fully_observed_valid_entry_no_barrier'] == totals['nonexited_no_barrier_excluded'] + totals['exited_no_barrier_retained']
    failures = totals['nonexited_no_barrier_excluded'] > 0 or sum(boundary.values()) > 0
    result = {'verdict': 'LEGACY_RESULT_NOT_PROMOTION_EVIDENCE' if failures else 'NO_CASES_FOUND_WITHIN_SCOPE', 'panel_end': str(end.date()),
              'scope': 'Current frozen panel, original reviewed code; not reproduction of unpinned August model results.',
              'counts': totals, 'quarterly_training_labels_resolved_at_or_after_fit_boundary': boundary,
              'training_boundary_examples': boundary_examples,
              'exited_definition': 'last observed symbol date < current panel end minus 14 calendar days; not a verified delisting date',
              'no_touch_examples_by_code': records, 'original_report_preserved': True,
              'model_fit_or_scoring': False, 'source_hashes': hashes}
    for name, source in [('panel.parquet', panel), ('legacy.py', legacy), ('legacy_report.json', report)]:
        assert digest(source) == hashes[name]['sha256'] == digest(output / name)
    (output / 'audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'counts': totals, 'label_boundary_total': sum(boundary.values())}, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--panel', type=Path, required=True)
    p.add_argument('--legacy', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    audit(a.panel, a.legacy, a.report, a.output)
