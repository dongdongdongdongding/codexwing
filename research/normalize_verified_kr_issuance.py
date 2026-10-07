"""Append verified non-pro-rata issuance corrections in an immutable research epoch."""
import argparse
from collections import Counter
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.run_lowliq_touch10_reconstruction import save_json
from research.normalize_verified_kr_events import ADJUSTED, corrected_chunk


def build(source, evidence, out, spec, *, implementation_sha):
    out.mkdir(parents=True, exist_ok=True)
    with (out/'build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if digest(source) != spec['source_sha256']:
            raise ValueError('changed_parent_source')
        for name, key in [('receipts.json','receipts_sha256'), ('economics_verification.json','economics_sha256')]:
            if digest(evidence/name) != spec[key]:
                raise ValueError('changed_official_evidence')
        receipts = json.loads((evidence/'receipts.json').read_text())
        for name in {r['evidence'] for r in spec['rules']}:
            if (digest(evidence/(name+'.html')) != receipts[name]['sha256']
                    or digest(evidence/(name+'.txt')) != receipts[name]['text_sha256']):
                raise ValueError('changed_official_document')
        save_json(out/'manifest.json', {'spec':spec, 'implementation_sha256':implementation_sha,
            'source_path':str(source), 'pandas_version':pd.__version__, 'pyarrow_version':pa.__version__,
            'source_certified':False, 'publication_allowed':False})
        destination = out/'panel.parquet'
        receipt_path = out/'receipt.json'
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            if digest(destination) != receipt['output_sha256']:
                raise ValueError('changed_corrected_output')
            return {'status':'REUSED', **receipt}
        expected = Counter()
        for rule in spec['rules']:
            expected[rule['code']] += rule['rows']
        fd, temporary = tempfile.mkstemp(dir=out, prefix='.panel.', suffix='.parquet')
        os.close(fd)
        try:
            reader = pq.ParquetFile(source)
            counts = Counter(); per_rule = Counter(); rows = 0
            with pq.ParquetWriter(temporary, reader.schema_arrow, compression='snappy') as writer:
                for batch in reader.iter_batches(batch_size=65536):
                    frame = batch.to_pandas()
                    for index, rule in enumerate(spec['rules']):
                        per_rule[index] += int((frame.code.eq(rule['code'])
                            & frame.date.between(rule['start'], rule['end'])).sum())
                    corrected, changed = corrected_chunk(frame, spec['rules'])
                    counts.update(changed); rows += len(frame)
                    table = pa.Table.from_pandas(corrected, schema=reader.schema_arrow, preserve_index=False)
                    pd.testing.assert_frame_equal(table.to_pandas(), corrected, check_exact=True)
                    writer.write_table(table)
            if (rows != spec['source_rows'] or counts != expected
                    or any(per_rule[i] != rule['rows'] for i, rule in enumerate(spec['rules']))):
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
                'corrected_rows_by_rule':[per_rule[i] for i in range(len(spec['rules']))],
                'other_rows_all_fields_exact':rows-sum(counts.values()), 'all_raw_fields_exact':True,
                'output_sha256':output_hash, 'parent_sha256_unchanged':spec['source_sha256'],
                'source_certified':False, 'publication_allowed':False,
                'test_strategy_outcomes_computed':False, 'live_consumers_changed':False}
            save_json(receipt_path, receipt)
            return {'status':'CREATED', **receipt}
        finally:
            os.unlink(temporary)


def run(root):
    spec_path = ROOT/'research/data/kr_issuance_corrections_20261007.json'
    spec = json.loads(spec_path.read_text())
    if digest(ROOT/'research/normalize_verified_kr_events.py') != spec['chunk_implementation_sha256']:
        raise ValueError('changed_chunk_implementation')
    audit = root/'runtime_state/audit'
    result = build(audit/'kr_verified_events_v1_20261007/panel.parquet',
        audit/'lowliq_corporate_actions_20261007/followup_issuance',
        audit/'kr_verified_events_v2_20261007', spec,
        implementation_sha={'builder':digest(Path(__file__)), 'spec':digest(spec_path),
                            'chunk':spec['chunk_implementation_sha256']})
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    run(parser.parse_args().root)
