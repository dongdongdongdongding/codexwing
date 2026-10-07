"""Current Nasdaq membership for scanner seeds; never a historical listing source."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
import time
import uuid

import requests

from multi_agent.tools.refresh_nasdaq_listing import URL, parse_directory

AUDIT_ROOT = Path(__file__).resolve().parents[1] / 'runtime_state/audit/nasdaq_scan_universe'
_CACHE_SECONDS = 300
_snapshot_cache = None
_snapshot_lock = threading.Lock()


class NasdaqUniverseUnavailable(RuntimeError):
    pass


def universe_warnings(provenance):
    if not provenance.get('seed_is_fallback'):
        return []
    return [{'code': 'SCAN_UNIVERSE_FALLBACK', 'severity': 'warning',
             'message': 'Current membership verified for a fallback seed; full provider universe unavailable.'}]


class NasdaqUniverse(dict):
    """Dict-compatible names plus the exact membership evidence used to select them."""

    def __init__(self, names, provenance, official_names):
        super().__init__(names)
        self.provenance = provenance
        self.official_names = official_names

    def select(self, symbols):
        requested = list(dict.fromkeys(str(s).strip().upper() for s in symbols))
        absent = [s for s in requested if s not in self.official_names]
        if absent:
            raise NasdaqUniverseUnavailable('requested_symbols_not_in_current_nasdaq_directory:' + ','.join(absent))
        return NasdaqUniverse(
            {s: self.official_names[s] for s in requested},
            {**self.provenance, 'selection': 'explicit_current_members', 'selected_count': len(requested)},
            self.official_names,
        )


def _write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def current_directory():
    """Bounded HTTP, validated source age, immutable capture, five-minute process cache."""
    global _snapshot_cache
    with _snapshot_lock:
        if _snapshot_cache is not None and time.monotonic() - _snapshot_cache[0] < _CACHE_SECONDS:
            return _snapshot_cache[1].copy(), dict(_snapshot_cache[2])
        audit = AUDIT_ROOT / uuid.uuid4().hex
        audit.mkdir(parents=True, exist_ok=False)
        try:
            response = requests.get(URL, timeout=20)
            observed = datetime.now(timezone.utc)
            body = response.content
            (audit / 'nasdaqlisted.txt').write_bytes(body)
            provenance = {'source_url': URL, 'observed_at_utc': observed.isoformat(),
                          'http_status': response.status_code, 'source_sha256': hashlib.sha256(body).hexdigest(),
                          'audit_dir': str(audit)}
            _write_json(audit / 'capture.json', provenance)
            response.raise_for_status()
            frame, generated = parse_directory(body, observed)
            provenance.update(source_generated_at_utc=generated.isoformat(),
                              source_age_seconds=(observed-generated).total_seconds(),
                              official_count=len(frame), membership_verified=True)
            _write_json(audit / 'validated.json', provenance)
            _snapshot_cache = (time.monotonic(), frame.copy(), dict(provenance))
            return frame, provenance
        except Exception as exc:
            _write_json(audit / 'failure.json', {'error_type': type(exc).__name__, 'membership_verified': False})
            raise NasdaqUniverseUnavailable('official_nasdaq_directory_unavailable:' + str(audit)) from exc


def reconcile_seed(seed, *, seed_source, seed_is_fallback=False):
    """Retain provider ordering/instrument scope, verify every member independently."""
    official, provenance = current_directory()
    # Test issues are not securities. ETF/preferred/right/note scope is preserved:
    # membership is separate from strategy-specific instrument admission.
    listed = official.loc[~official.test_issue]
    official_names = dict(zip(listed.symbol, listed.security_name))
    normalized = {str(s).strip().upper(): str(name) for s, name in seed.items() if str(s).strip()}
    selected = {s: official_names[s] for s in normalized if s in official_names}
    excluded = [s for s in normalized if s not in official_names]
    if not selected:
        raise NasdaqUniverseUnavailable('no_current_members_in_nasdaq_seed')
    provenance.update(seed_source=seed_source, seed_is_fallback=seed_is_fallback,
                      policy_version='nasdaq_current_members_v1',
                      excluded_reasons={s: 'TEST_ISSUE' if s in set(official.symbol) else 'NOT_IN_CURRENT_DIRECTORY'
                                        for s in excluded},
                      seed_count=len(normalized), selected_count=len(selected), excluded_symbols=excluded,
                      selection='provider_seed_current_members',
                      official_only_count=len(set(official_names)-set(normalized)),
                      scope='Current official membership of provider seed; not all official instruments or historical membership.')
    evidence = Path(provenance['audit_dir']) / ('selection_' + uuid.uuid4().hex + '.json')
    provenance['selection_evidence'] = str(evidence)
    _write_json(evidence, {'provenance': provenance, 'seed_names': normalized,
                           'selected_names': selected})
    return NasdaqUniverse(selected, provenance, official_names)
