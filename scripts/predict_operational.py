"""Single frozen-model entrypoint. No fit, market feature or implicit V1 fallback."""
import argparse, gzip, hashlib, json, math, subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.shadow_connections import live_record
from scripts.v6_holdout import verify as verify_v6
from turf_lab.opposition import augment as opposition
from turf_lab.evidence import EvidenceStore, dump, races
from turf_lab.history_sync import audit, summarize
from turf_lab.full_history_features import augment_continuous
from turf_lab.month_history import build_history
from turf_lab.connections import augment_connections
from turf_lab.demographics_tandem import augment as demographics, candidate
from turf_lab.pilot import probabilities
from turf_lab.market_probabilities import markets
from turf_lab.recommendation_policy import recommendation_state


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_history(today, target_day):
    states = audit(today)
    coverage = summarize(states, today)
    yesterday = (today-timedelta(days=1)).isoformat()
    recent = next(s for s in states if s['date']==yesterday)
    if recent['programme'] is None or (recent['expected'] and not recent['records']):
        raise ValueError('History has not reached yesterday; run daily refresh')
    # Only verified records; gaps remain explicit, never an all-years completeness gate.
    exclusions=json.loads(Path('config/full_history_protocol.json').read_text())['excluded_races']
    coverage['model_excluded_races']=exclusions
    records = [r for s in states for r in s['records'] if r['date'] < target_day and r['race_id'] not in exclusions
               and sum(p.get('ordreArrivee')==1 for p in r['participants'])==1]
    if len({r['race_id'] for r in records}) != len(records):
        raise ValueError('Duplicate history')
    # Preserve exactly the fields read by the frozen feature engines, avoiding raw market payloads in RAM.
    keys=('numPmu','nom','nomMere','nomPere','idCheval','statut','ordreArrivee','incident','driver','entraineur','deferre','age','sexe','reductionKilometrique','tempsObtenu','handicapDistance')
    compact=[{**{k:r[k] for k in ('date','race_id','venue','country','start_type','distance_m','scheduled_start_ms')},
              'course':{'conditions':r.get('course',{}).get('conditions')},
              'participants':[{k:p[k] for k in keys if k in p} for p in r['participants']]} for r in records]
    return compact, coverage


def classic_frame(records, race_id):
    rows=build_history(records,lookback_days=60)
    # Raw history lists are not read by any subsequent Classic feature function.
    for row in rows:
        for runner in row['runners']:runner.pop('history',None)
    rows=augment_continuous(rows)
    target_day=next(r['date'] for r in rows if r['race_id']==race_id)
    cutoff=(datetime.fromisoformat(target_day).date()-timedelta(days=60)).isoformat()
    # Elo is continuous from the entire archive. Connection/tandem inputs older than
    # their maximum 60-day window cannot affect the target and need no output frame.
    rows=[r for r in rows if r['date']>=cutoff]
    rows=augment_connections(rows,records,window=30,strength=20,equipment_days=60)
    rows=demographics(rows,records,window=60,strength=20)
    return candidate([next(r for r in rows if r['race_id']==race_id)],'combined')[0]


def compute_reference(history, target):
    # Original V6 feature pipeline and frozen verification; no V5/V7 inference.
    _, lock, p, models = verify_v6()
    if any(r['date'] >= target['date'] for r in history):
        raise ValueError('History must precede target day')
    records = history + [target]
    rows = augment_connections(opposition(build_history(records, lookback_days=p['lookback_days'])), records,
        window=p['connections_window_days'], strength=p['connections_prior_strength'],
        equipment_days=p['equipment_history_days'])
    v6p = json.loads(Path('config/demographics_tandem_v6_protocol.json').read_text())
    rows = demographics(rows, records, v6p['tandem_window_days'], v6p['prior_strength'])
    row = next(r for r in rows if r['race_id'] == target['race_id'])
    frame = candidate([row], 'combined')[0]
    return lock, {'probabilities': probabilities(frame, models['v6']), 'runners': frame['runners']}


def compute_all(history, target):
    lock_files=json.loads(Path('config/operational_frozen.json').read_text())['files_sha256']
    if any(digest(f)!=sha for f,sha in lock_files.items()):raise ValueError('Operational frozen dependency changed')
    legacy_history=[r for r in history if r['date'][:4]==target['date'][:4]]
    lock6, reference = compute_reference(legacy_history, target)
    print('Frozen V6 computed',flush=True)
    output = {'v6': reference}
    files = {'v6':'models/demographics_tandem_v6_candidates.json',
             'classic_full':'models/full_history/classic.json'}
    policy = json.loads(Path('config/full_history_protocol.json').read_text())
    full_history = [r for r in history if r['date'][:7] not in policy['excluded_months']
                    and r['race_id'] not in policy['excluded_races']]
    lock = json.loads(Path('models/full_history/frozen.json').read_text())
    if digest(files['classic_full']) != lock['model_hashes']['classic.json']:
        raise ValueError('Full-history model hash mismatch')
    if digest('config/full_history_protocol.json') != lock['provenance']['protocol_sha256']:
        raise ValueError('Full-history protocol hash mismatch')
    records=full_history+[target]
    row=classic_frame(records,target['race_id'])
    p = probabilities(row,json.loads(Path(files['classic_full']).read_text()))
    t = lock['temperatures']['classic']; p={n:v**(1/t) for n,v in p.items()}
    z=sum(p.values()); p={n:v/z for n,v in p.items()}
    print('Frozen Classic full computed',flush=True)
    output['classic_full']={'probabilities':p,'runners':row['runners']}
    active={r['numPmu'] for r in target['participants'] if r['statut']=='PARTANT'}
    all_numbers={r['numPmu'] for r in target['participants']}
    for name,result in output.items():
        probs=result['probabilities']
        if set(probs)!=all_numbers or any(not math.isfinite(v) or not 0<=v<=1 for v in probs.values()):
            raise ValueError('Missing runner or invalid probability: '+name)
        if abs(sum(probs[n] for n in active)-1)>1e-9 or any(probs[n]!=0 for n in all_numbers-active):
            raise ValueError('Invalid nonrunner normalization: '+name)
        result['model_file']=files[name];result['model_sha256']=digest(files[name])
        result['version']=name+'@'+result['model_sha256'][:12]
    place={'status':'EV placé non calculable','reason':'No evidenced prestart place quote; V6 has no calibrated placement model.'}
    if 10<=len(active)<=20 and len(active)==len(all_numbers):
        cf='reports/market_evaluation/calibration_frozen.json'
        cal=json.loads(Path(cf).read_text())
        if cal['classic_sha256'] != digest(files['classic_full']):raise ValueError('Place calibration mismatch')
        numbers=sorted(p);best=min(numbers,key=lambda n:(-p[n],n))
        raw=float(markets(numbers,[p[n] for n in numbers])['place3'][1][numbers.index(best)])
        c=cal['calibrators']['place3'];q=1/(1+math.exp(-(c['slope']*math.log(raw/(1-raw))+c['intercept'])))
        place.update(number=best,model='classic_full',probability=q,paid_places=3,
            fair_odds=1/q,calibration_sha256=digest(cf),
            scope='Exploratory calibrated top selection only; 10-20 starters, no nonrunners; operator must confirm three paid places.')
    return output,place,{'v6':lock6,'classic_full':lock}


def run(day,reunion,course):
    now=datetime.now(timezone.utc);today=now.astimezone(ZoneInfo('Europe/Paris')).date()
    delta=(datetime.fromisoformat(day).date()-today).days
    if not 0<=delta<=7 or not 1<=reunion<=30 or not 1<=course<=30:raise ValueError('Invalid race parameters')
    rid=f'{day}_R{reunion}C{course}';batch=now.strftime('%Y%m%dT%H%M%S%fZ')
    root=Path('predictions_operational')/day/(rid+'_'+batch)
    store=EvidenceStore(root/'evidence',max_requests=2)
    programme=store.programme(day)
    matches=[(r,c) for r,c in races(programme) if r['numOfficiel']==reunion and c['numOrdre']==course]
    if len(matches)!=1:raise ValueError('French harness race not uniquely found')
    meeting,detail=matches[0]
    raw=store.race(day,reunion,course,'participants')
    target=live_record(day,meeting,detail,(raw or {}).get('participants'),datetime.now(timezone.utc))
    history,coverage=load_history(today,day)
    print(json.dumps({'stage':'history_verified','races':len(history),'through':coverage['last_collected_day']}),flush=True)
    models,place,locks=compute_all(history,target)
    finished=datetime.now(timezone.utc)
    start=datetime.fromtimestamp(detail['heureDepart']/1000,timezone.utc)
    if finished>=start:raise ValueError('Race started during calculation')
    for m in models.values():m['calculated_at']=finished.isoformat()
    sha=hashlib.sha256(json.dumps(history,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    source_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip()
    output=dict(**recommendation_state(),status='PRESTART_RESEARCH',race_id=rid,predicted_at=finished.isoformat(),scheduled_start=start.isoformat(),
        primary_model='v6',models=models,place=place,target_snapshot=target,history_sha256=sha,history_source_tree=source_tree,history_loader='scripts.predict_operational.load_history',
        history_coverage=coverage,history_gap_days=(datetime.fromisoformat(day).date()-datetime.fromisoformat(coverage['last_collected_day']).date()).days-1,
        frozen=locks,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        requires_runner_recheck=True,odds_used_as_features=False,
        code_sha256={str(f):digest(f) for folder in ('scripts','turf_lab') for f in Path(folder).glob('*.py')})
    dump(root/'prediction.json',output)
    dump('reports/operational/latest.json',{**recommendation_state(),'prediction':str(root/'prediction.json'),'race_id':rid,'predicted_at':finished.isoformat(),
        'models':{n:{k:v for k,v in m.items() if k!='runners'} for n,m in models.items()},'place':place,
        'scheduled_start':start.isoformat(),'history_through':coverage['last_collected_day'],
        'runners':[{'number':p['numPmu'],'name':p['nom'],'status':p['statut']} for p in target['participants']]} )
    print(str(root/'prediction.json'),flush=True)
    return root/'prediction.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--date',required=True);p.add_argument('--reunion',type=int,required=True);p.add_argument('--course',type=int,required=True)
    a=p.parse_args();run(a.date,a.reunion,a.course)
if __name__=='__main__':main()
