"""One V4 research upgrade: DQ model, contexts, odds-band bias, joint ZE5.

All inputs originate from past/prestart evidence. Five positions use the
already-fitted V4 47-feature conditional ranking model, never independent
win-probability products. No stake/ROI claim.
"""
import math
from collections import defaultdict
from itertools import combinations

import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import expit

from scripts.train_stage_ranking_v2 import features, transform
from turf_lab.pilot import active
from turf_lab.stage_ranking import greedy, strengths, unordered

BANDS=("1-4","4-8","8-20","20-50","50+")
BOUNDARIES=(4.,8.,20.,50.)


def dq_label(participant):
    if participant.get("statut")=="NON_PARTANT":
        return None
    status=str(participant.get("incident") or "").upper()
    if status.startswith("DISQUALIFIE") or status=="DISTANCE":
        return 1
    n=participant.get("ordreArrivee")
    if isinstance(n,int) and not isinstance(n,bool) and n>0:
        return 0
    return None


def dq_vector(horse):
    """Use pretarget 47-feature recent disqualification and reliability."""
    f=horse["features"]
    if len(f)!=47:
        raise ValueError("DQ research needs exactly 47 chronological features")
    selected=[f[2],f[38],f[39],f[40],f[41],f[46]]
    return [1.]+[float(v) if v is not None and math.isfinite(v) else 0. for v in selected]+[
        float(v is None) for v in selected]


def fit_dq(rows,official_by_id,ridge=.003):
    xx=[];yy=[];dates=[]
    for race in rows:
        official=official_by_id[race["race_id"]]
        by={r["numPmu"]:r for r in official["participants"]}
        if set(by)!={r["number"] for r in race["runners"]}:
            raise ValueError("DQ training field mismatch")
        for horse in active(race):
            outcome=dq_label(by[horse["number"]])
            if outcome is None:
                continue
            xx.append(dq_vector(horse));yy.append(outcome)
            dates.append(race["date"])
    if len(xx)<2000 or not 0.015 <sum(yy)/len(yy)<.5:
        raise ValueError("Insufficient validated disqualification events")
    x=np.asarray(xx,float);y=np.asarray(yy,float)
    def fun(w):
        z=x@w
        loss=np.mean(np.logaddexp(0,z)-y*z)+.5*ridge*np.sum(w[1:]**2)
        gradient=x.T@(expit(z)-y)/len(y)
        gradient[1:]+=ridge*w[1:]
        return float(loss),gradient
    start=np.zeros(x.shape[1]);start[0]=math.log(y.mean()/(1-y.mean()))
    opt=minimize(fun,start,jac=True,method="L-BFGS-B",options={"maxiter":160,"ftol":1e-10})
    if not opt.success or not np.isfinite(opt.x).all():
        raise ValueError("DQ fitting failed")
    return {"version":"DQ_LOGISTIC_PRIOR_47F","weights":opt.x.tolist(),
            "fit_runners":len(y),"fit_races":len(rows),
            "observed_dq_rate":float(y.mean()),"ridge":ridge,
            "date_from":min(dates),"date_through":max(dates),
            "status":"RESEARCH_ONLY"}


def predict_dq(rows,model):
    w=np.asarray(model["weights"],float)
    result={}
    for r in rows:
        x=np.asarray([dq_vector(h) for h in active(r)],float)
        if x.shape[1]!=len(w):
            raise ValueError("DQ model feature width mismatch")
        p=expit(x@w)
        result[r["race_id"]]={h["number"]:float(v) for h,v in zip(active(r),p)}
    return result


def dq_metrics(rows,official_by_id,model):
    predicted=predict_dq(rows,model)
    losses=[];briers=[];observed=[];records=[]
    for r in rows:
        by={p["numPmu"]:p for p in official_by_id[r["race_id"]]["participants"]}
        for n,p in predicted[r["race_id"]].items():
            outcome=dq_label(by[n])
            if outcome is None:continue
            observed.append(outcome)
            briers.append((p-outcome)**2)
            losses.append(-(outcome*math.log(max(p,1e-12))+
                              (1-outcome)*math.log(max(1-p,1e-12))))
            records.append((p,outcome))
    if not observed:raise ValueError("No DQ results to evaluate")
    return {"horses":len(observed),"dq_frequency":sum(observed)/len(observed),
            "log_loss":sum(losses)/len(losses),
            "brier":sum(briers)/len(briers),
            "calibration": [
               {"range":[a/10,(a+1)/10],"count":sum(a/10<=p<(a+1)/10 for p,y in records),
                "p_mean":sum(p for p,y in records if a/10<=p<(a+1)/10)/max(1,sum(a/10<=p<(a+1)/10 for p,y in records)),
                "observed":sum(y for p,y in records if a/10<=p<(a+1)/10)/max(1,sum(a/10<=p<(a+1)/10 for p,y in records))}
               for a in range(10) if any(a/10<=p<(a+1)/10 for p,y in records)]}


def relative_context(row):
    dist=int(row["distance_m"])
    bucket="sprint" if dist<2200 else "middle" if dist<2900 else "long"
    departure=str(row["start_type"]).upper()
    track=str(row["venue"]).upper()
    return (track+"|"+departure+"|"+bucket,departure+"|"+bucket,departure)


def fit_context_temperatures(rows,win_probabilities,minimum=180,prior=600):
    """Learn context-specific *temperatures*, not a constant shared bonus."""
    if len(rows)!=len(win_probabilities):
        raise ValueError("Context fitting requires paired races")
    grouped=defaultdict(list)
    for race,prob in zip(rows,win_probabilities):
        winner=next((r["number"] for r in active(race) if r["won"]),None)
        if winner is None:continue
        candidates=[r["number"] for r in active(race)]
        if set(candidates)!=set(n for n,p in prob.items() if p>0):raise ValueError("Context field differs")
        logits=np.log(np.maximum([prob[n] for n in candidates],1e-14))
        idx=candidates.index(winner)
        for key in relative_context(race):grouped[key].append((logits,idx))
    corrections={}
    for key,samples in grouped.items():
        if len(samples)<minimum:continue
        def objective(t):
            loss=0.
            for logits,idx in samples:
                v=logits/t
                mx=max(v)
                loss+=math.log(sum(math.exp(x-mx) for x in v))+mx-v[idx]
            return loss/len(samples)+.12*(t-1)**2
        fit=minimize_scalar(objective,bounds=(.8,1.2),method="bounded")
        if not fit.success:continue
        strength=len(samples)/(len(samples)+prior)
        t=1+strength*(float(fit.x)-1)
        corrections[key]={"temperature":t,"races":len(samples),
                          "prior_races":prior,"clipped_range":[.8,1.2]}
    return {"status":"RESEARCH_ONLY","minimum_races":minimum,
            "training_races":len(rows),"groups":corrections,
            "policy":"Shrunk groupwise logit temperature, never venue-intercept"}


def apply_context(prob,venue,start_type,distance_m,model):
    row={"venue":venue,"start_type":start_type,"distance_m":distance_m}
    selected=next(((k,model["groups"][k]) for k in relative_context(row)
                   if k in model["groups"]),None)
    if selected is None:
        return dict(prob),None
    key,item=selected;t=item["temperature"]
    powered={n:p**(1/t) for n,p in prob.items()}
    z=sum(powered.values())
    return {n:v/z for n,v in powered.items()},key


def odds_band(odds):
    if not math.isfinite(odds) or odds<=1:
        raise ValueError("Invalid odds for market bias analysis")
    return next((label for bound,label in zip(BOUNDARIES,BANDS) if odds<bound),"50+")


def market_band_fit(rows,base_prob,prior=100):
    if len(rows)!=len(base_prob) or not rows:
        raise ValueError("Market band needs paired races")
    seen={k:[0.,0.,0] for k in BANDS}
    for row,pred in zip(rows,base_prob):
        if set(row["numbers"])!=set(pred):
            raise ValueError("Market fitted runner field mismatch")
        for i,n in enumerate(row["numbers"]):
            band=odds_band(row["odds"][i])
            acc=seen[band]
            acc[0]+=1;acc[1]+=pred[n];acc[2]+=int(i==row["winner_index"])
    corrections={}
    for b,(n,expected,actual) in seen.items():
        if n<150 or expected<10:
            corrections[b]={"log_factor":0.0,"count":int(n),"enabled":False}
            continue
        ratio=(actual+prior*expected/n)/(expected+prior*expected/n)
        factor=max(-.24,min(.24,math.log(max(1e-8,ratio))))
        corrections[b]={"log_factor":factor,"count":int(n),"observed_wins":actual,
                        "predicted_wins":expected,"enabled":True}
    return {"status":"RESEARCH_ONLY_NOT_INDEPENDENT","bands":corrections,
            "prior":prior,"races":len(rows),
            "limitations":["Previously fitted base market also used 2025 H2 outcomes.",
                           "These odds-bin corrections require virgin prospective validation."]}


def adjust_market_bands(prob,odds,model):
    if set(prob)!=set(odds):
        raise ValueError("Incomplete odds for market band correction")
    values={n:p*math.exp(model["bands"][odds_band(odds[n])]["log_factor"])
            for n,p in prob.items()}
    z=sum(values.values())
    return {n:v/z for n,v in values.items()}


def quinte_unordered(race,ranker,limit=12,alternatives=3):
    """Search candidate unordered top-fives using stage-specific joint DP.

    All results are PAPER only. No multiplication of win probabilities.
    """
    participants=active(race)
    if len(participants)<6 or any(len(p["features"])!=47 for p in participants):
        raise ValueError("Quinté needs at least 6 active horses with 47 V4 features")
    x=transform(features(race),np.asarray(ranker["mean"]),np.asarray(ranker["scale"]))
    weights=strengths(np.asarray(ranker["coefficients"])@x.T,ranker["temperatures"])
    greedy_set=tuple(sorted(greedy(weights,5)))
    aggregate=sorted(range(len(participants)),
                    key=lambda j:(-sum(weights[k,j]/weights[k].sum() for k in range(5)),j))
    shortlist=sorted(set(aggregate[:limit])|set(greedy_set))
    if len(shortlist)>limit+5:
        raise ValueError("Excessive Quinté candidate complexity")
    best=[]
    for candidate in combinations(shortlist,5):
        p=unordered(weights,list(candidate))
        best.append((p,candidate))
    best.sort(key=lambda item:(-item[0],item[1]))
    if not best:
        raise ValueError("Quinté candidate search returned nothing")
    numbers=lambda selection:sorted(participants[i]["number"] for i in selection)
    first,selection=best[0]
    return {"selection":numbers(selection),"joint_probability_unordered":float(first),
            "selection_probability_source":"FROZEN_5_STAGE_CONDITIONAL_RANK_MODEL",
            "greedy_selection":numbers(greedy_set),
            "greedy_unordered_probability":float(unordered(weights,list(greedy_set))),
            "alternatives":[{"numbers":numbers(candidate),"p_exact_five_unordered":float(p)}
                            for p,candidate in best[:alternatives]],
            "candidates_examined":len(best),
            "joint_calibration_verified":False,"recommended_stake_eur":None,
            "status":"RESEARCH_ONLY_NOT_A_VALIDATED_ZE5_BET"}
