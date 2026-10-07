from pathlib import Path

import pandas as pd
import pytest

from research.audit_kr_adjustment_asof import adjustment_block, rebuild, FIELDS
from research.trace_lowliq_adjustment_events import trace

BUILDER = Path(__file__).resolve().parents[1]/'research/data/build_px_delisted_20261007.py.txt'


def sample():
    # A later issuance can cause the heuristic to relabel an earlier price drop.
    raw = pd.DataFrame({'code':['000001']*6, 'date':pd.date_range('2026-07-01', periods=6),
        'open':[100,100,80,100,100,100], 'high':[100,100,80,100,100,100],
        'low':[100,100,80,100,100,100], 'close':[100,100,80,100,100,100],
        'volume':[10]*6, 'stocks':[100,100,100,100,120,120]})
    adjusted = rebuild(raw, adjustment_block(BUILDER))
    for field in FIELDS:
        raw[field] = adjusted[field]
    return raw


def test_trace_exposes_later_share_trigger_without_mutating_source():
    raw = sample(); original = raw.copy(deep=True)
    events = trace(raw, BUILDER)
    assert len(events) == 1
    event = events.iloc[0]
    assert event.rule == 'lag' and event.date == '2026-07-03'
    assert event.trigger_date == '2026-07-05'
    assert event.event_factor == 1.2 and event.code_rows_between_event_and_trigger == 2
    assert event.trigger_stocks_before == 100 and event.trigger_stocks_after == 120
    pd.testing.assert_frame_equal(raw, original)


def test_changed_adjusted_source_cannot_receive_verified_trace():
    raw = sample(); raw.loc[0,'adj_high'] += 1
    with pytest.raises(AssertionError):
        trace(raw, BUILDER)


def test_unreviewed_builder_is_not_executed(tmp_path):
    builder = tmp_path/'builder.py'
    builder.write_text('raise RuntimeError("must not execute")')
    with pytest.raises(ValueError, match='unreviewed_adjustment_builder'):
        trace(sample(), builder)
