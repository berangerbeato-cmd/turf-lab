"""Race-grouped tree ranking with chronological temperature selection."""
import math
from statistics import mean
from turf_lab.pilot import active
from turf_lab.xgb_model import matrix, from_margins


def training_matrix(races):
    import numpy as np
    data=matrix(races)
    groups=[];labels=[]
    for race in races:
        runners=active(race)
        if sum(r['won'] for r in runners)!=1:
            raise ValueError('One winner per race required')
        groups.append(len(runners))
        labels.extend(float(r['won']) for r in runners)
    data.set_label(labels)
    data.set_group(groups)
    data.set_weight(np.ones(len(groups)))
    return data


def fit(races,choice,protocol):
    import xgboost as xgb
    if xgb.__version__!=protocol['xgboost_version']:
        raise ValueError('Wrong XGBoost version')
    params=dict(protocol['params'],objective=choice['objective'],max_depth=choice['max_depth'])
    return xgb.train(params,training_matrix(races),num_boost_round=protocol['num_boost_round'])


def scores(races,model):
    raw=model.predict(matrix(races),output_margin=True)
    out=[];offset=0
    for race in races:
        n=len(active(race))
        out.append([float(v) for v in raw[offset:offset+n]])
        offset+=n
    if offset!=len(raw):
        raise ValueError('Ranking grouping mismatch')
    return out


def predictions(races,values,temperature):
    if not math.isfinite(temperature) or temperature<=0 or len(races)!=len(values):
        raise ValueError('Invalid temperature or race count')
    return [from_margins(r,[v/temperature for v in row]) for r,row in zip(races,values)]


def chronological(train,val):
    if not train or not val or max(r['date'] for r in train)>=min(r['date'] for r in val):
        raise ValueError('Training must strictly precede validation')
    if {r['race_id'] for r in train}&{r['race_id'] for r in val}:
        raise ValueError('Overlapping race groups')


def choose(trials):
    if not trials or any(not t['fold_log_losses'] or any(not math.isfinite(v) for v in t['fold_log_losses']) for t in trials):
        raise ValueError('Invalid tuning scores')
    return min(trials,key=lambda t:mean(t['fold_log_losses']))
