import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from modules import kis_openapi as kis

ROOT = Path(__file__).resolve().parents[1]


def configure(tmp_path, monkeypatch, spacing="0.02"):
    path = tmp_path / "shared/rate.json"
    monkeypatch.setenv("KIS_LIVE_RATE_STATE_PATH", str(path))
    monkeypatch.setenv("KIS_LIVE_CALL_SLEEP_SEC", spacing)
    return path


def test_independent_processes_pace_actual_request_dispatch(tmp_path, monkeypatch):
    path = configure(tmp_path, monkeypatch, "0.06")
    script = '''
import json,sys,time
from pathlib import Path
from modules import kis_openapi as k
base=Path(sys.argv[1]);number=sys.argv[2]
calls=[]
class Response:
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self):return b"{}"
def open_url(*args,**kwargs):
 calls.append(time.clock_gettime(time.CLOCK_MONOTONIC));return Response()
k.urllib.request.urlopen=open_url
client=k.KISOpenAPIClient(config=k.KISConfig(app_key="test",app_secret="test",live_network_allowed=True))
(base/(number+".ready")).write_text("ready")
deadline=time.monotonic()+15
while not (base/"go").exists():
 if time.monotonic()>deadline:raise RuntimeError("start barrier expired")
 time.sleep(.005)
for _ in range(3):client._raw_request("GET","https://example.invalid/",{},None)
print(json.dumps(calls))
'''
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    children = []
    for i in range(4):
        children.append(subprocess.Popen([sys.executable, "-c", script, str(tmp_path), str(i)],
                                         cwd=tmp_path, env=env, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True))
        # macOS Python 3.9 monotonic() has a process-local origin. Simultaneous
        # launches and local timestamps can conceal a broken shared-clock design.
        if i == 0:
            time.sleep(.4)
    try:
        deadline = time.monotonic() + 10
        while len(list(tmp_path.glob("*.ready"))) < 4 and time.monotonic() < deadline:
            for child in children:
                if child.poll() is not None:
                    raise AssertionError(child.communicate()[1])
            time.sleep(.01)
        assert len(list(tmp_path.glob("*.ready"))) == 4
        (tmp_path / "go").touch()
        calls = []
        for child in children:
            stdout, stderr = child.communicate(timeout=10)
            assert child.returncode == 0, stderr
            calls.extend(json.loads(stdout))
        calls.sort()
        assert len(calls) == 12
        # Timing tolerance for scheduling between reservation and mock urlopen.
        assert min(b-a for a, b in zip(calls, calls[1:])) >= .045
        assert calls[-1]-calls[0] >= .64
        state = json.loads(path.read_text())
        assert set(state) == {"clock", "monotonic", "spacing_sec"}
        assert state["clock"] == "CLOCK_MONOTONIC"
        assert path.stat().st_mode & 0o777 == 0o600
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)


@pytest.mark.parametrize("raw", ["", "{broken", '{"monotonic":0.1,"spacing_sec":0.02}',
    '{"clock":"CLOCK_MONOTONIC","monotonic":1e99,"spacing_sec":0.02}',
    '{"clock":"CLOCK_MONOTONIC","monotonic":NaN,"spacing_sec":0.02}'])
def test_uncertain_state_waits_full_interval_and_recovers(tmp_path, monkeypatch, raw):
    path = configure(tmp_path, monkeypatch)
    path.parent.mkdir();path.write_text(raw)
    start = time.monotonic();kis._live_request_throttle()
    assert time.monotonic()-start >= .018
    assert json.loads(path.read_text())["spacing_sec"] == .02


def test_crashed_holder_releases_lock_and_truncated_state_recovers(tmp_path, monkeypatch):
    path = configure(tmp_path, monkeypatch)
    path.parent.mkdir()
    script = 'import fcntl,os,sys;f=open(sys.argv[1],"w");fcntl.flock(f,fcntl.LOCK_EX);f.write("{");f.flush();os._exit(3)'
    result = subprocess.run([sys.executable, "-c", script, str(path)], timeout=5)
    assert result.returncode == 3
    start = time.monotonic();kis._live_request_throttle()
    assert .018 <= time.monotonic()-start < 1


def test_shared_file_keeps_inode_and_respects_previous_larger_spacing(tmp_path, monkeypatch):
    path = configure(tmp_path, monkeypatch, ".04")
    kis._live_request_throttle();inode = path.stat().st_ino
    monkeypatch.setenv("KIS_LIVE_CALL_SLEEP_SEC", ".001")
    start=time.monotonic();kis._live_request_throttle()
    assert time.monotonic()-start >= .035
    assert path.stat().st_ino == inode


def test_bad_storage_cannot_bypass_pacing_and_reach_network(tmp_path, monkeypatch):
    path = configure(tmp_path, monkeypatch)
    path.parent.write_text("not a directory")
    def forbidden(*a, **kw):
        raise AssertionError("network must not run when pacing state cannot be opened")
    monkeypatch.setattr(kis.urllib.request, "urlopen", forbidden)
    client = kis.KISOpenAPIClient(config=kis.KISConfig(app_key="test", app_secret="test", live_network_allowed=True))
    with pytest.raises(OSError):
        client._raw_request("GET", "https://example.invalid/", {}, None)


def test_explicit_disabled_spacing_preserved(tmp_path, monkeypatch):
    path = configure(tmp_path, monkeypatch, "0")
    kis._live_request_throttle()
    assert not path.exists()


@pytest.mark.parametrize("spacing", ["nan", "inf", "-inf"])
def test_nonfinite_spacing_is_not_silently_unthrottled(tmp_path, monkeypatch, spacing):
    configure(tmp_path, monkeypatch, spacing)
    with pytest.raises(ValueError, match="finite"):
        kis._live_request_throttle()
