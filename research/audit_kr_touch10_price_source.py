"""Cross-check a frozen replay using KIS KRX adjusted daily bars; no promotion."""
from __future__ import annotations
import argparse
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
sys.path.insert(0,str(ROOT))
from modules.kr_contract_settlement import settle
from research.validate_kr_touch10 import metrics
from multi_agent.tools.backfill_kr_intraday import save_json, request_deadline


def parse_bars(payload, start, end):
    if payload.get('rt_cd') != '0' or not isinstance(payload.get('output2'),list):
        raise ValueError('invalid_provider_response')
    records = []
    for item in payload['output2']:
        day = pd.to_datetime(item.get('stck_bsop_date'),format='%Y%m%d',errors='raise')
        if not pd.Timestamp(start) <= day <= pd.Timestamp(end):
            raise ValueError('date_outside_request')
        record = {'date':day}
        for target, source in [('adj_open','stck_oprc'),('adj_high','stck_hgpr'),('adj_low','stck_lwpr'),('adj_close','stck_clpr'),('volume','acml_vol')]:
            record[target] = float(item[source])
        if not all(np.isfinite(record[k]) and record[k] >= 0 for k in record if k != 'date'):
            raise ValueError('nonfinite_or_negative_bar')
        if record['volume'] > 0 and (min(record[k] for k in ['adj_open','adj_high','adj_low','adj_close']) <= 0 or
                record['adj_high'] < max(record[k] for k in ['adj_open','adj_low','adj_close']) or
                record['adj_low'] > min(record[k] for k in ['adj_open','adj_high','adj_close'])):
            raise ValueError('invalid_traded_OHLC')
        records.append(record)
    frame = pd.DataFrame(records)
    if frame.empty or frame.date.duplicated().any():
        raise ValueError('empty_or_duplicate_prices')
    return frame.sort_values('date')


def evaluate(spec, prior, groups, sessions):
    rows, differences = [], []
    old = {(r['date'],r['ticker'],r['variant']):r for r in prior['records']}
    calendar = [str(pd.Timestamp(d).date()) for d in sessions]
    for pick in spec['cohort']:
        for variant,horizon in [('baseline',pick['baseline_horizon']),('candidate_h10',10)]:
            code = pick['ticker'].split('.')[0]
            result = settle(groups[code],sessions,pick['date'],horizon) if code in groups else {'status':'data_error','reason':'missing_KIS_prices'}
            row = {'date':pick['date'],'ticker':pick['ticker'],'market':pick['market'],'variant':variant,**result}
            if result['status'] == 'resolved':row['net'] = result['policy_ret']-spec['contract']['cost_pct']
            rows.append(row)
            baseline = old[(pick['date'],pick['ticker'],variant)]
            if row.get('entry_open') and baseline.get('entry_open'):
                row['entry_open_ratio_to_prior'] = row['entry_open']/baseline['entry_open']
            changed = [key for key in ['status','touch'] if row.get(key) != baseline.get(key)]
            delta = row.get('policy_ret',0)-baseline.get('policy_ret',0) if row['status'] == baseline['status'] == 'resolved' else None
            if changed or delta is not None and abs(delta) > 1e-6:
                differences.append({'date':pick['date'],'ticker':pick['ticker'],'variant':variant,'changed':changed,
                                    'old_status':baseline['status'],'new_status':row['status'],'old_touch':baseline.get('touch'),
                                    'new_touch':row.get('touch'),'net_delta_pp':delta})
    stats = {f'{market}/{variant}':metrics([r for r in rows if r['variant']==variant and (market=='combined' or r['market']==market)],calendar)
             for market in ['KOSPI','KOSDAQ','combined'] for variant in ['baseline','candidate_h10']}
    return {'metrics':stats,'differences':differences,'records':rows,'publication_allowed':False,
            'status':'PRICE_SOURCE_SENSITIVE' if any(r['changed'] for r in differences) else 'NO_TOUCH_STATUS_DIFFERENCE',
            'limitations':['No new independent selection holdout','Same-day controls were not recollected from KIS; prior alpha statistics are not revalidated',
                           'Frequency and sample-size failures remain unchanged','A provider cross-check is not an official corporate-action ledger audit']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--collect',action='store_true')
    args=parser.parse_args()
    raw_spec=(ROOT/'research/prereg_kr_touch10_price_source_20261007.json').read_bytes()
    spec=json.loads(raw_spec)
    prior_path=args.root/'runtime_state/reports/validation/kr_touch10_replay_20261007.json'
    raw_prior=prior_path.read_bytes()
    if hashlib.sha256(raw_prior).hexdigest()!=spec['prior_replay_sha256']:raise ValueError('prior_replay_changed')
    prior=json.loads(raw_prior)
    audit=args.root/'runtime_state/audit/kr_touch10_kis_20261007'
    audit.mkdir(parents=True,exist_ok=True)
    spec_hash=hashlib.sha256(raw_spec).hexdigest()
    spec_path=audit/'prereg.json'
    if spec_path.exists() and spec_path.read_bytes()!=raw_spec:raise ValueError('capture_spec_changed')
    if not spec_path.exists():spec_path.write_bytes(raw_spec)
    request=spec['price_request']
    codes=sorted({p['ticker'].split('.')[0] for p in spec['cohort']})
    if args.collect:
        from dotenv import load_dotenv
        from modules.kis_openapi import KISOpenAPIClient
        load_dotenv(args.root/'.env.local')
        os.environ['KIS_ENABLE_LIVE_CALLS']='1';os.environ['KIS_LIVE_RETRY_COUNT']='0'
        client=KISOpenAPIClient(timeout=10)
        for i,code in enumerate(codes):
            path=audit/f'{code}.json'
            if path.exists():continue
            result={'code':code,'request':request,'prereg_sha256':spec_hash,'fetched_at':datetime.now(timezone.utc).isoformat()}
            try:
                with request_deadline(20):
                    result['payload']=client.daily_bars(code,start_date=request['start_date'],end_date=request['end_date'],adjusted=True,market_div='J')
            except Exception as exc:result['error_type']=type(exc).__name__
            save_json(path,result)
            print(f'captured {i+1}/{len(codes)} {code}',flush=True)
            time.sleep(.3)
    groups,errors={},[]
    for code in codes:
        path=audit/f'{code}.json'
        try:
            result=json.loads(path.read_text())
            if result['prereg_sha256']!=spec_hash or result['request']!=request:raise ValueError('request_mismatch')
            groups[code]=parse_bars(result.get('payload',{}),request['start_date'],request['end_date'])
        except Exception as exc:errors.append({'code':code,'error_type':type(exc).__name__})
    source=Path.home()/'research_cache/px_delisted.parquet'
    if source.stat().st_mtime_ns!=prior['price_mtime_ns']:raise ValueError('prior_price_vintage_changed')
    dates=pd.read_parquet(source,columns=['date']).date
    sessions=sorted(dates[(dates>=pd.Timestamp(request['start_date']))&(dates<=pd.Timestamp(request['end_date']))].unique())
    coverage = {}
    for code, bars in groups.items():
        first_signal = min(p['date'] for p in spec['cohort'] if p['ticker'].split('.')[0] == code)
        expected = {pd.Timestamp(d) for d in sessions if pd.Timestamp(d) >= pd.Timestamp(first_signal)}
        missing = sorted(expected-set(bars.date))
        coverage[code] = {'rows':len(bars),'missing_from_first_signal':[str(d.date()) for d in missing]}
        if missing:errors.append({'code':code,'error_type':'missing_observed_sessions'})
    report=evaluate(spec,prior,groups,sessions)
    report.update(prereg_sha256=spec_hash,source_errors=errors,coverage=coverage,source_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in audit.glob('*.json')},
                  generated_at=datetime.now(timezone.utc).isoformat(),calendar_sessions=len(sessions))
    if errors:report['status']='INCOMPLETE_SOURCE_COVERAGE'
    out=args.root/'runtime_state/reports/validation/kr_touch10_kis_price_audit.json'
    save_json(out,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['records','source_files_sha256']},ensure_ascii=False))


if __name__=='__main__':main()
