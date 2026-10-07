"""Apply guarded quote-reference overlays to the immutable v6 research panel."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.audit_kr_event_reference import quote_reference
from research.normalize_verified_kr_issuance import build
from research.normalize_verified_kr_issuance_v3 import verify_inputs
from research.normalize_kr_fixed_reference import overlay_factor


def run(root):
    audit=root/'runtime_state/audit';out=audit/'kr_verified_events_v7_20261007'
    path=ROOT/'research/data/kr_suspended_reference_corrections_20261007.json'
    spec=json.loads(path.read_text())
    helpers={'quote_verifier':'research/audit_kr_event_reference.py',
             'overlay':'research/normalize_kr_fixed_reference.py',
             'evidence_verifier':'research/normalize_verified_kr_issuance_v3.py'}
    for key,p in helpers.items():
        if digest(ROOT/p)!=spec[key+'_sha256']:raise ValueError('changed_reference_helper')
    verify_inputs(out/'evidence',spec)
    economics=json.loads((out/'evidence/economics_verification.json').read_text())
    for p,h in economics['input_sha256'].items():
        if digest(Path(p))!=h:raise ValueError('changed_reference_input')
    if spec['price_convention']!='KRX_QUOTE_IMPLIED_REFERENCE_OVERLAY_V1':
        raise ValueError('changed_reference_convention')
    if set(spec['contracts'])!={r['code'] for r in spec['rules']}:
        raise ValueError('reference_scope_disagreement')
    for code,c in spec['contracts'].items():
        p=audit/'lowliq_krx_source_20261007/responses'/f'{code}_nominal.json'
        rows=json.loads(p.read_text())['payload']['output2']
        rows=[r for r in rows if r['stck_bsop_date']==c['date'].replace('-','')]
        if len(rows)!=1 or quote_reference(rows[0],c['reference_price'],c['first_close'])!=c['reference_price']:
            raise ValueError('changed_quote_reference')
    for r in spec['rules']:
        c=spec['contracts'][r['code']]
        for value in [r['start'],r['end'],c['date']]:date.fromisoformat(value)
        if r['start']<c['date'] or r['start']>r['end'] or overlay_factor(r['old_factor'],c)!=r['new_factor']:
            raise ValueError('invalid_reference_rule')
    hashes={k:digest(ROOT/p) for k,p in helpers.items()}
    hashes.update(entrypoint=digest(Path(__file__)),spec=digest(path),
        builder=spec['builder_implementation_sha256'],chunk=spec['chunk_implementation_sha256'])
    result=build(audit/'kr_verified_events_v6_20261007/panel.parquet',out/'evidence',out,spec,implementation_sha=hashes)
    print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    run(parser.parse_args().root)
