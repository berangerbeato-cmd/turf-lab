"""Paper-only, prestart selections and evidence-backed operator settlements."""
import hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
from turf_lab.operational_quotes import compare,stamp

PROTOCOL=Path('config/sg_ev_probability_comparison_v2.json')
ROOT=Path('reports/sg_ev_probability_comparison_v2')

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def select(prediction,quotes,protocol,now=None):
    now=now or datetime.now(timezone.utc);start=stamp(prediction['scheduled_start'])
    if prediction['target_snapshot']['date']<protocol['first_eligible_race_date']:raise ValueError('Before prospective start')
    if not stamp(prediction['predicted_at'])<=now<start:raise ValueError('Selection must be recorded before departure')
    observed=stamp(quotes['observed_at'])
    if not 0<(start-observed).total_seconds()<=900 or observed>now:raise ValueError('Quote outside prestart window')
    model=prediction['models'][protocol['model']]
    if model['model_sha256']!=protocol['model_sha256']:raise ValueError('Frozen model mismatch')
    active={p['numPmu'] for p in prediction['target_snapshot']['participants'] if p['statut']=='PARTANT'}
    if {q['number'] for q in quotes['quotes']}!=active:raise ValueError('Complete active field required')
    result=compare(prediction,quotes)
    rows=sorted(result['rows'],key=lambda r:(-r['models'][protocol['model']]['probability'],r['number']))
    probs=[r['models'][protocol['model']]['probability'] for r in rows]
    if any(not math.isfinite(p) or p<0 or p>1 for p in probs) or abs(sum(probs)-1)>1e-8:raise ValueError('Invalid probabilities')
    strategies={}
    for rule in protocol['strategies']:
        strategies[rule['id']]=[r['number'] for rank,r in enumerate(rows,1)
          if rank<=rule.get('max_rank',len(rows)) and
          r['models'][protocol['model']]['probability']+1e-12>=rule.get('min_probability',0) and
          r['models'][protocol['model']]['ev']+1e-12>=protocol['minimum_ev']]
    checks=prediction.get('individual_history_check',{})
    return dict(race_id=prediction['race_id'],operator=quotes['operator'],scheduled_start=prediction['scheduled_start'],
        selected_at=now.isoformat(),observed_at=quotes['observed_at'],protocol_sha256=digest(protocol),
        model_sha256=model['model_sha256'],prediction_sha256=digest(prediction),quote_sha256=digest(quotes),
        stake_eur_per_runner=protocol['stake_eur_per_runner'],active=sorted(active),strategies=strategies,
        history_clean=checks.get('status')=='CHECKED_RETURNED_HISTORY_ONLY',
        history_warnings=checks.get('affected_runners',[]),recommendations_allowed=False)

def archive(prediction,quotes,root=ROOT):
    protocol=json.loads(PROTOCOL.read_text());path=root/'selections'/(prediction['race_id']+'.json')
    if path.exists():return json.loads(path.read_text()) # First qualifying selection is immutable.
    record=select(prediction,quotes,protocol)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(record,f,indent=2)
    return record

def settle(selection,evidence):
    if evidence is None:return {'status':'PENDING','reason':'Missing actual operator payouts'}
    if evidence.get('race_id')!=selection['race_id'] or evidence.get('operator')!=selection['operator']:raise ValueError('Settlement identity mismatch')
    if evidence.get('verified') is not True or not evidence.get('source_evidence') or evidence.get('final') is not True:raise ValueError('Unverified final settlement')
    if stamp(evidence['observed_at'])<stamp(selection['scheduled_start']):raise ValueError('Settlement before race')
    if evidence.get('field_changed') is True:return {'status':'REVIEW','reason':'Changed field/refunds require review'}
    # Explicit paid amount for every selected number: losers 0, refunds 1, dead heats actual dividend.
    payouts=evidence.get('sg_total_return_per_eur',{})
    selected={n for ns in selection['strategies'].values() for n in ns}
    if any(str(n) not in payouts for n in selected):return {'status':'PENDING','reason':'Incomplete operator payouts'}
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in payouts.values()):raise ValueError('Invalid paid return')
    winners=evidence.get('winner_numbers')
    if not isinstance(winners,list) or any(n not in selection['active'] for n in winners):raise ValueError('Missing verified winners')
    stake=selection['stake_eur_per_runner'];out={}
    for key,ns in selection['strategies'].items():
        cost=len(ns)*stake;ret=sum(payouts[str(n)]*stake for n in ns)
        out[key]=dict(bets=len(ns),wins=sum(n in winners for n in ns),staked=cost,returned=ret,net=ret-cost)
    return {'status':'SETTLED','strategies':out}

def summarize(records):
    """Unsettled races remain visible and do not masquerade as zero-return losses."""
    report={'status':'PAPER_ONLY','races':len(records),'pending':0,'review':0,'all':{},'clean_history':{}}
    for selection,result in sorted(records,key=lambda x:(x[0]['scheduled_start'],x[0]['race_id'])):
        if result['status']!='SETTLED':
            report['pending' if result['status']=='PENDING' else 'review']+=1;continue
        for cohort in ['all']+(['clean_history'] if selection['history_clean'] else []):
            for key,r in result['strategies'].items():
                m=report[cohort].setdefault(key,dict(races=0,bets=0,wins=0,staked=0.,returned=0.,net=0.,peak=0.,max_drawdown=0.))
                m['races']+=1
                for k in ('bets','wins','staked','returned','net'):m[k]+=r[k]
                m['peak']=max(m['peak'],m['net']);m['max_drawdown']=max(m['max_drawdown'],m['peak']-m['net'])
    for cohort in ('all','clean_history'):
        for m in report[cohort].values():
            m['roi']=m['net']/m['staked'] if m['staked'] else None
            m['win_frequency']=m['wins']/m['bets'] if m['bets'] else None
    return report
