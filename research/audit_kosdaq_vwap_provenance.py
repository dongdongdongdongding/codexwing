"""Read-only identity and timing reconciliation; never reconstruct missing picks."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

import pandas as pd

PREFIX = 'KQ-ITD-3D-T5-'
NAME = 'kosdaq_intraday_1500_3d_t5_vwap_guard_ledger.jsonl'
KST = ZoneInfo('Asia/Seoul')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def stamp(value, *, local=False):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    if result.tzinfo is None:
        return result.replace(tzinfo=KST) if local else None
    return result


def index(rows):
    result = {}
    for row in rows:
        key = (row['run_id'], row['ticker'])
        if not re.fullmatch(PREFIX+r'\d{8}', key[0]) or not re.fullmatch(r'\d{6}\.KQ', key[1]):
            raise ValueError('unexpected_identity')
        if key in result:
            raise ValueError('duplicate_source_identity')
        result[key] = row
    return result


def reconcile(ledger, scans, deep):
    sources = [index(rows) for rows in (ledger, scans, deep)]
    out = []
    for key in sorted(set().union(*sources)):
        l, s, d = [v.get(key) for v in sources]
        s = s or {}; d = d or {}
        entry = stamp(l.get('ordered_entry_at'), local=True) if l else None
        kind = 'ledger_observed_bar_KST' if entry else 'unavailable'
        # This alternative establishes only the explicitly declared schedule,
        # not an original observed execution or a recovered research row.
        if entry is None and (s.get('feature_snapshot') or {}).get('entry_time_kst') == '15:00':
            day = datetime.strptime(key[0][len(PREFIX):], '%Y%m%d')
            entry = day.replace(hour=15, tzinfo=KST)
            kind = 'archive_declared_1500_KST_only'
        stored = stamp(s.get('ordered_entry_at'))
        issued = stamp(s.get('recommended_at'))
        delta = (stored-entry).total_seconds() if stored and entry else None
        field_checks = {}
        if l and s:
            field_checks = {'timestamp_equal':l.get('generated_at') == s.get('recommended_at'),
                            'score_equal':abs(float(l['p'])*100-float(s['ml_prob'])) < 1e-8,
                            'tp_equal':l.get('target_tp_pct') == s.get('target_tp_pct'),
                            'horizon_equal':l.get('hold_days') == s.get('hold_days')}
        out.append({'run_id':key[0], 'ticker':key[1], 'in_ledger':l is not None,
                    'in_scan':bool(s), 'in_deep':bool(d), 'entry_evidence':kind,
                    'declared_or_observed_entry':entry.isoformat() if entry else None,
                    'stored_entry':s.get('ordered_entry_at'), 'stored_minus_reference_seconds':delta,
                    'recommended_at':s.get('recommended_at'),
                    'before_stored_entry':issued <= stored if issued and stored else None,
                    'before_reference_entry':issued <= entry if issued and entry else None,
                    'ledger_scan_checks':field_checks,
                    'deep_timestamp_equals_scan':d.get('generated_at') == s.get('recommended_at') if d and s else None,
                    'deep_score_equals_scan':abs(float(d['buy_score'])*100-float(s['ml_prob'])) < 1e-8 if d and s else None,
                    'scan_contract':{'tp':s.get('target_tp_pct'),'horizon':s.get('hold_days')},
                    'deep_trade_plan':d.get('trade_plan'),
                    'validation_excluded':s.get('validation_excluded'),
                    'recovered_original_pick':False})
    return out


def freeze(path, body):
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError('capture_changed')
    else:
        path.write_bytes(body)


def capture_db(root, audit):
    """Optional read-only capture; existing evidence cannot be overwritten."""
    import sys
    from dotenv import load_dotenv
    sys.path.insert(0, str(root))
    load_dotenv(root/'.env')
    load_dotenv(root/'.env.local')
    from modules.db_manager import DBManager
    db=DBManager()
    if not db.client:
        raise RuntimeError('database_client_unavailable')
    for table, order in [('market_scan_results','id'),('scan_deep_reports','report_id')]:
        rows=[]
        while True:
            batch=db.client.table(table).select('*').like('run_id',PREFIX+'%').order(order).range(len(rows),len(rows)+499).execute().data
            rows.extend(batch)
            if len(batch)<500:
                break
        path=audit/(table+'.json')
        if path.exists():
            if json.loads(path.read_text()) != rows:
                raise ValueError('database_rows_changed_after_capture')
        else:
            freeze(path,json.dumps(rows,ensure_ascii=False,indent=2,allow_nan=False).encode())


def run(root, audit):
    audit.mkdir(parents=True, exist_ok=True)
    ledger_path = root/'runtime_state/reports/experimental'/NAME
    ledger_raw = ledger_path.read_bytes(); freeze(audit/NAME, ledger_raw)
    scan_path = audit/'market_scan_results.json'; deep_path = audit/'scan_deep_reports.json'
    hashes = {str(p):sha(p) for p in [ledger_path, scan_path, deep_path]}
    ledger = [json.loads(line) for line in ledger_raw.splitlines() if line.strip()]
    scans = json.loads(scan_path.read_text()); deep = json.loads(deep_path.read_text())
    records = reconcile(ledger, scans, deep)
    archive_path = root/'runtime_state/reports/archive/scan_archive_learning_dataset_all.csv'
    hashes[str(archive_path)] = sha(archive_path)
    archive = pd.read_csv(archive_path, low_memory=False, dtype={'ticker':str})
    selected = archive.loc[archive.run_id.fillna('').str.startswith(PREFIX)]
    freeze(audit/'archive_rows.csv', selected.to_csv(index=False).encode())
    assert set(zip(selected.run_id,selected.ticker)) == set(index(scans))
    comparisons = 0
    for row in selected.to_dict('records'):
        db = index(scans)[(row['run_id'],row['ticker'])]
        for field in ['recommended_at','created_at','ordered_entry_at','target_tp_pct','hold_days','ml_prob']:
            assert row[field] == db[field], (row['run_id'],row['ticker'],field)
            comparisons += 1
    ops = []
    for path in sorted((root/'runtime_state/reports/ops').glob('*.json')):
        raw=path.read_bytes()
        obj=json.loads(raw)
        dest=audit/'ops';dest.mkdir(exist_ok=True);freeze(dest/path.name,raw)
        matching=[]
        for i, command in enumerate(obj.get('commands', [])):
            text = command.get('stdout_tail','') + command.get('stderr_tail','')
            if PREFIX in text or 'kosdaq_intraday_1500_3d_t5' in text:
                matching.append(i)
        ops.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'matching_command_indices':matching})
    freeze(audit/'ops_census.json', (json.dumps(ops,indent=2)+'\n').encode())
    cache=[]
    for path in sorted((root/'runtime_state/precision_cache').glob(PREFIX+'*/*.json')):
        raw=path.read_bytes();obj=json.loads(raw)
        dest=audit/'precision_cache';dest.mkdir(exist_ok=True);freeze(dest/(path.parent.name+'_'+path.name),raw)
        cache.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),
                      'cached_at':obj.get('cached_at'),'code':obj.get('code'),
                      'model_keys':sorted(obj.get('model',{}))})
    report_path='runtime_state/reports/experimental/'+NAME.replace('_ledger.jsonl','_latest.json')
    commits=subprocess.check_output(['git','log','--all','--format=%H','--',report_path],cwd=root,text=True).splitlines()
    history=[]
    for commit in commits:
        raw=subprocess.check_output(['git','show',commit+':'+report_path],cwd=root)
        obj=json.loads(raw);freeze(audit/(commit+'_latest.json'),raw)
        history.append({'commit':commit,'sha256':hashlib.sha256(raw).hexdigest(),
                        'generated_at':obj.get('generated_at'),'pick_count':len(obj.get('picks',[]))})
    ledger_history=subprocess.check_output(['git','log','--all','--format=%H','--',str(ledger_path.relative_to(root))],cwd=root,text=True).splitlines()
    assert all(sha(p)==h for p,h in hashes.items())
    result={'captured_at':datetime.now(timezone.utc).isoformat(),'source_hashes':hashes,
            'counts':{'ledger':len(ledger),'scan':len(scans),'deep':len(deep),'archive':len(selected),'union':len(records),
                      'before_stored_entry':sum(r['before_stored_entry'] is True for r in records),
                      'before_reference_entry':sum(r['before_reference_entry'] is True for r in records),
                      'additional_recovered_original_picks':0},
            'records':records,'archive_db_exact_field_checks':comparisons,
            'ops_files':len(ops),'ops_matching_tails':sum(bool(r['matching_command_indices']) for r in ops),
            'precision_cache':cache,'git_report_snapshots':history,'git_ledger_commits':ledger_history,
            'publication_allowed':False,'model_fit_performed':False,'live_mutations':0,
            'limitations':['Negative recovery search is restricted to captured DB rows, archive, local ops command tails, matching precision caches and reachable git history.',
                          'Stored duplicate values and embedded timestamps are not independent pre-entry feature snapshots.',
                          'A before-entry timestamp alone cannot prove that scoring inputs were available then.',
                          'Archive-only schedules do not reconstruct missing ledger rows, contracts or executable fills.']}
    (audit/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--capture-db',action='store_true')
    args=parser.parse_args();args.audit.mkdir(parents=True,exist_ok=True)
    if args.capture_db:
        capture_db(args.root,args.audit)
    report=run(args.root,args.audit)
    print(json.dumps({k:report[k] for k in ['counts','archive_db_exact_field_checks','ops_files','ops_matching_tails','precision_cache','git_report_snapshots','git_ledger_commits']},indent=2))
