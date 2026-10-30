"""Dated supplemental history diagnostics. Never mutate frozen feature vectors."""
import re
from datetime import date,timedelta
from urllib.parse import quote
from pathlib import Path
from collect import BASE
from turf_lab.evidence import EvidenceStore
from turf_lab.history import race_day,summarize_run
from turf_lab.pilot import features


def normalized_name(s):return ' '.join(str(s).upper().split())

def normalize_history(payload, runner, target_day):
    if not isinstance(payload,dict) or not isinstance(payload.get('runner'),dict) or not isinstance(payload['runner'].get('racesRun'),list):
        raise ValueError('Missing individual history')
    accepted={};excluded=[]
    for raw in payload['runner']['racesRun']:
        day=race_day(raw).isoformat()
        if day>=target_day:
            excluded.append({'date':day,'reason':'target_or_future_day'});continue
        p=raw.get('raceRunParticipant',{})
        if normalized_name(p.get('horseName'))!=normalized_name(runner['nom']):
            raise ValueError('Individual history identity mismatch')
        if raw.get('discipline')!='ATTELE':continue
        status=p.get('place',{}).get('arrivalStatus')
        if status=='NON_PARTANT':continue
        summary=summarize_run(raw)
        if not summary['disqualified'] and not isinstance(summary['rank'],int):
            excluded.append({'date':day,'reason':'unknown_outcome'});continue
        if not summary['venue'] or not isinstance(summary['race_number'],int):
            raise ValueError('Missing dated race identity')
        key=(day,normalized_name(summary['venue']),summary['race_number'])
        if key in accepted and accepted[key]!=summary:raise ValueError('Conflicting individual history')
        accepted[key]=summary
    return sorted(accepted.values(),key=lambda r:r['date'],reverse=True),excluded


def reconcile(runner,frame,payload,target_day):
    rows,excluded=normalize_history(payload,runner,target_day)
    cutoff=(date.fromisoformat(target_day)-timedelta(days=60)).isoformat()
    available=[r for r in rows if cutoff<=r['date']<target_day]
    prior=frame.get('history',[])
    def key_old(r):
        m=re.search(r'C(\d+)$',r.get('race_id',''))
        return (r['date'],normalized_name(r['venue']),int(m.group(1)) if m else None)
    merged={key_old(r):r for r in prior};missing=[];conflicts=[]
    for r in available:
        key=(r['date'],normalized_name(r['venue']),r['race_number'])
        row={'date':r['date'],'venue':r['venue'],'rank':r['rank'],'dq':r['disqualified'],
            'status':r['arrival_status'],'source':'PMU_INDIVIDUAL_HISTORY'}
        if key in merged:
            old=merged[key]
            if bool(old['dq'])!=row['dq'] or old.get('rank')!=row['rank']:conflicts.append({'key':key,'archive':old,'individual':row})
        else:missing.append(r);merged[key]=row
    recent=sorted(merged.values(),key=lambda r:r['date'],reverse=True)[:5]
    return {'number':runner['numPmu'],'name':runner['nom'],'status':'CONFLICT' if conflicts else 'MODEL_HISTORY_INCOMPLETE' if missing else 'NO_DISCREPANCY_IN_RETURNED_WINDOW',
        'snapshot_career_starts':runner.get('nombreCourses'),'model_recent_starts':len(prior),
        'individual_prior_starts_returned':len(rows),'missing_recent_starts':missing,'conflicts':conflicts,
        'excluded':excluded,'supplemented_recent_features_for_research':features(recent,target_day) if not conflicts else None,
        'frozen_features_unchanged':True,'recommendations_allowed':False,
        'limits':'Returned history may be truncated. No assertion of complete career. Supplemented features are not fed to frozen model weights.'}


def check_all(target,models,evidence_root,max_requests=None):
    frames={r['number']:r for r in models['v6']['runners']}
    parts=[r for r in target['participants'] if r['statut']=='PARTANT']
    store=EvidenceStore(evidence_root,max_requests=len(parts) if max_requests is None else max_requests)
    out=[]
    for runner in parts:
        try:
            horse_id=runner.get('idCheval')
            if not horse_id:raise ValueError('No source horse ID')
            payload=store.get(BASE.rsplit('/',1)[0]+'/program/'+quote(horse_id,safe='')+'/light-performances','horse_'+str(runner['numPmu']))
            out.append(reconcile(runner,frames[runner['numPmu']],payload,target['date']))
        except (ValueError,KeyError,TypeError,OSError,RuntimeError) as e:
            out.append({'number':runner['numPmu'],'name':runner['nom'],'status':'UNVERIFIED','reason':str(e)})
    bad=[r['number'] for r in out if r['status'] in ('CONFLICT','MODEL_HISTORY_INCOMPLETE','UNVERIFIED')]
    return {'status':'RESEARCH_HISTORY_WARNING' if bad else 'CHECKED_RETURNED_HISTORY_ONLY',
        'affected_runners':bad,'runners':out,'evidence_manifest':str(Path(evidence_root)/'manifest.json'),
        'market_independent':True,'frozen_features_changed':False,'recommendations_allowed':False}
