import numpy as np
import pandas as pd
import pytest

from research.audit_lowliq_selection import barrier_labels, causal_feature_eligible, legacy_labels, load_legacy


def frame(n=8):
    return pd.DataFrame({'date': pd.date_range('2026-01-01', periods=n),
                         'adj_open': 100., 'adj_high': 101., 'adj_low': 99.,
                         'adj_close': 100., 'volume': 1e6, 'amount': 1e9})


def untouched(*args):
    return np.full(len(args[0]), np.nan)


def test_mature_untouched_rows_are_nan_and_future_exit_changes_retention():
    f = frame()
    raw, offsets = barrier_labels(f)
    assert np.isnan(raw).all() and not offsets.any()
    alive, valid = legacy_labels(f, untouched, False)
    exited, _ = legacy_labels(f, untouched, True)
    assert valid[0] and len(f) > 5
    assert np.isnan(alive[0]) and exited[0] == 0
    assert np.isnan(exited[-1])  # No next-open entry at the right edge.


def test_first_event_controls_label_and_resolution_date():
    f = frame()
    f.loc[2, 'adj_low'] = 94
    f.loc[3, 'adj_high'] = 110
    labels, offsets = barrier_labels(f)
    assert labels[0] == 0 and offsets[0] == 2
    assert labels[2] == 1 and offsets[2] == 1


def test_suspended_touch_is_ignored_and_horizon_does_not_expand():
    f = frame()
    f.loc[1, ['adj_high', 'volume']] = [110, 0]
    f.loc[6, 'adj_high'] = 110
    labels, offsets = barrier_labels(f)
    assert np.isnan(labels[0]) and offsets[0] == 0


def test_same_bar_ambiguity_reproduces_old_rule_without_endorsing_it():
    f = frame()
    f.loc[2, ['adj_high', 'adj_low']] = [106, 94]
    labels, offsets = barrier_labels(f)
    assert labels[0] == 1 and offsets[0] == 2


def test_candidate_eligibility_depends_only_on_observed_prefix():
    f = frame(90)
    before = causal_feature_eligible(f)
    changed = f.copy()
    changed.loc[71:, ['adj_close', 'amount']] = [2., 1e12]
    np.testing.assert_array_equal(before[:71], causal_feature_eligible(changed)[:71])
    assert not before[:60].any() and before[60:].all()


def test_future_touch_changes_legacy_retention_but_not_signal_eligibility():
    quiet = frame(90)
    touched = quiet.copy()
    touched.loc[72, 'adj_high'] = 106
    assert causal_feature_eligible(quiet)[70] and causal_feature_eligible(touched)[70]
    assert np.isnan(barrier_labels(quiet)[0][70])
    assert barrier_labels(touched)[0][70] == 1


def test_unreviewed_legacy_source_is_not_executed(tmp_path):
    path = tmp_path / 'legacy.py'
    path.write_text('raise RuntimeError("must not execute")')
    with pytest.raises(ValueError, match='unreviewed_legacy_source'):
        load_legacy(path)
