"""Exact, independently audited split-basis normalization.

Only known nominal rows are transformed. Supported pre-split rows can leave
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
REFERENCES = {
    'VWAV': (REFERENCE, REFERENCE_SHA256),
    'CPOP': (REFERENCE.with_name('cpop_split_basis_20261007.json'), 'b5dfbe3fc72ffd81a34858c91e6d96fae97184d976edfcbe0ebb1d539d9e8d85'),
    'AIXI': (REFERENCE.with_name('aixi_split_basis_20261007.json'), '0bed47a45f16b5dbe90ff52a9e98fad4dbc077eea8ed29d7629732e87663ba6d'),
    'DLXY': (REFERENCE.with_name('dlxy_split_basis_20261007.json'), '1f1cd5ab2c49ce77a9a1862c95e8edbf8264e230041c907d63b52517385c7088'),
    'SFWL': (REFERENCE.with_name('sfwl_split_basis_20261007.json'), 'a3ca2157c1f8389190b47d25073cacdfbbca6614a4192984ab2b02e465262a40'),
    'WCT': (REFERENCE.with_name('wct_split_basis_20261007.json'), '1b26938dabc218821cf09f825bdd6ad2531bd85e515f457b9b257395f4a0aee5'),
}


@lru_cache(maxsize=len(REFERENCES))
def reference(symbol='VWAV'):
    path, expected = REFERENCES[symbol]
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('split_basis_reference_integrity_failed')
    return json.loads(raw)


def _candidates(frame, symbol):
    if not {'symbol', 'source', 'date'}.issubset(frame.columns):
        return np.array([], dtype=int)
    if not frame.symbol.eq(symbol).any():
        return np.array([], dtype=int)
    return np.flatnonzero((frame.symbol.eq(symbol) & frame.source.eq('yfinance') &
                           pd.to_datetime(frame.date, errors='coerce').lt(reference(symbol)['effective'])).to_numpy())


def _matches(row, values, fields):
    if values is None or not set(fields).issubset(row.index):
        return False
    actual = pd.to_numeric(row[fields], errors='coerce').to_numpy(dtype=float)
    return bool(np.isfinite(actual).all() and np.array_equal(actual, np.asarray(values, dtype=float)))


def normalize_known_split_rows(frame):
    out = frame
    for symbol in REFERENCES:
        positions = _candidates(frame, symbol)
        if not len(positions):
            continue
        ref = reference(symbol)
        if out is frame:
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
    for symbol in REFERENCES:
        positions = _candidates(frame, symbol)
        if not len(positions):
            continue
        ref = reference(symbol)
        for position in positions:
            row = frame.iloc[position]
            day = str(pd.Timestamp(row['date']).date())
            verified[position] = _matches(row, ref['verified_adjusted_rows'].get(day), ref['fields'])
    return verified
