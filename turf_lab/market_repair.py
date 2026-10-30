"""Explicit market-informed RESEARCH model, separate from frozen sports models."""
import math
import numpy as np


def normalize(values):
    if not values or any(isinstance(v,bool) or not math.isfinite(v) or v<=0 for v in values):
        raise ValueError('Positive finite values required')
    z=sum(values)
    return [v/z for v in values]


def predict(odds, sport, weights):
    if len(odds)!=len(sport) or len(odds)<2 or any(isinstance(c,bool) or not math.isfinite(c) or c<=1 for c in odds):
        raise ValueError('Complete matching valid field required')
    if len(weights)!=2 or any(isinstance(w,bool) or not math.isfinite(w) for w in weights) or not 0<=weights[0]<=3 or not 0<=weights[1]<=1:
        raise ValueError('Invalid weights')
    market=normalize([1/c for c in odds]);sport=normalize(sport)
    scores=[weights[0]*math.log(m)+weights[1]*math.log(p) for m,p in zip(market,sport)]
    return normalize([math.exp(s-max(scores)) for s in scores])


def fit(rows, protocol, market_only=False):
    """Projected Newton descent, fixed ridge and bounds; no evaluation input."""
    if not rows or any(not protocol['fit'][0]<=r['date']<=protocol['fit'][1] for r in rows):
        raise ValueError('Fit data outside declared training period')
    width=max(len(r['odds']) for r in rows)
    x=np.zeros((len(rows),width,2)); mask=np.zeros((len(rows),width),dtype=bool);y=np.zeros_like(mask,dtype=float)
    for i,r in enumerate(rows):
        n=len(r['odds']);m=normalize([1/c for c in r['odds']]);s=normalize(r['sport'])
        x[i,:n,:]=np.column_stack([np.log(m),np.log(s)]);mask[i,:n]=True;y[i,r['winner_index']]=1
    ridge=protocol['ridge'];anchor=np.asarray(protocol['ridge_anchor'],dtype=float);w=anchor.copy()
    upper=np.asarray([3.,0. if market_only else 1.])
    def loss(v):
        scores=np.einsum('rni,i->rn',x,v);scores=np.where(mask,scores,-1e100)
        mx=scores.max(axis=1);ex=np.exp(scores-mx[:,None]);z=ex.sum(axis=1)
        return float(np.mean(np.log(z)+mx-(scores*y).sum(axis=1))+.5*ridge*((v-anchor)**2).sum()),ex/z[:,None]
    iterations=0
    for iterations in range(protocol['iterations']):
        old,p=loss(w);ex=np.einsum('rn,rni->ri',p,x)
        grad=np.einsum('rn,rni->i',p-y,x)/len(rows)+ridge*(w-anchor)
        h=np.einsum('rn,rni,rnj->ij',p,x,x)/len(rows)-ex.T@ex/len(rows)+ridge*np.eye(2)
        if market_only:direction=np.array([grad[0]/h[0,0],0.])
        else:direction=np.linalg.solve(h,grad)
        accepted=False
        for power in range(30):
            proposal=np.clip(w-direction*(.5**power),0,upper)
            if loss(proposal)[0]<=old+1e-14:
                accepted=True;break
        if not accepted:break
        delta=np.max(np.abs(proposal-w));w=proposal
        if delta<1e-9:break
    return {'weights':w.tolist(),'penalized_fit_loss':loss(w)[0], 'iterations':iterations+1,
            'fit_races':len(rows),'fit_from':min(r['date'] for r in rows),'fit_through':max(r['date'] for r in rows),
            'market_informed':True,'recommendations_allowed':False,'status':'EXPERIMENTAL_NO_BET'}
