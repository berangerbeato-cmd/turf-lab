"""14-day, two-race/day prospective observation. No odds or betting.

A fixed model checksum, explicit end date and small request budget limit scope.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo
from turf_lab.evidence import EvidenceStore,dump,races
from turf_lab.manual_value import timestamp
from turf_lab.shadow import score


def main():
    now=datetime.now(timezone.utc);today=now.astimezone(ZoneInfo('Europe/Paris')).date()
    protocol=json.loads(Path('config/shadow_protocol.json').read_text())
    window_active=today.isoformat()<=protocol['last_execution_date']
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as output:output.write('active='+str(window_active).lower()+'\n')
    if not window_active:
        print('Bounded observation window ended; no network request.');return
    model_hash=hashlib.sha256(Path('models/pilot_v1.json').read_bytes()).hexdigest()
    if model_hash!=protocol['model_sha256']:raise ValueError('Frozen shadow model changed; new protocol required')
    store=EvidenceStore(f'evidence/shadow/{today}',max_requests=65)
    path=Path('reports/shadow_v1.json');report=json.loads(path.read_text()) if path.exists() else {'protocol':protocol,'results':{},'capture_log':{}}
    latest={}
    for p in sorted(Path('predictions').glob('*/*/prediction.json')):
        d=json.loads(p.read_text());rid=d['race_id'];day=rid.split('_')[0]
        if not protocol['first_target_date']<=day<=protocol['last_target_date'] or d.get('model_sha256')!=model_hash:continue
        if timestamp(d['predicted_at'])>=timestamp(d['scheduled_start']):continue
        if rid not in latest or timestamp(d['predicted_at'])>timestamp(latest[rid][1]['predicted_at']):latest[rid]=(p,d)
    for rid,(p,d) in sorted(latest.items()):
        if report['results'].get(rid,{}).get('status') in ('SCORED','QUARANTINE'):continue
        if timestamp(d['scheduled_start'])>=now:continue
        match=re.fullmatch(r'(\d{4}-\d{2}-\d{2})_R(\d+)C(\d+)',rid)
        if not match:raise ValueError('Invalid stored race ID')
        day,rn,cn=match.groups();detail=store.race(day,int(rn),int(cn),'')
        if not detail:report['results'][rid]={'status':'PENDING','reason':'detail_unavailable'};continue
        if not (detail.get('arriveeDefinitive') or detail.get('isArriveeDefinitive')):continue
        raw=store.race(day,int(rn),int(cn),'participants')
        if not raw:report['results'][rid]={'status':'PENDING','reason':'participants_unavailable'};continue
        result=score(d,detail,raw.get('participants',[]));result.update(prediction_file=str(p),evaluated_at=now.isoformat(),date=day,venue=d['venue'],distance_m=d['distance_m'],start_type=d['start_type'])
        report['results'][rid]=result;dump(path,report)
    target=(today+timedelta(days=1)).isoformat()
    if protocol['first_target_date']<=target<=protocol['last_target_date']:
        programme=store.programme(target)
        if not programme:raise ValueError('Programme unavailable; preserved data will be saved by workflow')
        options=list(races(programme));chosen=[]
        for vincennes in (True,False):
            choices=[(r,c) for r,c in options if ('VINCENNES' in r['hippodrome']['libelleCourt'].upper())==vincennes]
            if choices:chosen.append(min(choices,key=lambda rc:rc[1]['heureDepart']))
        for meeting,course in chosen[:protocol['max_races_per_day']]:
            rn,cn=meeting['numOfficiel'],course['numOrdre'];rid=f'{target}_R{rn}C{cn}'
            if rid in latest:report['capture_log'][rid]={'status':'ALREADY_CAPTURED','prediction_file':str(latest[rid][0])};continue
            attempt=subprocess.run([sys.executable,'-m','scripts.predict_race','--date',target,'--reunion',str(rn),'--course',str(cn)],capture_output=True,text=True)
            report['capture_log'][rid]={'status':'CAPTURED' if attempt.returncode==0 else 'FAILED','returncode':attempt.returncode,'log':(attempt.stdout+attempt.stderr)[-2000:]}
            dump(path,report)
    scored=[r for r in report['results'].values() if r['status']=='SCORED']
    report['summary']={'scored_races':len(scored),'days':len({r['date'] for r in scored}),'status':'EXPERIMENTAL_NO_BET',
      'metrics':{k:mean(r[k] for r in scored) for k in ('log_loss','brier_multiclass','top1_hit','uniform_log_loss','uniform_brier_multiclass','uniform_top1_hit')} if scored else None,
      'note':'No result exists before the race; no ROI, no tuning, no automatic promotion.'}
    report['updated_at']=now.isoformat();dump(path,report)
    Path('reports/SHADOW_V1.md').write_text('# Observation prospective V1\n\n**EXPÉRIMENTAL — NO BET.**\n\n'+f"{len(scored)} course(s) évaluée(s), {report['summary']['days']} journée(s).\n\n"+'Résultats, captures, quarantaines et causes : shadow_v1.json. Modèle figé ; fenêtre de courses du 13 au 26 octobre 2026, deux courses maximum par jour. Après le 28 octobre, le workflow ne fait aucun appel réseau. Aucun ROI.\n')
    print(json.dumps(report['summary']))
    failed=[v for k,v in report['capture_log'].items() if k.startswith(target+'_') and v['status']=='FAILED']
    if failed:raise SystemExit('One or more predictions failed; checkpoint preserved')

if __name__=='__main__':main()
