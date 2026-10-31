"""Joint top-four/top-five research baseline from frozen win probabilities."""
import math
from itertools import permutations

def ordered_probability(probabilities, order):
    if len(set(order)) != len(order) or not set(order) <= probabilities.keys():
        raise ValueError('Invalid order')
    if any(not math.isfinite(p) or p <= 0 for p in probabilities.values()):
        raise ValueError('Positive finite active probabilities required')
    total=sum(probabilities.values()); remaining=total; result=1.
    for n in order:
        result*=probabilities[n]/remaining
        remaining-=probabilities[n]
    return result

def unordered_probability(probabilities, selection):
    if len(selection) not in (4,5): raise ValueError('Four or five runners required')
    return math.fsum(ordered_probability(probabilities,p) for p in permutations(selection))

def forecast(probabilities,k):
    if k not in (4,5) or len(probabilities)<k: raise ValueError('Invalid field')
    order=sorted(probabilities,key=lambda n:(-probabilities[n],n))[:k]
    return dict(order=order,ordered_probability=ordered_probability(probabilities,order),
                unordered_probability=unordered_probability(probabilities,order),
                status='UNVALIDATED_PLACKETT_LUCE_BASELINE',recommendations_allowed=False)
