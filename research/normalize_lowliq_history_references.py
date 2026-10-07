"""Build v8 with nine verified historical price-reference overlays only."""
import argparse
from collections import Counter
import fcntl
from fractions import Fraction as F
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
from research.audit_kr_adjustment_asof import digest
from research.freeze_lowliq_history_scope import V7_SHA
from research.normalize_verified_kr_events import corrected_chunk,ADJUSTED
from research.run_lowliq_touch10_reconstruction import save_json

VERIFICATION_SHA='1fa0fa0b6e505c61a6b1581cc24f267977757a60096fa3cbaa5bce08e476e8ef'
CHUNK_SHA='6128ab7ce1d3394da5097e87f604762975201b121ded97376f9c92ac0716d306'


def overlay_rules(raw,events):
    rules=[]
    for code,group in raw.groupby('code',sort=True):
        applicable=sorted([e for e in events if e['code']==code],key=lambda e:e['date'])
        if not applicable:continue
        for event in applicable:
            pair=group[group.date.le(event['date'])].tail(2)
            if len(pair)!=2 or pair.date.iloc[-1]!=pd.Timestamp(event['date']):raise ValueError('missing_event_boundary')
            before,current=pair.iloc[0],pair.iloc[1]
            if (before.close!=event['prior_close'] or current.close!=event['first_close']
                or before.adj_factor!=event['before_factor'] or current.adj_factor!=event['old_event_factor']):
                raise ValueError('changed_event_boundary')
            expected=F(str(before.adj_factor))/F(str(current.adj_factor))*F(str(before.close))/F(event['reference_price'])
            if expected!=F(event['multiplier_numerator'],event['multiplier_denominator']):raise ValueError('changed_event_multiplier')
        previous_key=None
        for row in group.itertuples():
            active=[e for e in applicable if e['date']<=str(row.date.date())]
            if not active:continue
            factor=F(str(row.adj_factor))
            for e in active:factor*=F(e['multiplier_numerator'],e['multiplier_denominator'])
            new=float(factor)
            key=(row.adj_factor,row.stocks,new,tuple(e['id'] for e in active))
            if key!=previous_key:
                rules.append({'code':code,'start':str(row.date.date()),'end':str(row.date.date()),
                              'old_factor':float(row.adj_factor),'new_factor':new,'expected_stocks':int(row.stocks),
                              'rows':1,'verified_events':list(key[3])})
            else:
                rules[-1]['end']=str(row.date.date());rules[-1]['rows']+=1
            previous_key=key
    return rules


def run(root):
    audit=root/'runtime_state/audit';source=audit/'kr_verified_events_v7_20261007/panel.parquet'
    proof=audit/'lowliq_history_reference_evidence_20261007/verification.json'
    if digest(proof)!=VERIFICATION_SHA or digest(source)!=V7_SHA:raise ValueError('changed_verified_inputs')
    evidence=json.loads(proof.read_text())
    if digest(ROOT/'research/audit_lowliq_history_references.py')!=evidence['implementation_sha256']:
        raise ValueError('changed_reference_verifier')
    if digest(ROOT/'research/normalize_verified_kr_events.py')!=CHUNK_SHA:raise ValueError('changed_chunk_helper')
    for path,sha in evidence['input_sha256'].items():
        if digest(Path(path))!=sha:raise ValueError('changed_supporting_evidence')
    codes=sorted({e['code'] for e in evidence['events']})
    subset=pd.read_parquet(source,filters=[('code','in',codes)]).sort_values(['code','date'])
    rules=overlay_rules(subset,evidence['events'])
    out=audit/'kr_verified_events_v8_20261007';out.mkdir(parents=True,exist_ok=True)
    expected=Counter()
    for r in rules:expected[r['code']]+=r['rows']
    manifest={'source_sha256':V7_SHA,'verification_sha256':VERIFICATION_SHA,'events':evidence['events'],'rules':rules,
              'implementation_sha256':digest(Path(__file__)),'chunk_sha256':CHUNK_SHA,'source_rows':5360785,
              'source_certified':False,'publication_allowed':False,'portfolio_return_certified':False,
              'unresolved':evidence['unresolved'],'test_outcomes_computed':False}
    with (out/'build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);save_json(out/'manifest.json',manifest)
        destination=out/'panel.parquet';receipt_path=out/'receipt.json'
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text())
            if digest(destination)!=receipt['output_sha256']:raise ValueError('changed_v8_output')
            print(json.dumps({'status':'REUSED',**receipt}),flush=True);return receipt
        fd,temp=tempfile.mkstemp(dir=out,prefix='.panel.',suffix='.parquet');os.close(fd)
        try:
            reader=pq.ParquetFile(source);counts=Counter();per_rule=Counter();total=0
            with pq.ParquetWriter(temp,reader.schema_arrow,compression='snappy') as writer:
                for batch in reader.iter_batches(batch_size=65536):
                    frame=batch.to_pandas()
                    for i,r in enumerate(rules):per_rule[i]+=int((frame.code.eq(r['code'])&frame.date.between(r['start'],r['end'])).sum())
                    corrected,changed=corrected_chunk(frame,rules);counts.update(changed);total+=len(frame)
                    table=pa.Table.from_pandas(corrected,schema=reader.schema_arrow,preserve_index=False)
                    pd.testing.assert_frame_equal(table.to_pandas(),corrected,check_exact=True);writer.write_table(table)
            if total!=5360785 or counts!=expected or any(per_rule[i]!=r['rows'] for i,r in enumerate(rules)):
                raise ValueError('changed_correction_scope')
            if digest(source)!=V7_SHA:raise ValueError('parent_changed_during_build')
            with open(temp,'rb') as stream:os.fsync(stream.fileno())
            output_sha=digest(Path(temp))
            try:os.link(temp,destination)
            except FileExistsError:
                if digest(destination)!=output_sha:raise ValueError('immutable_output_changed')
            receipt={'source_rows':total,'corrected_rows':sum(counts.values()),'corrected_rows_by_code':dict(counts),
                     'rules':len(rules),'verified_events':len(evidence['events']),'output_sha256':output_sha,
                     'parent_sha256':V7_SHA,'all_raw_fields_exact':True,'other_rows_all_fields_exact':total-sum(counts.values()),
                     'corrected_fields':ADJUSTED,'source_certified':False,'publication_allowed':False,
                     'portfolio_return_certified':False,'test_outcomes_computed':False,'live_consumers_changed':False}
            save_json(receipt_path,receipt);print(json.dumps({'status':'CREATED',**receipt}),flush=True);return receipt
        finally:os.unlink(temp)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    run(p.parse_args().root)
