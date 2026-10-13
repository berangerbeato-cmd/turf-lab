"""Vectorized equivalent of the existing conditional-logit gradient descent."""
from turf_lab.pilot import active,fit_transform,vector


def fit(races,l2,iterations=800,learning_rate=0.03):
    import numpy as np
    if not races or l2<0 or iterations<1 or learning_rate<=0:raise ValueError('Invalid fit settings')
    transform=fit_transform(races);xs=[];ys=[];sizes=[]
    for race in races:
        runners=active(race)
        if sum(r['won'] for r in runners)!=1:raise ValueError('Single winner required')
        sizes.append(len(runners))
        for r in runners:xs.append(vector(r['features'],transform));ys.append(r['won'])
    x=np.asarray(xs,dtype=np.float64);y=np.asarray(ys,dtype=np.float64)
    if not np.isfinite(x).all():raise ValueError('Non-finite features')
    starts=np.r_[0,np.cumsum(sizes)[:-1]];groups=np.repeat(np.arange(len(sizes)),sizes)
    weights=np.zeros(x.shape[1])
    for _ in range(iterations):
        scores=x@weights;maximum=np.maximum.reduceat(scores,starts)
        exp=np.exp(scores-maximum[groups]);denom=np.add.reduceat(exp,starts)
        gradient=x.T@(exp/denom[groups]-y)/len(races)
        weights-=learning_rate*(gradient+l2*weights)
    return {'kind':'logit','weights':weights.tolist(),'transform':transform,'l2':l2,'omitted_feature':None}
