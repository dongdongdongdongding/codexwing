"""Independent prediction/ranking/cadence checks; never reads test outcomes."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.lowliq_touch10_core import FEATS
from research.audit_kr_adjustment_asof import digest
from research.run_lowliq_touch10_reconstruction import save_json


def verify(root):
    parent = root/'runtime_state/audit/lowliq_touch10_20261007'
    amended = root/'runtime_state/audit/lowliq_touch10_cumulative_20261007'
    complete = json.loads((parent/'scores_complete.json').read_text())
    manifest = json.loads((parent/'manifest.json').read_text())
    spec = json.loads((parent/'prereg.json').read_text())
    assert digest(parent/'prereg.json') == manifest['spec_sha256']
    assert complete['publication_allowed'] is False and complete['test_outcomes_computed'] is False
    for path, sha in manifest['code'].items():
        assert digest(root/path) == sha
    derivative = json.loads((amended/'manifest.json').read_text())
    assert derivative['parent_manifest'] == manifest
    assert derivative['parent_complete_sha256'] == digest(parent/'scores_complete.json')
    assert digest(amended/'prereg.json') == derivative['spec_sha256']
    assert digest(root/'research/freeze_lowliq_cumulative_cadence.py') == derivative['code_sha256']
    model_receipts = {p.stem: json.loads(p.read_text()) for p in (parent/'models').glob('*.json')}
    assert set(model_receipts) == {f'{k}_{s}' for k in ['real','noise'] for s in [0,1,2]}
    models = {}
    for name, receipt in model_receipts.items():
        path = parent/'models'/f'{name}.txt'
        assert digest(path) == receipt['model_sha256'] == derivative['models'][name]
        models[name] = lgb.Booster(model_file=str(path))
        assert models[name].num_feature() == len(FEATS) and models[name].num_trees() == 400
    files = sorted((parent/'scores').glob('*.json'))
    assert len(files) == complete['dates'] == len(derivative['inputs'])
    histories = {kind: {name: [] for name in models} for kind in ['parent','amended']}
    total_rows = 0
    checks = []
    required_columns = set(FEATS + ['date','code','market','volume','liq'] + list(models))
    for i, path in enumerate(files):
        day = path.stem; record = json.loads(path.read_text())
        changed = json.loads((amended/'scores'/path.name).read_text())
        data = path.with_suffix('.parquet'); frame = pd.read_parquet(data)
        inp = derivative['inputs'][day]
        assert digest(path) == inp['record_sha256']
        assert digest(data) == inp['universe_sha256'] == record['universe_sha256']
        assert changed['parent_universe_sha256'] == record['universe_sha256']
        assert set(frame.columns) == required_columns
        assert not frame.code.duplicated().any() and frame.date.eq(pd.Timestamp(day)).all()
        assert frame.market.isin(['KOSPI','KOSDAQ']).all()
        assert (frame.liq.ge(5e8) & frame.liq.lt(3e9) & frame.volume.gt(0)).all()
        assert frame[FEATS[:6]].notna().all().all()
        assert record['date'] == record['input_max_date'] == changed['date'] == day
        assert record['model_fit_cutoff'] == spec['fit_cutoff']
        assert record['publication_allowed'] is changed['publication_allowed'] is False
        x = frame[FEATS].clip(-1e4, 1e4).to_numpy(dtype=np.float32)
        for name, model in models.items():
            kind, seed = name.split('_')
            if kind == 'noise':
                # Reconstruct the documented RNG without calling the runner helper.
                raw_seed = hashlib.sha256(f'lowliq-touch10:{seed}:predict-{day}'.encode()).digest()[:8]
                values = np.random.default_rng(int.from_bytes(raw_seed, 'big')).normal(size=x.shape).astype(np.float32)
            else:
                values = x
            predicted = model.predict(values, num_threads=4) if len(frame) else np.array([])
            np.testing.assert_array_equal(predicted, frame[name].to_numpy())
            assert np.isfinite(predicted).all()
            order = np.lexsort((frame.code.to_numpy(), -predicted))[:3]
            top = [{'code': frame.iloc[j].code, 'market': frame.iloc[j].market,
                    'liq': float(frame.iloc[j].liq), 'score': float(predicted[j])} for j in order]
            for stream, rec in [('parent', record), ('amended', changed)]:
                prior = histories[stream][name]
                allow = sum(prior[-4:]) < 3
                if stream == 'amended':
                    allow = allow and (sum(prior)+1 <= 3*(i+1)//5)
                expected = top if allow else []
                assert rec['variants'][name] == {'source_picks': top, 'picks': expected}
                prior.append(bool(expected))
        total_rows += len(frame)
        checks.append({'date': day, 'universe_rows': len(frame), 'universe_sha256': digest(data)})
    result = {'dates': len(files), 'universe_rows': total_rows,
              'prediction_cells_exact': total_rows*len(models),
              'parent_and_amended_rank_cadence_exact': True,
              'test_outcomes_read_or_computed': False, 'publication_allowed': False,
              'firing_dates': {kind: {name: sum(flags) for name,flags in group.items()}
                               for kind,group in histories.items()}, 'date_checks': checks}
    out = root/'runtime_state/audit/lowliq_touch10_verification_20261007/scores_verification.json'
    save_json(out, result)
    print(json.dumps({k:v for k,v in result.items() if k != 'date_checks'}), flush=True)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True, type=Path)
    verify(ap.parse_args().root)
