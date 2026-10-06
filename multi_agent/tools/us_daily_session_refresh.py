"""Session-aware, audited daily US cache refresh. No selection or label policy."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import time
import uuid
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from multi_agent.tools.intraday_cache_journal import atomic_write, digest, save_json


def latest_completed_session(paths, now=None):
    from multi_agent.tools import backfill_us_daily_features as bf
    now=now or datetime.now(ZoneInfo('America/New_York'))
    now=now.astimezone(ZoneInfo('America/New_York'))
    frame=bf._download_single('SPY',(now.date()-timedelta(days=20)).isoformat(),
                              (now.date()+timedelta(days=1)).isoformat(),10)
    if frame.empty:raise ValueError('missing_US_reference_calendar')
    # Conservatively wait until normal close even on an early-close day.
    cutoff=pd.Timestamp(now.date())
    valid=frame[pd.to_datetime(frame.date)<=cutoff]
    if now.hour<16:valid=valid[pd.to_datetime(valid.date)<cutoff]
    if valid.empty:raise ValueError('no_completed_US_reference_session')
    target=pd.to_datetime(valid.date).max().normalize()
    if (cutoff-target).days>7:raise ValueError('stale_US_reference_calendar')
    path=paths.market_root/'.refresh/reference'/f'{now.strftime("%Y%m%dT%H%M%S")}_{uuid.uuid4().hex}.json'
    save_json(path,{'captured_at':now.isoformat(),'provider':'yfinance/SPY','required_through':str(target.date()),
                    'reference_rows':json.loads(frame.to_json(orient='records',date_format='iso')),
                    'meaning':'latest observed provider session after normal close; not an independent exchange-calendar certification'})
    return str(target.date())


def coverage(path, required_through, expected_symbols=None):
    if path is None or not Path(path).exists():
        return {'current':False,'reason':'missing_panel','required_through':required_through}
    target=pd.Timestamp(required_through)
    frame=pd.read_parquet(path,columns=['date','symbol'])
    frame['date']=pd.to_datetime(frame.date)
    # Use the existing universe snapshot where available; otherwise the recent
    # observed panel cohort. Never let a single new symbol certify all others.
    recent=frame[(frame.date<=target)&(frame.date>=target-pd.Timedelta(days=30))]
    expected=set(map(str,expected_symbols)) if expected_symbols is not None else set(recent.symbol.astype(str))
    present=set(frame.loc[frame.date==target,'symbol'].astype(str))
    missing=sorted(expected-present)
    return {'current':bool(expected) and not missing,'required_through':str(target.date()),
            'expected_symbols':len(expected),'present_expected_symbols':len(expected&present),
            'missing_symbols':missing,'reason':None if expected and not missing else 'incomplete_session_coverage'}


def _needs_full(existing, fetched):
    if existing.empty:return False
    common=existing.set_index('date')[['raw_close','adj_factor']].join(
        fetched.set_index('date')[['raw_close','adj_factor']],how='inner',lsuffix='_old',rsuffix='_new')
    if common.empty:return True
    for field in ['raw_close','adj_factor']:
        if not np.isclose(common[field+'_old'],common[field+'_new'],rtol=1e-7,atol=1e-10,equal_nan=False).all():
            return True
    return False


def _store(path, frame, audit):
    """Verified full backup and source hash check before atomic replacement."""
    before=digest(path)
    if path.exists() and pd.read_parquet(path).equals(frame):return False
    estimate=max(path.stat().st_size if path.exists() else 0,int(frame.memory_usage(deep=True).sum()))
    if shutil.disk_usage(path.parent).free<10*1024**3+3*estimate:
        raise OSError('US_raw_storage_reserve')
    backup=audit/'before'/path.name
    if before:
        backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():raise ValueError('duplicate_raw_write_in_run')
        shutil.copyfile(path,backup)
        if digest(backup)!=before:raise ValueError('raw_backup_hash_mismatch')
    pending=audit/'writes'/f'{path.stem}.json'
    record={'path':str(path),'before_sha256':before,'backup':str(backup) if before else None,'rows':len(frame),'status':'PREPARED'}
    save_json(pending,record)
    def writer(temp):
        frame.to_parquet(temp,index=False)
        if not pd.read_parquet(temp).equals(frame):raise ValueError('raw_roundtrip_mismatch')
        if digest(path)!=before:raise ValueError('raw_changed_before_replace')
    atomic_write(path,writer)
    record.update(status='APPLIED',after_sha256=digest(path));save_json(pending,record)
    return True


def refresh_raw(universe,paths,target,*,start,batch_size,timeout,sleep,budget,audit):
    from multi_agent.tools import backfill_us_daily_features as bf
    paths.raw_dir.mkdir(parents=True,exist_ok=True)
    target=pd.Timestamp(target);end=(target+pd.Timedelta(days=1)).date().isoformat()
    groups=defaultdict(list);skipped=[];failed=[];revised=[];written=[];visited=[]
    names=dict(zip(universe.symbol.astype(str),universe.name.astype(str)))
    for symbol in names:
        path=bf._raw_path(paths,symbol)
        try:
            dates=pd.to_datetime(pd.read_parquet(path,columns=['date']).date) if path.exists() else pd.Series([],dtype='datetime64[ns]')
            receipt_path=paths.market_root/'.refresh/receipts'/f'{bf._safe_filename(symbol)}.json'
            receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
            if (target in set(dates) and receipt.get('required_through')==str(target.date())
                    and receipt.get('sha256')==digest(path)):
                skipped.append(symbol);continue
            last=dates.max() if len(dates) else None
            first=max(pd.Timestamp(start),last-pd.Timedelta(days=14)) if last is not None else pd.Timestamp(start)
            groups[first.date().isoformat()].append(symbol)
        except Exception as exc:failed.append({'symbol':symbol,'reason':'existing_raw_unreadable:'+type(exc).__name__})
    save_json(audit/"request_plan.json", {"required_through":str(target.date()),"end_exclusive":end,"request_groups":dict(groups),"skipped_current":skipped,"implementation_sha256":digest(Path(__file__))})
    began=time.monotonic();stopped=False
    # Recent caches first, while retaining every requested symbol in the plan.
    for first,symbols in sorted(groups.items(),reverse=True):
        for batch in bf._chunk(symbols,batch_size):
            if time.monotonic()-began>=budget:stopped=True;break
            try:payload=bf._download_batch(batch,first,end,timeout)
            except Exception:payload=pd.DataFrame()
            for symbol in batch:
                visited.append(symbol);path=bf._raw_path(paths,symbol)
                try:
                    fetched=bf._extract_yfinance_frame(payload,symbol)
                    if fetched.empty:fetched=bf._download_single(symbol,first,end,timeout)
                    if fetched.empty:raise ValueError('empty_provider_response')
                    fetched=fetched[pd.to_datetime(fetched.date)<=target].copy()
                    if target not in set(pd.to_datetime(fetched.date)):raise ValueError('provider_missing_requested_session')
                    existing=pd.read_parquet(path) if path.exists() else pd.DataFrame()
                    if not existing.empty:existing['date']=pd.to_datetime(existing.date)
                    if _needs_full(existing,fetched):
                        revised.append(symbol)
                        fetched=bf._download_single(symbol,start,end,timeout)
                        if fetched.empty:raise ValueError('adjustment_refresh_empty')
                        fetched=fetched[pd.to_datetime(fetched.date)<=target].copy()
                        if target not in set(pd.to_datetime(fetched.date)):raise ValueError('adjustment_refresh_missing_target')
                        # A changed adjustment basis may not be spliced onto an old prefix.
                        expected=set(existing.loc[existing.date<=target,'date'])
                        if not expected.issubset(set(pd.to_datetime(fetched.date))):raise ValueError('adjustment_refresh_incomplete_history')
                    fetched['name']=names[symbol];fetched['market']=paths.market
                    if not existing.empty:
                        fetched=fetched.reindex(columns=existing.columns)
                    frame=bf._merge_raw(existing,fetched)
                    if frame.date.duplicated().any():raise ValueError('duplicate_raw_dates')
                    if target not in set(pd.to_datetime(frame.date)):raise ValueError('merged_target_missing')
                    prices=frame[['open','high','low','close']].apply(pd.to_numeric,errors='coerce')
                    if not np.isfinite(prices).all().all() or (prices<=0).any().any():raise ValueError('invalid_raw_prices')
                    if (frame.high<prices.max(axis=1)).any() or (frame.low>prices.min(axis=1)).any():raise ValueError('invalid_raw_OHLC_order')
                    if not np.isfinite(frame.volume).all() or (frame.volume<0).any():raise ValueError('invalid_raw_volume')
                    if _store(path,frame,audit):written.append(symbol)
                    save_json(paths.market_root/'.refresh/receipts'/f'{bf._safe_filename(symbol)}.json',
                              {'required_through':str(target.date()),'sha256':digest(path),'audit':str(audit)})
                except Exception as exc:failed.append({'symbol':symbol,'reason':str(exc) or type(exc).__name__})
            print(json.dumps({'US_raw_visited':len(visited),'written':len(written),'failed':len(failed),'elapsed_seconds':round(time.monotonic()-began,1)}),flush=True)
            if sleep>0:time.sleep(sleep)
        if stopped:break
    planned={s for values in groups.values() for s in values}
    result={'target':str(target.date()),'written':written,'skipped_current':skipped,'failed':failed,
            'unvisited':sorted(planned-set(visited)),'full_adjustment_refresh':revised,
            'budget_seconds':budget,'elapsed_seconds':time.monotonic()-began,
            'budget_scope':'checked between batches; active network calls complete before stopping'}
    save_json(audit/'raw_result.json',result);return result


def run(paths,*,required_through,output_prefix='daily_features',start='2018-01-01',end=None,
        batch_size=80,feature_batch_size=100,timeout=30,sleep=.1,max_symbols=0,keep_panels=3,budget=600):
    from multi_agent.tools import backfill_us_daily_features as bf
    if not np.isfinite(budget) or budget<=0:raise ValueError('invalid_US_refresh_budget')
    audit=paths.market_root/'.refresh/audit'/f'{datetime.now().strftime("%Y%m%dT%H%M%S")}_{uuid.uuid4().hex}'
    audit.mkdir(parents=True)
    universe=bf._fetch_universe(paths.market,allow_fallback=False)
    if universe.empty:return {'status':'failed','reason':'empty_universe'}
    if max_symbols>0:universe=universe.head(max_symbols).copy()
    # Preserve the previous universe manifest and verify it before replacing it.
    if paths.universe_path.exists():
        backup=audit/'universe_before.csv';shutil.copyfile(paths.universe_path,backup)
        if digest(backup)!=digest(paths.universe_path):raise ValueError('universe_backup_mismatch')
    atomic_write(paths.universe_path,lambda p:universe.to_csv(p,index=False))
    raw=refresh_raw(universe,paths,required_through,start=start,batch_size=batch_size,timeout=timeout,
                    sleep=sleep,budget=budget,audit=audit)
    end=(pd.Timestamp(required_through)+pd.Timedelta(days=1)).date().isoformat()
    if shutil.disk_usage(paths.market_root).free<15*1024**3:
        result={'status':'partial','reason':'panel_storage_reserve','raw':raw,'audit':str(audit)}
        save_json(audit/'result.json',result);return result
    info=bf.write_feature_panel(universe,paths,start=start,end=end,output_prefix=output_prefix,feature_batch_size=feature_batch_size)
    after=coverage(info['output_feature_path'],required_through,universe.symbol)
    complete=after['current'] and not raw['failed'] and not raw['unvisited'] and not info['failed_feature_symbols']
    # Keep prior panels on incomplete recovery; an error must not delete evidence.
    removed=bf.prune_old_panels(paths,output_prefix=output_prefix,keep=keep_panels) if complete else []
    result={'status':'refreshed' if complete else 'partial','required_through':required_through,'audit':str(audit),
            'universe_size':len(universe),'raw_refreshed':len(raw['written']),'raw_skipped_fresh':len(raw['skipped_current']),
            'raw_failed':len(raw['failed']),'raw_unvisited':len(raw['unvisited']),'coverage':after,'pruned_panels':removed,**info}
    panel=Path(info['output_feature_path'])
    result['panel_identity']={'path':str(panel),'mtime_ns':panel.stat().st_mtime_ns,'size':panel.stat().st_size}
    result['universe_sha256']=digest(paths.universe_path)
    save_json(audit/'result.json',result)
    if complete:save_json(paths.market_root/'.refresh/current.json',result)
    return result
