import json
from types import SimpleNamespace

import pytest

from research.capture_kr_action_documents import Capture, parse_search, capture_code, document_numbers, body_paths


def page(records,total):
    rows=''.join("<tr><td>1</td><td>2026-09-01 12:00</td><td>Company</td><td><a onclick=\"openDisclsViewer('%s','')\" title=\"%s\">%s</a></td></tr>" % (code,title,title) for code,title in records)
    return ('<table>'+rows+'</table>전체 '+str(total)+' 건 : 1 /1').encode()


def test_search_retains_all_records_and_selects_by_frozen_document_types():
    total,rows=parse_search(page([('20260901000001','추가상장'),('20260901000002','사업보고서')],2))
    assert total==2 and len(rows)==2
    assert [r['selected'] for r in rows]==[True,False]
    assert rows[0]['published_at']=='2026-09-01 12:00'
    assert parse_search(page([],0))==(0,[])


@pytest.mark.parametrize('body',[b'',b'<html>error</html>',page([],1),page([('1','추가상장'),('1','추가상장')],2)])
def test_invalid_search_cannot_claim_complete(body):
    with pytest.raises(ValueError):parse_search(body)


def test_official_viewer_and_routing_require_resolvable_documents():
    assert document_numbers(b'<select id="mainDoc"><option value=""></option><option value="20260001|Y"></option></select>')==['20260001']
    assert body_paths(b"setPath('', 'https://kind.krx.co.kr/external/2026/a.htm', '/external/2026/a.htm')")==['/external/2026/a.htm']
    with pytest.raises(ValueError):body_paths(b'no body')
    with pytest.raises(ValueError):document_numbers(b'<html>error</html>')


def test_cached_capture_has_no_network_and_rejects_tampering(tmp_path):
    calls=[]
    def get(url,**kw):
        calls.append(url)
        return SimpleNamespace(content=b'<html>official</html>',status_code=200,url=url,raise_for_status=lambda:None)
    capture=Capture(tmp_path,SimpleNamespace(get=get),100)
    body=capture.fetch('one','https://kind.krx.co.kr/test',params={'a':'b'})
    assert capture.fetch('one','https://kind.krx.co.kr/test',params={'a':'b'})==body
    assert len(calls)==1
    with pytest.raises(ValueError,match='changed_capture_request'):
        capture.fetch('one','https://kind.krx.co.kr/test',params={'a':'different'})
    (tmp_path/'captures/one.html').write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed_capture'):
        capture.fetch('one','https://kind.krx.co.kr/test',params={'a':'b'})


def test_total_change_across_pages_rejected():
    class Fake:
        def fetch(self,key,*a,**kw):return page([('1','사업보고서')],2) if key.endswith('_1') else page([('2','사업보고서')],3)
    with pytest.raises(ValueError,match='total_changed'):
        capture_code(Fake(),{'code':'A','name':'company'},'2026-06-01','2026-10-07')


def test_duplicate_across_pages_rejected():
    class Fake:
        def fetch(self,*a,**kw):return page([('1','사업보고서')],2)
    with pytest.raises(ValueError,match='duplicate_or_excess'):
        capture_code(Fake(),{'code':'A','name':'company'},'2026-06-01','2026-10-07')


def test_budget_exhaustion_inside_document_is_resumable_not_terminal_failure():
    class Fake:
        def fetch(self,key,*a,**kw):
            if '_search_' in key:return page([('1','추가상장')],1)
            raise TimeoutError('capture_budget_exhausted')
    with pytest.raises(TimeoutError):capture_code(Fake(),{'code':'A','name':'company'},'2026-06-01','2026-10-07')


def test_supplement_captures_every_revision_and_body_without_network():
    from research.capture_kr_action_document_supplement import capture_document
    calls=[]
    class Fake:
        def fetch(self,key,url,**kw):
            calls.append((key,url,kw))
            if key.endswith('_viewer'):
                return b'<select id="mainDoc"><option value="11|Y"></option><option value="12|Y"></option></select>'
            if key.endswith('_routing'):
                return b"'/external/first.htm' '/external/second.htm'"
            return b'<html>body</html>'
    result=capture_document(Fake(),'000880',{'acptno':'20260820000527','title':'변경상장'})
    assert result['query_code']=='000880' and result['document_numbers']==['11','12']
    assert result['body_keys']==['000880_20260820000527_'+n+'_body_'+str(i) for n in ['11','12'] for i in range(2)]
    assert len(calls)==7


def test_supplement_missing_body_propagates_failure():
    from research.capture_kr_action_document_supplement import capture_document
    class Fake:
        def fetch(self,key,url,**kw):
            if key.endswith('_viewer'):return b'<select id="mainDoc"><option value="11|Y"></option></select>'
            return b'<html>error page</html>'
    with pytest.raises(ValueError,match='unresolved_document_body'):
        capture_document(Fake(),'000880',{'acptno':'20260820000527'})
