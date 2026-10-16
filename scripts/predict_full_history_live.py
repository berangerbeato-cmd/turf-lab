"""Current-field research forecast, refusing stale history or late completion."""
import argparse, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from turf_lab.evidence import EvidenceStore, dump, start_type
from turf_lab.full_history_features import prepare
from turf_lab.live_history import load_available_history
from turf_lab.market_probabilities import markets
from turf_lab.pilot import probabilities


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reunion',type=int,required=True)
    parser.add_argument('--course',type=int,required=True)
    args=parser.parse_args()
    if not 1<=args.reunion<=30 or not 1<=args.course<=30: raise ValueError('Invalid race')
    now=datetime.now(timezone.utc); today=now.astimezone(ZoneInfo('Europe/Paris')).date()
    day=today.isoformat();rid=f'{day}_R{args.reunion}C{args.course}'
    records=load_available_history(today)
    root=Path('predictions_full_history')/day/(rid+'_'+now.strftime('%H%M%S'))
    store=EvidenceStore(root/'evidence',max_requests=2)
    course=store.race(day,args.reunion,args.course,'')
    raw=store.race(day,args.reunion,args.course,'participants')
    if not isinstance(course,dict) or not isinstance(raw,dict): raise ValueError('Missing live input')
    if course.get('discipline') not in ('ATTELE','TROT_ATTELE'): raise ValueError('Wrong discipline')
    # Only courses located in France are supported; use programme metadata to verify country.
    ps=EvidenceStore(root/'programme',max_requests=1)
    from turf_lab.evidence import races
    programme=ps.programme(day)
    matches=[(r,c) for r,c in races(programme) if r['numOfficiel']==args.reunion and c['numOrdre']==args.course]
    if len(matches)!=1: raise ValueError('French race not uniquely identified')
    start=datetime.fromtimestamp(course['heureDepart']/1000,timezone.utc)
    parts=raw.get('participants',[])
    if datetime.now(timezone.utc)>=start or course.get('arriveeDefinitive') or course.get('isArriveeDefinitive'): raise ValueError('Race already started')
    if not 10<=len(parts)<=20 or any(p.get('statut')!='PARTANT' for p in parts): raise ValueError('Field outside calibrated cohort')
    if any(p.get('ordreArrivee') or p.get('tempsObtenu') for p in parts): raise ValueError('Postrace fields')
    target=dict(date=day,race_id=rid,venue=matches[0][0]['hippodrome']['libelleCourt'],country='FRA',start_type=start_type(course),distance_m=course['distance'],scheduled_start_ms=course['heureDepart'],course=course,participants=parts)
    rows=prepare(records+[target]);row=next(r for r in rows if r['race_id']==rid)
    mb=Path('models/full_history/classic.json').read_bytes()
    lock=json.loads(Path('models/full_history/frozen.json').read_text())
    digest=hashlib.sha256(mb).hexdigest()
    if digest!=lock['model_hashes']['classic.json']:raise ValueError('Model hash mismatch')
    probs=probabilities(row,json.loads(mb)); t=lock['temperatures']['classic']
    probs={n:p**(1/t) for n,p in probs.items()}; total=sum(probs.values());probs={n:p/total for n,p in probs.items()}
    numbers=sorted(probs);market=markets(numbers,[probs[n] for n in numbers]);best=max(probs,key=probs.get)
    cfile=json.loads(Path('reports/market_evaluation/calibration_frozen.json').read_text())
    if cfile['classic_sha256']!=digest:raise ValueError('Calibration model mismatch')
    c=cfile['calibrators']['place3'];p=float(market['place3'][1][numbers.index(best)])
    p=1/(1+math.exp(-(c['slope']*math.log(p/(1-p))+c['intercept'])))
    finished=datetime.now(timezone.utc)
    if finished>=start:
        dump(root/'blocked.json',dict(status='LATE_COMPLETION_NO_PRESTART_FORECAST',completed_at=finished.isoformat()))
        raise ValueError('Calculation finished after scheduled departure')
    names={p['numPmu']:p['nom'] for p in parts}
    result=dict(race_id=rid,status='RESEARCH_NO_BET',predicted_at=finished.isoformat(),scheduled_start=start.isoformat(),history_checked_through=str(today.fromordinal(today.toordinal()-1)),model_sha256=digest,
        ranking=[dict(number=n,name=names[n],win_probability=probs[n]) for n in sorted(probs,key=probs.get,reverse=True)],selected_place=dict(number=best,name=names[best],probability=p,break_even=1/p))
    dump(root/'prediction.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
