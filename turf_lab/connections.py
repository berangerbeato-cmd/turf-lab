"""Past-only driver/trainer residual form and explicit equipment categories."""
import math
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from itertools import groupby
from turf_lab.opposition import is_dq

EQUIPMENT=('PROTEGE_ANTERIEURS_POSTERIEURS','DEFERRE_ANTERIEURS_POSTERIEURS',
 'DEFERRE_ANTERIEURS','PROTEGE_ANTERIEURS_DEFERRRE_POSTERIEURS',
 'DEFERRE_POSTERIEURS','PROTEGE_ANTERIEURS','DEFERRE_ANTERIEURS_PROTEGE_POSTERIEURS',
 'PROTEGE_POSTERIEURS','UNKNOWN')
BLOCK_NAMES={
 'driver':['driver_residual','driver_log_classified','driver_dq_rate','driver_log_known'],
 'trainer':['trainer_residual','trainer_log_classified','trainer_dq_rate','trainer_log_known'],
 'equipment':['equipment_'+x for x in EQUIPMENT]+['equipment_changed','equipment_horse_residual','equipment_log_history']}


def entity(value):
    if not isinstance(value,str):return None
    name=' '.join(value.upper().split())
    return name if name and name not in ('INCONNU','UNKNOWN','N/A','-') else None


def equipment(value):
    return value if isinstance(value,str) and value in EQUIPMENT else 'UNKNOWN'


def augment_connections(races,records,window=30,strength=20,equipment_days=60):
    if min(window,strength,equipment_days)<=0:raise ValueError('Invalid connection parameters')
    sources={r['race_id']:r for r in records}
    if len(sources)!=len(records) or len({r['race_id'] for r in races})!=len(races):raise ValueError('Duplicate race')
    people={'driver':defaultdict(list),'trainer':defaultdict(list)}
    horses=defaultdict(list);population=[];out=[]
    for day,items in groupby(sorted(races,key=lambda r:(r['date'],r['race_id'])),key=lambda r:r['date']):
        batch=deepcopy(list(items));cutoff=(date.fromisoformat(day)-timedelta(days=window)).isoformat()
        horse_cutoff=(date.fromisoformat(day)-timedelta(days=equipment_days)).isoformat()
        population=[x for x in population if x['day']>=cutoff]
        known=[x for x in population if x['dq'] is not None]
        prior=sum(x['dq'] for x in known)/len(known) if known else 0.2
        for race in batch:
            raw={p['numPmu']:p for p in sources[race['race_id']]['participants']}
            for r in race['runners']:
                p=raw[r['number']];r['connection_features']={}
                r['connection_entities']={'driver':entity(p.get('driver')),'trainer':entity(p.get('entraineur'))}
                for group in ('driver','trainer'):
                    key=r['connection_entities'][group]
                    history=[x for x in people[group][key] if cutoff<=x['day']<day] if key else []
                    classified=[x['residual'] for x in history if x['residual'] is not None]
                    dq=[x['dq'] for x in history if x['dq'] is not None]
                    r['connection_features'][group]=[
                        sum(classified)/(len(classified)+strength) if classified else None,
                        math.log1p(len(classified)),
                        (sum(dq)+strength*prior)/(len(dq)+strength) if key else None,
                        math.log1p(len(dq))]
                cfg=equipment(p.get('deferre'));r['equipment_code']=cfg
                history=[x for x in horses[r['horse_id']] if horse_cutoff<=x['day']<day]
                last=[x for x in history if x['day']==history[-1]['day']] if history else []
                previous=last[0]['equipment'] if len(last)==1 else 'UNKNOWN'
                change=float(previous!=cfg) if previous!='UNKNOWN' and cfg!='UNKNOWN' else None
                same=[x['residual'] for x in history if cfg!='UNKNOWN' and x['equipment']==cfg and x['residual'] is not None]
                r['connection_features']['equipment']=[float(cfg==x) for x in EQUIPMENT]+[
                    change,sum(same)/(len(same)+strength) if same else None,math.log1p(len(same))]
            out.append(race)
        # Neither target nor any same-day result can enter the features above.
        for race in batch:
            active=[r for r in race['runners'] if not r['non_runner']]
            classified=[r for r in active if not is_dq(r) and isinstance(r.get('rank'),int) and r['rank']>0]
            residuals={}
            if len(classified)>1:
                for r in classified:
                    total=0
                    for other in classified:
                        if other is r:continue
                        observed=1 if r['rank']<other['rank'] else 0.5 if r['rank']==other['rank'] else 0
                        expected=1/(1+10**(other['opposition_features'][0]-r['opposition_features'][0]))
                        total+=(observed-expected)/(len(classified)-1)
                    residuals[r['number']]=total
            for r in active:
                dq=True if is_dq(r) else False if isinstance(r.get('rank'),int) and r['rank']>0 else None
                event={'day':day,'dq':dq,'residual':residuals.get(r['number']),'equipment':r['equipment_code']}
                population.append(event);horses[r['horse_id']].append(event)
                for group in ('driver','trainer'):
                    key=r['connection_entities'][group]
                    if key:people[group][key].append(event)
    return out


def candidate(races,name):
    if name not in ('v3','driver','trainer','equipment','combined'):raise ValueError('Unknown candidate')
    rows=deepcopy(races)
    groups=list(BLOCK_NAMES) if name=='combined' else [] if name=='v3' else [name]
    for race in rows:
        for r in race['runners']:
            r['features']+=r['opposition_features']
            for group in groups:r['features']+=r['connection_features'][group]
    return rows
