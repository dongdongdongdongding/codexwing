"""Fit and freeze the preregistered retrospective candidate, without test P&L.

Immutable research artifacts only. This runner cannot publish or replace a lane.
Score collection is resumable, source/code/model-pinned and budget bounded.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.audit_kr_adjustment_asof import adjustment_block, asof_adjustment, digest
from research.lowliq_touch10_core import FEATS, feature_frame, training_labels, rank_and_cap


def publish(path, content):
    """Atomic create-only publication; never replace an earlier observation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.'+path.name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            if path.read_bytes() != content:
                raise ValueError('immutable_artifact_changed:' + str(path))
    finally:
        os.unlink(temp)


def save_json(path, value):
    publish(path, (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())


def save_frame(path, frame):
    if path.exists():
        pd.testing.assert_frame_equal(pd.read_parquet(path), frame, check_exact=True)
        return
    import io
    stream = io.BytesIO()
    frame.to_parquet(stream, index=False)
    pd.testing.assert_frame_equal(pd.read_parquet(io.BytesIO(stream.getvalue())), frame, check_exact=True)
    publish(path, stream.getvalue())


def noise(shape, seed, phase):
    key = hashlib.sha256(f'lowliq-touch10:{seed}:{phase}'.encode()).digest()
    return np.random.default_rng(int.from_bytes(key[:8], 'big')).normal(size=shape).astype(np.float32)


def replay_record(record, frame, calendar, prior, hashes):
    """Recompute selection and cadence on resume; a receipt alone is not proof."""
    if record['model_hashes'] != hashes or record['publication_allowed'] is not False:
        raise ValueError('changed_score_receipt')
    if record['input_max_date'] != record['date'] or record['kind'] != 'retrospective_reconstruction':
        raise ValueError('invalid_reconstruction_identity')
    if len(frame) != record['universe_rows']:
        raise ValueError('changed_score_universe')
    for name in hashes:
        rebuilt = frame.assign(score=frame[name])
        original,picks = rank_and_cap(rebuilt,calendar,prior[name])
        columns = ['code','market','liq','score']
        expected = {'source_picks':original[columns].to_dict('records'), 'picks':picks[columns].to_dict('records')}
        if expected != record['variants'][name]:
            raise ValueError('changed_cadence_or_selection')
        prior[name][record['date']] = bool(len(picks))


def prepare(root):
    import lightgbm
    spec_path = ROOT/'research/prereg_lowliq_touch10_20261007.json'
    spec = json.loads(spec_path.read_text())
    assert spec['features'] == FEATS
    assert spec['contract']['horizon_sessions'] == 10 and spec['contract']['tp'] == .05
    assert spec['selection']['top_k_combined_markets'] == 3
    previous = root/'runtime_state/audit/kr_adjustment_asof_20261007/final'
    paths = {'panel':previous/'panel.parquet', 'fit_prices':previous/'asof_2026-06-30.parquet',
             'builder':previous/'builder.py.txt'}
    expected = {name:spec['source'][key] for name,key in
                [('panel','panel_sha256'),('fit_prices','fit_snapshot_sha256'),('builder','builder_sha256')]}
    for name,path in paths.items():
        if digest(path) != expected[name]:
            raise ValueError('changed_frozen_source:' + name)
    audit = root/'runtime_state/audit/lowliq_touch10_20261007'
    audit.mkdir(parents=True, exist_ok=True)
    files = ['research/run_lowliq_touch10_reconstruction.py', 'research/lowliq_touch10_core.py',
             'research/audit_kr_adjustment_asof.py', 'research/data/build_px_delisted_20261007.py.txt']
    manifest = {'spec_sha256':digest(spec_path), 'sources':expected,
                'code':{name:digest(ROOT/name) for name in files},
                'libraries':{'lightgbm':lightgbm.__version__, 'numpy':np.__version__, 'pandas':pd.__version__}}
    save_json(audit/'manifest.json', manifest)
    publish(audit/'prereg.json',spec_path.read_bytes())
    return spec, paths, audit, manifest


def training_data(spec, paths, audit):
    saved = audit/'training_receipt.json'
    if saved.exists():
        receipt = json.loads(saved.read_text())
        if digest(audit/'training.parquet') != receipt['training_sha256']:
            raise ValueError('training_artifact_changed')
        if digest(audit/'training_eligibility.parquet') != receipt['eligibility_sha256']:
            raise ValueError('training_eligibility_changed')
        return pd.read_parquet(audit/'training.parquet'), receipt
    raw = pd.read_parquet(paths['panel']).sort_values(['code','date']).reset_index(drop=True)
    raw = raw.loc[raw.date.le(spec['fit_cutoff'])].reset_index(drop=True)
    prices = pd.read_parquet(paths['fit_prices'])
    features = feature_frame(raw,prices,start=spec['train_signal_start'],progress=lambda x:print(x,flush=True))
    calendar = sorted(raw.date.unique())
    lookup = {code:group for code,group in features.groupby('code',sort=False)}
    records = []
    for code,indices in raw.groupby('code',sort=False).groups.items():
        if code not in lookup:
            continue
        b = prices.loc[indices, ['date','adj_open','adj_high','adj_low','adj_close']].copy()
        b['volume'] = raw.loc[indices,'volume'].to_numpy()
        labels = training_labels(b,calendar).set_index('date').loc[lookup[code].date].reset_index()
        labels['code'] = code
        records.append(labels)
    labels = pd.concat(records,ignore_index=True)
    whole = features.merge(labels,on=['code','date'],validate='one_to_one')
    mask = whole.status.eq('resolved') & whole.target.notna() & whole.label_available_date.le(spec['fit_cutoff'])
    training = whole.loc[mask].reset_index(drop=True)
    if len(training) < spec['model']['minimum_train_rows'] or training.target.nunique() != 2:
        raise ValueError('insufficient_training_outcomes')
    assert training.date.min() >= pd.Timestamp(spec['train_signal_start'])
    assert training.label_available_date.max() <= pd.Timestamp(spec['fit_cutoff'])
    save_frame(audit/'training_eligibility.parquet',whole[['code','date','target','label_available_date','status']])
    save_frame(audit/'training.parquet',training)
    receipt = {'rows':len(training),'eligible_rows':len(whole),'status_counts':dict(Counter(whole.status)),
               'target_counts':{str(int(k)):int(v) for k,v in training.target.value_counts().items()},
               'max_signal_date':str(training.date.max().date()),
               'max_label_available_date':str(training.label_available_date.max().date()),
               'training_sha256':digest(audit/'training.parquet'),
               'eligibility_sha256':digest(audit/'training_eligibility.parquet')}
    save_json(saved,receipt)
    print(json.dumps(receipt),flush=True)
    return training,receipt


def fit(spec, paths, audit):
    import lightgbm as lgb
    training,receipt = training_data(spec,paths,audit)
    x = training[FEATS].clip(-1e4,1e4).to_numpy(dtype=np.float32)
    y = training.target.to_numpy(dtype=int)
    params = {key:spec['model'][key] for key in ['n_estimators','learning_rate','num_leaves',
              'min_child_samples','subsample','subsample_freq','colsample_bytree','reg_lambda']}
    for kind in ['real','noise']:
        for seed in spec['model']['seeds']:
            name = f'{kind}_{seed}'
            path = audit/'models'/f'{name}.txt'
            record = audit/'models'/f'{name}.json'
            if record.exists():
                old = json.loads(record.read_text())
                assert digest(path) == old['model_sha256'] and old['training_sha256'] == receipt['training_sha256']
                continue
            model = lgb.LGBMClassifier(**params,random_state=seed,n_jobs=spec['model']['num_threads'],verbosity=-1)
            data = x if kind == 'real' else noise(x.shape,seed,'train-'+spec['fit_cutoff'])
            model.fit(data,y)
            publish(path,model.booster_.model_to_string().encode())
            save_json(record,{'kind':kind,'seed':seed,'model_sha256':digest(path),
                              'training_sha256':receipt['training_sha256'],'features':FEATS,'trees':model.booster_.num_trees(),
                              'created_at':datetime.now(timezone.utc).isoformat()})
            print('fitted',name,'rows',len(training),'trees',model.booster_.num_trees(),flush=True)
            del model,data
            gc.collect()


def score(spec, paths, audit, budget):
    import lightgbm as lgb
    start = time.monotonic()
    models,hashes = {},{}
    for kind in ['real','noise']:
        for seed in spec['model']['seeds']:
            name=f'{kind}_{seed}'
            path=audit/'models'/f'{name}.txt'
            record=json.loads((audit/'models'/f'{name}.json').read_text())
            assert digest(path)==record['model_sha256']
            models[name]=lgb.Booster(model_file=str(path))
            hashes[name]=record['model_sha256']
    source=pd.read_parquet(paths['panel']).sort_values(['code','date']).reset_index(drop=True)
    calendar=sorted(source.loc[source.date.between(spec['test_signal_start'],spec['test_signal_end']),'date'].unique())
    prior={name:{} for name in models}
    block=adjustment_block(paths['builder'])
    completed=0
    for date in calendar:
        day=str(pd.Timestamp(date).date())
        record=audit/'scores'/f'{day}.json'
        data_path=audit/'scores'/f'{day}.parquet'
        if record.exists():
            old=json.loads(record.read_text())
            assert old['date']==day and old['model_hashes']==hashes and digest(data_path)==old['universe_sha256']
            assert old['model_fit_cutoff']==spec['fit_cutoff']
            replay_record(old,pd.read_parquet(data_path),calendar,prior,hashes)
            completed+=1
            continue
        if time.monotonic()-start>=budget:
            print(json.dumps({'status':'SCORE_BUDGET_EXHAUSTED','completed':completed,'target_dates':len(calendar),'publication_allowed':False}),flush=True)
            return
        print('scoring date',day,flush=True)
        prices=asof_adjustment(source,day,block)
        raw=source.loc[source.date.le(day)].reset_index(drop=True)
        frame=feature_frame(raw,prices,only_date=day)
        x=frame[FEATS].clip(-1e4,1e4).to_numpy(dtype=np.float32)
        variants={}
        for name,model in models.items():
            kind,seed=name.split('_')
            data=x if kind=='real' else noise(x.shape,int(seed),'predict-'+day)
            frame['score']=model.predict(data,num_threads=spec['model']['num_threads']) if len(frame) else np.array([])
            frame[name]=frame.score
            original,picks=rank_and_cap(frame,calendar,prior[name])
            columns=['code','market','liq','score']
            variants[name]={'source_picks':original[columns].to_dict('records'),'picks':picks[columns].to_dict('records')}
            prior[name][day]=bool(len(picks))
        frame=frame.drop(columns=['score'])
        save_frame(data_path,frame)
        result={'date':day,'kind':'retrospective_reconstruction','input_max_date':str(raw.date.max().date()),
                'model_fit_cutoff':spec['fit_cutoff'],'universe_rows':len(frame),'universe_sha256':digest(data_path),
                'model_hashes':hashes,'variants':variants,'publication_allowed':False,
                'computed_at':datetime.now(timezone.utc).isoformat()}
        save_json(record,result)
        completed+=1
        print('frozen',day,'eligible',len(frame),'completed',completed,'of',len(calendar),flush=True)
        del prices,raw,frame,x,data,original,picks
        gc.collect()
    result={'status':'SCORES_FROZEN_AWAITING_FIXED_H10_WINDOW_AND_SOURCE_REVIEW','dates':completed,
            'test_signal_end':spec['test_signal_end'],'latest_frozen_price_date':str(source.date.max().date()),
            'test_outcomes_computed':False,'publication_allowed':False}
    save_json(audit/'scores_complete.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--phase',choices=['fit','score'],required=True)
    parser.add_argument('--budget',type=float,default=600)
    args=parser.parse_args()
    if not np.isfinite(args.budget) or args.budget<=0:
        parser.error('positive finite budget required')
    lock_path=args.root/'runtime_state/audit/lowliq_touch10_20261007.lock'
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        spec,paths,audit,manifest=prepare(args.root)
        fit(spec,paths,audit) if args.phase=='fit' else score(spec,paths,audit,args.budget)
