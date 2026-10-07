"""Overlay verified fixed-price event references without changing later events."""
import argparse
from datetime import date
from fractions import Fraction
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.normalize_verified_kr_issuance import build
from research.normalize_verified_kr_issuance_v3 import verify_inputs

CONVENTION='KRX_OFFICIAL_FIXED_REFERENCE_OVERLAY_V1'


def overlay_factor(old_factor, contract):
    values=[Fraction(str(v)) for v in [old_factor,contract['before_factor'],
            contract['old_event_factor'],contract['prior_close'],contract['reference_price']]]
    if any(v<=0 for v in values):
        raise ValueError('invalid_fixed_reference_input')
    old,before,event,prior,reference=values
    return float(old*before/event*prior/reference)


def validate_rules(spec):
    if spec['price_convention']!=CONVENTION:
        raise ValueError('changed_fixed_reference_convention')
    if set(spec['contracts'])!={r['code'] for r in spec['rules']}:
        raise ValueError('fixed_reference_scope_disagreement')
    for rule in spec['rules']:
        contract=spec['contracts'][rule['code']]
        for value in [rule['start'],rule['end'],contract['date']]:date.fromisoformat(value)
        if rule['start']<contract['date'] or rule['start']>rule['end']:
            raise ValueError('invalid_fixed_reference_dates')
        if overlay_factor(rule['old_factor'],contract)!=rule['new_factor']:
            raise ValueError('fixed_reference_factor_disagreement')


def run(root):
    audit=root/'runtime_state/audit';out=audit/'kr_verified_events_v5_20261007'
    path=ROOT/'research/data/kr_fixed_reference_corrections_20261007.json'
    spec=json.loads(path.read_text())
    if digest(ROOT/'research/normalize_verified_kr_issuance_v3.py')!=spec['evidence_verifier_sha256']:
        raise ValueError('changed_evidence_verifier')
    verify_inputs(out/'evidence',spec);validate_rules(spec)
    result=build(audit/'kr_verified_events_v4_20261007/panel.parquet',out/'evidence',out,spec,
        implementation_sha={'entrypoint':digest(Path(__file__)),'spec':digest(path),
                            'builder':spec['builder_implementation_sha256'],'chunk':spec['chunk_implementation_sha256'],
                            'evidence_verifier':spec['evidence_verifier_sha256']})
    print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    run(parser.parse_args().root)
