import json
from pathlib import Path

import pytest

from research.audit_kr_adjustment_asof import digest
from research.normalize_verified_kr_issuance_v3 import ROOT, verify_inputs


@pytest.mark.parametrize('tamper', [None, 'support.html', 'support.txt', 'receipts.json', 'economics_verification.json'])
def test_supporting_split_and_issuance_evidence_is_pinned(tmp_path, tamper):
    for suffix in ['html', 'txt']:
        (tmp_path / ('support.' + suffix)).write_text('supporting issuance evidence')
    receipts={'support': {'sha256': digest(tmp_path/'support.html'), 'text_sha256': digest(tmp_path/'support.txt')}}
    (tmp_path/'receipts.json').write_text(json.dumps(receipts))
    (tmp_path/'economics_verification.json').write_text('{}')
    spec={'receipts_sha256': digest(tmp_path/'receipts.json'),
          'economics_sha256': digest(tmp_path/'economics_verification.json'),
          'chunk_implementation_sha256': digest(ROOT/'research/normalize_verified_kr_events.py'),
          'builder_implementation_sha256': digest(ROOT/'research/normalize_verified_kr_issuance.py')}
    if tamper:
        with (tmp_path/tamper).open('a') as f: f.write('changed')
        with pytest.raises(ValueError, match='changed_v3_'): verify_inputs(tmp_path, spec)
    else:
        verify_inputs(tmp_path, spec)
        spec['builder_implementation_sha256']='changed'
        with pytest.raises(ValueError, match='changed_v3_builder'): verify_inputs(tmp_path, spec)
