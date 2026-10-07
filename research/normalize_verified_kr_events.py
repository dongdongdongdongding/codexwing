"""Create a separate immutable, partially corrected research source epoch.

No live cache or frozen parent is replaced. Unsupported source revisions fail.
The two reviewed events do not certify all other corporate actions or models.
"""
import argparse
from collections import Counter
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.run_lowliq_touch10_reconstruction import save_json

ADJUSTED = ['adj_factor', 'adj_open', 'adj_high', 'adj_low', 'adj_close']


def corrected_chunk(frame, rules):
    changed = np.zeros(len(frame), dtype=bool)
    result = frame.copy(deep=True)
    counts = Counter()
    for rule in rules:
        mask = (frame.code.eq(rule['code']) & frame.date.between(rule['start'], rule['end'])).to_numpy()
        if (mask & changed).any():
            raise ValueError('overlapping_correction_rules')
        if not mask.any():
            continue
        original = frame.loc[mask]
        if not original.adj_factor.eq(rule['old_factor']).all() or not original.stocks.eq(rule['expected_stocks']).all():
            raise ValueError('unsupported_factor_or_share_revision')
        for name in ['open', 'high', 'low', 'close']:
            np.testing.assert_array_equal(original['adj_'+name], original[name]*rule['old_factor'])
            result.loc[mask, 'adj_'+name] = original[name]*rule['new_factor']
        result.loc[mask, 'adj_factor'] = rule['new_factor']
        changed |= mask
        counts[rule['code']] += int(mask.sum())
    pd.testing.assert_frame_equal(frame.loc[~changed], result.loc[~changed], check_exact=True)
    untouched = [name for name in frame if name not in ADJUSTED]
    pd.testing.assert_frame_equal(frame[untouched], result[untouched], check_exact=True)
    return result, counts


def run(root):
    audit = root/'runtime_state/audit'
    source = audit/'kr_adjustment_asof_20261007/final/panel.parquet'
    evidence = audit/'lowliq_corporate_actions_20261007'
    out = audit/'kr_verified_events_v1_20261007'
    out.mkdir(parents=True, exist_ok=True)
    with (out/'build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        spec_path = ROOT/'research/data/kr_action_corrections_20261007.json'
        spec = json.loads(spec_path.read_text())
        if digest(source) != spec['source_sha256']:
            raise ValueError('changed_parent_source')
        if digest(evidence/'capture_receipts.json') != spec['official_receipts_sha256'] or digest(evidence/'confirmed_examples.json') != spec['confirmed_examples_sha256']:
            raise ValueError('changed_official_evidence')
        receipts = json.loads((evidence/'capture_receipts.json').read_text())
        for name in {name for rule in spec['rules'] for name in rule['evidence']}:
            if digest(evidence/(name+'.html')) != receipts[name]['sha256'] or digest(evidence/(name+'.txt')) != receipts[name]['text_sha256']:
                raise ValueError('changed_official_document')
        save_json(out/'manifest.json', {'spec':spec, 'spec_sha256':digest(spec_path),
            'code_sha256':digest(Path(__file__)), 'source_path':str(source),
            'pandas_version':pd.__version__, 'pyarrow_version':pa.__version__,
            'source_certified':False, 'publication_allowed':False})
        destination = out/'panel.parquet'
        receipt_path = out/'receipt.json'
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            if digest(destination) != receipt['output_sha256']:
                raise ValueError('changed_corrected_output')
            print(json.dumps({'status':'REUSED', **receipt}), flush=True)
            return receipt
        fd, temporary = tempfile.mkstemp(dir=out, prefix='.panel.', suffix='.parquet')
        os.close(fd)
        try:
            reader = pq.ParquetFile(source)
            counts = Counter(); rows = 0
            with pq.ParquetWriter(temporary, reader.schema_arrow, compression='snappy') as writer:
                for batch in reader.iter_batches(batch_size=65536):
                    frame = batch.to_pandas()
                    corrected, batch_counts = corrected_chunk(frame, spec['rules'])
                    counts.update(batch_counts); rows += len(frame)
                    table = pa.Table.from_pandas(corrected, schema=reader.schema_arrow, preserve_index=False)
                    pd.testing.assert_frame_equal(table.to_pandas(), corrected, check_exact=True)
                    writer.write_table(table)
            if rows != spec['source_rows'] or dict(counts) != {r['code']:r['rows'] for r in spec['rules']}:
                raise ValueError('unexpected_source_scope')
            if digest(source) != spec['source_sha256']:
                raise ValueError('parent_changed_during_build')
            with open(temporary, 'rb') as stream:
                os.fsync(stream.fileno())
            output_hash = digest(temporary)
            try:
                os.link(temporary, destination)
            except FileExistsError:
                if digest(destination) != output_hash:
                    raise ValueError('immutable_output_changed')
            receipt = {'source_rows':rows, 'corrected_rows':sum(counts.values()),
                'corrected_rows_by_code':dict(counts), 'corrected_fields':ADJUSTED,
                'other_rows_all_fields_exact':rows-sum(counts.values()),
                'all_raw_fields_exact':True, 'output_sha256':output_hash,
                'parent_sha256_unchanged':spec['source_sha256'],
                'source_certified':False, 'publication_allowed':False,
                'test_strategy_outcomes_computed':False, 'live_consumers_changed':False}
            save_json(receipt_path, receipt)
            print(json.dumps({'status':'CREATED', **receipt}), flush=True)
            return receipt
        finally:
            os.unlink(temporary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    run(parser.parse_args().root)
