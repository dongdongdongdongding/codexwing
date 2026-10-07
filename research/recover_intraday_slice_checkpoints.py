"""Recover only verified request checkpoints; never change intraday price bars.

Fresh failed-slice captures must validate and match every cached OHLCV value.
Invalid responses remain partial. REQUESTED_ALL_SLICES is not session coverage.
"""
import argparse
from collections import defaultdict
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from modules.kis_operational_adapter import normalize_kis_minute_bars
from multi_agent.tools.backfill_kr_intraday import filter_bars,HOURS,legacy_writers
from multi_agent.tools.intraday_cache_journal import atomic_write,digest
from research.capture_lowliq_krx_source import payload_sha
from research.run_lowliq_touch10_reconstruction import publish,save_json

COLS=['Open','High','Low','Close','Volume']


def verified_frame(code,day,payload,old):
    if payload.get('rt_cd')!='0':raise ValueError('provider_error')
    frame=filter_bars(normalize_kis_minute_bars(code,payload,trade_date=day),day)
    if frame.empty:raise ValueError('empty_slice')
    if not frame.index.isin(old.index).all():raise ValueError('new_bar_requires_separate_repair')
    pd.testing.assert_frame_equal(frame[COLS],old.loc[frame.index,COLS],check_exact=True,
                                  check_dtype=False,check_freq=False)
    return frame


def recovered_state(before,accepted,cache_frame):
    result=copy.deepcopy(before)
    for day,rows in accepted.items():
        cell=result['days'][day]
        hours=set(cell.get('successful_hours',[]))
        if not hours.issubset(HOURS):raise ValueError('unknown_checkpoint_hour')
        for row in rows:
            if row['hour'] not in HOURS:raise ValueError('unknown_recovered_hour')
            hours.add(row['hour'])
        observed=filter_bars(cache_frame,day)
        cell.update(successful_hours=sorted(hours),rows_observed=len(observed),
                    first_bar=str(observed.index.min()) if len(observed) else None,
                    last_bar=str(observed.index.max()) if len(observed) else None,
                    session_complete=None,status='REQUESTED_ALL_SLICES' if hours==set(HOURS) and len(observed) else 'PARTIAL_OR_EMPTY')
        if cell['status']=='REQUESTED_ALL_SLICES':cell.pop('retry_after',None)
        cell['verified_slice_recovery']={'kind':'fresh_response_matches_existing_cache',
                                        'requests':rows,'session_completeness':'NOT_ESTABLISHED'}
    return result


def prepare(capture,cache,out):
    plan_path=out/'plan.json'
    if plan_path.exists():return json.loads(plan_path.read_text())
    report_path=capture/'original_report.json';report=json.loads(report_path.read_text())
    if report['run_id']!='20261007T171511552855' or len(report['request_errors'])!=10:
        raise ValueError('changed_failure_cohort')
    source_plan=json.loads((capture/'plan.json').read_text())
    if digest(report_path)!=source_plan['source_report_sha256']:raise ValueError('changed_original_report')
    for name,sha in source_plan['dependencies'].items():
        if digest(ROOT/name)!=sha:raise ValueError('changed_capture_dependency')
    inputs={str(report_path):digest(report_path),str(capture/'plan.json'):digest(capture/'plan.json')}
    grouped=defaultdict(list)
    for request in report['request_errors']:grouped[request['code']].append(request)
    proposals=[];rejected=[];accepted_count=0;matched_rows=0
    for code,requests in sorted(grouped.items()):
        cache_path=cache/(code+'.parquet');state_path=cache/'.backfill'/(code+'.json')
        before_bytes=state_path.read_bytes();before=json.loads(before_bytes);frame=pd.read_parquet(cache_path)
        if (not isinstance(frame.index,pd.DatetimeIndex) or frame.index.tz is not None
            or frame.index.has_duplicates or frame.index.hasnans):raise ValueError('invalid_cache_index')
        stat=cache_path.stat();identity=[stat.st_mtime_ns,stat.st_size]
        if before['identity']!=identity:raise ValueError('stale_cache_checkpoint')
        accepted=defaultdict(list)
        for request in requests:
            day,hour=request['day'],request['hour'];path=capture/'responses'/f'{code}_{day}_{hour}.json'
            item=json.loads(path.read_text());inputs[str(path)]=digest(path)
            if item['request']!=request or payload_sha(item['payload'])!=item['payload_sha256']:
                raise ValueError('changed_response_identity')
            try:valid=verified_frame(code,day,item['payload'],frame)
            except ValueError as exc:
                # Only malformed/empty provider rows may remain rejected; a cache
                # mismatch or new timestamp requires a separately reviewed plan.
                if str(exc) not in {'invalid_minute_OHLCV','empty_slice','provider_error'}:raise
                rejected.append({'request':request,'reason':str(exc),'response_sha256':digest(path)});continue
            if day not in before['days'] or hour in before['days'][day].get('successful_hours',[]):
                raise ValueError('changed_failed_checkpoint')
            accepted[day].append({'hour':hour,'response_path':str(path),'response_sha256':digest(path),
                                  'captured_at':item['captured_at'],'matched_cache_rows':len(valid)})
            accepted_count+=1;matched_rows+=len(valid)
        if not accepted:continue
        after=recovered_state(before,accepted,frame)
        after_bytes=(json.dumps(after,ensure_ascii=False,indent=2)+'\n').encode()
        backup=out/'states'/(code+'.before.json');proposed=out/'states'/(code+'.after.json')
        publish(backup,before_bytes);publish(proposed,after_bytes)
        if backup.read_bytes()!=before_bytes:raise ValueError('state_backup_failed')
        proposals.append({'code':code,'state_path':str(state_path),'before_sha256':digest(backup),
                          'after_sha256':digest(proposed),'backup_path':str(backup),'proposed_path':str(proposed),
                          'cache_path':str(cache_path),'cache_sha256':digest(cache_path),'cache_identity':identity,
                          'changed_days':sorted(accepted)})
    plan={'implementation_sha256':digest(Path(__file__)),'dependencies':{name:digest(ROOT/name) for name in [
              'modules/kis_operational_adapter.py','multi_agent/tools/backfill_kr_intraday.py',
              'multi_agent/tools/intraday_cache_journal.py','research/run_lowliq_touch10_reconstruction.py']},
          'inputs':inputs,'proposals':proposals,'rejected':rejected,'accepted_requests':accepted_count,
          'matched_cache_rows':matched_rows,'price_bars_modified':False,'session_completeness':'NOT_ESTABLISHED',
          'historical_original_error_cause_proved':False}
    save_json(plan_path,plan);return plan


def apply(plan,out):
    if digest(Path(__file__))!=plan['implementation_sha256']:raise ValueError('changed_recovery_implementation')
    for name,sha in plan['dependencies'].items():
        if digest(ROOT/name)!=sha:raise ValueError('changed_recovery_dependency')
    for path,sha in plan['inputs'].items():
        if digest(Path(path))!=sha:raise ValueError('changed_capture_evidence')
    # Preflight the entire transaction before its first mutation. Each replacement
    # repeats CAS while holding the existing operational writer lock.
    for row in plan['proposals']:
        for field,sha in [('backup_path','before_sha256'),('proposed_path','after_sha256')]:
            if digest(Path(row[field]))!=row[sha]:raise ValueError('changed_state_backup_or_proposal')
        cache=Path(row['cache_path']);stat=cache.stat()
        if digest(cache)!=row['cache_sha256'] or [stat.st_mtime_ns,stat.st_size]!=row['cache_identity']:
            raise ValueError('cache_changed_since_plan')
        if digest(Path(row['state_path'])) not in {row['before_sha256'],row['after_sha256']}:
            raise ValueError('state_changed_since_plan')
    applied=0
    for row in plan['proposals']:
        state=Path(row['state_path'])
        if digest(state)==row['after_sha256']:continue
        def write(temp):
            temp.write_bytes(Path(row['proposed_path']).read_bytes())
            if digest(state)!=row['before_sha256'] or digest(Path(row['cache_path']))!=row['cache_sha256']:
                raise ValueError('state_or_cache_changed_during_apply')
            if digest(temp)!=row['after_sha256']:raise ValueError('state_temp_verification_failed')
        atomic_write(state,write);applied+=1
        if digest(state)!=row['after_sha256']:raise ValueError('state_apply_verification_failed')
    result={'status':'APPLIED' if applied else 'REUSED','changed_state_files_this_run':applied,
            'state_files':len(plan['proposals']),'accepted_requests':plan['accepted_requests'],
            'rejected_requests':len(plan['rejected']),'matched_cache_rows':plan['matched_cache_rows'],
            'price_bars_modified':False,'session_completeness':'NOT_ESTABLISHED'}
    save_json(out/'applied_state.json',{'proposals':plan['proposals'],'accepted_requests':plan['accepted_requests'],
              'rejected_requests':len(plan['rejected']),'price_bars_modified':False})
    return result


def validate_cache_binding(plan,cache):
    expected_cache=cache.resolve();expected_state=(cache/'.backfill').resolve()
    for row in plan['proposals']:
        if (Path(row['cache_path']).resolve().parent!=expected_cache
            or Path(row['state_path']).resolve().parent!=expected_state):
            raise ValueError('plan_outside_locked_cache')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--cache',type=Path,default=Path.home()/'research_cache/intraday')
    parser.add_argument('--out',type=Path,help='Explicit audit destination; default is the capture recovery directory')
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    capture=args.root/'runtime_state/audit/intraday_failed_slices_20261007';out=args.out or capture/'checkpoint_recovery'
    with (args.cache/'.backfill/writer.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status':'BUSY','reason':'writer_lock','state_files_modified':0}),flush=True)
            return 2
        if legacy_writers(args.cache):raise ValueError('legacy_intraday_writer_active')
        plan=prepare(capture,args.cache,out)
        validate_cache_binding(plan,args.cache)
        result=apply(plan,out) if args.apply else {'status':'PLANNED','state_files':len(plan['proposals']),
            'accepted_requests':plan['accepted_requests'],'rejected_requests':len(plan['rejected']),
            'matched_cache_rows':plan['matched_cache_rows'],'price_bars_modified':False}
        print(json.dumps(result),flush=True)


if __name__=='__main__':raise SystemExit(main())
