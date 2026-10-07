"""Independent rational-number check of ex-right price-basis evidence.

Intervals describe coefficients compatible with integer truncation. They do not
identify a provider's private implementation or estimate strategy performance.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fraction(value):
    return {'numerator':value.numerator, 'denominator':value.denominator}


def run(root):
    audit=root/'runtime_state/audit';out=audit/'kr_exrights_basis_20261007'
    plan=json.loads((out/'plan.json').read_text());result=json.loads((out/'result.json').read_text())
    saved_cells=json.loads((out/'comparison_cells.json').read_text())
    expected={(r['code'],r['date'],r['field']):r for r in saved_cells}
    assert len(expected)==len(saved_cells)==4420
    for key,h in plan['official_body_hashes'].items():
        p=audit/'kr_remaining_action_documents_20261007/captures'/key
        receipt=json.loads(p.with_suffix('.json').read_text())
        assert sha(p.with_suffix('.html'))==h==receipt['sha256']
        assert sha(p.with_suffix('.txt'))==receipt['text_sha256']
    codes=sorted({e['code'] for e in plan['events']});assert len(codes)==17
    compared=[e for e in result['event_checks'] if e['status']=='compared']
    assert len(compared)==16 and all(e['provider_matches_rounded_reference_percent'] for e in compared)
    # Known distinct capital-reduction listing boundary; no assumed factor.
    split='354200_20260708000562_20260708001349_body_0'
    body=audit/'kr_remaining_action_documents_20261007/captures'/split
    receipt=json.loads(body.with_suffix('.json').read_text())
    assert sha(body.with_suffix('.html'))==receipt['sha256']
    assert sha(body.with_suffix('.txt'))==receipt['text_sha256']
    text=body.with_suffix('.txt').read_text()
    assert all(s in text for s in ['A354200','감자(무상)','2026-07-13'])
    segments=[];checked=0;baseline_once=0;baseline_each=0
    for code in codes:
        payload={}
        for basis in ['nominal','adjusted']:
            path=audit/'lowliq_krx_source_20261007/responses'/f'{code}_{basis}.json'
            assert sha(path)==plan['provider_response_hashes'][code+'_'+basis]
            rows=json.loads(path.read_text())['payload']['output2']
            payload[basis]={r['stck_bsop_date']:r for r in rows}
            assert len(rows)==len(payload[basis])==65
        nominal=payload['nominal'];adjusted=payload['adjusted'];assert set(nominal)==set(adjusted)
        boundaries=sorted({e['date'].replace('-','') for e in plan['events'] if e['code']==code}|({'20260713'} if code=='354200' else set()))
        groups={}
        for dt in nominal:
            groups.setdefault(sum(dt>=when for when in boundaries),[]).append(dt)
        for _,dates in sorted(groups.items()):
            lower=Fraction(0);upper=None;cell_count=0
            for dt in sorted(dates):
                future=[r['prtt_rate'] for when,r in sorted(adjusted.items()) if when>dt and Fraction(r['prtt_rate'])!=0]
                for field,key in {'open':'stck_oprc','high':'stck_hgpr','low':'stck_lwpr','close':'stck_clpr'}.items():
                    n=int(nominal[dt][key]);a=int(adjusted[dt][key]);assert n>0
                    lower=max(lower,Fraction(a,n));u=Fraction(a+1,n);upper=u if upper is None else min(upper,u)
                    once=Fraction(n);each=Fraction(n)
                    for rate in future:
                        factor=1+Fraction(rate)/100;once*=factor;each=Fraction(int(each*factor))
                    record=expected[(code,dt,field)]
                    assert int(once)==int(record['projected_round_once']) and int(each)==int(record['projected_round_each'])
                    assert n==int(record['nominal']) and a==int(record['provider_adjusted'])
                    assert (int(once)==a)==record['once_exact'] and (int(each)==a)==record['each_exact']
                    baseline_once+=int(once)==a;baseline_each+=int(each)==a;checked+=1;cell_count+=1
            assert lower<upper
            official=Fraction(1)
            for event in compared:
                if event['code']==code and event['date'].replace('-','')>min(dates):
                    prior=nominal[event['prior_date']]
                    assert prior['stck_clpr']==event['prior_nominal_close']
                    official*=Fraction(int(event['reference_price']),int(prior['stck_clpr']))
            known_missing_split=code=='354200' and max(dates)<'20260713'
            closure=lower<=official<=upper
            if not known_missing_split:
                assert closure
            segments.append({'code':code,'start':min(dates),'end':max(dates),'rows':len(dates),'cells':cell_count,
                             'compatible_truncation_interval_lower_inclusive':fraction(lower),
                             'compatible_truncation_interval_upper_exclusive':fraction(upper),
                             'official_exrights_coefficient':fraction(official),
                             'official_coefficient_in_closed_interval':closure,
                             'official_coefficient_at_excluded_upper_boundary':official==upper,
                             'earlier_capital_reduction_factor_not_applied':known_missing_split})
    assert checked==4420 and baseline_once==4142 and baseline_each==4130
    value={'status':'PASS','independent_cells_checked':checked,'baseline_round_once_exact':baseline_once,
           'baseline_round_each_exact':baseline_each,'segments':segments,
           'official_coefficient_in_closed_interval_cells':sum(s['cells'] for s in segments if s['official_coefficient_in_closed_interval']),
           'known_earlier_capital_reduction_cells':sum(s['cells'] for s in segments if s['earlier_capital_reduction_factor_not_applied']),
           'exact_integer_provider_implementation_claimed':False,'source_certified':False,
           'plan_sha256':sha(out/'plan.json'),'result_sha256':sha(out/'result.json'),
           'verification_code_sha256':sha(Path(__file__)),'capital_reduction_body_sha256':receipt['sha256']}
    path=out/'independent_intervals.json';encoded=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    if path.exists():
        assert path.read_text()==encoded
    else:
        with path.open('x') as stream:stream.write(encoded)
    print(json.dumps({k:v for k,v in value.items() if k!='segments'}),flush=True)
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    run(parser.parse_args().root)
