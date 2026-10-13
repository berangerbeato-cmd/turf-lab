"""Retrospective, strictly dated features and small conditional-logit pilot.

The feature function has no access to current race results or market fields.
Historical facts are NOT asserted to be original pre-race snapshots.
"""
import math
from datetime import datetime, timedelta, timezone, date
from statistics import mean

FEATURES=['win_rate','top3_rate','dq_rate','log_rest','history_coverage']


def norm_name(value):
    return ' '.join(str(value).upper().split())


def dated_history(horse, target_date):
    rows=[]; seen={}
    for run in horse.get('coursesCourues',[]):
        stamp=run.get('date')
        if not isinstance(stamp,(int,float)): raise ValueError('Missing history date')
        day=(datetime.fromtimestamp(stamp/1000,timezone.utc)+timedelta(milliseconds=run.get('timezoneOffset',0))).date().isoformat()
        if day>=target_date: raise ValueError('Target/future history forbidden')
        selected=[x for x in run.get('participants',[]) if x.get('itsHim') is True]
        if len(selected)!=1 or norm_name(selected[0]['nomCheval'])!=norm_name(horse['nomCheval']):
            raise ValueError('Ambiguous historical identity')
        own=selected[0]; place=own.get('place') or {}; status=place.get('statusArrivee')
        if status in ('NON_PARTANT','NP'): continue
        if run.get('discipline')!='ATTELE': continue
        key=(day,run.get('hippodrome'),run.get('nomPrix'))
        row={'date':day,'venue':run.get('hippodrome'),'distance_m':run.get('distance'),
             'field_size':run.get('nbParticipants'),'rank':place.get('place'),
             'status':status,'dq':bool(status and ('DISQUALIF' in status or status=='DISTANCE'))}
        if key in seen:
            if seen[key]!=row: raise ValueError('Conflicting history duplicate')
            continue
        seen[key]=row;rows.append(row)
    return sorted(rows,key=lambda x:x['date'],reverse=True)[:5]


def features(history, target_date):
    if any(h['date']>=target_date for h in history): raise ValueError('Feature leakage')
    n=len(history)
    if not n: return [None,None,None,None,0.0]
    # Non-place/DQ do not become invented numeric ranks.
    return [sum(h['rank']==1 for h in history)/n,
            sum(isinstance(h['rank'],int) and 1<=h['rank']<=3 for h in history)/n,
            sum(h['dq'] for h in history)/n,
            math.log1p(min(365,(date.fromisoformat(target_date)-date.fromisoformat(history[0]['date'])).days)),n/5]


def active(race): return [r for r in race['runners'] if not r['non_runner']]


def fit_transform(races):
    values=[r['features'] for race in races for r in active(race)]
    dimensions=len(values[0])
    if any(len(v)!=dimensions for v in values): raise ValueError('Inconsistent feature dimensions')
    mu=[mean(v[i] for v in values if v[i] is not None) if any(v[i] is not None for v in values) else 0.0 for i in range(dimensions)]
    scale=[max(0.01,math.sqrt(mean((v[i]-mu[i])**2 for v in values if v[i] is not None))) if any(v[i] is not None for v in values) else 1 for i in range(dimensions)]
    return {'mean':mu,'scale':scale}


def vector(values, transform):
    return [0.0 if v is None else (v-transform['mean'][i])/transform['scale'][i] for i,v in enumerate(values)]+[float(v is None) for v in values]


def probabilities(race, model):
    runners=active(race)
    if not runners: raise ValueError('No active runners')
    scores=[sum(a*b for a,b in zip(vector(r['features'],model['transform']),model['weights'])) for r in runners] if model['kind']=='logit' else [0.0]*len(runners)
    m=max(scores);exp=[math.exp(s-m) for s in scores];total=sum(exp)
    out={r['number']:p/total for r,p in zip(runners,exp)}
    out.update({r['number']:0.0 for r in race['runners'] if r['non_runner']})
    return out


def fit(races,l2,omit=None):
    transform=fit_transform(races);weights=[0.0]*(2*len(transform['mean']))
    prepared=[]
    for race in races:
        runners=active(race)
        if sum(r['won'] for r in runners)!=1: raise ValueError('Single winner required')
        prepared.append([(vector(r['features'],transform),r['won']) for r in runners])
    for _ in range(800):
        grad=[0.0]*len(weights)
        for entries in prepared:
            scores=[sum(a*b for a,b in zip(x,weights)) for x,y in entries];mx=max(scores)
            e=[math.exp(s-mx) for s in scores];total=sum(e)
            for (x,y),p in zip(entries,e):
                for j in range(len(weights)): grad[j]+=(p/total-y)*x[j]/len(prepared)
        for j in range(len(weights)):
            weights[j]-=0.03*(grad[j]+l2*weights[j])
            if omit is not None and j in (omit,omit+len(transform['mean'])): weights[j]=0.0
    return {'kind':'logit','weights':weights,'transform':transform,'l2':l2,'omitted_feature':omit}


def metrics(races,model):
    losses=[];briers=[];hits=[];bins=[{'count':0,'sum_p':0.0,'wins':0} for _ in range(10)]
    for race in races:
        runners=active(race);p=probabilities(race,model)
        winner=[r for r in runners if r['won']]
        if len(winner)!=1: raise ValueError('Single winner required')
        losses.append(-math.log(max(1e-15,p[winner[0]['number']])))
        briers.append(sum((p[r['number']]-r['won'])**2 for r in runners))
        best=min(runners,key=lambda r:(-p[r['number']],r['number']));hits.append(best['won'])
        for r in runners:
            b=bins[min(9,int(p[r['number']]*10))];b['count']+=1;b['sum_p']+=p[r['number']];b['wins']+=r['won']
    return {'races':len(races),'log_loss':mean(losses),'brier_multiclass':mean(briers),'top1_accuracy':mean(hits),
            'calibration':[{'bin':[i/10,(i+1)/10],'count':b['count'],'mean_probability':b['sum_p']/b['count'],'win_frequency':b['wins']/b['count']} for i,b in enumerate(bins) if b['count']]}
