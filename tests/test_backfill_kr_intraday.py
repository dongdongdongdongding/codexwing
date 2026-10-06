from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import signal
import time

import pandas as pd
import pytest

from multi_agent.tools import backfill_kr_intraday as m

NOW = datetime(2026, 10, 7, 2, 30, tzinfo=m.KST)


def payload(day, hour):
    return {"output2": [{"stck_bsop_date": day, "stck_cntg_hour": hour,
                         "stck_oprc": "100", "stck_hgpr": "102", "stck_lwpr": "99",
                         "stck_prpr": "101", "cntg_vol": "10"}]}


class Clock:
    value = 0.
    def __call__(self):
        return self.value
    def sleep(self, seconds):
        self.value += seconds


class Client:
    def __init__(self, clock=None, failure=None, empty=False):
        self.calls = []
        self.clock = clock
        self.failure = failure
        self.empty = empty
    def daily_minute_bars(self, code, *, trade_date, input_hour, include_past):
        self.calls.append((code, trade_date, input_hour))
        if self.clock:
            self.clock.value += 1.
        if input_hour == self.failure:
            raise RuntimeError("provider failure must not leak credentials")
        return {} if self.empty else payload(trade_date, input_hour)


def run(out, client, schedule=None, budget=100, now=NOW, clock=None):
    clock = clock or Clock()
    return m.collect(schedule or {"20261006": ["000001"]}, out, client,
                     budget, 0, clock=clock, sleep=clock.sleep, now=now,
                     bounded_request=False, progress=lambda *a, **kw: None)


def test_latest_session_across_all_codes_before_history(tmp_path):
    client = Client()
    report = run(tmp_path, client, {"20261002": ["000001", "000002"], "20261006": ["000001", "000002"]})
    assert [(c, d) for c, d, h in client.calls[::4]] == [
        ("000001", "20261006"), ("000002", "20261006"), ("000001", "20261002"), ("000002", "20261002")]
    assert report["requested_all_slices"] == 4
    assert report["session_completeness"] == "NOT_ESTABLISHED"
    assert len(pd.read_parquet(tmp_path / "000001.parquet")) == 8
    client.calls.clear()
    report = run(tmp_path, client, {"20261002": ["000001", "000002"], "20261006": ["000001", "000002"]})
    assert not client.calls
    assert report["pairs_skipped"] == 4


def test_budget_check_inside_ticker_checkpoints_and_resumes(tmp_path):
    clock = Clock()
    client = Client(clock)
    report = run(tmp_path, client, budget=2, clock=clock)
    assert report["status"] == "BUDGET_EXHAUSTED"
    assert len(client.calls) == 2
    assert len(pd.read_parquet(tmp_path / "000001.parquet")) == 2
    second = Client()
    report = run(tmp_path, second)
    assert [c[2] for c in second.calls] == list(m.HOURS[2:])
    assert report["requested_all_slices"] == 1
    audit = Path(report["audit_path"])
    record = json.loads(next(audit.glob("*.json")).read_text())
    assert m.digest(Path(record["backup"])) == record["before_sha256"]
    assert m.digest(tmp_path / "000001.parquet") == record["after_sha256"]


def test_request_failure_partial_data_never_complete_and_retry_missing_slice(tmp_path):
    report = run(tmp_path, Client(failure="133000"))
    assert len(report["request_errors"]) == 1
    assert "provider failure" not in json.dumps(report)
    assert report["requested_all_slices"] == 0
    assert len(pd.read_parquet(tmp_path / "000001.parquet")) == 3
    client = Client()
    report = run(tmp_path, client)
    assert report["retry_deferred_pairs"] == 1 and not client.calls
    report = run(tmp_path, client, now=NOW+timedelta(days=1))
    assert [call[2] for call in client.calls] == ["133000"]
    assert report["requested_all_slices"] == 1


def test_empty_responses_do_not_certify_legacy_partial_day(tmp_path):
    frame = m.normalize_kis_minute_bars("000001", payload("20261006", "100000"))
    frame.to_parquet(tmp_path / "000001.parquet")
    report = run(tmp_path, Client(empty=True))
    assert report["requested_all_slices"] == 0 and report["empty_responses"] == 4
    state = json.loads((tmp_path / ".backfill/000001.json").read_text())
    assert state["days"]["20261006"]["successful_hours"] == []
    assert state["days"]["20261006"]["session_complete"] is None


def test_corrupt_existing_cache_preserved_and_no_requests(tmp_path):
    path = tmp_path / "000001.parquet"
    path.write_bytes(b"broken but must remain for repair")
    client = Client()
    report = run(tmp_path, client)
    assert report["storage_errors"]
    assert not client.calls
    assert path.read_bytes() == b"broken but must remain for repair"


def test_failed_temp_write_preserves_original_and_no_checkpoint(tmp_path, monkeypatch):
    frame = m.normalize_kis_minute_bars("000001", payload("20261002", "100000"))
    path = tmp_path / "000001.parquet"
    frame.to_parquet(path)
    original = path.read_bytes()
    def fail_write(self, path, *args, **kwargs):
        Path(path).write_bytes(b"interrupted")
        raise OSError("disk write failed")
    monkeypatch.setattr(pd.DataFrame, "to_parquet", fail_write)
    report = run(tmp_path, Client())
    assert report["storage_errors"]
    assert path.read_bytes() == original
    assert not (tmp_path / ".backfill/000001.json").exists()
    assert not list(tmp_path.glob(".backfill-*"))
    backup = next(Path(report["audit_path"]).glob("*.parquet"))
    assert backup.read_bytes() == original


def test_external_cache_write_invalidates_success_checkpoints(tmp_path):
    run(tmp_path, Client())
    path = tmp_path / "000001.parquet"
    pd.read_parquet(path).iloc[:1].to_parquet(path)
    client = Client()
    run(tmp_path, client)
    assert len(client.calls) == 4


def test_compare_and_set_does_not_clobber_new_writer(tmp_path, monkeypatch):
    path = tmp_path / "000001.parquet"
    original = pd.DataFrame({"x": [1]}, index=pd.to_datetime(["2026-10-01"]))
    original.to_parquet(path)
    sha = m.digest(path)
    old_write = pd.DataFrame.to_parquet
    def interference(self, target, *a, **kw):
        old_write(self, target, *a, **kw)
        path.write_bytes(b"external writer")
    monkeypatch.setattr(pd.DataFrame, "to_parquet", interference)
    with pytest.raises(ValueError, match="concurrently"):
        m.persist_bars(path, original, original.set_axis(pd.to_datetime(["2026-10-02"])), sha, tmp_path/"audit", "000001", "20261002")
    assert path.read_bytes() == b"external writer"


def test_target_pairs_preserve_old_listings_without_prelisting_or_future(tmp_path):
    panel = pd.DataFrame({"code": ["000001", "000002", "000002", "000003"],
                          "date": ["2025-11-01", "2026-10-06", "2026-10-07", "2026-10-08"]})
    assert m.targets(panel, NOW, 355) == {"20251101": ["000001"], "20261006": ["000002"]}
    assert m.targets(panel, NOW.replace(hour=16), 355)["20261007"] == ["000002"]


def test_legacy_process_detection_ignores_shell_text_and_self():
    text = "22 /bin/zsh -c 'python intraday_backfill.py'\n23 /usr/bin/python3 /a/intraday_backfill.py\n24 /usr/bin/python3 intraday_backfill.py\n25 /usr/bin/python3 unrelated.py"
    assert m.legacy_writers(Path("/a"), text) == [23, 24]


def test_network_call_deadline_interrupts_hang_and_restores_handler():
    before = signal.getsignal(signal.SIGALRM)
    start = time.monotonic()
    with pytest.raises(m.BudgetExpired):
        with m.request_deadline(.02):
            time.sleep(1)
    assert time.monotonic()-start < .8
    assert signal.getsignal(signal.SIGALRM) == before


def test_invalid_ohlc_is_not_written(tmp_path):
    class Invalid(Client):
        def daily_minute_bars(self, code, **kwargs):
            result = payload(kwargs["trade_date"], kwargs["input_hour"])
            result["output2"][0]["stck_hgpr"] = "50"
            return result
    report = run(tmp_path, Invalid())
    assert len(report["request_errors"]) == 4
    assert not (tmp_path/"000001.parquet").exists()


def test_wraparound_and_outside_hours_are_not_coverage():
    frame = pd.DataFrame({"Open": [1]*3, "High": [1]*3, "Low": [1]*3, "Close": [1]*3, "Volume": [1]*3},
                         index=pd.to_datetime(["2026-10-02 10:00", "2026-10-06 08:00", "2026-10-06 10:00"]))
    result = m.filter_bars(frame, "20261006")
    assert list(result.index) == [pd.Timestamp("2026-10-06 10:00")]


def test_existing_identical_bars_do_not_rewrite_or_backup_again(tmp_path):
    frame=m.normalize_kis_minute_bars('000001',payload('20261006','100000'))
    path=tmp_path/'000001.parquet';frame.to_parquet(path)
    before=path.read_bytes();stamp=path.stat().st_mtime_ns
    result=m.persist_bars(path,frame,frame,m.digest(path),tmp_path/'audit','000001','20261006')
    assert result.equals(frame)
    assert path.read_bytes()==before and path.stat().st_mtime_ns==stamp
    assert not (tmp_path/'audit').exists()


def test_low_disk_space_stops_before_network_and_preserves_cache(tmp_path,monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(m.shutil,'disk_usage',lambda _:SimpleNamespace(free=1))
    client=Client()
    result=run(tmp_path,client)
    assert result['status']=='STORAGE_BUDGET_EXHAUSTED'
    assert not client.calls
    assert not list(tmp_path.glob('*.parquet'))


def test_disk_budget_includes_backup_and_temporary_file(tmp_path,monkeypatch):
    from types import SimpleNamespace
    frame=m.normalize_kis_minute_bars('000001',payload('20261006','100000'))
    path=tmp_path/'000001.parquet';frame.to_parquet(path)
    before=path.read_bytes()
    added=m.normalize_kis_minute_bars('000001',payload('20261006','113000'))
    monkeypatch.setattr(m.shutil,'disk_usage',lambda _:SimpleNamespace(free=10*1024**3+1))
    with pytest.raises(m.StorageBudgetExceeded):
        m.persist_bars(path,frame,added,m.digest(path),tmp_path/'audit','000001','20261006')
    assert path.read_bytes()==before and not (tmp_path/'audit').exists()
