import hashlib
import json

import pytest

from research.run_historical_reference_capture import completion_exit_code, main


def complete():
    return {'target_windows':2,'processed_windows':2,'unvisited_windows':0,'failure':None,
            'status':'ALL_WINDOWS_ATTEMPTED','statuses':{'complete':2},
            'results':[{'window':'a','status':'complete'},{'window':'b','status':'complete'}]}


def test_full_scope_only_success():
    assert completion_exit_code(complete())==0


@pytest.mark.parametrize('change',[
    {'status':'CAPTURE_FAILED','failure':{'error_type':'HTTPError'}},
    {'status':'BUDGET_EXHAUSTED','unvisited_windows':1},
    {'statuses':{'complete':1,'empty_search':1}},
    {'statuses':{'complete':1,'partial':1}},
    {'results':[{'window':'a','status':'complete'}]*2},
    {'results':[]},
])
def test_partial_or_inconsistent_receipt_never_success(change):
    r=complete();r.update(change);assert completion_exit_code(r)==2


def test_saved_failure_cli_needs_no_network(tmp_path,monkeypatch):
    r=complete();r['status']='CAPTURE_FAILED';r['failure']={'error_type':'HTTPError'}
    p=tmp_path/'receipt.json';p.write_text(json.dumps(r));sha=hashlib.sha256(p.read_bytes()).hexdigest()
    monkeypatch.setattr('research.run_historical_reference_capture.run',lambda *a:pytest.fail('must not collect'))
    assert main(['--receipt',str(p),'--receipt-sha256',sha])==2


def test_changed_saved_receipt_rejected(tmp_path):
    p=tmp_path/'receipt.json';p.write_text(json.dumps(complete()))
    with pytest.raises(SystemExit):main(['--receipt',str(p),'--receipt-sha256','0'*64])
