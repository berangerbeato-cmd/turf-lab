"""Prospective scoring: never fix old probabilities after seeing a non-runner."""
import math
from turf_lab.manual_value import timestamp
from turf_lab.quality import horse_id


def score(prediction, detail, participants):
    if not (detail.get('arriveeDefinitive') or detail.get('isArriveeDefinitive')):
        return {'status':'PENDING','reason':'result_not_definitive'}
    if timestamp(prediction['predicted_at'])>=timestamp(prediction['scheduled_start']):
        return {'status':'QUARANTINE','reason':'prediction_not_before_start'}
    active=[r for r in prediction['runners'] if r['status']=='PARTANT']
    current=[r for r in participants if r.get('statut')=='PARTANT']
    if any(r.get('statut') not in ('PARTANT','NON_PARTANT') for r in participants):
        return {'status':'QUARANTINE','reason':'unknown_status'}
    old_ids={(r['number'],r['horse_id']) for r in active};new_ids={(r['numPmu'],horse_id(r)) for r in current}
    if len(old_ids)!=len(active) or len(new_ids)!=len(current) or old_ids!=new_ids:
        return {'status':'QUARANTINE','reason':'field_changed_or_identity_mismatch'}
    winners=[r['numPmu'] for r in current if r.get('ordreArrivee')==1]
    order=detail.get('ordreArrivee') or []
    if len(winners)!=1 or not order or order[0]!=winners:
        return {'status':'QUARANTINE','reason':'winner_ambiguous_or_inconsistent'}
    winner=next(r for r in current if r['numPmu']==winners[0])
    if str(winner.get('incident','')).startswith('DISQUALIFIE') or winner.get('incident')=='DISTANCE':
        return {'status':'QUARANTINE','reason':'disqualified_winner'}
    p={r['number']:r['probability'] for r in active};n=len(p)
    if not n or any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in p.values()) or abs(sum(p.values())-1)>1e-8:
        return {'status':'QUARANTINE','reason':'invalid_probabilities'}
    best=min(p,key=lambda k:(-p[k],k))
    return {'status':'SCORED','winner':winners[0],'log_loss':-math.log(max(1e-15,p[winners[0]])),
      'brier_multiclass':sum((v-int(k==winners[0]))**2 for k,v in p.items()),'top1_hit':int(best==winners[0]),
      'uniform_log_loss':math.log(n),'uniform_brier_multiclass':1-1/n,
      'uniform_top1_hit':int(min(p)==winners[0]),'probabilities':p,'active_runners':n}
