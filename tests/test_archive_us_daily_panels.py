import json
import os
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
import pytest
from multi_agent.tools import archive_us_daily_panels as ar
from multi_agent.tools import backfill_us_daily_features as bf
from multi_agent.tools import report_nasdaq_session_tape as tape
from modules import market_sessions


@pytest.fixture
def setup(tmp_path,monkeypatch):
    root=tmp_path/'cache/us_daily/NASDAQ';root.mkdir(parents=True)
    audit=tmp_path/'audit';audit.mkdir();dest=tmp_path/'external';dest.mkdir()
    panels=[]
    for i in range(4):
        p=root/f'daily_features_2026100{i+1}.parquet'
        pd.DataFrame({'date':pd.to_datetime(['2026-10-01']),'value':[i]}).to_parquet(p)
        os.utime(p,ns=(1000+i,1000+i));panels.append(p)
    alias=audit/'before.parquet';os.link(panels[0],alias)
    config={'keep_local':3,'alias_roots':[str(audit)],'destination':str(dest)}
    monkeypatch.setattr(ar,'verify_volume',lambda c:Path(c['destination']))
    monkeypatch.setattr(ar.shutil,'disk_usage',lambda p:SimpleNamespace(free=100*ar.GIB))
    return root,panels,alias,config


def test_archive_preserves_all_bytes_paths_mtimes_and_restores_links(setup):
    root,ps,alias,c=setup;sha=ar.file_sha(ps[0]);mtime=ps[0].stat().st_mtime_ns
    before={p:ar.file_sha(p) for p in ps+[alias]}
    assert ar.archive(root,c)['planned']==1
    assert not ps[0].is_symlink()
    assert ar.archive(root,c,apply=True)['completed']==1
    assert ps[0].is_symlink() and alias.is_symlink()
    assert all(not p.is_symlink() for p in ps[1:])
    assert before=={p:ar.file_sha(p) for p in before}
    assert ps[0].stat().st_mtime_ns==mtime
    pd.testing.assert_frame_equal(pd.read_parquet(ps[0]),pd.DataFrame({'date':pd.to_datetime(['2026-10-01']),'value':[0]}))
    assert ar.archive(root,c,apply=True)['completed']==0
    record=next(p for p in (root/'.refresh/panel_archive').glob('*.json') if not p.name.startswith('plan_'))
    assert ar.restore(record)['status']=='RESTORED'
    assert not ps[0].is_symlink() and ps[0].stat().st_ino==alias.stat().st_ino
    assert ar.file_sha(alias)==sha


def test_unaccounted_hardlink_prevents_any_relocation(setup,tmp_path):
    root,ps,alias,c=setup;os.link(ps[0],tmp_path/'untracked.parquet')
    with pytest.raises(ValueError,match='unaccounted'):ar.archive(root,c,apply=True)
    assert not ps[0].is_symlink()


def test_changed_copy_is_rejected_without_replacing_source(setup,monkeypatch):
    root,ps,alias,c=setup;orig=ar.shutil.copyfileobj
    def corrupt(src,out,*a):orig(src,out,*a);out.write(b'bad')
    monkeypatch.setattr(ar.shutil,'copyfileobj',corrupt)
    with pytest.raises(ValueError,match='copy_hash'):ar.archive(root,c,apply=True)
    assert not ps[0].is_symlink() and not alias.is_symlink()


def test_interrupted_alias_replacement_resumes(setup,monkeypatch):
    root,ps,alias,c=setup;replace=ar.os.replace;calls=[]
    def stop(a,b):
        if str(a).endswith('.archive-link'):
            calls.append(b)
            if len(calls)==2:raise OSError('interrupted')
        return replace(a,b)
    monkeypatch.setattr(ar.os,'replace',stop)
    with pytest.raises(OSError,match='interrupted'):ar.archive(root,c,apply=True)
    # Simulate the process having stopped between symlink creation and replace.
    monkeypatch.setattr(ar.os,'replace',replace)
    ar.archive(root,c,apply=True)
    assert ps[0].is_symlink() and alias.is_symlink()
    assert not (root/'.refresh/panel_archive/pending.json').exists()


def test_archive_configuration_prevents_legacy_pruning(setup):
    root,ps,alias,c=setup;(root/'.refresh').mkdir();(root/'.refresh/archive_storage.json').write_text(json.dumps(c))
    paths=bf.BackfillPaths(root.parent,'NASDAQ')
    assert bf.prune_old_panels(paths,keep=1)==[]
    assert all(p.exists() for p in ps)


def test_disconnected_cold_archive_does_not_break_current_consumers(setup,monkeypatch):
    root,ps,alias,c=setup;ar.archive(root,c,apply=True);ps[0].resolve().unlink()
    monkeypatch.setattr(tape,'PANELD',str(root));monkeypatch.setattr(market_sessions,'CACHE',root.parents[1])
    assert tape._latest_panel()==str(ps[-1])
    assert market_sessions.price_source('US')==ps[-1]
    assert bf._consumer_panel(bf.BackfillPaths(root.parent,'NASDAQ'),'daily_features')==ps[-1]


def test_absent_mount_rejected_before_destination_creation(tmp_path):
    c={'mount':str(tmp_path/'unmounted'),'volume_uuid':'never','destination':str(tmp_path/'unmounted/archive')}
    with pytest.raises(OSError,match='unmounted'):ar.verify_volume(c)
    assert not Path(c['destination']).exists()


def test_copy_reserve_failure_preserves_originals(setup,monkeypatch):
    root,ps,alias,c=setup
    monkeypatch.setattr(ar.shutil,'disk_usage',lambda p:SimpleNamespace(free=1))
    with pytest.raises(OSError,match='storage_reserve'):ar.archive(root,c,apply=True)
    assert not ps[0].is_symlink() and not alias.is_symlink()


def test_restore_rejects_tampered_archive(setup):
    root,ps,alias,c=setup;ar.archive(root,c,apply=True)
    record=next(p for p in (root/'.refresh/panel_archive').glob('*.json') if not p.name.startswith('plan_'))
    ps[0].resolve().write_bytes(b'tampered')
    with pytest.raises(ValueError,match='archive_hash'):ar.restore(record)
    assert ps[0].is_symlink() and alias.is_symlink()


@pytest.mark.parametrize('enabled,dry',[('1','0'),('1','1'),('0','0')])
def test_real_daily_shell_orders_archive_before_refresh(enabled,dry,tmp_path):
    import subprocess
    script=Path('multi_agent/tools/run_daily_ops.sh').read_text()
    start=script.index('  if [[ "${AG_US_DAILY_PANEL_REFRESH_ENABLE:-1}"')
    end=script.index('  echo "[STEP] report_nasdaq_daily_edge_shadow"',start)
    harness='''set -euo pipefail
OPTIONAL_FAILURES=()
run_optional() { shift; "$@"; }
python3() { echo "CALLED $*"; }
'''+script[start:end]
    env={**os.environ,'AG_US_DAILY_PANEL_REFRESH_ENABLE':enabled,'DRY_RUN':dry}
    result=subprocess.run(['/bin/bash','-c',harness],env=env,text=True,capture_output=True,check=True)
    out=result.stdout
    if enabled=='0':assert 'CALLED' not in out
    else:
        assert out.index('CALLED multi_agent/tools/archive_us_daily_panels.py')<out.index('CALLED multi_agent/tools/backfill_us_daily_features.py')
        line=next(v for v in out.splitlines() if v.startswith('CALLED multi_agent/tools/archive_us_daily_panels.py'))
        assert ('--apply' in line)==(dry=='0')


def test_restore_resumes_after_one_alias_was_replaced(setup,monkeypatch):
    root,ps,alias,c=setup;ar.archive(root,c,apply=True)
    record=next(p for p in (root/'.refresh/panel_archive').glob('*.json') if not p.name.startswith('plan_'))
    replace=ar.os.replace;calls=[]
    def interrupt(a,b):
        if str(a).endswith('.restore-link'):
            calls.append(b)
            if len(calls)==2:raise OSError('restore_interrupted')
        return replace(a,b)
    monkeypatch.setattr(ar.os,'replace',interrupt)
    with pytest.raises(OSError,match='restore_interrupted'):ar.restore(record)
    monkeypatch.setattr(ar.os,'replace',replace)
    ar.restore(record)
    assert not ps[0].is_symlink() and not alias.is_symlink()
    assert ps[0].stat().st_ino==alias.stat().st_ino


def test_volume_uuid_mismatch_is_rejected(tmp_path,monkeypatch):
    import plistlib
    monkeypatch.setattr(Path,'is_mount',lambda p:True)
    monkeypatch.setattr(ar.subprocess,'check_output',lambda *a:plistlib.dumps({'VolumeUUID':'different'}))
    with pytest.raises(OSError,match='identity_mismatch'):
        ar.verify_volume({'mount':str(tmp_path),'volume_uuid':'expected','destination':str(tmp_path/'archive')})


def test_readonly_volume_parent_is_rejected_before_plan(tmp_path,monkeypatch):
    import plistlib
    monkeypatch.setattr(Path,'is_mount',lambda p:True)
    monkeypatch.setattr(ar.subprocess,'check_output',lambda *a:plistlib.dumps({'VolumeUUID':'expected'}))
    monkeypatch.setattr(ar.os,'access',lambda *a:False)
    with pytest.raises(OSError,match='not_writable'):
        ar.verify_volume({'mount':str(tmp_path),'volume_uuid':'expected','destination':str(tmp_path/'new/archive')})
    assert not (tmp_path/'new').exists()
