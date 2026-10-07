from copy import deepcopy
import numpy as np
import pandas as pd
import pytest

from research.run_lowliq_touch10_reconstruction import publish, noise, replay_record


def test_create_only_artifact_is_repeat_safe_and_rejects_mutation(tmp_path):
    p=tmp_path/'artifact'
    publish(p,b'first')
    publish(p,b'first')
    with pytest.raises(ValueError,match='immutable'):
        publish(p,b'second')
    assert p.read_bytes()==b'first'
    assert list(tmp_path.iterdir())==[p]


def test_noise_is_reproducible_and_independent_across_time_and_seed():
    a=noise((20,35),0,'train-2026-06-30')
    np.testing.assert_array_equal(a,noise((20,35),0,'train-2026-06-30'))
    assert not np.array_equal(a,noise((20,35),0,'predict-2026-07-01'))
    assert not np.array_equal(a,noise((20,35),1,'train-2026-06-30'))


def test_resume_verifies_actual_selected_codes_instead_of_trusting_receipt():
    day=pd.Timestamp('2026-07-01')
    frame=pd.DataFrame({'date':[day]*3,'code':['1','2','3'],'market':['KOSPI']*3,'liq':[1e9]*3,'real_0':[.9,.8,.7]})
    picks=[{'code':str(i),'market':'KOSPI','liq':1e9,'score':score} for i,score in zip([1,2,3],[.9,.8,.7])]
    receipt={'model_hashes':{'real_0':'hash'},'publication_allowed':False,'input_max_date':'2026-07-01',
             'date':'2026-07-01','kind':'retrospective_reconstruction','universe_rows':3,
             'variants':{'real_0':{'source_picks':picks,'picks':picks}}}
    prior={'real_0':{}}
    replay_record(receipt,frame,[day],prior,{'real_0':'hash'})
    assert prior['real_0']['2026-07-01']
    damaged=deepcopy(receipt)
    damaged['variants']['real_0']['picks']=[]
    with pytest.raises(ValueError,match='cadence_or_selection'):
        replay_record(damaged,frame,[day],{'real_0':{}},{'real_0':'hash'})
