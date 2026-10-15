"""Exact unordered top-k Plackett-Luce baseline, not independent placements."""
from functools import lru_cache
from itertools import combinations
import math
import numpy as np


@lru_cache(maxsize=32)
def layouts(n):
    result=[]; previous={():0}
    for k in range(1,5):
        subsets=list(combinations(range(n),k))
        parents=[[previous[s[:j]+s[j+1:]] for j in range(k)] for s in subsets]
        result.append((np.asarray(subsets,dtype=int),np.asarray(parents,dtype=int)))
        previous={s:i for i,s in enumerate(subsets)}
    return result


def markets(numbers, weights):
    w=np.asarray(weights,dtype=float)
    n=len(w)
    if n<5 or len(numbers)!=n or len(set(numbers))!=n or not np.isfinite(w).all() or (w<=0).any():
        raise ValueError('Require at least five unique runners and positive finite weights')
    w=w/w.sum(); previous=np.ones(1); distributions={}
    for k,(subsets,parents) in enumerate(layouts(n),1):
        sw=w[subsets]
        denominators=1-sw.sum(axis=1)[:,None]+sw
        current=(previous[parents]*sw/denominators).sum(axis=1)
        if not np.isclose(current.sum(),1,atol=1e-9):raise ValueError('Probability mass mismatch')
        distributions[k]=(subsets,current);previous=current
    pairs=list(combinations(range(n),2)); pair_map={p:i for i,p in enumerate(pairs)}
    outputs={'win':(list(numbers),w)}
    subsets,pr=distributions[3]
    placed=np.bincount(subsets.ravel(),weights=np.repeat(pr,3),minlength=n)
    outputs['place3']=(list(numbers),placed)
    for name,k in [('pair_place3',3),('pair_top4',4)]:
        subsets,pr=distributions[k]; out=np.zeros(len(pairs))
        for a,b in combinations(range(k),2):
            ix=np.array([pair_map[(int(s[a]),int(s[b]))] for s in subsets])
            out+=np.bincount(ix,weights=pr,minlength=len(pairs))
        outputs[name]=([(numbers[a],numbers[b]) for a,b in pairs],out)
    return outputs


def value_bounds(probability, low, high):
    """Scenario EV per euro; probable returns are not guaranteed final dividends."""
    if not all(math.isfinite(x) for x in (probability,low,high)) or not 0<probability<=1 or not 1<=low<=high:
        raise ValueError('Invalid probability or total-return interval')
    return {'break_even_total_return':1/probability,
            'ev_low':probability*low-1,'ev_high':probability*high-1,
            'status':'SCENARIO_ONLY_NOT_VALIDATED_VALUE'}
