"""Repair only captured KOSDAQ VWAP entry-reference timezone serialization."""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from research.audit_kosdaq_vwap_provenance import index, stamp, freeze, NAME, KST


def plan(ledger, scans):
    known=index(ledger);index(scans);out=[]
    for row in scans:
        l=known.get((row['run_id'],row['ticker']))
        if row.get('feature_origin')!='kosdaq_intraday_1500_vwap_guard' or row.get('market')!='KOSDAQ':
            raise ValueError('unexpected_source')
        if l:
            value=l.get('ordered_entry_at')
            if not isinstance(value,str) or datetime.fromisoformat(value).tzinfo is not None:
                raise ValueError('requires_original_naive_Korean_bar')
            expected=stamp(value,local=True).astimezone(timezone.utc)
            for key in ['target_tp_pct','hold_days']:
                if l.get(key)!=row.get(key):raise ValueError('contract_changed')
            if l.get('generated_at')!=row.get('recommended_at') or abs(l['p']*100-row['ml_prob'])>1e-8:
                raise ValueError('original_pick_changed')
            basis='original_ledger_Korean_bar'
        else:
            # Two archive-only rows are audited declarations, not recovered fills.
            if (row['run_id'],row['ticker']) not in {('KQ-ITD-3D-T5-20260630','036930.KQ'),('KQ-ITD-3D-T5-20260630','080220.KQ')}:
                raise ValueError('unverified_archive_only_identity')
            if (row.get('feature_snapshot') or {}).get('entry_time_kst')!='15:00':
                raise ValueError('missing_explicit_Korean_schedule')
            expected=stamp('2026-06-30T15:00:00',local=True).astimezone(timezone.utc)
            basis='explicit_archive_schedule_only'
        if expected.astimezone(KST).strftime('%Y%m%d') != row['run_id'][-8:]:
            raise ValueError('entry_day_differs_from_identity')
        old=stamp(row.get('ordered_entry_at'))
        if old is None or old-expected!=timedelta(hours=9):
            raise ValueError('not_known_nine_hour_mismatch')
        out.append({'before':row,'after':{'ordered_entry_at':expected.isoformat()},'basis':basis})
    return out


def cas_sql(updates):
    if not updates or any(set(x['after'])!={'ordered_entry_at'} for x in updates):
        raise ValueError('only_entry_reference_time_may_change')
    ids=[x['before']['id'] for x in updates]
    if len(set(ids))!=len(ids) or any(type(i)is not int or i<=0 for i in ids):
        raise ValueError('invalid_or_duplicate_ID')
    blob=base64.b64encode(json.dumps(updates,allow_nan=False).encode()).decode()
    table='public.market_scan_results'
    return ("WITH p AS (SELECT jsonb_populate_record(NULL::"+table+",x->'before') AS b, "
            "jsonb_populate_record(NULL::"+table+",x->'after') AS a FROM jsonb_array_elements(" 
            "convert_from(decode('"+blob+"','base64'),'UTF8')::jsonb) x) UPDATE "+table+
            " t SET ordered_entry_at=(p.a).ordered_entry_at FROM p WHERE t.id=(p.b).id "
            "AND to_jsonb(t)=to_jsonb(p.b) RETURNING t.id")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--apply',action='store_true');args=parser.parse_args();args.audit.mkdir(parents=True,exist_ok=True)
    provenance=json.loads((args.evidence/'report.json').read_text());inputs={}
    for name in [NAME,'market_scan_results.json']:
        path=args.evidence/name;raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        source=next((p for p in provenance['source_hashes'] if Path(p).name==name),None)
        if source is None or digest!=provenance['source_hashes'][source]:raise ValueError('source_hash_mismatch')
        freeze(args.audit/name,raw);inputs[name]=raw
    ledger=[json.loads(line) for line in inputs[NAME].splitlines() if line.strip()]
    scans=json.loads(inputs['market_scan_results.json']);updates=plan(ledger,scans)
    freeze(args.audit/'plan.json',json.dumps(updates,indent=2,allow_nan=False).encode())
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env');load_dotenv(ROOT/'.env.local')
    from modules.db_manager import DBManager
    from multi_agent.tools.repair_flow_snapshot_metadata import Database
    client=DBManager().client
    if not client:raise RuntimeError('database_client_unavailable')
    ids=[x['before']['id'] for x in updates]
    rows=client.table('market_scan_results').select('*').in_('id',ids).execute().data
    current={r['id']:r for r in rows}
    if len(current)!=len(rows) or set(current)!=set(ids):raise ValueError('current_cohort_incomplete')
    pending=[];done=[]
    for u in updates:
        row=current[u['before']['id']];expected={**u['before'],**u['after']}
        if row==expected:done.append(row['id'])
        elif row==u['before']:pending.append(u)
        else:raise ValueError('current_row_changed_outside_plan')
    # Preserve and verify full current rows before any mutation.
    before=args.audit/('apply_before.json' if args.apply else 'dry_run_before.json')
    if not before.exists():freeze(before,json.dumps(rows,indent=2,allow_nan=False).encode())
    else:
        captured=json.loads(before.read_text())
        by_id={u['before']['id']:u for u in updates}
        if len(captured)!=len(ids) or {r['id'] for r in captured}!=set(ids):raise ValueError('backup_scope_changed')
        for r in captured:
            u=by_id[r['id']]
            if r!=u['before'] and r!={**u['before'],**u['after']}:raise ValueError('backup_differs_from_verified_sources')
    wrote=[]
    if args.apply and pending:
        # Entire batch is a single SQL statement; each row uses typed full-row CAS.
        sql=cas_sql(pending)
        if len(sql.encode())>1000000:raise ValueError('unexpected_query_size')
        wrote=[r['id'] for r in Database().query(sql)]
        if set(wrote)!={u['before']['id'] for u in pending}:raise RuntimeError('concurrent_row_change')
        after=client.table('market_scan_results').select('*').in_('id',ids).execute().data
        if {r['id']:r for r in after}!={u['before']['id']:{**u['before'],**u['after']} for u in updates}:
            raise RuntimeError('readback_differs_from_exact_plan')
        freeze(args.audit/'after.json',json.dumps(after,indent=2,allow_nan=False).encode())
    result={'planned':len(updates),'pending':len(pending),'already_correct':len(done),'writes':len(wrote),
            'backup_sha256':hashlib.sha256(before.read_bytes()).hexdigest(),
            'applied':args.apply,'field':'ordered_entry_at','ledger_changed':False,
            'scope':'Entry-reference serialization only; no fills, original recommendations or model evidence reconstructed.'}
    name='apply_result.json' if args.apply and wrote else 'repeat_result.json' if args.apply else 'dry_run_result.json'
    (args.audit/name).write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':main()
