"""Archive cold immutable panels on an explicitly configured mounted volume.

Verified copies replace every known hardlink with a same-path symlink. The newest
local generations remain local. No raw prices, provenance or contracts are removed.
A pending journal resumes interrupted relocation before planning another group.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from multi_agent.tools.us_daily_panel_cache import file_sha
from multi_agent.tools.intraday_cache_journal import save_json

GIB = 1024**3


def verify_volume(config):
    mount = Path(config['mount']).resolve()
    if not mount.is_mount():
        raise OSError('archive_volume_unmounted')
    info = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', str(mount)]))
    if info.get('VolumeUUID') != config['volume_uuid']:
        raise OSError('archive_volume_identity_mismatch')
    destination = Path(config['destination']).absolute()
    if not destination.resolve().is_relative_to(mount) or destination == mount:
        raise ValueError('archive_destination_outside_volume')
    parent=destination
    while not parent.exists():parent=parent.parent
    if not os.access(parent,os.W_OK|os.X_OK):
        raise OSError('archive_destination_not_writable')
    return destination


def _copy_verified(source, destination, sha):
    if destination.exists():
        if file_sha(destination) != sha:
            raise ValueError('archive_destination_hash_mismatch')
        return
    if shutil.disk_usage(destination.parent).free < source.stat().st_size + 10*GIB:
        raise OSError('archive_storage_reserve')
    tmp = destination.with_name('.'+destination.name+'.copying')
    with source.open('rb') as src, tmp.open('wb') as out:
        shutil.copyfileobj(src, out, 4*1024*1024)
        out.flush(); os.fsync(out.fileno())
    shutil.copystat(source, tmp)
    if file_sha(tmp) != sha or file_sha(source) != sha:
        raise ValueError('archive_copy_hash_mismatch')
    os.replace(tmp, destination)


def _finish_group(group, config, audit):
    destination = verify_volume(config)
    target = Path(group['target'])
    if target.parent != destination:
        raise ValueError('pending_destination_mismatch')
    destination.mkdir(parents=True, exist_ok=True)
    aliases = [Path(p) for p in group['aliases']]
    originals = [p for p in aliases if not p.is_symlink()]
    for p in originals:
        st=p.stat()
        if [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns] != group['identity']:
            raise ValueError('panel_changed_since_plan')
    if not target.exists() and not originals:
        raise ValueError('missing_archive_and_original')
    if originals:
        _copy_verified(originals[0], target, group['sha256'])
    if file_sha(target) != group['sha256']:
        raise ValueError('archive_hash_mismatch')
    for p in aliases:
        if p.is_symlink():
            if p.resolve() != target:
                raise ValueError('unexpected_panel_symlink')
            continue
        st=p.stat()
        if [st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns] != group['identity']:
            raise ValueError('panel_changed_before_relocation')
        link=p.with_name('.'+p.name+'.archive-link')
        if link.exists() or link.is_symlink():
            if not link.is_symlink() or link.resolve()!=target:
                raise FileExistsError(link)
        else:
            link.symlink_to(target)
        os.replace(link,p)
    assert all(p.resolve()==target and p.stat().st_mtime_ns==group['identity'][3] for p in aliases)
    save_json(audit/(group['id']+'.json'),{**group,'status':'ARCHIVED'})
    (audit/'pending.json').unlink()
    print(json.dumps({'archived_bytes':group['identity'][2],'aliases':len(aliases),'sha256':group['sha256']}),flush=True)
    return group


def archive(market_root, config, *, apply=False):
    market_root=Path(market_root); keep=int(config.get('keep_local',3))
    if keep<2:raise ValueError('at_least_two_local_generations_required')
    destination=verify_volume(config)
    if destination.is_relative_to(market_root.resolve()):raise ValueError('archive_inside_source')
    audit=market_root/'.refresh/panel_archive';audit.mkdir(parents=True,exist_ok=True)
    roots=[market_root]+[Path(p) for p in config.get('alias_roots',[])]
    groups={}; moved=[]
    with (market_root/'.daily_refresh.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pending=audit/'pending.json'
        if pending.exists():
            if not apply:raise ValueError('pending_relocation_requires_resume')
            moved.append(_finish_group(json.loads(pending.read_text()),config,audit))
        for p in market_root.glob('daily_features_[0-9]*.parquet'):
            if p.is_symlink() or not p.is_file():continue
            st=p.stat(); key=(st.st_dev,st.st_ino)
            groups.setdefault(key,{'source':str(p),'identity':[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns],'nlink':st.st_nlink,'aliases':set()})
        cold=sorted(groups,key=lambda k:groups[k]['identity'][3],reverse=True)[keep:]
        for root in roots:
            for p in root.rglob('*.parquet'):
                if p.is_symlink() or not p.is_file():continue
                st=p.stat();key=(st.st_dev,st.st_ino)
                if key in cold:groups[key]['aliases'].add(str(p.absolute()))
        plans=[]
        for key in cold:
            g=groups[key];g['aliases']=sorted(g['aliases'])
            if len(g['aliases'])!=g['nlink']:raise ValueError('unaccounted_panel_hardlinks')
            sha=file_sha(g['source']);g.update(id=uuid.uuid4().hex,market_root=str(market_root.absolute()),sha256=sha,target=str(destination/f"{sha}_{g['identity'][3]}.parquet"))
            plans.append(g)
        plan={'keep_local':keep,'groups':plans,'source_free_before':shutil.disk_usage(market_root).free}
        save_json(audit/('plan_'+uuid.uuid4().hex+'.json'),plan)
        if apply:
            for g in plans:
                save_json(pending,g);moved.append(_finish_group(g,config,audit))
        return {'status':'ARCHIVED' if apply else 'DRY_RUN','planned':len(plans),'completed':len(moved),'archived_unique_bytes':sum(g['identity'][2] for g in moved),'source_free_after':shutil.disk_usage(market_root).free,'audit':str(audit)}


def restore(record):
    """Restore all original aliases, preserving exact bytes and hardlink sharing."""
    group=json.loads(Path(record).read_text())
    with (Path(group['market_root'])/'.daily_refresh.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _restore_group(group,record)


def _restore_group(group,record):
    target=Path(group['target']);aliases=[Path(p) for p in group['aliases']]
    if file_sha(target)!=group['sha256']:raise ValueError('archive_hash_mismatch')
    originals=[p for p in aliases if not p.is_symlink()]
    if any((p.is_symlink() and p.resolve()!=target) or
           (not p.is_symlink() and file_sha(p)!=group['sha256']) for p in aliases):
        raise ValueError('restore_requires_unchanged_archive_links')
    tmp=aliases[0].with_name('.'+aliases[0].name+'.restore-'+group['id'])
    if originals:
        source=originals[0]
    else:
        if shutil.disk_usage(aliases[0].parent).free<target.stat().st_size+10*GIB:
            raise OSError('restore_storage_reserve')
        _copy_verified(target,tmp,group['sha256']);source=tmp
    for p in aliases:
        if not p.is_symlink():continue
        link=p.with_name('.'+p.name+'.restore-link')
        if link.exists():
            if not os.path.samefile(link,source):raise ValueError('unexpected_restore_link')
        else:os.link(source,link)
        os.replace(link,p)
    if tmp.exists():
        if file_sha(tmp)!=group['sha256']:raise ValueError('restore_temporary_hash_mismatch')
        tmp.unlink()
    save_json(Path(record).with_suffix('.restored.json'),{'status':'RESTORED','sha256':group['sha256'],'aliases':group['aliases']})
    return {'status':'RESTORED','aliases':len(aliases)}


def run_cli(args):
    """Keep a local receipt even when a long batch truncates the traceback.

    This observes the journal without changing it. A failed resume must remain
    failed, and a failure to save diagnostics must not hide the original error.
    """
    market_root = Path(args.market_root)
    record = {'started_at': datetime.now(timezone.utc).isoformat(),
              'operation': 'restore' if args.restore else 'archive',
              'apply': bool(args.apply), 'market_root': str(market_root)}
    try:
        if args.restore:
            # A restore record owns its market root, regardless of CLI default.
            market_root = Path(json.loads(args.restore.read_text())['market_root'])
            record['market_root'] = str(market_root)
            result = restore(args.restore)
        else:
            config_path = market_root/'.refresh/archive_storage.json'
            result = ({'status': 'DISABLED', 'reason': 'no_explicit_archive_configuration'}
                      if not config_path.exists() else
                      archive(market_root, json.loads(config_path.read_text()), apply=args.apply))
        record.update(status='SUCCEEDED', result=result)
        return result
    except Exception as exc:
        record.update(status='FAILED', error_type=type(exc).__name__,
                      error=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        record['finished_at'] = datetime.now(timezone.utc).isoformat()
        try:
            pending = market_root/'.refresh/panel_archive/pending.json'
            if pending.exists():
                record['observed_pending'] = {'sha256': file_sha(pending),
                                              'content': json.loads(pending.read_text())}
            receipt = market_root/'.refresh/panel_archive/runs'/(uuid.uuid4().hex+'.json')
            save_json(receipt, record)
            print(json.dumps({'archive_run_receipt': str(receipt),
                              'status': record['status']}), file=sys.stderr, flush=True)
        except Exception as diagnostic_error:
            print('archive_receipt_write_failed: '+repr(diagnostic_error), file=sys.stderr, flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--market-root',type=Path,default=Path.home()/'research_cache/us_daily/NASDAQ')
    ap.add_argument('--apply',action='store_true');ap.add_argument('--restore',type=Path)
    args=ap.parse_args()
    print(json.dumps(run_cli(args)))


if __name__=='__main__':main()
