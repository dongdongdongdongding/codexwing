"""Build an immutable eight-event extension of the partially corrected KR source."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.normalize_verified_kr_issuance import build


def verify_inputs(evidence, spec):
    """Pin supporting same-day issuance documents as well as primary rule bodies."""
    for filename, key in [('receipts.json', 'receipts_sha256'),
                          ('economics_verification.json', 'economics_sha256')]:
        if digest(evidence / filename) != spec[key]:
            raise ValueError('changed_v3_evidence')
    receipts = json.loads((evidence / 'receipts.json').read_text())
    for name, receipt in receipts.items():
        for suffix, key in [('html', 'sha256'), ('txt', 'text_sha256')]:
            if digest(evidence / (name + '.' + suffix)) != receipt[key]:
                raise ValueError('changed_v3_supporting_document')
    for path, key in [('research/normalize_verified_kr_events.py', 'chunk_implementation_sha256'),
                      ('research/normalize_verified_kr_issuance.py', 'builder_implementation_sha256')]:
        if digest(ROOT / path) != spec[key]:
            raise ValueError('changed_v3_builder')


def run(root):
    audit = root / 'runtime_state/audit'
    out = audit / 'kr_verified_events_v3_20261007'
    spec_path = ROOT / 'research/data/kr_issuance_corrections_v3_20261007.json'
    spec = json.loads(spec_path.read_text())
    verify_inputs(out / 'evidence', spec)
    result = build(audit / 'kr_verified_events_v2_20261007/panel.parquet',
                   out / 'evidence', out, spec,
                   implementation_sha={'entrypoint': digest(Path(__file__)),
                                       'spec': digest(spec_path),
                                       'builder': spec['builder_implementation_sha256'],
                                       'chunk': spec['chunk_implementation_sha256']})
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    run(parser.parse_args().root)
