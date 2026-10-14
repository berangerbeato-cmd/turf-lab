"""Bounded capture of indicative PMU quotes, separate from model features."""
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.v6_holdout import verify
from scripts.backtest_connections import digest
from turf_lab.evidence import EvidenceStore, dump
from turf_lab.shadow_v5_score import choose_snapshot
from turf_lab.month_history import identity
from turf_lab.connections import entity, equipment


def window(now,start,p):
    minutes=(start-now).total_seconds()/60
    return p['minimum_minutes_before_start']<=minutes<=p['maximum_minutes_before_start']


def validate(prediction,detail,participants,now,p):
    start=datetime.fromisoformat(prediction['scheduled_start'])
    if detail.get('heureDepart'):
        start=datetime.fromtimestamp(detail['heureDepart']/1000,timezone.utc)
    if not window(now,start,p):
        raise ValueError('Outside prestart capture window')
    if detail.get('arriveeDefinitive') or detail.get('isArriveeDefinitive') or detail.get('ordreArrivee'):
        raise ValueError('Results already present')
    if detail.get('statut')=='COURSE_ANNULEE' or detail.get('categorieStatut')=='ANNULEE':
        raise ValueError('Cancelled race')
    original=prediction['target_snapshot']['participants']
    if not participants or any(r.get('statut') not in ('PARTANT','NON_PARTANT') for r in original+participants):
        raise ValueError('Missing participants or unknown status')
    if len({r['numPmu'] for r in participants})!=len(participants):
        raise ValueError('Duplicate runner')
    def signature(r):
        return (r['numPmu'],identity(r),entity(r.get('driver')),entity(r.get('entraineur')),
            equipment(r.get('deferre')),r.get('age'),r.get('sexe'))
    old=[r for r in original if r['statut']=='PARTANT']
    active=[r for r in participants if r['statut']=='PARTANT']
    if {signature(r) for r in old}!={signature(r) for r in active}:
        raise ValueError('Current field differs from frozen forecast')
    output=[]
    for r in active:
        if any(r.get(k) not in (None,'',[]) for k in ('ordreArrivee','tempsObtenu','commentaireApresCourse','incident')):
            raise ValueError('Post-race participant fields present')
        q=r.get('dernierRapportDirect') or {}
        value=q.get('rapport');stamp=q.get('dateRapport')
        if q.get('typePari')!=p['market'] or q.get('typeRapport')!='DIRECT' or q.get('numPmu1')!=r['numPmu']:
            raise ValueError('Missing or wrong direct market quote')
        if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<=0:
            raise ValueError('Invalid quote value')
        if not isinstance(stamp,(int,float)) or isinstance(stamp,bool) or not math.isfinite(stamp):
            raise ValueError('Invalid quote timestamp')
        quote_time=datetime.fromtimestamp(stamp/1000,timezone.utc)
        age=(now-quote_time).total_seconds()
        if not 0<=age<=p['maximum_quote_age_seconds'] or quote_time>=start:
            raise ValueError('Stale, future or post-start quote')
        probability=prediction['models']['v6']['probabilities'][str(r['numPmu'])]
        output.append({'number':r['numPmu'],'name':r.get('nom'),'pmu_indicative_report':value,
            'quote_time':quote_time.isoformat(),'quote_age_seconds':age,'v6_probability':probability})
    return {'scheduled_start':start.isoformat(),'minutes_before_start':(start-now).total_seconds()/60,'quotes':output}


def main():
    policy=Path('config/pmu_quotes_today.json')
    p=json.loads(policy.read_text())
    now=datetime.now(timezone.utc)
    if now.astimezone(ZoneInfo('Europe/Paris')).date().isoformat()!=p['date']:
        print('Outside authorized quote date; no requests')
        return
    _,frozen,_,_=verify()
    batch=now.strftime('%Y%m%dT%H%M%S%fZ')
    store=EvidenceStore('evidence/pmu_quotes/'+batch,max_requests=p['max_requests_per_run'],delay=.5)
    results=[]
    for rid in p['race_ids']:
        path=Path('quotes_pmu')/p['date']/(rid+'.json')
        if path.exists():
            results.append({'race_id':rid,'status':'CAPTURED','path':str(path)})
            continue
        candidates=[(f,json.loads(f.read_text())) for f in Path('predictions_v6').glob(p['date']+'/'+rid+'_*/prediction.json')]
        chosen=choose_snapshot(candidates)
        if chosen is None:
            results.append({'race_id':rid,'status':'BLOCKED','reason':'no_prestart_forecast'})
            continue
        source,prediction=chosen
        start=datetime.fromisoformat(prediction['scheduled_start'])
        now=datetime.now(timezone.utc)
        if not window(now,start,p):
            status='WAITING' if (start-now).total_seconds()>p['maximum_minutes_before_start']*60 else 'MISSED_WINDOW'
            results.append({'race_id':rid,'status':status,'scheduled_start':start.isoformat()})
            continue
        try:
            if prediction['frozen']!=frozen:
                raise ValueError('Frozen V6 mismatch')
            day,rn,cn=re.fullmatch(r'(\d{4}-\d{2}-\d{2})_R(\d+)C(\d+)',rid).groups()
            detail=store.race(day,int(rn),int(cn),'')
            data=store.race(day,int(rn),int(cn),'participants')
            if not isinstance(detail,dict) or not isinstance(data,dict):
                raise ValueError('Quote response unavailable')
            checked=datetime.now(timezone.utc)
            result=validate(prediction,detail,data.get('participants'),checked,p)
            dump(path,dict(result,race_id=rid,status='INDICATIVE_QUOTES_NO_BET',captured_at=checked.isoformat(),
                prediction_path=str(source),prediction_sha256=digest(source),policy_sha256=digest(policy),
                evidence_manifest=str(store.manifest_path),code_sha256=digest(__file__)))
            results.append({'race_id':rid,'status':'CAPTURED','path':str(path)})
        except (ValueError,KeyError,TypeError,OverflowError) as error:
            results.append({'race_id':rid,'status':'REJECTED','reason':str(error)})
    report={'status':'OBSERVATION_ONLY_NO_BET','checked_at':datetime.now(timezone.utc).isoformat(),
        'races':results,'requests':store.requests,'limits':p['scope']}
    dump('reports/pmu_quotes_status.json',report)
    dump('reports/pmu_quote_runs/'+batch+'.json',report)
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    main()
