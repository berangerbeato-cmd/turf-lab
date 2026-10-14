"""Separate tree challenger; never changes frozen logit inference."""
import math
import random
from collections import defaultdict
from statistics import mean
from turf_lab.pilot import active


def matrix(races, training=False):
    import numpy as np
    import xgboost as xgb
    rows, labels, weights = [], [], []
    for race in races:
        runners=active(race)
        if len(runners)<2 or len({r['number'] for r in race['runners']}) != len(race['runners']):
            raise ValueError('Invalid race field')
        if training and sum(r['won'] for r in runners)!=1:
            raise ValueError('Exactly one winner required')
        for r in runners:
            values=r['features']
            if len(values)!=38 or any(v is not None and (not isinstance(v,(int,float)) or not math.isfinite(v)) for v in values):
                raise ValueError('Expected 38 finite-or-missing V6 features')
            rows.append([np.nan if v is None else v for v in values])
            if training:
                labels.append(float(r['won']))
                weights.append(1/len(runners))
    if not rows:
        raise ValueError('Empty race list')
    return xgb.DMatrix(np.asarray(rows,dtype=np.float32),label=labels if training else None,
                       weight=weights if training else None,missing=np.nan,nthread=1)


def from_margins(race,margins):
    runners=active(race)
    if len(runners)!=len(margins) or not runners or any(not math.isfinite(float(v)) for v in margins):
        raise ValueError('Invalid margin vector')
    maximum=max(margins)
    exps=[math.exp(float(v)-float(maximum)) for v in margins]
    total=sum(exps)
    result={r['number']:v/total for r,v in zip(runners,exps)}
    result.update({r['number']:0.0 for r in race['runners'] if r['non_runner']})
    return result


def fit(races,protocol):
    import xgboost as xgb
    if xgb.__version__!=protocol['xgboost_version']:
        raise ValueError('XGBoost version differs from protocol')
    return xgb.train(protocol['params'],matrix(races,training=True),num_boost_round=protocol['num_boost_round'])


def predict(races,model):
    margins=model.predict(matrix(races),output_margin=True)
    offset=0
    result=[]
    for race in races:
        count=len(active(race))
        result.append(from_margins(race,margins[offset:offset+count]))
        offset+=count
    if offset!=len(margins):
        raise ValueError('Prediction grouping mismatch')
    return result


def metrics(races,predictions):
    if len(races)!=len(predictions) or not races:
        raise ValueError('Prediction count mismatch')
    losses,briers,hits=[],[],[]
    bins=[{'count':0,'sum_p':0.,'wins':0} for _ in range(10)]
    for race,p in zip(races,predictions):
        runners=active(race)
        winner=[r for r in runners if r['won']]
        if len(winner)!=1 or set(p)!={r['number'] for r in race['runners']}:
            raise ValueError('Invalid winner or probability field')
        if any(not math.isfinite(v) or not 0<=v<=1 for v in p.values()) or abs(sum(p.values())-1)>1e-8:
            raise ValueError('Invalid probability distribution')
        if any(p[r['number']]!=0 for r in race['runners'] if r['non_runner']):
            raise ValueError('Nonrunner probability must be zero')
        losses.append(-math.log(max(1e-15,p[winner[0]['number']])))
        briers.append(sum((p[r['number']]-r['won'])**2 for r in runners))
        hits.append(min(runners,key=lambda r:(-p[r['number']],r['number']))['won'])
        for r in runners:
            value=p[r['number']]
            b=bins[min(9,int(value*10))]
            b['count']+=1;b['sum_p']+=value;b['wins']+=r['won']
    return {'races':len(races),'log_loss':mean(losses),'brier_multiclass':mean(briers),'top1_accuracy':mean(hits),
        'calibration':[{'bin':[i/10,(i+1)/10],'count':b['count'],'mean_probability':b['sum_p']/b['count'],
            'win_frequency':b['wins']/b['count']} for i,b in enumerate(bins) if b['count']]}


def paired(races,baseline,challenger):
    by_day=defaultdict(list)
    if len(races)!=len(baseline) or len(races)!=len(challenger):
        raise ValueError('Paired count mismatch')
    for race,a,b in zip(races,baseline,challenger):
        winner=next(r['number'] for r in active(race) if r['won'])
        by_day[race['date']].append(-math.log(max(1e-15,b[winner]))+math.log(max(1e-15,a[winner])))
    days=sorted(by_day);rng=random.Random(20261013);estimates=[]
    for _ in range(1000):
        values=[x for d in rng.choices(days,k=len(days)) for x in by_day[d]]
        estimates.append(mean(values))
    estimates.sort()
    return {'delta_log_loss':mean(x for values in by_day.values() for x in values),
        'day_bootstrap_95_percent':[estimates[24],estimates[974]],'days':len(days),
        'interpretation':'Exploratory reused validation only; not an independent test.'}
