"""Replay verified prestart evidence; isolated partial feature repair, no promotion."""
import gzip,hashlib,json
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from turf_lab.individual_history_check import reconcile,normalize_history,venue_key
from turf_lab.available_history_operational import verify_active
from turf_lab.available_history_research import recent_values
from turf_lab.pilot import probabilities
from turf_lab.month_history import identity
from scripts.predict_operational import load_history

ROOT=Path('reports/history_reconciliation_2026-11-15')
SOURCE=Path('predictions_operational/2026-11-15/2026-11-15_R3C5_20261115T115929320844Z/prediction.json')

def main():
    raw=SOURCE.read_bytes();p=json.loads(raw);target=p['target_snapshot'];day=target['date']
    evidence=SOURCE.parent/'individual_history_evidence';manifest=json.loads((evidence/'manifest.json').read_text())
    frames={r['number']:r for r in p['models']['v6']['runners']};checks=[];payloads={}
    for runner in target['participants']:
        if runner['statut']!='PARTANT':continue
        n=runner['numPmu'];meta=manifest['horse_'+str(n)];body=gzip.decompress((evidence/meta['file']).read_bytes())
        assert hashlib.sha256(body).hexdigest()==meta['sha256']
        assert datetime.fromisoformat(meta['fetched_at_utc'])<datetime.fromisoformat(p['scheduled_start'])
        payloads[n]=json.loads(body);checks.append(reconcile(runner,frames[n],payloads[n],day))
    ROOT.mkdir(parents=True,exist_ok=True)
    audit={'race_id':p['race_id'],'source_sha256':hashlib.sha256(raw).hexdigest(),'checks':checks,
           'affected_before':p['individual_history_check']['affected_runners'],
           'affected_after':[c['number'] for c in checks if c['status']!='NO_DISCREPANCY_IN_RETURNED_WINDOW']}
    (ROOT/'diagnostic.json').write_text(json.dumps(audit,indent=2))
    print('Reconciled:',audit['affected_after'],flush=True)
    # Rebuild all available last-five and DQ20 histories, not V6's 60-day window.
    history,coverage=load_history(datetime.fromisoformat(day).date(),day)
    scope=json.loads(Path('config/full_history_protocol.json').read_text())
    history=[r for r in history if r['date'][:7] not in scope['excluded_months']]
    model=p['models']['available_history_v3'];frame={'runners':deepcopy(model['runners'])}
    own={identity(r):[] for r in target['participants']};total=dq=0
    for race in sorted(history,key=lambda r:(r['date'],r['race_id'])):
        for r in race['participants']:
            if r.get('statut')=='NON_PARTANT':continue
            incident=str(r.get('incident') or '');fault=incident.startswith('DISQUALIFIE') or incident=='DISTANCE';rank=r.get('ordreArrivee')
            if fault or isinstance(rank,int) and rank>0:total+=1;dq+=int(fault)
            key=identity(r)
            if key in own:own[key].append(dict(date=race['date'],venue=race['venue'],race_number=race.get('course_number') or int(race['race_id'].split('C')[-1]),rank=rank,status=incident,dq=fault))
    # Reproduce the nine original V3 inputs before evaluating any repair.
    for r in frame['runners']:
        if r['non_runner']:continue
        rows=own[r['horse_id']];known=[int(h['dq']) for h in rows if h['dq'] or isinstance(h['rank'],int) and h['rank']>0][-20:]
        trailing=0
        for v in reversed(known):
            if not v:break
            trailing+=1
        baseline=recent_values(list(reversed(rows))[:5],day)+[(sum(known)+10*dq/total)/(len(known)+10),len(known)/20,float(known[-1]) if known else None,trailing/20]
        original=r['features'][:5]+r['features'][-4:]
        if any((a is None)!=(b is None) or a is not None and abs(a-b)>1e-10 for a,b in zip(baseline,original)):
            raise ValueError('Baseline features do not reproduce for '+str(r['number']))
    additions=[]
    for r in frame['runners']:
        if r['non_runner']:continue
        n=r['number'];rows=own[r['horse_id']];merged={(h['date'],venue_key(h['venue']),h['race_number']):h for h in rows}
        participant=next(x for x in target['participants'] if x['numPmu']==n)
        for h in normalize_history(payloads[n],participant,day)[0]:
            key=(h['date'],venue_key(h['venue']),h['race_number'])
            if key in merged:
                old=merged[key]
                if bool(old['dq'])!=h['disqualified'] or old['rank']!=h['rank']:raise ValueError('Conflicting history '+str((n,key)))
            else:
                item=dict(date=h['date'],venue=h['venue'],race_number=h['race_number'],rank=h['rank'],status=h['arrival_status'],dq=h['disqualified'])
                merged[key]=item;additions.append(dict(number=n,**item));total+=1;dq+=int(item['dq'])
        own[r['horse_id']]=sorted(merged.values(),key=lambda h:(h['date'],h['race_number']))
    for r in frame['runners']:
        if r['non_runner']:continue
        rows=own[r['horse_id']];r['features'][:5]=recent_values(list(reversed(rows))[:5],day)
        known=[int(h['dq']) for h in rows if h['dq'] or isinstance(h['rank'],int) and h['rank']>0][-20:]
        trailing=0
        for v in reversed(known):
            if not v:break
            trailing+=1
        r['features'][-4:]=[(sum(known)+10*dq/total)/(len(known)+10),len(known)/20,float(known[-1]) if known else None,trailing/20]
    policy,temp=verify_active();m=json.loads(Path(policy['model_file']).read_text());probs=probabilities(frame,m)
    powered={n:v**(1/temp) for n,v in probs.items()};z=sum(powered.values());probs={n:v/z for n,v in powered.items()}
    changes=[dict(number=r['number'],name=r['name'],before=model['probabilities'][str(r['number'])],after=probs[r['number']]) for r in frame['runners'] if not r['non_runner']]
    result=dict(status='RETROSPECTIVE_PARTIAL_FEATURE_SENSITIVITY_NOT_VALIDATION',source_sha256=hashlib.sha256(raw).hexdigest(),model_sha256=model['model_sha256'],temperature=temp,history_through=coverage['last_collected_day'],additions=additions,comparison=changes,recommendations_allowed=False,limits=['Only last-five and DQ20 rebuilt; Elo/connections/tandem unchanged.','Truncated individual history cannot prove complete career.','Old fitted weights with enriched features: separate validation required.','Historical source snapshots preserved; no result of target race used.'])
    (ROOT/'sensitivity.json').write_text(json.dumps(result,indent=2))
    assert SOURCE.read_bytes()==raw
    print(json.dumps(changes,indent=2))
if __name__=='__main__':main()
