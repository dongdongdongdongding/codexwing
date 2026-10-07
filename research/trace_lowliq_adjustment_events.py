"""Trace the pinned adjustment algorithm; never fit, score or settle a model.

The injected callback observes lagged assignments only. Every resulting adjusted
field must reproduce the frozen panel before the trace is accepted.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import BUILDER_SHA, FIELDS, digest
from research.run_lowliq_touch10_reconstruction import save_frame, save_json


def trace(raw, builder):
    if digest(builder) != BUILDER_SHA:
        raise ValueError('unreviewed_adjustment_builder')
    source = builder.read_text()
    start = source.index('# ---------------- event detection ----------------')
    end = source.index('# ---------------- delisting join ----------------')
    block = source[start:end]
    assignment = '        factor[best] = rs_u'
    if block.count(assignment) != 1:
        raise ValueError('ambiguous_lag_assignment')
    block = block.replace(assignment, assignment + '\n        capture_lag(best, u, rs_u)')
    frame = raw.sort_values(['code', 'date']).reset_index(drop=True).copy()
    if frame.empty or frame.duplicated(['code', 'date']).any():
        raise ValueError('empty_or_duplicate_source')
    lag = {}
    scope = {'df': frame, 'np': np, 'pd': pd, 'print': lambda *a, **k: None,
             'capture_lag': lambda t, u, factor: lag.update({int(t): int(u)})}
    exec(compile(block, str(builder), 'exec'), scope)
    for field in FIELDS:
        np.testing.assert_array_equal(scope['df'][field], raw.sort_values(['code', 'date'])[field])
    records = []
    for t in np.flatnonzero(scope['factor'] != 1):
        row = frame.iloc[t]
        rule = ('same_day' if scope['same_day'][t] else 'admin' if scope['admin'][t]
                else 'limit' if scope['limit_viol'][t] else 'lag')
        u = lag[int(t)] if rule == 'lag' else int(t)
        trigger = frame.iloc[u]
        previous = frame.iloc[u-1] if u > 0 and frame.iloc[u-1].code == row.code else None
        records.append({'code': row.code, 'date': str(row.date.date()), 'rule': rule,
            'event_factor': float(scope['factor'][t]), 'trigger_date': str(trigger.date.date()),
            'trigger_stocks_before': int(previous.stocks) if previous is not None else None,
            'trigger_stocks_after': int(trigger.stocks),
            'code_rows_between_event_and_trigger': int(u-t),
            'close_ratio_at_event': float(scope['r_p'][t]),
            'volume_at_event': float(row.volume)})
    return pd.DataFrame(records)


def run(root):
    audits = root/'runtime_state/audit'
    comp = audits/'lowliq_krx_comparison_20261007'
    out = audits/'lowliq_corporate_actions_20261007'
    source = audits/'kr_adjustment_asof_20261007/final/panel.parquet'
    builder = ROOT/'research/data/build_px_delisted_20261007.py.txt'
    differences = pd.read_parquet(comp/'adjusted_differences.parquet')
    diag = pd.read_parquet(comp/'provider_factor_diagnostics.parquet')
    selected = differences.merge(diag[['code','date','traded']], on=['code','date'], validate='many_to_one')
    codes = sorted(selected.loc[selected.traded, 'code'].unique())
    plan = json.loads((comp/'plan.json').read_text())
    if digest(source) != plan['panel_sha256']:
        raise ValueError('changed_frozen_panel')
    receipts = json.loads((out/'capture_receipts.json').read_text())
    for name, receipt in receipts.items():
        if digest(out/(name+'.html')) != receipt['sha256'] or digest(out/(name+'.txt')) != receipt['text_sha256']:
            raise ValueError('changed_official_evidence')
    save_json(out/'trace_plan_v2.json', {'code_sha256': digest(Path(__file__)), 'codes': codes,
        'panel_sha256': digest(source), 'builder_sha256': digest(builder),
        'comparison_differences_sha256': digest(comp/'adjusted_differences.parquet'),
        'provider_diagnostics_sha256': digest(comp/'provider_factor_diagnostics.parquet'),
        'official_capture_receipts_sha256': digest(out/'capture_receipts.json'),
        'scope': 'All 65 traded-path mismatch codes, all available history; source diagnostics only.'})
    raw = pd.read_parquet(source, filters=[('code', 'in', codes)])
    events = trace(raw, builder)
    save_frame(out/'events_all_history.parquet', events)
    q3 = events[events.date.between('2026-06-30', '2026-10-02')].reset_index(drop=True)
    save_frame(out/'events_comparison_window.parquet', q3)
    h = q3[(q3.code == '005440') & (q3.date == '2026-07-20')].iloc[0]
    d = q3[(q3.code == '008830') & (q3.date == '2026-08-07')].iloc[0]
    assert h.rule == d.rule == 'lag'
    assert h.trigger_stocks_after-h.trigger_stocks_before == 27492898
    assert d.trigger_date == '2026-08-24' and d.event_factor == 1.3
    assert '주식교환' in (out/'hyundai_listing.txt').read_text()
    assert '27,492,898' in (out/'hyundai_listing.txt').read_text()
    assert all(word in (out/'daedong_exdate.txt').read_text() for word in ['A008830','2026-08-03','7,000','무상증자'])
    examples = [
        {'code':'005440', 'algorithm_event_date':'2026-07-20',
         'problem':'Share-exchange issuance incorrectly treated as proportional holder adjustment.',
         'trace': h.to_dict(), 'supported_event_factor':1.0,
         'evidence':['hyundai_listing','hyundai_exchange'],
         'inference':'New shares went to Hyundai Home Shopping holders, not pro-rata to existing 005440 holders. '
             'The 27,492,898 share increase exactly matches the algorithm trigger; KIS remains nominal throughout scope.'},
        {'code':'008830', 'algorithm_event_date':'2026-08-07',
         'problem':'Bonus factor placed four observed trading sessions after official ex-date.',
         'trace': d.to_dict(), 'official_ex_date':'2026-08-03',
         'supported_event_factor':1.3, 'evidence':['daedong_exdate','daedong_offering'],
         'inference':'The August24 share-count increase led the heuristic to choose August7; '
             'the official August3 ex-date and KIS factor marker disagree with that choice.'}]
    save_json(out/'confirmed_examples.json', examples)
    summary = {'codes':len(codes), 'full_history_rows_reproduced':len(raw),
        'all_five_adjusted_fields_exact':True, 'comparison_window_events':len(q3),
        'comparison_window_rules':q3.rule.value_counts().to_dict(),
        'confirmed_economic_or_timing_errors':2,
        'source_verdict':'INPUT_REJECTED_FOR_QUALIFICATION',
        'reason':'Official evidence contradicts at least two input adjustment events. '
            'This is a source rejection, not an alpha or strategy-outcome verdict.',
        'other_63_codes_certified':False, 'live_or_frozen_data_changed':False,
        'test_strategy_outcomes_read_or_computed':False, 'publication_allowed':False}
    save_json(out/'source_verdict.json', summary)
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    run(parser.parse_args().root)
