from datetime import datetime
import json
import pandas as pd

from multi_agent.tools import backfill_kr_extended_intraday as ext
from multi_agent.tools import backfill_kr_intraday as regular


def test_extended_calendar_uses_observed_dates_and_waits_until_twenty(tmp_path):
    (tmp_path/'000001.parquet').touch()
    panel=pd.DataFrame({'code':['000001','000001','000002'],
                        'date':pd.to_datetime(['2026-10-06','2026-10-07','2026-10-07'])})
    now=datetime(2026,10,7,19,59,tzinfo=regular.KST)
    codes,schedule=ext.extended_schedule(panel,tmp_path,now,355)
    assert codes==['000001'] and schedule=={'20261006':['000001']}
    assert ext.extended_schedule(panel,tmp_path,now.replace(hour=20),355)[1]['20261007']==['000001']


def test_un_slices_include_afterhours_and_resume_under_budget(tmp_path):
    class Client:
        clock=0
        calls=[]
        def daily_minute_bars(self,code,**kwargs):
            assert kwargs['market_div']=='UN'
            self.calls.append(kwargs['input_hour']);self.clock+=1
            return {'output2':[{'stck_bsop_date':kwargs['trade_date'],
                'stck_cntg_hour':'195900' if kwargs['input_hour']=='200000' else kwargs['input_hour'],
                'stck_oprc':'100','stck_hgpr':'102','stck_lwpr':'99','stck_prpr':'101','cntg_vol':'10'}]}
    client=Client()
    def run(budget):
        return regular.collect({'20261006':['000001']},tmp_path,client,budget,0,
            now=datetime(2026,10,7,4,tzinfo=regular.KST),clock=lambda:client.clock,sleep=lambda _:None,
            bounded_request=False,progress=lambda *a,**k:None,hours=ext.HOURS,market_div='UN',
            session_start='08:00',session_end='20:00',universe='existing_extended_cache_codes')
    first=run(3);assert first['status']=='BUDGET_EXHAUSTED'
    assert client.calls==list(ext.HOURS[:3])
    second=run(20);assert client.calls==list(ext.HOURS)
    assert second['requested_all_slices']==1
    assert second['session_completeness']=='NOT_ESTABLISHED'
    frame=pd.read_parquet(tmp_path/'000001.parquet')
    assert str(frame.index.max())=='2026-10-06 19:59:00'
    assert len(frame)==6
    assert len(regular.filter_bars(frame,'20261006'))==3


def test_extended_legacy_writers_do_not_confuse_regular_collector():
    process='11 /usr/bin/python3 intraday_ext_update.py\n12 /usr/bin/python3 intraday_backfill.py\n13 /usr/bin/python3 build_intraday_ext.py'
    assert regular.legacy_writers(None,process,entrypoints=('intraday_ext_update.py','build_intraday_ext.py'))==[11,13]
    assert regular.legacy_writers(None,process)==[12]
