"""Top-k labels, coherent joint-event projection and combination accounting."""
import math
from itertools import permutations
from turf_lab.rank45 import ordered_probability

def finish(participants,k=5):
    active=[p for p in participants if p.get('statut')!='NON_PARTANT']
    ranks=[[p for p in active if p.get('ordreArrivee')==j] for j in range(1,k+1)]
    if len(active)<k or any(len(r)!=1 for r in ranks):return None
    truth=[r[0] for r in ranks]
    if any(str(p.get('incident') or '').startswith('DISQUALIFIE') or p.get('incident')=='DISTANCE' for p in truth):return None
    return [p['numPmu'] for p in truth]

def weights(scores,temperature):
    if temperature<=0 or not scores or any(not math.isfinite(x) for x in scores):raise ValueError('Invalid scores')
    top=max(scores);v=[math.exp(max(-700,(s-top)/temperature)) for s in scores];z=sum(v)
    return [x/z for x in v]

def unordered(p,selection):
    if len(selection) not in (3,4,5):raise ValueError('Unsupported event')
    return math.fsum(ordered_probability(p,s) for s in permutations(selection))

def portfolio(p,selections,unit_cost=1.):
    if not math.isfinite(unit_cost) or unit_cost<=0:raise ValueError('Invalid cost')
    keys=[tuple(sorted(s)) for s in selections]
    if not keys or len(set(keys))!=len(keys) or len({len(s) for s in keys})!=1:raise ValueError('Duplicate or incompatible selections')
    probability=sum(unordered(p,s) for s in keys)
    cost=len(keys)*unit_cost
    return dict(combinations=len(keys),total_cost=cost,probability=probability,
       break_even_total_return_per_winning_combination=cost/probability,
       assumption='Distinct exact unordered top-k events; equal payout if one wins, no bonuses. Unit cost is hypothetical, not operator minimum.',
       status='EXPERIMENTAL_PROBABILITIES_NOT_BETTING_VALUE')
