"""Convex mixtures of immutable probability distributions."""
import math


def blend(baseline,challenger,weight):
    if not math.isfinite(weight) or not 0<=weight<=1:
        raise ValueError('Invalid ensemble weight')
    if set(baseline)!=set(challenger) or not baseline:
        raise ValueError('Race fields differ')
    for p in (baseline,challenger):
        if any(not math.isfinite(v) or not 0<=v<=1 for v in p.values()) or abs(sum(p.values())-1)>1e-8:
            raise ValueError('Invalid probability distribution')
    return {number:(1-weight)*baseline[number]+weight*challenger[number] for number in baseline}
