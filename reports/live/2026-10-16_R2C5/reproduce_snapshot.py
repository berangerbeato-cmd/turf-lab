import gzip,json,hashlib,math
from pathlib import Path
from datetime import datetime,timezone
from turf_lab.evidence import start_type
from turf_lab.full_history_features import prepare
from turf_lab.pilot import probabilities
from turf_lab.market_probabilities import markets
root=Path('/tmp/r2c5-live')
parts=json.loads(gzip.decompress((root/'2026-10-16_R2C5_participants.json.gz').read_bytes()))['participants']
course=json.loads(gzip.decompress((root/'2026-10-16_R2C5_course_detail.json.gz').read_bytes()))
assert len(parts)==14 and all(p['statut']=='PARTANT' for p in parts)
assert all(not p.get('ordreArrivee') and not p.get('tempsObtenu') for p in parts)
assert datetime.now(timezone.utc).timestamp()*1000<course['heureDepart']
names={p['numPmu']:p['nom'] for p in parts}
assert names[14]=='LADY DE MONGOCHY' and names[9]=='LILI DU CHERISAY'
p=json.loads(Path('config/full_history_protocol.json').read_text())
records=[]
for manifest in sorted(Path('data').glob('month_*/manifest.json')):
 month=manifest.parent.name[6:]
 if month in p['excluded_months']:continue
 for e in json.loads(manifest.read_text())['partitions']:
  raw=gzip.decompress(Path(e['file']).read_bytes())
  assert hashlib.sha256(raw).hexdigest()==e['sha256']
  r=json.loads(raw)
  if r['race_id'] in p['excluded_races'] or r['date']>='2026-10-16':continue
  records.append(r)
assert len({r['race_id'] for r in records})==len(records)
last=max(r['date'] for r in records)
print('History:',len(records),'last date:',last,flush=True)
target=dict(date='2026-10-16',race_id='2026-10-16_R2C5',venue='BORELY',country='FRA',start_type=start_type(course),distance_m=3000,scheduled_start_ms=course['heureDepart'],course=course,participants=parts)
records.append(target)
rows=prepare(records)
r=next(r for r in rows if r['race_id']==target['race_id'])
model_bytes=Path('models/full_history/classic.json').read_bytes()
frozen=json.loads(Path('models/full_history/frozen.json').read_text())
assert hashlib.sha256(model_bytes).hexdigest()==frozen['model_hashes']['classic.json']
assert frozen['temperatures']['classic']==1
ps=probabilities(r,json.loads(model_bytes))
number_list=sorted(ps)
m=markets(number_list,[ps[n] for n in number_list])
c=json.loads(Path('reports/market_evaluation/calibration_frozen.json').read_text())['calibrators']['place3']
best=max(ps,key=ps.get)
raw=float(m['place3'][1][number_list.index(best)])
cal=1/(1+math.exp(-(c['slope']*math.log(raw/(1-raw))+c['intercept'])))
now=datetime.now(timezone.utc)
out=dict(race_id=target['race_id'],predicted_at=now.isoformat(),before_scheduled_start=now.timestamp()*1000<course['heureDepart'],history_through=last,history_races=len(records)-1,model_sha256=hashlib.sha256(model_bytes).hexdigest(),ranking=[dict(number=n,name=names[n],win_probability=ps[n]) for n in sorted(ps,key=ps.get,reverse=True)],selected_place=dict(number=best,name=names[best],probability=cal,break_even=1/cal),limits=['Research model; no guaranteed performance','Historical input gaps retained','No verified placed price; no value verdict'])
Path('/tmp/r2c5-live/prediction.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2),flush=True)
