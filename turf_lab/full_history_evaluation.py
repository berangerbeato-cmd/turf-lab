"""Isolated evaluation helpers with fixed race grouping and day/week uncertainty."""
import math
from collections import defaultdict
from datetime import date
from statistics import mean
from turf_lab.pilot import active, probabilities
from turf_lab.xgb_model import from_margins, metrics
from turf_lab.ensemble import blend


def chronological(train, validation, test):
    groups=[{r['race_id'] for r in rows} for rows in (train,validation,test)]
    if any(not g for g in groups) or any(len(g)!=len(rows) for g,rows in zip(groups,(train,validation,test))):
        raise ValueError('Empty split or duplicate race')
    if any(groups[i]&groups[j] for i,j in ((0,1),(0,2),(1,2))):raise ValueError('Overlapping splits')
    if not max(r['date'] for r in train)<min(r['date'] for r in validation):raise ValueError('Train must precede validation')
    if not max(r['date'] for r in validation)<min(r['date'] for r in test):raise ValueError('Validation must precede test')


def matrix(rows, training=False, ranking=False):
    import numpy as np
    import xgboost as xgb
    xs=[];ys=[];weights=[];groups=[];width=None
    for race in rows:
        runners=active(race)
        if len(runners)<2 or len({r['number'] for r in race['runners']})!=len(race['runners']):raise ValueError('Invalid race')
        if training and sum(r['won'] for r in runners)!=1:raise ValueError('Single winner required')
        groups.append(len(runners))
        for r in runners:
            width=width or len(r['features'])
            if len(r['features'])!=width or any(v is not None and not math.isfinite(v) for v in r['features']):raise ValueError('Invalid feature matrix')
            xs.append([np.nan if v is None else v for v in r['features']])
            if training:ys.append(float(r['won']));weights.append(1/len(runners))
    if not xs:raise ValueError('Empty matrix')
    d=xgb.DMatrix(np.asarray(xs,dtype=np.float32),missing=np.nan,nthread=1)
    if training:
        d.set_label(ys)
        if ranking:d.set_group(groups);d.set_weight(np.ones(len(groups)))
        else:d.set_weight(weights)
    return d


def tree_fit(rows,p,ranking=False):
    import xgboost as xgb
    if xgb.__version__!=p['xgboost_version']:raise ValueError('XGBoost version mismatch')
    params=dict(p['params'])
    if ranking:params['objective']='rank:pairwise'
    return xgb.train(params,matrix(rows,True,ranking),num_boost_round=p['num_boost_round'])


def tree_predict(rows, model):
    values=model.predict(matrix(rows),output_margin=True);offset=0;out=[]
    for race in rows:
        n=len(active(race));out.append(from_margins(race,values[offset:offset+n]));offset+=n
    if offset!=len(values):raise ValueError('Prediction grouping mismatch')
    return out


def temper(rows, predictions, temperature):
    if temperature<=0 or len(rows)!=len(predictions):raise ValueError('Invalid temperature')
    return [from_margins(r,[math.log(max(1e-15,p[x['number']]))/temperature for x in active(r)]) for r,p in zip(rows,predictions)]


def tune(rows, predictions, temperatures):
    t=min(temperatures,key=lambda t:metrics(rows,temper(rows,predictions,t))['log_loss'])
    return t,temper(rows,predictions,t)


def mix(a,b,weight):
    if len(a)!=len(b):raise ValueError('Different race counts')
    return [blend(x,y,weight) for x,y in zip(a,b)]


def season(day):
    return ('winter' if int(day[5:7]) in (12,1,2) else 'spring' if int(day[5:7]) in (3,4,5)
            else 'summer' if int(day[5:7]) in (6,7,8) else 'autumn')


def score(rows, predictions):
    result={'overall':metrics(rows,predictions)}
    for field,key in [('month',lambda r:r['date'][:7]),('season',lambda r:season(r['date'])),('venue',lambda r:r['venue']),('start_type',lambda r:r['start_type']),('field_size',lambda r:'2-9' if len(active(r))<10 else '10-14' if len(active(r))<15 else '15+')]:
        groups=defaultdict(list)
        for i,r in enumerate(rows):groups[key(r)].append(i)
        result['by_'+field]={g:metrics([rows[i] for i in ix],[predictions[i] for i in ix]) for g,ix in groups.items()}
    bins=result['overall']['calibration']
    result['overall']['runner_ece']=sum(b['count']*abs(b['mean_probability']-b['win_frequency']) for b in bins)/sum(b['count'] for b in bins)
    return result


def paired(rows, a, b, block='week', repetitions=1000):
    import numpy as np
    if len(rows)!=len(a) or len(a)!=len(b) or not rows:raise ValueError('Invalid paired input')
    groups=defaultdict(list)
    for r,x,y in zip(rows,a,b):
        runners=active(r);winner=next(p['number'] for p in runners if p['won'])
        loss=lambda p:-math.log(max(1e-15,p[winner]))
        brier=lambda p:sum((p[z['number']]-z['won'])**2 for z in runners)
        hit=lambda p:float(min(runners,key=lambda z:(-p[z['number']],z['number']))['won'])
        key=r['date'] if block=='day' else date.fromisoformat(r['date']).isocalendar()[:2]
        groups[key].append([loss(y)-loss(x),brier(y)-brier(x),hit(y)-hit(x)])
    totals=np.asarray([np.sum(v,axis=0) for v in groups.values()]);counts=np.asarray([len(v) for v in groups.values()])
    rng=np.random.default_rng(20261014);estimates=[]
    for _ in range(repetitions):
        ix=rng.integers(0,len(counts),len(counts));estimates.append(totals[ix].sum(axis=0)/counts[ix].sum())
    intervals=np.quantile(estimates,[.025,.975],axis=0);delta=totals.sum(axis=0)/counts.sum()
    return dict(block=block,blocks=len(counts),metrics={name:{'challenger_minus_classic':float(delta[i]),'interval_95':[float(v) for v in intervals[:,i]]} for i,name in enumerate(('log_loss','brier_multiclass','top1_accuracy'))},
                interpretation='Exploratory paired cluster bootstrap, not corrected for model search; repeated horses can remain dependent across weeks.')
