"""Guarded fixed-cohort price/checkpoint repair from reviewed immutable receipts.

One received high-price correction, 100 received new bars, and validated request
checkpoints. Query-dependent lower-volume replacements are outside this scope.
"""
import argparse
import copy
import fcntl
import io
import json
import os
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.recover_lowliq_history_request import digest
from research.capture_intraday_terminal_failures import DEPENDENCIES, inspect
from research.run_lowliq_touch10_reconstruction import publish, save_json
from research.capture_lowliq_krx_source import payload_sha
from modules.kis_operational_adapter import normalize_kis_minute_bars
from multi_agent.tools.backfill_kr_intraday import filter_bars, HOURS, legacy_writers
from multi_agent.tools.intraday_cache_journal import atomic_write, prepare_states, restore_state

CAPTURE_PLAN='c0974ebf5ba6c175b68168b105c48dd0945f3cb131cd850f9256ddb5c58c36be'
RECEIPTS={
 '011230_20260923_100000':'076cc14dc2cd3091f205dcfe032a2214f6f3a753efa10bee2a2c26abef3ec7cd',
 '011230_20260923_113000':'65d8e125794e8aa4d4dc890488e25397d857a35f67854f8d27ebc2acd46a280f',
 '011230_20260923_133000':'4afcece2a37b1e629fc77743bd570d074ad6c5fae2b876e22c85cd5056a63813',
 '011230_20260923_153000':'5b652ec8db39adadf62dabf77f9c0fa61dc6e8cb7f85d212b36d33e0888291c8',
 '012280_20260923_153000':'d0e32e4d60a78329bbed9806a0b4ab3be45c6164c4a78b20659dd1625aae92a8',
 '220260_20260928_153000':'3b4c44ddec0a8884374a25c1aff27760afb7776f86277ad1fab24b199057c1ef',
 '393890_20260923_100000':'b4f22cb3dd53b4a04e9891d0db187e07d841230d228dcd998611ecf1ef9321a9',
 '460850_20260923_113000':'0e46f1805e32a0ec01a5c3be4d2926980b38509e855e4115f41e42c0f615a001',
}
COLS=['Open','High','Low','Close','Volume']


def encoded(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()


def identity(path):
    stat=path.stat();return [stat.st_mtime_ns,stat.st_size]


def corrected_frame(code,old,frames):
    if not isinstance(old.index,pd.DatetimeIndex) or old.index.tz is not None or old.index.has_duplicates or old.index.hasnans:
        raise ValueError('invalid_existing_index')
    result=old.copy()
    if code=='011230':
        t=pd.Timestamp('2026-09-23 09:00:00')
        if list(old.loc[t,COLS])!=[2730,2725,2725,2725,385]:raise ValueError('changed_reviewed_bad_bar')
        source=frames['100000'].loc[t,COLS]
        if list(source)!=[2730,2730,2725,2725,385]:raise ValueError('changed_reviewed_replacement')
        result.loc[t,'High']=source['High']
    new=[]
    for frame in frames.values():
        shared=frame.index.intersection(result.index)
        pd.testing.assert_frame_equal(frame.loc[shared,COLS],result.loc[shared,COLS],check_exact=True,
                                      check_dtype=False,check_freq=False)
        extra=frame.loc[~frame.index.isin(result.index)].copy()
        if len(extra):extra['code']=code;new.append(extra)
    if new:
        delta=pd.concat(new)
        if delta.index.has_duplicates:raise ValueError('overlapping_new_bars')
        if code!='220260' or len(delta)!=100:raise ValueError('unexpected_new_bars')
        result=pd.concat([result,delta]).sort_index()
    elif code=='220260':raise ValueError('missing_reviewed_new_bars')
    if list(result.columns)!=list(old.columns) or list(result.dtypes)!=list(old.dtypes):raise ValueError('changed_cache_schema')
    day='20260928' if code=='220260' else '20260923'
    filter_bars(result,day)
    return result


def artifact(out,code,role,path,after_bytes,*,price=False):
    before=out/'files'/f'{code}.{role}.before';after=out/'files'/f'{code}.{role}.after'
    publish(before,path.read_bytes());publish(after,after_bytes)
    item={'code':code,'role':role,'path':str(path),'before_path':str(before),'after_path':str(after),
          'before_sha256':digest(before),'after_sha256':digest(after)}
    if price:item.update(before_identity=identity(path),after_identity=identity(after))
    return item


def prepare(root,cache,out):
    if (out/'plan.json').exists():return json.loads((out/'plan.json').read_text())
    capture=root/'runtime_state/audit/intraday_terminal_20261007_205547/fresh_capture'
    if digest(capture/'plan.json')!=CAPTURE_PLAN:raise ValueError('changed_capture_plan')
    dependencies={**DEPENDENCIES,'multi_agent/tools/intraday_cache_journal.py':digest(ROOT/'multi_agent/tools/intraday_cache_journal.py')}
    for name,sha in dependencies.items():
        if digest(ROOT/name)!=sha or digest(root/name)!=sha:raise ValueError('changed_dependency')
    inputs={str(capture/'plan.json'):CAPTURE_PLAN};grouped={}
    for key,sha in RECEIPTS.items():
        path=capture/'responses'/(key+'.json')
        if digest(path)!=sha:raise ValueError('changed_reviewed_receipt')
        inputs[str(path)]=sha;item=json.loads(path.read_text());code,day,hour=key.split('_')
        request={'code':code,'day':day,'hour':hour}
        if item['request']!=request or item['plan_sha256']!=CAPTURE_PLAN:raise ValueError('changed_receipt_identity')
        if payload_sha(item['payload'])!=item['payload_sha256'] or inspect(request,item['payload'])!=item['inspection']:
            raise ValueError('changed_receipt_inspection')
        if item['inspection']['status']!='VALID_SLICE':raise ValueError('unaccepted_receipt')
        grouped.setdefault(code,{})[hour]=filter_bars(normalize_kis_minute_bars(code,item['payload'],trade_date=day),day)
    entries=[];guards=[];summaries=[]
    for code,frames in sorted(grouped.items()):
        path=cache/(code+'.parquet');state_path=cache/'.backfill'/(code+'.json')
        old=pd.read_parquet(path);state=json.loads(state_path.read_text())
        if state['identity']!=identity(path):raise ValueError('stale_checkpoint_identity')
        head_path=cache/'.backfill/journal'/code/'head.json';head=json.loads(head_path.read_text())
        if head['file_sha256']!=digest(path) or not restore_state(head['state']).equals(old):raise ValueError('invalid_existing_journal')
        changed=corrected_frame(code,old,frames);cache_identity=identity(path)
        if not changed.equals(old):
            recovery=prepare_states(path,old,changed,digest(path))
            buffer=io.BytesIO();changed.to_parquet(buffer)
            if not pd.read_parquet(io.BytesIO(buffer.getvalue())).equals(changed):raise ValueError('parquet_roundtrip_failed')
            entry=artifact(out,code,'cache',path,buffer.getvalue(),price=True);entries.append(entry)
            cache_identity=entry['after_identity']
            entries.append(artifact(out,code,'head',head_path,encoded({'file_sha256':entry['after_sha256'],'state':recovery['after_state']})))
        else:
            guards.extend([{'path':str(path),'sha256':digest(path),'identity':identity(path)},
                           {'path':str(head_path),'sha256':digest(head_path)}])
        day='20260928' if code=='220260' else '20260923';after=copy.deepcopy(state);observed=filter_bars(changed,day)
        cell=after['days'].setdefault(day,{})
        hours=set(cell.get('successful_hours',[]))|set(frames)
        if not hours.issubset(HOURS):raise ValueError('unknown_checkpoint_hour')
        cell.update(successful_hours=sorted(hours),rows_observed=len(observed),first_bar=str(observed.index.min()),
                    last_bar=str(observed.index.max()),session_complete=None,
                    status='REQUESTED_ALL_SLICES' if hours==set(HOURS) else 'PARTIAL_OR_EMPTY',
                    reviewed_recovery={'capture_plan_sha256':CAPTURE_PLAN,'accepted_hours':sorted(frames),
                                       'session_completeness':'NOT_ESTABLISHED'})
        if hours==set(HOURS):cell.pop('retry_after',None)
        after['identity']=cache_identity;entries.append(artifact(out,code,'checkpoint',state_path,encoded(after)))
        summaries.append({'code':code,'day':day,'rows_before':len(old),'rows_after':len(changed),
                          'added_rows':len(changed)-len(old),'status':cell['status'],'accepted_hours':sorted(frames)})
    plan={'implementation_sha256':digest(Path(__file__)),'dependencies':dependencies,'inputs':inputs,
          'entries':entries,'guards':guards,'summaries':summaries,'session_completeness':'NOT_ESTABLISHED',
          'source_certified':False,'publication_allowed':False}
    save_json(out/'plan.json',plan);return plan


def validate_binding(plan,cache):
    expected={}
    for code in {key.split('_')[0] for key in RECEIPTS}:
        expected[code]={'cache':cache/(code+'.parquet'),'checkpoint':cache/'.backfill'/(code+'.json'),
                        'head':cache/'.backfill/journal'/code/'head.json'}
    for row in plan['entries']:
        if Path(row['path']).resolve()!=expected[row['code']][row['role']].resolve():raise ValueError('plan_outside_locked_cache')
    paths=[row['path'] for row in plan['entries']]
    if len(set(paths))!=len(paths):raise ValueError('duplicate_mutation_target')


def state_of(row):
    path=Path(row['path']);sha=digest(path)
    for state in ['after','before']:
        if sha==row[state+'_sha256'] and (state+'_identity' not in row or identity(path)==row[state+'_identity']):return state
    raise ValueError('changed_live_target')


def apply(plan):
    if digest(Path(__file__))!=plan['implementation_sha256']:raise ValueError('changed_implementation')
    for name,sha in plan['dependencies'].items():
        if digest(ROOT/name)!=sha:raise ValueError('changed_dependency')
    for path,sha in plan['inputs'].items():
        if digest(Path(path))!=sha:raise ValueError('changed_evidence')
    for guard in plan['guards']:
        path=Path(guard['path'])
        if digest(path)!=guard['sha256'] or ('identity' in guard and identity(path)!=guard['identity']):raise ValueError('changed_guard')
    # All targets and saved before/after artifacts must be valid before mutation.
    for row in plan['entries']:
        for state in ['before','after']:
            if digest(Path(row[state+'_path']))!=row[state+'_sha256']:raise ValueError('changed_saved_artifact')
        state_of(row)
    for row in plan['entries']:
        if row.get('role')!='head':continue
        price=next(x for x in plan['entries'] if x.get('role')=='cache' and x['code']==row['code'])
        for state in ['before','after']:
            head=json.loads(Path(row[state+'_path']).read_text())
            if head['file_sha256']!=price[state+'_sha256'] or not restore_state(head['state']).equals(
                    pd.read_parquet(price[state+'_path'])):raise ValueError('changed_saved_journal')
    writes=0
    for row in plan['entries']:
        if state_of(row)=='after':continue
        def writer(temp):
            temp.write_bytes(Path(row['after_path']).read_bytes())
            if 'after_identity' in row:os.utime(temp,ns=(row['after_identity'][0],row['after_identity'][0]))
            if digest(temp)!=row['after_sha256'] or state_of(row)!='before':raise ValueError('concurrent_target_change')
        atomic_write(Path(row['path']),writer)
        if state_of(row)!='after':raise ValueError('write_verification_failed')
        writes+=1
    return {'status':'APPLIED' if writes else 'REUSED','files_changed_this_run':writes,
            'summaries':plan['summaries'],'session_completeness':'NOT_ESTABLISHED'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--cache',type=Path,default=Path.home()/'research_cache/intraday')
    p.add_argument('--apply',action='store_true');args=p.parse_args()
    out=args.root/'runtime_state/audit/intraday_terminal_20261007_205547/recovery'
    with (args.cache/'.backfill/writer.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status':'BUSY','files_changed':0}));return 2
        if legacy_writers(args.cache):raise ValueError('legacy_writer_active')
        plan=prepare(args.root,args.cache,out);validate_binding(plan,args.cache)
        result=apply(plan) if args.apply else {'status':'PLANNED','summaries':plan['summaries'],'entries':len(plan['entries'])}
        if args.apply:save_json(out/'applied.json',{'plan_sha256':digest(out/'plan.json'),'summaries':plan['summaries']})
        print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
