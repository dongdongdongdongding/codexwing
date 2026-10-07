"""Capture a fixed corporate-action document cohort; never infer price corrections."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import digest
from research.run_lowliq_touch10_reconstruction import save_json

HOST = 'https://kind.krx.co.kr'
KEYWORDS = ('추가상장','변경상장','권리락','감자','주식분할','주식병합','무상증자',
            '유상증자','분할','합병','주식교환','배당','전환청구','신주인수권','증권발행','증권 발행')


def utc():
    return datetime.now(timezone.utc).isoformat()


def parse_search(body):
    soup = BeautifulSoup(body, 'html.parser')
    total = re.search(r'전체\s*([\d,]+)\s*건', soup.get_text(' ', strip=True))
    if total is None:
        raise ValueError('missing_search_total')
    records = []
    for link in soup.select('a[onclick]'):
        match = re.search(r"openDisclsViewer\('([0-9]+)'", link['onclick'])
        if not match:
            continue
        row = link.find_parent('tr')
        cells = row.find_all('td', recursive=False) if row else []
        if len(cells) < 4:
            raise ValueError('malformed_search_row')
        title = link.get('title') or link.get_text(' ', strip=True)
        records.append({'acptno':match.group(1), 'title':title,
                        'published_at':cells[1].get_text(' ', strip=True),
                        'company':cells[2].get_text(' ', strip=True),
                        'selected':any(word in title for word in KEYWORDS)})
    if len({r['acptno'] for r in records}) != len(records):
        raise ValueError('duplicate_disclosures_in_page')
    count = int(total.group(1).replace(',', ''))
    if (count == 0 and records) or (count > 0 and not records):
        raise ValueError('search_total_row_disagreement')
    return count, records


def document_numbers(body):
    soup = BeautifulSoup(body, 'html.parser')
    numbers = list(dict.fromkeys(o.get('value','').split('|')[0]
        for o in soup.select('select#mainDoc option') if o.get('value')))
    if not numbers or any(not n.isdigit() for n in numbers):
        raise ValueError('missing_or_invalid_document_numbers')
    return numbers


def body_paths(body):
    paths = re.findall(rb'(?:https?://kind.krx.co.kr)?(/external/[^\s\"\x27<>]+\.htm)', body)
    result = list(dict.fromkeys(p.decode() for p in paths))
    if not result:
        raise ValueError('unresolved_document_body')
    return result


class Capture:
    def __init__(self, root, session, budget):
        self.root = root; self.session = session
        self.deadline = time.monotonic()+budget
        self.requests = 0
        (root/'captures').mkdir(parents=True, exist_ok=True)

    def verify(self, key):
        path = self.root/'captures'/key
        receipt = json.loads(path.with_suffix('.json').read_text())
        if digest(path.with_suffix('.html')) != receipt['sha256'] or digest(path.with_suffix('.txt')) != receipt['text_sha256']:
            raise ValueError('changed_capture:' + key)
        return receipt

    def fetch(self, key, url, *, params=None, data=None):
        if urlparse(url).hostname != 'kind.krx.co.kr':
            raise ValueError('unexpected_capture_host')
        path = self.root/'captures'/key
        request = {'url':url, 'params':params, 'data':data, 'method':'POST' if data is not None else 'GET'}
        if path.with_suffix('.json').exists():
            receipt = self.verify(key)
            if receipt['request'] != request:
                raise ValueError('changed_capture_request:' + key)
            if receipt['status'] != 200 or receipt['bytes'] == 0:
                raise ValueError('previous_capture_failed:' + key)
            return path.with_suffix('.html').read_bytes()
        if path.with_suffix('.html').exists() or path.with_suffix('.txt').exists():
            raise ValueError('orphaned_capture:' + key)
        if time.monotonic() >= self.deadline:
            raise TimeoutError('capture_budget_exhausted')
        start = utc(); self.requests += 1
        response = (self.session.post(url, data=data, timeout=15) if data is not None
                    else self.session.get(url, params=params, timeout=15))
        body = response.content
        text = BeautifulSoup(body, 'html.parser').get_text(' ', strip=True)
        path.with_suffix('.html').write_bytes(body)
        path.with_suffix('.txt').write_text(text, encoding='utf-8')
        save_json(path.with_suffix('.json'), {'request':request, 'resolved_url':response.url,
            'requested_at':start, 'received_at':utc(), 'status':response.status_code,
            'bytes':len(body), 'sha256':hashlib.sha256(body).hexdigest(),
            'text_sha256':hashlib.sha256(text.encode()).hexdigest()})
        response.raise_for_status()
        if not body:
            raise ValueError('empty_response:' + key)
        return body


def capture_code(capture, target, begin, end):
    code = target['code']; records = []; total = None
    for page in range(1, 101):
        params = {'method':'searchDetailsSub','currentPageSize':'100','pageIndex':str(page),
            'orderMode':'0','orderStat':'D','forward':'details_sub','repIsuSrtCd':'A'+code,
            'searchCorpName':target['name'],'fromDate':begin,'toDate':end,'lastReport':'T'}
        body = capture.fetch(code+'_search_'+str(page), HOST+'/disclosure/details.do', data=params)
        count, incoming = parse_search(body)
        if total is not None and count != total:
            raise ValueError('search_total_changed_during_pagination')
        total = count; records.extend(incoming)
        if len({r['acptno'] for r in records}) != len(records) or len(records) > total:
            raise ValueError('duplicate_or_excess_disclosures_across_pages')
        if len(records) == total:
            break
    if len(records) != total:
        raise ValueError('incomplete_search_pagination')
    documents = []; errors = []
    for record in records:
        if not record['selected']:
            continue
        stem = code+'_'+record['acptno']
        try:
            viewer = capture.fetch(stem+'_viewer', HOST+'/common/disclsviewer.do',
                params={'method':'search','acptno':record['acptno']})
            numbers = document_numbers(viewer); bodies = []
            for number in numbers:
                prefix = stem+'_'+number
                route = capture.fetch(prefix+'_routing', HOST+'/common/disclsviewer.do',
                    params={'method':'searchContents','docNo':number})
                for i, path in enumerate(body_paths(route)):
                    key = prefix+'_body_'+str(i)
                    capture.fetch(key, HOST+path)
                    bodies.append(key)
            documents.append({**record,'document_numbers':numbers,'body_keys':bodies})
        except TimeoutError:
            raise
        except Exception as exc:
            errors.append({'acptno':record['acptno'],'error_type':type(exc).__name__,'reason':str(exc)[:250]})
    return {'code':code,'name':target['name'],'status':'partial' if errors else ('empty_search' if total==0 else 'complete'),
        'search_pages':page,'total_disclosures':total,'records':records,'documents':documents,
        'selected_count':sum(r['selected'] for r in records),'document_errors':errors}


def write_checkpoint(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    os.replace(temporary, path)


def run(root, budget):
    audit = root/'runtime_state/audit'
    original = audit/'lowliq_corporate_actions_20261007/trace_plan_v2.json'
    trace = json.loads(original.read_text())
    if len(trace['codes']) != 65 or len(set(trace['codes'])) != 65:
        raise ValueError('changed_original_cohort')
    price_plan_path = audit/'lowliq_krx_comparison_20261007/plan.json'
    price_plan = json.loads(price_plan_path.read_text())
    covered = {'005440','008830','291810','270520','071950'}
    codes = sorted(set(trace['codes'])-covered)
    if len(codes) != 60:
        raise ValueError('unexpected_fixed_cohort')
    cohort = []
    for code in codes:
        response = audit/'lowliq_krx_source_20261007/responses'/f'{code}_nominal.json'
        if digest(response) != price_plan['response_sha256'][code+'_nominal']:
            raise ValueError('changed_name_source')
        data = json.loads(response.read_text())
        cohort.append({'code':code,'name':data['payload']['output1']['hts_kor_isnm'],
                       'name_source_sha256':digest(response)})
    out = audit/'kr_remaining_action_documents_20261007'; out.mkdir(exist_ok=True)
    with (out/'capture.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = {'cohort':cohort,'begin':'2026-06-01','end':'2026-10-07',
                'trace_plan_sha256':digest(original),'implementation_sha256':digest(Path(__file__)),
                'price_comparison_plan_sha256':digest(price_plan_path),
                'keywords':KEYWORDS,'source_certified':False,'scope':'Current observed official disclosures only. No historical availability or economic certification.'}
        save_json(out/'plan.json', plan)
        session = requests.Session()
        session.headers.update({'User-Agent':'Mozilla/5.0','Referer':HOST+'/disclosure/details.do?method=searchDetailsMain','X-Requested-With':'XMLHttpRequest'})
        capture = Capture(out, session, budget)
        for receipt in sorted((out/'captures').glob('*.json')):
            capture.verify(receipt.stem)
        capture.fetch('search_main', HOST+'/disclosure/details.do', params={'method':'searchDetailsMain'})
        results = []
        summary = {'target':60,'visited':0,'requests_this_run':capture.requests,
            'statuses':{},'results':results,'source_certified':False,'strategy_outcomes_computed':False}
        for target in cohort:
            dest = out/(target['code']+'_result.json')
            if dest.exists():
                result = json.loads(dest.read_text())
            else:
                try:
                    result = capture_code(capture, target, plan['begin'], plan['end'])
                except TimeoutError:
                    break
                except Exception as exc:
                    result = {'code':target['code'],'name':target['name'],'status':'failed',
                              'error_type':type(exc).__name__,'reason':str(exc)[:250]}
                save_json(dest, result)
            results.append(result)
            summary = {'target':60,'visited':len(results),'requests_this_run':capture.requests,
                'statuses':{s:sum(r['status']==s for r in results) for s in sorted({r['status'] for r in results})},
                'results':results,'source_certified':False,'strategy_outcomes_computed':False}
            write_checkpoint(out/'checkpoint.json',summary)
            print(json.dumps({'code':target['code'],'status':result['status'],
                'disclosures':result.get('total_disclosures'),'selected':result.get('selected_count'),
                'bodies':sum(len(d['body_keys']) for d in result.get('documents',[])),
                'requests':capture.requests}),flush=True)
        summary['terminal_at']=utc()
        summary['requests_this_run']=capture.requests
        summary['status']='captured' if len(results)==60 and all(r['status']=='complete' for r in results) else 'partial'
        write_checkpoint(out/'result.json',summary)
        print(json.dumps({k:v for k,v in summary.items() if k!='results'}),flush=True)
        return summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--budget',type=float,default=1200)
    args=parser.parse_args();run(args.root,args.budget)
