"""Append observed official NASDAQ directories without backdating membership."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import fcntl
import io
import json
from pathlib import Path
import shutil
import sys
import uuid
from zoneinfo import ZoneInfo

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from multi_agent.tools.intraday_cache_journal import atomic_write, save_json
from multi_agent.tools.us_daily_panel_cache import file_sha

URL = 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'
DEFAULT_PATH = Path.home() / 'research_cache/T1_nasdaq_listing_snapshots.parquet'
HEADER = ['Symbol', 'Security Name', 'Market Category', 'Test Issue',
          'Financial Status', 'Round Lot Size', 'ETF', 'NextShares']


def now_utc():
    return datetime.now(timezone.utc)


def parse_directory(body: bytes, observed_at: datetime):
    rows = list(csv.reader(io.StringIO(body.decode('utf-8-sig')), delimiter='|'))
    rows = [r for r in rows if r and any(r)]
    if not rows or rows[0] != HEADER or len(rows) < 3:
        raise ValueError('invalid_listing_header_or_empty_directory')
    if (not rows[-1][0].startswith('File Creation Time: ')
            or len(rows[-1]) != len(HEADER) or any(rows[-1][1:])):
        raise ValueError('missing_listing_footer')
    generated = datetime.strptime(rows[-1][0].split(': ', 1)[1], '%m%d%Y%H:%M')
    generated = generated.replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
    if generated > observed_at:
        raise ValueError('future_listing_generation_time')
    # Operational stale-response bound, allowing weekends/holiday closures.
    # The exact source age is recorded; this is not a same-session certificate.
    if observed_at - generated > timedelta(days=7):
        raise ValueError('stale_listing_source_over_7_days')
    records = rows[1:-1]
    if any(len(row) != len(HEADER) for row in records):
        raise ValueError('invalid_listing_row_width')
    frame = pd.DataFrame(records, columns=HEADER)
    if (frame.Symbol.eq('').any() or frame.Symbol.duplicated().any()
            or frame['Security Name'].eq('').any()
            or not frame['Test Issue'].isin(['Y', 'N']).all()
            or not frame.ETF.isin(['Y', 'N']).all()):
        raise ValueError('invalid_listing_keys_or_flags')
    lots = pd.to_numeric(frame['Round Lot Size'], errors='raise')
    if lots.isna().any() or lots.le(0).any() or lots.mod(1).ne(0).any():
        raise ValueError('invalid_round_lot_size')
    # Legacy snapshots are date-only. New rows use the actual observed UTC
    # instant (stored without timezone to match the consumer's date axis).
    snapshot = pd.Timestamp(observed_at).tz_convert('UTC').tz_localize(None)
    out = pd.DataFrame({
        'snapshot_ts': snapshot, 'symbol': frame.Symbol,
        'security_name': frame['Security Name'], 'market_category': frame['Market Category'],
        'test_issue': frame['Test Issue'].eq('Y'), 'financial_status': frame['Financial Status'],
        'round_lot': lots.astype('int64'), 'etf': frame.ETF.eq('Y'), 'source_url': URL,
        'observed_at_utc': observed_at.isoformat(), 'source_generated_at_utc': generated.isoformat(),
    })
    return out, generated


def refresh(output: Path = DEFAULT_PATH, *, timeout: float = 20):
    output = Path(output).expanduser()
    state = output.parent / ('.' + output.stem + '_refresh')
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'writer.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status': 'busy', 'reason': 'listing_writer_lock'}
        audit = state / 'audit' / (now_utc().strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex)
        audit.mkdir(parents=True)
        try:
            response = requests.get(URL, timeout=timeout)
            observed = now_utc()
            raw_path = audit / 'nasdaqlisted.txt'
            raw_path.write_bytes(response.content)
            capture = {'url': URL, 'observed_at_utc': observed.isoformat(),
                       'http_status': response.status_code, 'content_type': response.headers.get('Content-Type'),
                       'last_modified': response.headers.get('Last-Modified'), 'body_sha256': file_sha(raw_path)}
            save_json(audit / 'capture.json', capture)
            if response.status_code != 200:
                raise ValueError('listing_HTTP_' + str(response.status_code))
            incoming, generated = parse_directory(response.content, observed)
            incoming['source_sha256'] = capture['body_sha256']
            incoming.to_parquet(audit / 'parsed_snapshot.parquet', index=False)
            before_sha = file_sha(output)
            latest_path = state / 'latest.json'
            latest = json.loads(latest_path.read_text()) if latest_path.exists() else {}
            if latest.get('after_sha256') and latest['after_sha256'] != before_sha:
                raise ValueError('listing_changed_outside_verified_writer')
            implementation_sha = file_sha(__file__)
            if (latest.get('source_sha256') == capture['body_sha256'] and before_sha
                    and latest.get('implementation_sha256') == implementation_sha):
                result = {**latest, 'status': 'unchanged', 'audit': str(audit),
                          'checked_at_utc': observed.isoformat(), 'appended_rows': 0,
                          'before_rows': latest['total_rows'], 'before_sha256': before_sha,
                          'source_age_seconds': (observed-generated).total_seconds()}
            else:
                old = pd.read_parquet(output) if output.exists() else incoming.iloc[:0].copy()
                old['snapshot_ts'] = pd.to_datetime(old.snapshot_ts)
                if (old.snapshot_ts.isna().any() or old.symbol.isna().any()
                        or old.duplicated(['snapshot_ts', 'symbol']).any()):
                    raise ValueError('invalid_existing_listing_keys')
                stamp = incoming.snapshot_ts.iloc[0]
                if len(old) and stamp <= old.snapshot_ts.max():
                    raise ValueError('non_forward_listing_capture')
                if before_sha:
                    backup = audit / 'before.parquet'
                    shutil.copyfile(output, backup)
                    if file_sha(backup) != before_sha:
                        raise ValueError('listing_backup_hash_mismatch')
                combined = pd.concat([old, incoming], ignore_index=True) if len(old) else incoming.copy()
                journal = {'status': 'PREPARED', 'before_sha256': before_sha,
                           'old_rows': len(old), 'new_rows': len(incoming), 'snapshot_ts': stamp.isoformat()}
                save_json(audit / 'write.json', journal)

                def writer(temp):
                    combined.to_parquet(temp, index=False)
                    restored = pd.read_parquet(temp)
                    if not restored.equals(combined):
                        raise ValueError('listing_roundtrip_mismatch')
                    if len(old) and not restored.iloc[:len(old)][old.columns].reset_index(drop=True).equals(old.reset_index(drop=True)):
                        raise ValueError('historical_listing_rows_changed')
                    if file_sha(output) != before_sha:
                        raise ValueError('listing_changed_before_replace')
                    journal['expected_after_sha256'] = file_sha(temp)
                    save_json(audit / 'write.json', journal)

                atomic_write(output, writer)
                after_sha = file_sha(output)
                journal.update(status='APPLIED', after_sha256=after_sha)
                save_json(audit / 'write.json', journal)
                result = {'status': 'appended', 'output': str(output), 'audit': str(audit),
                          'snapshot_ts': stamp.isoformat(), 'observed_at_utc': observed.isoformat(),
                          'source_generated_at_utc': generated.isoformat(), 'source_sha256': capture['body_sha256'],
                          'source_age_seconds': (observed-generated).total_seconds(),
                          'before_rows': len(old), 'appended_rows': len(incoming), 'total_rows': len(combined),
                          'before_sha256': before_sha, 'after_sha256': after_sha,
                          'implementation_sha256': implementation_sha,
                          'legacy_dates_preserved_as_midnight': True}
            save_json(audit / 'result.json', result)
            save_json(state / 'latest.json', result)
            return result
        except Exception as exc:
            result = {'status': 'failed', 'error': str(exc), 'audit': str(audit)}
            save_json(audit / 'result.json', result)
            return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_PATH)
    parser.add_argument('--timeout', type=float, default=20)
    args = parser.parse_args()
    result = refresh(args.output, timeout=args.timeout)
    print(json.dumps(result))
    return 0 if result['status'] in {'appended', 'unchanged'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
