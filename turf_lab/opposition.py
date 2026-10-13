"""Past-only opposition and regularized disqualification features."""
import math
from collections import defaultdict
from copy import deepcopy
from itertools import groupby

NAMES = ['relative_elo', 'log_classified_starts', 'shrunk_dq_rate', 'dq_posterior_sd']


def is_dq(runner):
    incident = str(runner.get('incident') or '')
    return incident.startswith('DISQUALIFIE') or incident == 'DISTANCE'


def augment(races, k=32, scale=400, prior_strength=10, initial_prior=0.2):
    if k<=0 or scale<=0 or prior_strength<=0 or not 0<initial_prior<1:
        raise ValueError('Invalid opposition parameters')
    if len({r['race_id'] for r in races})!=len(races):
        raise ValueError('Duplicate race')
    output=[]; year=None
    for day, grouped in groupby(sorted(races,key=lambda r:(r['date'],r['race_id'])),key=lambda r:r['date']):
        if year!=day[:4]:
            year=day[:4]; ratings=defaultdict(float); starts=defaultdict(int)
            dq=defaultdict(int); observed=defaultdict(int); total_dq=0; total_n=0
        batch=deepcopy(list(grouped))
        base_prior=total_dq/total_n if total_n else initial_prior
        # Keep Beta shapes positive even if the first observed day contains no faults.
        base_prior=min(1-1e-6,max(1e-6,base_prior))
        for race in batch:
            active=[r for r in race['runners'] if not r['non_runner']]
            mean_rating=sum(ratings[r['horse_id']] for r in active)/max(1,len(active))
            for r in race['runners']:
                h=r['horse_id'];a=dq[h]+prior_strength*base_prior
                b=observed[h]-dq[h]+prior_strength*(1-base_prior)
                r['opposition_features']=[(ratings[h]-mean_rating)/scale,math.log1p(starts[h]),
                    a/(a+b),math.sqrt(a*b/((a+b)**2*(a+b+1)))]
            race['opposition_cutoff']=day
            output.append(race)
        deltas=defaultdict(float)
        for race in batch:
            active=[r for r in race['runners'] if not r['non_runner']]
            classified=[r for r in active if not is_dq(r) and isinstance(r.get('rank'),int) and r['rank']>0]
            for r in classified:
                h=r['horse_id'];starts[h]+=1
                for other in classified:
                    if other is r:continue
                    expected=1/(1+10**((ratings[other['horse_id']]-ratings[h])/scale))
                    actual=1.0 if r['rank']<other['rank'] else 0.5 if r['rank']==other['rank'] else 0.0
                    deltas[h]+=k*(actual-expected)/max(1,len(classified)-1)
            for r in active:
                fault=is_dq(r);rank=r.get('rank')
                if fault or (isinstance(rank,int) and rank>0):
                    h=r['horse_id'];observed[h]+=1;dq[h]+=int(fault)
                    total_n+=1;total_dq+=int(fault)
        for h,delta in deltas.items():ratings[h]+=delta
    return output


def candidate(races, name):
    if name not in ('baseline','opposition','dq','combined'):raise ValueError('Unknown candidate')
    rows=deepcopy(races)
    for race in rows:
        for r in race['runners']:
            extra=r['opposition_features']
            r['features']+=extra[:2] if name=='opposition' else extra[2:] if name=='dq' else extra if name=='combined' else []
    return rows
