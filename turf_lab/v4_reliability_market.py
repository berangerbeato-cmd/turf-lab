"""New V4 research market model: reliability-conditioned sport vs odds.

Market log score = alpha log(p_market) +
    beta * [1+tanh(gamma)*(R-.5)] * log(p_sport).
R is a source-data completeness INDEX, NOT an estimated win probability.
The gamma gate is fitted on strictly time-disjoint 2025 prestart PMU data.
"""
import math
import numpy as np
from scipy.optimize import minimize


def probs(odds,sport,reliability,weights):
    if (len(odds)!=len(sport) or len(odds)!=len(reliability) or len(odds)<2
            or len(weights)!=3):
        raise ValueError("Incomplete 3-parameter market field")
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or
           not math.isfinite(x) for x in list(odds)+list(sport)+list(reliability)+list(weights)):
        raise ValueError("Invalid market numeric inputs")
    if (any(o<=1 for o in odds) or any(p<=0 for p in sport)
            or any(r<0 or r>1.000001 for r in reliability)):
        raise ValueError("Invalid odds, sport or R values")
    alpha,beta,gamma=weights
    if not (0<=alpha<=3 and 0<=beta<=1 and -2<=gamma<=2):
        raise ValueError("Market reliability model outside frozen parameter bounds")
    m=np.asarray([1/o for o in odds],float)
    m/=m.sum()
    p=np.asarray(sport,float)
    p/=p.sum()
    R=np.asarray(reliability,float)
    z=alpha*np.log(m)+beta*(1+math.tanh(gamma)*(R-.5))*np.log(p)
    a=np.exp(z-np.max(z))
    return (a/a.sum()).tolist()


def fit(rows,configuration,baseline):
    if len(rows)<200 or len(baseline)!=2:
        raise ValueError("Insufficient time-disjoint money+R market calibration data")
    if any(not configuration["market_fit"][0]<=r["date"]<=configuration["market_fit"][1] for r in rows):
        raise ValueError("Market R fit period violation")
    ridge=float(configuration["market_ridge"])
    bounds=[(0,3),(0,1),(-2,2)]
    start=np.array([*baseline,0.],float)
    def loss(weights):
        total=0.
        for row in rows:
            p=probs(row["odds"],row["sport"],row["reliability"],weights)
            total-=math.log(max(1e-15,p[row["winner_index"]]))
        total/=len(rows)
        return total+ridge*float(np.sum((weights-start)**2))
    fitted=minimize(loss,start,method="L-BFGS-B",bounds=bounds,
                    options={"maxiter":90,"ftol":1e-10})
    if not fitted.success:
        raise ValueError("Market reliability fit did not converge: "+str(fitted.message))
    return {"kind":"V4_RELIABILITY_CONDITIONAL_MARKET",
            "weights":fitted.x.tolist(),
            "baseline_two_weight_anchor":list(baseline),
            "ridge":ridge,"fit_races":len(rows),
            "fit_from":min(r["date"] for r in rows),
            "fit_through":max(r["date"] for r in rows),
            "status":"RESEARCH_ONLY","recommendations_allowed":False}


def evaluate(rows,weights):
    losses=[];briers=[];tops=[];positive=[]
    for row in rows:
        p=probs(row["odds"],row["sport"],row["reliability"],weights)
        won=row["winner_index"]
        losses.append(-math.log(max(p[won],1e-15)))
        briers.append(sum((v-int(i==won))**2 for i,v in enumerate(p)))
        tops.append(int(max(range(len(p)),key=lambda i:p[i])==won))
        for i,(v,c) in enumerate(zip(p,row["odds"])):
            if v*c-1>=0.1:positive.append((v,int(i==won)))
    return {"races":len(rows),
            "log_loss":sum(losses)/len(losses),
            "brier":sum(briers)/len(briers),
            "top1":sum(tops)/len(tops),
            "positive_ev_diagnostic":{"count":len(positive),
                        "predicted_wins":sum(p for p,y in positive),
                        "actual_wins":sum(y for p,y in positive)},
            "roi":None}
