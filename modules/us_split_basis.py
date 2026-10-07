"""Exact, independently audited VWAV split-basis normalization.

Only two known nominal rows are transformed. The 299 pre-split rows can leave
quarantine only when all nine numeric fields equal the audited adjusted rows.
Unfamiliar corrections or later corporate actions require another source audit.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

REFERENCE = Path(__file__).with_name('data') / 'vwav_split_basis_20261007.json'
REFERENCE_SHA256 = '7b83cbb065c54a1879715e35d8d46f0ec803d2d60a2c815875a8a1fd2ec47f8e'


@lru_cache(maxsize=1)
def reference():
    raw = REFERENCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REFERENCE_SHA256:
        raise ValueError('split_basis_reference_integrity_failed')
    return json.loads(raw)


def _candidates(frame):
    if not {'symbol', 'source', 'date'}.issubset(frame.columns):
        return np.array([], dtype=int)
    return np.flatnonzero((frame.symbol.eq('VWAV') & frame.source.eq('yfinance') &
                           pd.to_datetime(frame.date, errors='coerce').lt('2026-09-22')).to_numpy())


def _matches(row, values, fields):
    if values is None or not set(fields).issubset(row.index):
        return False
    actual = pd.to_numeric(row[fields], errors='coerce').to_numpy(dtype=float)
    return bool(np.isfinite(actual).all() and np.array_equal(actual, np.asarray(values, dtype=float)))


def normalize_known_split_rows(frame):
    positions = _candidates(frame)
    if not len(positions):
        return frame
    ref = reference()
    out = frame.copy()
    for position in positions:
        row = out.iloc[position]
        day = str(pd.Timestamp(row['date']).date())
        if _matches(row, ref['known_nominal_rows'].get(day), ref['fields']):
            for field, value in zip(ref['fields'], ref['verified_adjusted_rows'][day]):
                out.iat[position, out.columns.get_loc(field)] = value
    return out


def verified_split_rows(frame):
    verified = np.zeros(len(frame), dtype=bool)
    positions = _candidates(frame)
    if len(positions):
        ref = reference()
        for position in positions:
            row = frame.iloc[position]
            day = str(pd.Timestamp(row['date']).date())
            verified[position] = _matches(row, ref['verified_adjusted_rows'].get(day), ref['fields'])
    return verified
