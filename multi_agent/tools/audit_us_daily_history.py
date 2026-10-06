"""Read-only, resumable comparison of a frozen US raw universe with Yahoo chart.

This records provider differences, not independent price certification or alpha.
It never replaces production raw, panels, listings, receipts or issued contracts.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
from urllib.parse import quote
import uuid

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from multi_agent.tools import backfill_us_daily_features as bf
from multi_agent.tools import report_nasdaq_session_tape as tape
from multi_agent.tools.intraday_cache_journal import save_json
from multi_agent.tools.us_daily_panel_cache import file_sha
from modules.us_symbol_lineage import daily_bar_issues
from modules import ohlcv_quality

FIELDS = ['open', 'high', 'low', 'close', 'raw_close', 'adj_close', 'volume', 'adj_factor']


def implementation():
    files = [__file__, bf.__file__, tape.__file__, ohlcv_quality.__file__,
             sys.modules[daily_bar_issues.__module__].__file__]
    return {'files': {Path(p).name: file_sha(p) for p in files},
            'pandas': pd.__version__, 'numpy': np.__version__}


def parse_chart(payload, symbol, start, target):
    chart = payload['chart']
    if chart.get('error') or len(chart.get('result') or []) != 1:
        raise ValueError('provider_chart_error_or_missing_result')
    result = chart['result'][0]
    if result['meta']['symbol'] != symbol:
        raise ValueError('provider_symbol_mismatch')
    if result['meta']['exchangeTimezoneName'] != 'America/New_York':
        raise ValueError('unexpected_exchange_timezone')
    dates = pd.to_datetime(result.get('timestamp', []), unit='s', utc=True)
    dates = dates.tz_convert('America/New_York').tz_localize(None).normalize()
    if dates.isna().any() or dates.duplicated().any():
        raise ValueError('invalid_or_duplicate_provider_dates')
    quotes = pd.DataFrame(result['indicators']['quote'][0], index=dates)
    quotes.columns = quotes.columns.str.title()
    quotes['Adj Close'] = result['indicators']['adjclose'][0]['adjclose']
    frame = bf._extract_yfinance_frame(quotes, symbol)
    if frame.empty:
        raise ValueError('empty_provider_prices')
    return frame.loc[frame.date.between(pd.Timestamp(start), pd.Timestamp(target))].copy()


def compare_frames(existing, observed, start, target):
    def indexed(frame):
        frame = frame.copy()
        frame['date'] = pd.to_datetime(frame['date'])
        if frame.date.isna().any() or frame.date.duplicated().any():
            raise ValueError('invalid_or_duplicate_comparison_dates')
        return frame.loc[frame.date.between(pd.Timestamp(start), pd.Timestamp(target))].set_index('date')
    old, new = indexed(existing), indexed(observed)
    common = old.index.intersection(new.index).sort_values()
    changed = pd.DataFrame(index=common)
    strict = pd.DataFrame(index=common)
    for field in FIELDS:
        a, b = old.loc[common, field].astype(float), new.loc[common, field].astype(float)
        changed[field] = ~np.isclose(a, b, rtol=1e-6 if field != 'volume' else 0,
                                    atol=1e-8, equal_nan=True)
        strict[field] = ~(a.eq(b) | (a.isna() & b.isna()))
    different = changed.any(axis=1)
    cutoff = old.index.max() - pd.Timedelta(days=14) if len(old) else pd.NaT
    historical = different & (common < cutoff)
    issues = daily_bar_issues(new.reset_index())
    summary = {
        'baseline_rows': len(old), 'observed_rows': len(new), 'common_rows': len(common),
        'missing_dates': old.index.difference(new.index).strftime('%Y-%m-%d').tolist(),
        'added_dates': new.index.difference(old.index).strftime('%Y-%m-%d').tolist(),
        'changed_rows': int(different.sum()), 'changed_fields': changed.sum().astype(int).to_dict(),
        'exact_changed_rows': int(strict.any(axis=1).sum()),
        'outside_overlap_changed_dates': common[historical].strftime('%Y-%m-%d').tolist(),
        'overlap_cutoff': str(cutoff),
        'target_present': pd.Timestamp(target) in new.index,
        'invalid_observed_rows': int(issues.ne('').sum()),
        'invalid_observed_reasons': issues[issues.ne('')].value_counts().to_dict(),
        'price_rtol': 1e-6, 'atol': 1e-8, 'volume_rtol': 0,
    }
    differences = old.loc[common[different], FIELDS].join(
        new.loc[common[different], FIELDS], lsuffix='_baseline', rsuffix='_observed')
    return summary, differences


def freeze_plan(audit, paths, start, target):
    """Freeze the existing collector universe; selection never uses outcomes."""
    destination = audit / 'plan.json'
    if destination.exists():
        plan = json.loads(destination.read_text())
        if (plan['start'], plan['target'], plan['implementation']) != (start, target, implementation()):
            raise ValueError('audit_configuration_changed')
        return plan
    with (paths.market_root / '.daily_refresh.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        universe = pd.read_csv(paths.universe_path, keep_default_na=False, dtype={'symbol': str})
        if universe.symbol.duplicated().any() or universe.empty:
            raise ValueError('invalid_frozen_universe')
        if universe.symbol.map(bf._safe_filename).duplicated().any():
            raise ValueError('ambiguous_symbol_filename')
        listing = pd.read_parquet(tape.T1_PATH)
        latest = listing.loc[listing.snapshot_ts.eq(listing.snapshot_ts.max())]
        eligible = latest.loc[
            latest.test_issue.astype(str).str.upper().isin(['N', 'FALSE', '0'])
            & latest.etf.astype(str).str.upper().isin(['N', 'FALSE', '0'])
            & ~latest.security_name.astype(str).str.contains(tape.T1_EXCLUDE, na=False), 'symbol']
        baseline = audit / 'baseline'
        baseline.mkdir(exist_ok=True)
        records = []
        listed_symbols, eligible_symbols = set(latest.symbol), set(eligible)
        for symbol in sorted(universe.symbol):
            source = bf._raw_path(paths, symbol)
            snap = baseline / source.name
            sha = file_sha(source)
            if sha:
                if not snap.exists():
                    os.link(source, snap)
                if file_sha(snap) != sha:
                    raise ValueError('baseline_snapshot_changed')
            records.append({'symbol': symbol, 'source': str(source), 'baseline': str(snap),
                            'sha256': sha, 'currently_listed': symbol in listed_symbols,
                            'current_name_eligible': symbol in eligible_symbols})
        metadata = [paths.universe_path, Path(tape.T1_PATH), Path(tape._latest_panel()), tape.LEDGER]
        plan = {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                'start': start, 'target': target, 'records': records,
                'metadata': {str(p): file_sha(p) for p in metadata},
                'implementation': implementation(),
                'scope': 'Frozen collector universe, alphabetical requests; read-only source comparison, no qualification.'}
        save_json(destination, plan)
        return plan


def observe(record, audit, start, target, timeout):
    from curl_cffi import requests
    symbol = record['symbol']
    stem = bf._safe_filename(symbol)
    receipt = audit / 'results' / (stem + '.json')
    if receipt.exists():
        saved = json.loads(receipt.read_text())
        if saved.get('response_file'):
            content = gzip.decompress(Path(saved['response_file']).read_bytes())
            if hashlib.sha256(content).hexdigest() != saved['response_sha256']:
                raise ValueError('saved_response_hash_mismatch')
        return saved
    result = {'symbol': symbol, 'baseline_sha256': record['sha256'],
              'requested_at': datetime.now(timezone.utc).isoformat()}
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + quote(symbol, safe='')
    params = {'period1': int(pd.Timestamp(start, tz='UTC').timestamp()),
              'period2': int((pd.Timestamp(target, tz='UTC') + pd.Timedelta(days=1)).timestamp()),
              'interval': '1d', 'events': 'div,splits', 'includeAdjustedClose': 'true'}
    result.update(url=url, params=params)
    try:
        response = requests.get(url, params=params, impersonate='chrome', timeout=timeout)
        result.update(http_status=response.status_code, observed_at=datetime.now(timezone.utc).isoformat())
        response_path = audit / 'responses' / (stem + '_' + uuid.uuid4().hex + '.json.gz')
        response_path.parent.mkdir(exist_ok=True)
        with response_path.open('xb') as out:
            out.write(gzip.compress(response.content, mtime=0))
        result.update(response_file=str(response_path), response_sha256=hashlib.sha256(response.content).hexdigest())
        if response.status_code != 200:
            raise ValueError('provider_http_' + str(response.status_code))
        observed = parse_chart(response.json(), symbol, start, target)
        if observed.empty:
            raise ValueError('empty_provider_requested_period')
        if file_sha(record['baseline']) != record['sha256']:
            raise ValueError('frozen_baseline_hash_mismatch')
        if record['sha256']:
            existing = pd.read_parquet(record['baseline'])
        else:
            existing = pd.DataFrame(columns=['date'] + FIELDS)
        comparison, differences = compare_frames(existing, observed, start, target)
        output = audit / 'observations' / (stem + '.parquet')
        output.parent.mkdir(exist_ok=True)
        observed.to_parquet(output, index=False)
        result.update(status='COMPARED', comparison=comparison, observation_file=str(output),
                      observation_sha256=file_sha(output))
        if not differences.empty:
            delta = audit / 'differences' / (stem + '.parquet')
            delta.parent.mkdir(exist_ok=True)
            differences.to_parquet(delta)
            result.update(difference_file=str(delta), difference_sha256=file_sha(delta))
    except Exception as exc:
        result.update(status='ERROR', error=str(exc) or type(exc).__name__)
    save_json(receipt, result)
    return result


def run(audit, paths, start, target, budget=600, workers=4, timeout=10):
    audit = Path(audit).resolve()
    audit.mkdir(parents=True, exist_ok=True)
    if not np.isfinite(budget) or budget <= 0 or workers not in range(1, 9) or timeout <= 0:
        raise ValueError('invalid_audit_budget_or_concurrency')
    with (audit / '.audit.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = freeze_plan(audit, paths, start, target)
        pending = [r for r in plan['records'] if not (audit / 'results' / (bf._safe_filename(r['symbol']) + '.json')).exists()]
        began = time.monotonic()
        stop = 'REQUESTS_COMPLETE'
        visited = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for first in range(0, len(pending), workers):
                if time.monotonic() - began >= budget:
                    stop = 'BUDGET_EXHAUSTED'
                    break
                if shutil.disk_usage(audit).free < 10 * 1024 ** 3:
                    stop = 'STORAGE_RESERVE'
                    break
                batch = pending[first:first + workers]
                results = list(pool.map(lambda r: observe(r, audit, start, target, timeout), batch))
                visited += len(results)
                if visited % 100 < workers:
                    print(json.dumps({'new_requests': visited, 'elapsed_seconds': round(time.monotonic() - began, 1)}), flush=True)
                if any(r.get('http_status') == 429 for r in results):
                    stop = 'PROVIDER_RATE_LIMIT'
                    break
        results = []
        for r in plan['records']:
            path = audit / 'results' / (bf._safe_filename(r['symbol']) + '.json')
            if path.exists():
                # Resume verifies immutable response evidence; no re-request.
                result = observe(r, audit, start, target, timeout)
                for field in ['observation', 'difference']:
                    if result.get(field + '_file') and file_sha(result[field + '_file']) != result[field + '_sha256']:
                        raise ValueError('saved_comparison_artifact_hash_mismatch')
                results.append(result)
        compared = [r for r in results if r['status'] == 'COMPARED']
        source_changes = [r['symbol'] for r in plan['records'] if file_sha(r['source']) != r['sha256']]
        metadata_changes = [p for p, sha in plan['metadata'].items() if file_sha(p) != sha]
        summary = {'status': stop, 'planned': len(plan['records']), 'terminal': len(results),
                   'new_requests': visited, 'unvisited': len(plan['records']) - len(results),
                   'compared': len(compared), 'errors': len(results) - len(compared),
                   'outside_overlap_changed_symbols': [r['symbol'] for r in compared if r['comparison']['outside_overlap_changed_dates']],
                   'incomplete_history_symbols': [r['symbol'] for r in compared if r['comparison']['missing_dates']],
                   'baseline_sources_changed': source_changes, 'metadata_changed': metadata_changes,
                   'scope': 'Source differences only; errors and missing observations do not imply delisting or valid replacement.'}
        save_json(audit / 'summary.json', summary)
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-dir', type=Path, required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--start', default='2018-01-01')
    parser.add_argument('--budget', type=float, default=600)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    paths = bf.BackfillPaths(Path.home() / 'research_cache/us_daily', 'NASDAQ')
    print(json.dumps(run(args.audit_dir, paths, args.start, args.target, args.budget, args.workers), indent=2))


if __name__ == '__main__':
    main()
