"""Frozen extended-session residual transfer diagnostic; never publishes picks."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.intraday_cache_journal import restore_state, save_json, atomic_write
from multi_agent.tools.backfill_kr_intraday import request_deadline
from research.audit_kr_touch10_price_source import parse_bars
from research.validate_kr_touch10 import metrics
from modules.kr_contract_settlement import settle


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunks(start, end, days):
    day, end = pd.Timestamp(start), pd.Timestamp(end)
    while day <= end:
        last = min(day + pd.Timedelta(days=days-1), end)
        yield day.strftime('%Y%m%d'), last.strftime('%Y%m%d')
        day = last + pd.Timedelta(days=1)


def capture(spec, spec_hash, audit, root, budget):
    from dotenv import load_dotenv
    from modules.kis_openapi import KISOpenAPIClient
    load_dotenv(root/'.env.local')
    os.environ['KIS_ENABLE_LIVE_CALLS'] = '1'
    os.environ['KIS_LIVE_RETRY_COUNT'] = '0'
    client = KISOpenAPIClient(timeout=10)
    started = time.monotonic(); count = 0
    for source in spec['inputs']['frozen_states']:
        code = source['code']
        for start, end in chunks(spec['prices']['start'], spec['prices']['end'], spec['prices']['chunk_calendar_days']):
            path = audit/'daily'/f'{code}_{start}_{end}.json'
            if path.exists():
                record = json.loads(path.read_text())
                if record['prereg_sha256'] != spec_hash:
                    raise ValueError('existing_capture_spec_mismatch')
                continue
            if time.monotonic()-started >= budget:
                print(json.dumps({'capture_status':'BUDGET_EXHAUSTED','new_requests':count}), flush=True)
                return
            request = {'code':code,'start':start,'end':end,'adjusted':True,'market_div':'J'}
            record = {'request':request,'prereg_sha256':spec_hash,'fetched_at':datetime.now(timezone.utc).isoformat()}
            try:
                with request_deadline(20):
                    record['payload'] = client.daily_bars(code,start_date=start,end_date=end,adjusted=True,market_div='J')
            except Exception as exc:
                record['error_type'] = type(exc).__name__
            save_json(path, record);count += 1
            if count % 20 == 0:
                print(json.dumps({'new_requests':count,'elapsed':round(time.monotonic()-started,1)}),flush=True)
            time.sleep(.15)
    print(json.dumps({'capture_status':'REQUESTS_VISITED','new_requests':count}),flush=True)


def residual(frame, after=None):
    x = np.column_stack([np.ones(len(frame)),frame.regular,frame.log_turnover,(frame.market=='KOSDAQ').astype(float)])
    y = frame.after.to_numpy() if after is None else np.asarray(after)
    return y-x@np.linalg.lstsq(x,y,rcond=None)[0]


def controls_for(frame, selected):
    row = frame.loc[selected]
    same = frame[frame.market==row.market]
    scales = same[['regular','log_turnover']].std(ddof=0).replace(0,1)
    other = same.drop(index=selected).copy()
    other['distance'] = (((other[['regular','log_turnover']]-row[['regular','log_turnover']].astype(float))/scales)**2).sum(axis=1)
    return other.sort_values(['distance','code']).head(20).code.tolist()


def decisions(panel, calendar, seeds):
    groups = {day:frame.sort_values('code').reset_index(drop=True) for day,frame in panel.groupby('date')}
    result=[]; accepted=[]
    for i, day in enumerate(calendar):
        frame=groups.get(day)
        if frame is None or frame.empty:
            result.append({'date':day,'decision':'NO_ELIGIBLE_SIGNAL_DATA','eligible':0});continue
        frame=frame.copy();frame['score']=residual(frame)
        top=frame.sort_values(['score','code'],ascending=[False,True]).index[0]
        common={'date':day,'eligible':len(frame),'source_code':frame.loc[top,'code'],'score':float(frame.loc[top,'score'])}
        if frame.loc[top,'score'] <= 0:
            result.append({**common,'decision':'NO_POSITIVE_RESIDUAL'});continue
        if sum(i-j<=4 for j in accepted)>=3:
            result.append({**common,'decision':'CADENCE_CAP'});continue
        accepted.append(i)
        noise={}
        for seed in seeds:
            # Stable per-date generator; adding another date cannot change this date's draw.
            rng=np.random.default_rng(seed+int(day.replace('-','')))
            values=frame.after.to_numpy().copy()
            for _, indexes in frame.groupby('market').groups.items():
                ix=np.array(list(indexes));values[ix]=rng.permutation(values[ix])
            variant=frame.copy();variant['noise_score']=residual(frame,values)
            noise[str(seed)]=variant.sort_values(['noise_score','code'],ascending=[False,True]).iloc[0].code
        baseline=frame.sort_values(['regular','code'],ascending=[False,True]).iloc[0].code
        result.append({**common,'decision':'ACCEPT','code':frame.loc[top,'code'],'market':frame.loc[top,'market'],
                       'controls':controls_for(frame,top),'baseline_code':baseline,'noise_codes':noise})
    return result


def build_signals(spec, spec_hash, audit):
    existing=audit/'signal_decisions.json'
    if existing.exists():
        result=json.loads(existing.read_text())
        if result['prereg_sha256']!=spec_hash or sha(audit/'signal_panel.parquet')!=result['panel_sha256']:
            raise ValueError('frozen_signal_inputs_changed')
        return result
    meta_path=Path(spec['inputs']['calendar_market'])
    if sha(meta_path)!=spec['inputs']['calendar_market_sha256']:
        raise ValueError('calendar_market_vintage_changed')
    meta=pd.read_parquet(meta_path);meta['date']=pd.to_datetime(meta.date).dt.strftime('%Y-%m-%d');meta['code']=meta.code.astype(str).str.zfill(6)
    if meta.duplicated(['code','date']).any():raise ValueError('duplicate_market_metadata')
    calendar=sorted(meta.date.unique());metadata=meta.set_index(['code','date']).market.to_dict()
    rows=[]; counts=Counter(); file_counts=[]
    for source in spec['inputs']['frozen_states']:
        frame=restore_state(source['journal_state']); code=source['code']
        if frame.index.has_duplicates:raise ValueError('duplicate_signal_bar')
        date=frame.index.strftime('%Y-%m-%d'); minute=frame.index.strftime('%H:%M')
        reg=(minute>='09:00')&(minute<='15:30')
        aft=(minute>'15:30')&(minute<='20:00')&(frame.Volume.to_numpy()>0)
        turnover=pd.Series((frame.Close*frame.Volume).to_numpy()[reg],index=date[reg]).groupby(level=0).sum()
        after_count=pd.Series(1,index=date[aft]).groupby(level=0).sum()
        anchor=frame.loc[np.isin(minute,spec['eligibility']['anchors']),['Open','Close','Volume']].copy()
        anchor['date']=anchor.index.strftime('%Y-%m-%d');anchor['minute']=anchor.index.strftime('%H:%M')
        table=anchor.set_index(['date','minute']).unstack('minute')
        observed=set(date); valid=0
        for day in calendar:
            reason=None;market=metadata.get((code,day))
            if day not in observed:reason='no_observed_bars'
            elif market not in spec['eligibility']['market']:reason='no_market_metadata'
            elif day not in table.index or any((field,m) not in table.columns or pd.isna(table.loc[day,(field,m)]) for m in spec['eligibility']['anchors'] for field in ['Open','Close','Volume']):reason='missing_anchor'
            elif any(table.loc[day,('Volume',m)]<=0 for m in spec['eligibility']['anchors']):reason='nontrading_anchor'
            elif after_count.get(day,0)<spec['eligibility']['minimum_positive_afterhours_rows']:reason='insufficient_afterhours_bars'
            elif turnover.get(day,0)<=0:reason='invalid_regular_turnover'
            if reason:
                counts[reason]+=1;continue
            op,close,last=[float(table.loc[day,key]) for key in [('Open','09:00'),('Close','15:30'),('Close','19:59')]]
            if not all(np.isfinite(x) and x>0 for x in [op,close,last]):raise ValueError('invalid_anchor_price')
            rows.append({'code':code,'date':day,'market':market,'regular':np.log(close/op),'after':np.log(last/close),
                         'log_turnover':np.log(turnover[day]),'after_rows':int(after_count[day])});valid+=1
        file_counts.append({'code':code,'observed_dates':len(observed),'anchor_eligible_dates':valid})
        if len(file_counts)%25==0:print('signal files',len(file_counts),flush=True)
    panel=pd.DataFrame(rows)
    if panel.empty:raise ValueError('no_signal_data')
    market_ok=panel.groupby(['date','market']).code.transform('size')>=spec['eligibility']['minimum_same_market_codes']
    counts['insufficient_same_market_pool']=int((~market_ok).sum());panel=panel[market_ok].copy()
    date_ok=panel.groupby('date').code.transform('size')>=spec['eligibility']['minimum_date_codes']
    counts['insufficient_date_pool']=int((~date_ok).sum());panel=panel[date_ok].copy()
    path=audit/'signal_panel.parquet';atomic_write(path,lambda temp:panel.to_parquet(temp,index=False))
    result={'prereg_sha256':spec_hash,'calendar':calendar,'panel_sha256':sha(path),'signal_rows':len(panel),
            'eligibility_counts':dict(counts),'file_counts':file_counts,
            'decisions':decisions(panel,calendar,[20261007,20261008,20261009]),'outcomes_used':False}
    save_json(audit/'signal_decisions.json',result)
    print(json.dumps({'signal_rows':len(panel),'decisions':dict(Counter(d['decision'] for d in result['decisions'])),'eligibility_counts':dict(counts)}),flush=True)
    return result


def load_prices(spec, spec_hash, audit):
    groups={};errors=[];sources={};missing=[]
    for source in spec['inputs']['frozen_states']:
        code=source['code'];parts=[]
        for start,end in chunks(spec['prices']['start'],spec['prices']['end'],spec['prices']['chunk_calendar_days']):
            path=audit/'daily'/f'{code}_{start}_{end}.json'
            if not path.exists():missing.append(path.name);continue
            sources[path.name]=sha(path)
            try:
                record=json.loads(path.read_text())
                request={'code':code,'start':start,'end':end,'adjusted':True,'market_div':'J'}
                if record['prereg_sha256']!=spec_hash or record['request']!=request:raise ValueError('request_mismatch')
                payload=record.get('payload',{})
                if payload.get('rt_cd')=='0' and payload.get('output2')==[]:
                    continue  # Empty before-listing/holiday chunks are evidence, not invented bars.
                parts.append(parse_bars(payload,start,end))
            except Exception as exc:errors.append({'code':code,'file':path.name,'reason':str(exc)})
        if parts:
            frame=pd.concat(parts).sort_values('date')
            if frame.date.duplicated().any():raise ValueError('overlapping_captured_daily_bars')
            groups[code]=frame
    if missing:raise ValueError(f'capture_incomplete:{len(missing)} requests; resume --collect')
    return groups,errors,sources


def ci(rows, calendar, field, block=5, seed=20261007, draws=5000):
    if not rows or len(calendar)<block:return None
    daily=pd.DataFrame(rows).groupby('date')[field].agg(['sum','count']).reindex(calendar,fill_value=0).to_numpy(float)
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,len(calendar)-block+1,size=(draws,int(np.ceil(len(calendar)/block))))
    ix=(starts[...,None]+np.arange(block)).reshape(draws,-1)[:,:len(calendar)]
    sums=daily[ix].sum(axis=1);usable=sums[:,1]>0
    if not usable.any():return None
    return np.quantile(sums[usable,0]/sums[usable,1],[.025,.975]).tolist()


def evaluate(spec,spec_hash,audit):
    frozen=json.loads((audit/'signal_decisions.json').read_text())
    if frozen['prereg_sha256']!=spec_hash or sha(audit/'signal_panel.parquet')!=frozen['panel_sha256']:
        raise ValueError('frozen_signal_inputs_changed')
    groups,source_errors,source_hashes=load_prices(spec,spec_hash,audit)
    calendar=frozen['calendar'];sessions=[pd.Timestamp(d) for d in calendar]
    resolved_calendar=calendar[:-spec['contract']['horizon_sessions']]
    cost=spec['contract']['cost_pct'];memo={}
    def outcome(code,day):
        key=(code,day)
        if key not in memo:
            value=settle(groups[code],sessions,day,10) if code in groups else {'status':'data_error','reason':'missing_daily_code'}
            memo[key]={'date':day,'code':code,**value}
            if value['status']=='resolved':memo[key]['net']=value['policy_ret']-cost
        return memo[key]
    records=[];paired=[];control_records=[];comparisons={'baseline':[],'noise20261007':[],'noise20261008':[],'noise20261009':[]}
    pools={};selected_errors=[]
    for decision in frozen['decisions']:
        if decision['decision']!='ACCEPT':continue
        day=decision['date'];r=outcome(decision['code'],day)
        records.append({**r,'market':decision['market'],'score':decision['score']})
        controls=[outcome(code,day) for code in decision['controls']]
        if len(controls)!=20:raise ValueError('prespecified_control_count_mismatch')
        control_records.append({'date':day,'selected':decision['code'],'controls':controls})
        selected_errors.extend(x for x in [r,*controls] if x['status']=='data_error')
        if r['status']=='resolved' and all(c['status']=='resolved' for c in controls):
            values=np.array([c['net'] for c in controls]);pools[day]=values
            paired.append({**r,'excess':r['net']-float(values.mean())})
        alternates={'baseline':decision['baseline_code'],**{'noise'+seed:code for seed,code in decision['noise_codes'].items()}}
        for variant,code in alternates.items():
            alternative=outcome(code,day)
            comparisons[variant].append({'date':day,'candidate_status':r['status'],'alternative':alternative,
                'delta':r['net']-alternative['net'] if r['status']==alternative['status']=='resolved' else None})
    m=metrics(records,calendar)
    m['net_ev_block10_ci95']=ci([r for r in records if r['status']=='resolved'],calendar,'net',block=10)
    tests={};observed=sum(r['net'] for r in paired)
    for seed in [20261007,20261008,20261009]:
        rng=np.random.default_rng(seed);null=np.zeros(5000)
        for row in paired:null+=rng.choice(pools[row['date']],5000)
        tests[str(seed)]=float((1+(null>=observed).sum())/5001) if paired else None
    excess={'paired_n':len(paired),'mean_pp':float(np.mean([r['excess'] for r in paired])) if paired else None,
            'block5_ci95':ci(paired,calendar,'excess'),'block10_ci95':ci(paired,calendar,'excess',block=10),
            'ticker_placebo_p_by_seed':tests,'ticker_placebo_p_max':max(tests.values()) if paired else None}
    contrasts={}
    for variant,rows in comparisons.items():
        valid=[r for r in rows if r['delta'] is not None]
        contrasts[variant]={'n':len(valid),'mean_delta_pp':float(np.mean([r['delta'] for r in valid])) if valid else None,
                            'block5_ci95':ci(valid,calendar,'delta')}
    fired={r['date'] for r in records};weeks=pd.DataFrame({'date':calendar})
    weeks['week']=pd.to_datetime(weeks.date).dt.to_period('W-SUN').astype(str);weeks['fired']=weeks.date.isin(fired).astype(int)
    frequency={'all_sessions':len(calendar),'firing_dates':len(fired),'per_five_sessions':5*len(fired)/len(calendar),
               'calendar_weeks':weeks.groupby('week').fired.sum().to_dict(),
               'mature_per_five_sessions':5*len(fired.intersection(resolved_calendar))/len(resolved_calendar)}
    # Timing-only circular placebo. Benchmarks retain the pre-outcome same-date matching rule
    # on nonfiring dates too. Missing dates are enumerated; no timing-alpha promotion claim.
    panel=pd.read_parquet(audit/'signal_panel.parquet');benchmarks={};benchmark_missing=[]
    byday={day:g.sort_values('code').reset_index(drop=True) for day,g in panel.groupby('date')}
    for day in resolved_calendar:
        frame=byday.get(day)
        if frame is None:benchmark_missing.append(day);continue
        frame=frame.copy();frame['score']=residual(frame)
        top=frame.sort_values(['score','code'],ascending=[False,True]).index[0]
        controls=[outcome(code,day) for code in controls_for(frame,top)]
        if len(controls)==20 and all(c['status']=='resolved' for c in controls):benchmarks[day]=float(np.mean([c['net'] for c in controls]))
        else:benchmark_missing.append(day)
    dates=sorted(benchmarks);flag=np.array([d in fired for d in dates]);values=np.array([benchmarks[d] for d in dates]);timing=None
    if flag.any() and len(dates)>1:
        actual=float(values[flag].mean());shifted=[float(values[np.roll(flag,k)].mean()) for k in range(1,len(dates))]
        timing={'statistic':'matched benchmark mean on firing dates; diagnostic only','observed':actual,
                'p_ge':(1+sum(v>=actual for v in shifted))/(1+len(shifted)),'rotations':len(shifted),
                'missing_market_dates':benchmark_missing,'calendar_compressed_for_missing_dates':bool(benchmark_missing)}
    halves={}
    for name,dates in [('first',calendar[:len(calendar)//2]),('second',calendar[len(calendar)//2:])]:
        subset=[r for r in records if r['date'] in dates];ps=[r for r in paired if r['date'] in dates]
        halves[name]={'metrics':metrics(subset,dates),'matched_excess_pp':float(np.mean([r['excess'] for r in ps])) if ps else None}
    inconclusive=[];reject=[];target_fail=[]
    if m['n']<30 or m['unique_dates']<20:inconclusive.append('insufficient_mature_sample')
    if selected_errors:inconclusive.append('selected_or_control_data_errors')
    if not paired:inconclusive.append('no_complete_matched_pairs')
    if paired:
        if excess['mean_pp']<=0:reject.append('nonpositive_matched_excess')
        if excess['block5_ci95'] is None or excess['block5_ci95'][0]<=0:reject.append('matched_excess_ci_not_positive')
        if excess['ticker_placebo_p_max']>.05:reject.append('ticker_placebo_not_significant')
    if m['net_ev_block_ci95'] is not None and m['net_ev_block_ci95'][0]<=0:reject.append('net_ev_ci_not_positive')
    if m['touch_rate'] is not None and m['touch_rate']<.7:target_fail.append('touch_rate_below70pct')
    if not 2<=frequency['per_five_sessions']<=3:target_fail.append('frequency_outside2to3')
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'prereg_sha256':spec_hash,
            'implementation_sha256':sha(Path(__file__)),'signal_decisions_sha256':sha(audit/'signal_decisions.json'),
            'source_files_sha256':source_hashes,'source_errors':source_errors,'eligibility':frozen['eligibility_counts'],
            'metrics':m,'matched_excess':excess,'contrasts_diagnostic':contrasts,'frequency':frequency,'stability_halves':halves,
            'circular_timing_diagnostic':timing,'selected_data_errors':selected_errors,'records':records,
            'matched_pairs':paired,'control_records':control_records,'alternate_records':comparisons,
            'decision':{'inconclusive':inconclusive,'mechanism_reject':reject,'user_target_fail':target_fail},
            'status':'INCONCLUSIVE' if inconclusive else 'REJECT_FIXED_RULE' if reject or target_fail else 'RETROSPECTIVE_RULE_PASS_ONLY',
            'publication_allowed':False,'limitations':spec['decision']['mandatory_remaining']}
    out=audit.parent.parent/'reports/validation/ext_transfer_20261007.json'
    save_json(out,report)
    print(json.dumps({k:report[k] for k in ['status','metrics','matched_excess','frequency','decision']},ensure_ascii=False),flush=True)
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--spec',type=Path,default=ROOT/'research/prereg_ext_transfer_20261007.json')
    ap.add_argument('--collect',action='store_true')
    ap.add_argument('--signals',action='store_true')
    ap.add_argument('--evaluate',action='store_true')
    ap.add_argument('--budget',type=float,default=600)
    args=ap.parse_args()
    raw=args.spec.read_bytes();spec=json.loads(raw);spec_hash=hashlib.sha256(raw).hexdigest()
    if sha(Path(spec['inputs']['extended_manifest']))!=spec['inputs']['extended_manifest_sha256']:
        raise ValueError('extended_source_manifest_changed')
    if args.budget<=0:ap.error('positive budget required')
    audit=args.root/'runtime_state/audit/ext_transfer_20261007';audit.mkdir(parents=True,exist_ok=True)
    spec_path=audit/'prereg.json'
    if spec_path.exists() and spec_path.read_bytes()!=raw:raise ValueError('prereg_changed')
    if not spec_path.exists():spec_path.write_bytes(raw)
    if args.collect:capture(spec,spec_hash,audit,args.root,args.budget)
    if args.signals:build_signals(spec,spec_hash,audit)
    if args.evaluate:evaluate(spec,spec_hash,audit)


if __name__=='__main__':main()
