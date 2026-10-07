"""Content-verified feature reuse, independent of collection success status."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa

from modules import ohlcv_quality, us_symbol_lineage, us_split_basis
from multi_agent.tools.intraday_cache_journal import save_json


def file_sha(path):
    path = Path(path)
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inputs(universe, paths, *, start, end, output_prefix, feature_batch_size):
    from multi_agent.tools import backfill_us_daily_features as bf
    return {
        'schema': 1, 'start': start, 'end_exclusive': end,
        'market': paths.market, 'output_prefix': output_prefix,
        'feature_batch_size': feature_batch_size, 'feature_version': bf.FEATURE_VERSION,
        'universe_csv_sha256': hashlib.sha256(universe.to_csv(index=False).encode()).hexdigest(),
        'raw': {str(bf._raw_path(paths, s)): file_sha(bf._raw_path(paths, s))
                for s in universe.symbol.astype(str)},
        'implementation': {Path(p).name: file_sha(p) for p in
                           [bf.__file__, ohlcv_quality.__file__, us_symbol_lineage.__file__,
                            us_split_basis.__file__, us_split_basis.REFERENCE, __file__]},
        'libraries': {'pandas': pd.__version__, 'numpy': np.__version__, 'pyarrow': pa.__version__},
    }


def _index(paths, prefix):
    key = hashlib.sha256(prefix.encode()).hexdigest()
    return paths.market_root / '.refresh/feature_panels' / (key + '.json')


def lookup(paths, expected):
    from multi_agent.tools import backfill_us_daily_features as bf
    try:
        record = json.loads(_index(paths, expected['output_prefix']).read_text())
        if record['inputs'] != expected:
            return None
        info = record['info']
        if not isinstance(info, dict) or not isinstance(record.get('artifacts'), dict):
            return None
        # A transient feature computation/read failure must get another attempt.
        if info.get('failed_feature_reasons'):
            return None
        selected = bf._consumer_panel(paths, expected['output_prefix'])
        if selected is None or str(selected) != info['output_feature_path']:
            return None
        for field in ('output_feature_path', 'output_latest_path', 'output_latest_csv_path'):
            path = info.get(field)
            if path and (not record['artifacts'].get(path) or file_sha(path) != record['artifacts'][path]):
                return None
        return {**info, 'feature_panel_reused': True}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def record(paths, manifest, info):
    panel = Path(info['output_feature_path'])
    if not panel.exists():
        return
    artifacts = {info[k]: file_sha(info[k]) for k in
                 ('output_feature_path', 'output_latest_path', 'output_latest_csv_path') if info.get(k)}
    payload = {'inputs': manifest, 'info': info, 'artifacts': artifacts}
    provenance = panel.with_suffix('.provenance.json')
    if provenance.exists():
        raise FileExistsError(provenance)
    save_json(provenance, payload)
    save_json(_index(paths, manifest['output_prefix']), payload)
