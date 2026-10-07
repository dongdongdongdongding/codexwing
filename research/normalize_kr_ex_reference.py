"""Build a separate, explicit KRX ex-reference price-continuity source epoch.

This price convention does not certify cash/share-flow portfolio returns.
"""
import argparse
from datetime import date
from fractions import Fraction
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.normalize_verified_kr_issuance import build
from research.normalize_verified_kr_issuance_v3 import verify_inputs

CONVENTION = 'KRX_OFFICIAL_EX_REFERENCE_PRICE_CONTINUITY_V1'


def reference_factor(contract, asof):
    date.fromisoformat(asof)
    dates=[e['date'] for e in contract['events']]
    if dates != sorted(set(dates)):
        raise ValueError('ambiguous_reference_schedule')
    factor=Fraction(str(contract['baseline_factor']))
    if factor <= 0:
        raise ValueError('invalid_reference_baseline')
    for event in contract['events']:
        date.fromisoformat(event['date'])
        numerator=Fraction(str(event['prior_close']))
        denominator=Fraction(str(event['reference_price']))
        if numerator <= 0 or denominator <= 0:
            raise ValueError('invalid_official_reference_price')
        if event['date'] <= asof:
            factor *= numerator / denominator
    return float(factor)


def validate_rules(spec):
    if spec['price_convention'] != CONVENTION:
        raise ValueError('changed_price_convention')
    if set(spec['contracts']) != {r['code'] for r in spec['rules']}:
        raise ValueError('reference_contract_scope_disagreement')
    for rule in spec['rules']:
        contract=spec['contracts'][rule['code']]
        if rule['start'] < contract['start'] or rule['start'] > rule['end']:
            raise ValueError('invalid_reference_rule_dates')
        if (reference_factor(contract, rule['start']) != rule['new_factor']
                or reference_factor(contract, rule['end']) != rule['new_factor']):
            raise ValueError('reference_rule_factor_disagreement')


def run(root):
    audit=root/'runtime_state/audit';out=audit/'kr_verified_events_v4_20261007'
    path=ROOT/'research/data/kr_ex_reference_corrections_20261007.json'
    spec=json.loads(path.read_text())
    if digest(ROOT/'research/normalize_verified_kr_issuance_v3.py') != spec['evidence_verifier_sha256']:
        raise ValueError('changed_evidence_verifier')
    verify_inputs(out/'evidence',spec)
    validate_rules(spec)
    result=build(audit/'kr_verified_events_v3_20261007/panel.parquet',out/'evidence',out,spec,
                 implementation_sha={'entrypoint':digest(Path(__file__)),'spec':digest(path),
                                     'builder':spec['builder_implementation_sha256'],
                                     'chunk':spec['chunk_implementation_sha256'],
                                     'evidence_verifier':spec['evidence_verifier_sha256']})
    print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    run(parser.parse_args().root)
