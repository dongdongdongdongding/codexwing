"""Unit tests for the peak-chase overextension primitives (network-free).

Locks the validated rule: the guard fires only on at-high AND overheated, and fails OPEN.
"""
import pandas as pd

from modules.overextension import rsi14_rolling, peak_chase_verdict


def test_rsi_all_up_is_100():
    s = pd.Series(range(1, 40))  # strictly rising
    assert rsi14_rolling(s) == 100.0


def test_rsi_insufficient_data_is_none():
    assert rsi14_rolling(pd.Series([1, 2, 3])) is None


def test_rsi_midrange_between_bounds():
    # alternating up/down should sit well under overheated
    s = pd.Series([10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11])
    r = rsi14_rolling(s)
    assert r is not None and 30 < r < 70


def test_peak_chase_only_on_combination():
    # at-high AND overheated -> guard fires
    assert peak_chase_verdict(72.0, -1.0) is True
    # overheated but pulled back -> no guard (today's picks)
    assert peak_chase_verdict(72.0, -15.0) is False
    # at-high but not overheated -> no guard
    assert peak_chase_verdict(50.0, -1.0) is False


def test_peak_chase_fails_open_on_missing():
    assert peak_chase_verdict(None, -1.0) is False
    assert peak_chase_verdict(72.0, None) is False


def test_peak_chase_threshold_boundary():
    # exactly at thresholds counts as peak-chase
    assert peak_chase_verdict(65.0, -3.0) is True
    assert peak_chase_verdict(64.9, -3.0) is False
    assert peak_chase_verdict(65.0, -3.1) is False
