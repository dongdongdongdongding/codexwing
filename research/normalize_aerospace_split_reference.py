"""Build immutable v11 for the verified Aerospace 2024 auction reference."""
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
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_aerospace_split_reference import SOURCE_SHA
from research.normalize_lowliq_history_references import overlay_rules
from research.normalize_verified_kr_events import corrected_chunk, ADJUSTED
from research.recover_lowliq_history_request import digest
from research.run_lowliq_touch10_reconstruction import save_json

VERIFICATION_SHA='31d8267d88203bdacfe424b8f23a8735c3d4e84778189a80636684dc08007c63'


def run(root):
    audit=root/'runtime_state/audit';source=audit/'kr_verified_events_v10_20261008/panel.parquet'
    proof=audit/'aerospace_split_evidence_20261008/verification.json'
    if digest(source)!=SOURCE_SHA or digest(proof)!=VERIFICATION_SHA:raise ValueError('changed_verified_inputs')
    evidence=json.loads(proof.read_text())
    if digest(ROOT/'research/audit_aerospace_split_reference.py')!=evidence['implementation_sha256']:raise ValueError('changed_verifier')
    for name,sha in evidence['dependencies'].items():
        if digest(ROOT/name)!=sha:raise ValueError('changed_verifier_dependency')
    for path,sha in evidence['input_sha256'].items():
        if digest(Path(path))!=sha:raise ValueError('changed_supporting_evidence')
    if len(evidence['events'])!=1 or {e['code'] for e in evidence['events']}!={'012450'}:
        raise ValueError('changed_correction_scope')
    subset=pd.read_parquet(source,filters=[('code','==','012450')]).sort_values('date')
    rules=overlay_rules(subset,evidence['events']);expected=Counter()
    for rule in rules:expected[rule['code']]+=rule['rows']
    out=audit/'kr_verified_events_v11_20261008';out.mkdir(parents=True,exist_ok=True)
    manifest={'source_sha256':SOURCE_SHA,'verification_sha256':VERIFICATION_SHA,'events':evidence['events'],
        'rules':rules,'source_rows':5360785,'implementation_sha256':digest(Path(__file__)),
        'helper_sha256':{name:digest(ROOT/name) for name in ['research/normalize_lowliq_history_references.py',
                        'research/normalize_verified_kr_events.py']},
        'source_certified':False,'portfolio_return_certified':False,'point_in_time_certified':False,
        'publication_allowed':False,'strategy_outcomes_computed':False}
    with (out/'build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);save_json(out/'manifest.json',manifest)
        destination=out/'panel.parquet';receipt_path=out/'receipt.json'
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text())
            if digest(destination)!=receipt['output_sha256']:raise ValueError('changed_v11_output')
            print(json.dumps({'status':'REUSED',**receipt}),flush=True);return receipt
        fd,temp=tempfile.mkstemp(dir=out,prefix='.panel.',suffix='.parquet');os.close(fd)
        try:
            reader=pq.ParquetFile(source);counts=Counter();per_rule=Counter();total=0
            with pq.ParquetWriter(temp,reader.schema_arrow,compression='snappy') as writer:
                for batch in reader.iter_batches(batch_size=65536):
                    frame=batch.to_pandas()
                    for i,rule in enumerate(rules):per_rule[i]+=int((frame.code.eq(rule['code'])&frame.date.between(rule['start'],rule['end'])).sum())
                    corrected,changed=corrected_chunk(frame,rules);counts.update(changed);total+=len(frame)
                    table=pa.Table.from_pandas(corrected,schema=reader.schema_arrow,preserve_index=False)
                    pd.testing.assert_frame_equal(table.to_pandas(),corrected,check_exact=True);writer.write_table(table)
            if total!=5360785 or counts!=expected or any(per_rule[i]!=r['rows'] for i,r in enumerate(rules)):
                raise ValueError('changed_whole_source_scope')
            if digest(source)!=SOURCE_SHA:raise ValueError('parent_changed_during_build')
            with open(temp,'rb') as stream:os.fsync(stream.fileno())
            output_sha=digest(Path(temp))
            try:os.link(temp,destination)
            except FileExistsError:
                if digest(destination)!=output_sha:raise ValueError('immutable_output_changed')
            receipt={'source_rows':total,'corrected_rows':sum(counts.values()),'corrected_rows_by_code':dict(counts),
                'rules':len(rules),'verified_events':1,'output_sha256':output_sha,'parent_sha256':SOURCE_SHA,
                'all_raw_fields_exact':True,'other_rows_all_fields_exact':total-sum(counts.values()),
                'corrected_fields':ADJUSTED,'source_certified':False,'portfolio_return_certified':False,
                'point_in_time_certified':False,'publication_allowed':False,'strategy_outcomes_computed':False,
                'live_consumers_changed':False}
            save_json(receipt_path,receipt);print(json.dumps({'status':'CREATED',**receipt}),flush=True);return receipt
        finally:os.unlink(temp)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
