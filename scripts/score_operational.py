"""Score immutable genuine prestart snapshots against verified daily results."""
import json, math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from turf_lab.history_sync import History
from turf_lab.month_history import identity
from turf_lab.evidence import dump


def main():
 history=History();cache={};scores=[];pending=[];excluded=[]
 # One earliest valid capture per race for aggregate scores; every snapshot remains archived.
 seen=set()
 for path in sorted(Path('predictions_operational').glob('*/*/prediction.json')):
  p=json.loads(path.read_text());rid=p['race_id']
  if rid in seen:continue
  if datetime.fromisoformat(p['predicted_at'])>=datetime.fromisoformat(p['scheduled_start']):
   excluded.append({'race_id':rid,'reason':'late_prediction'});continue
  day=p['target_snapshot']['date']
  if day not in cache:cache[day]={r['race_id']:r for r in history.day(day)['records']}
  actual=cache[day].get(rid)
  if actual is None:pending.append(rid);continue
  before={r['numPmu']:(identity(r),r['statut']) for r in p['target_snapshot']['participants']}
  after={r['numPmu']:(identity(r),r['statut']) for r in actual['participants']}
  if before!=after:
   excluded.append({'race_id':rid,'reason':'field_changed_no_posthoc_renormalization'});continue
  winners=[r['numPmu'] for r in actual['participants'] if r.get('ordreArrivee')==1]
  if len(winners)!=1:excluded.append({'race_id':rid,'reason':'ambiguous_winner'});continue
  seen.add(rid);winner=winners[0]
  for model,result in p['models'].items():
   probs={int(n):v for n,v in result['probabilities'].items() if before[int(n)][1]=='PARTANT'}
   rows=[{'p':v,'y':int(n==winner)} for n,v in probs.items()]
   scores.append({'race_id':rid,'snapshot':str(path),'model':model,'version':result['version'],'venue':actual['venue'],
    'start_type':actual['start_type'],'log_loss':-math.log(max(1e-15,probs[winner])),
    'brier':sum((r['p']-r['y'])**2 for r in rows),'top1':int(min(probs,key=lambda n:(-probs[n],n))==winner),'calibration_rows':rows})
 aggregates={}
 for model in sorted({s['model'] for s in scores}):
  subset=[s for s in scores if s['model']==model];bins=[]
  for i in range(10):
   rs=[r for s in subset for r in s['calibration_rows'] if min(int(r['p']*10),9)==i]
   if rs:bins.append({'range':[i/10,(i+1)/10],'n':len(rs),'predicted':sum(r['p'] for r in rs)/len(rs),'observed':sum(r['y'] for r in rs)/len(rs)})
  aggregates[model]={'races':len(subset),**{k:sum(s[k] for s in subset)/len(subset) for k in ('log_loss','brier','top1')},'calibration':bins}
 dump('reports/operational/prospective_scores.json',{'checked_at':datetime.now(timezone.utc).isoformat(),'selection':'earliest valid snapshot per race','metrics':aggregates,'scores':scores,'pending':pending,'excluded':excluded,'roi':None,'roi_reason':'No verified operator settlement joined; screenshot replay excluded.'})
if __name__=='__main__':main()
