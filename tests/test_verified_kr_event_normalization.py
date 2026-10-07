import copy

import pandas as pd
import pytest

from research.normalize_verified_kr_events import corrected_chunk


def sample():
    frame = pd.DataFrame({'code':['000001']*4+['000002'],
        'date':pd.to_datetime(['2026-08-02','2026-08-03','2026-08-06','2026-08-07','2026-08-03']),
        'stocks':[100]*5, 'open':[50.]*5, 'high':[55.]*5, 'low':[48.]*5,
        'close':[52.]*5, 'volume':[1000.]*5, 'amount':[51000.]*5, 'adj_factor':[10.]*5})
    for name in ['open','high','low','close']:
        frame['adj_'+name] = frame[name]*frame.adj_factor
    rule={'code':'000001','start':'2026-08-03','end':'2026-08-06',
          'old_factor':10.,'new_factor':13.,'expected_stocks':100}
    return frame, rule


def test_exact_scope_and_nominal_volume_preserved():
    frame,rule=sample();before=frame.copy(deep=True)
    result,counts=corrected_chunk(frame,[rule])
    assert counts=={'000001':2}
    assert result.adj_factor.tolist()==[10.,13.,13.,10.,10.]
    assert result.adj_close.tolist()==[520.,676.,676.,520.,520.]
    pd.testing.assert_frame_equal(result[['volume','amount']],before[['volume','amount']])
    pd.testing.assert_frame_equal(result.loc[[0,3,4]],before.loc[[0,3,4]])
    pd.testing.assert_frame_equal(frame,before)


def test_already_corrected_input_rejected_instead_of_double_adjustment():
    frame,rule=sample();result,_=corrected_chunk(frame,[rule])
    with pytest.raises(ValueError,match='unsupported_factor'):
        corrected_chunk(result,[rule])


def test_revised_share_count_or_adjusted_price_fails():
    frame,rule=sample();frame.loc[1,'stocks']=101
    with pytest.raises(ValueError,match='share_revision'):
        corrected_chunk(frame,[rule])
    frame,rule=sample();frame.loc[1,'adj_high']+=1
    with pytest.raises(AssertionError):
        corrected_chunk(frame,[rule])


def test_overlapping_rules_fail_without_mutating_input():
    frame,rule=sample();before=frame.copy(deep=True)
    with pytest.raises(ValueError,match='overlapping'):
        corrected_chunk(frame,[rule,copy.deepcopy(rule)])
    pd.testing.assert_frame_equal(frame,before)
