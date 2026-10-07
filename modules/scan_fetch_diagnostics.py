"""Describe source availability separately from trading-policy exclusions."""
from collections import Counter

import pandas as pd

FETCH_REASONS = {'FETCH_DATA_FAIL', 'INTRADAY_FETCH_FAIL'}


def history_diagnostic(frame, *, period, interval, minimum=50):
    fields = ['Open', 'High', 'Low', 'Close', 'Volume']
    rows = len(frame) if isinstance(frame, pd.DataFrame) else 0
    missing = [name for name in fields if not isinstance(frame, pd.DataFrame) or name not in frame]
    valid = len(frame[fields].dropna()) if not missing else 0
    status = ('empty' if rows == 0 else 'missing_columns' if missing else
              'insufficient_history' if rows < minimum else
              'insufficient_valid_history' if valid < minimum else 'usable')
    return {'status':status, 'rows':rows, 'valid_rows':valid, 'minimum_rows':minimum,
            'missing_columns':missing, 'period':period, 'interval':interval,
            'source_provider':str(getattr(frame, 'attrs', {}).get('source_provider') or ''),
            'first_date':str(frame.index.min()) if rows else None,
            'last_date':str(frame.index.max()) if rows else None}


def summarize_fetch_rejections(diagnostics):
    counts = Counter()
    reasons = diagnostics.get('reject_reasons_by_symbol', {})
    details = diagnostics.get('reject_details_by_symbol', {})
    for symbol, reason in reasons.items():
        if reason not in FETCH_REASONS:
            continue
        observations = [r.get('fetch_diagnostic') for r in details.get(symbol, [])
                        if isinstance(r, dict) and isinstance(r.get('fetch_diagnostic'), dict)]
        observation = observations[-1] if observations else {}
        status = observation.get('status', 'unknown')
        # Only affirmative, nonempty observations establish a history exclusion.
        short = (status == 'insufficient_history' and observation.get('rows', 0) > 0
                 and observation.get('valid_rows', 0) > 0 and not observation.get('missing_columns'))
        counts['insufficient_history' if short else 'source_unavailable_or_unknown'] += 1
    reported = sum(int(diagnostics.get('reject_reason_counts', {}).get(k, 0) or 0) for k in FETCH_REASONS)
    counts['source_unavailable_or_unknown'] += max(0, reported-sum(counts.values()))
    return {'fetch_rejection_count':max(reported, sum(counts.values())),
            'insufficient_history_count':counts['insufficient_history'],
            'source_failure_count':counts['source_unavailable_or_unknown']}
