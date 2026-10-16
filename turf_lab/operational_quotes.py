"""Compare independently computed probabilities with verified screenshot quotes."""
import math, re, unicodedata
from datetime import datetime, timezone


def stamp(s):
    t=datetime.fromisoformat(s.replace('Z','+00:00'))
    if t.tzinfo is None:raise ValueError('Quote timestamp requires timezone')
    return t


def name(s):
    return re.sub('[^A-Z0-9]','',unicodedata.normalize('NFKD',s.upper()).encode('ascii','ignore').decode())


def compare(prediction,quotes):
    start=stamp(prediction['scheduled_start']);now=datetime.now(timezone.utc)
    if stamp(prediction['predicted_at'])>=start or stamp(prediction['predicted_at'])>now:raise ValueError('Invalid prediction time')
    if quotes['race_id']!=prediction['race_id']:raise ValueError('Race mismatch')
    if not quotes.get('source_evidence') or not quotes.get('operator') or quotes.get('verified') is not True:raise ValueError('Unverified screenshot')
    observed=stamp(quotes['observed_at'])
    if observed>=start or observed>now:raise ValueError('Invalid quote time')
    if quotes['odds_format']!='DECIMAL_TOTAL_RETURN':raise ValueError('Unsupported odds basis')
    parts={p['numPmu']:p for p in prediction['target_snapshot']['participants']}
    rows=[];seen=set()
    for q in quotes['quotes']:
        n=q['number']
        if n in seen or n not in parts:raise ValueError('Duplicate/unknown number')
        seen.add(n);p=parts[n]
        if name(q['name'])!=name(p['nom']) or p['statut']!='PARTANT':raise ValueError('Horse mismatch or nonrunner')
        c=q['decimal_odds']
        if isinstance(c,bool) or not isinstance(c,(float,int)) or not math.isfinite(c) or c<=1:raise ValueError('Invalid decimal odds')
        models={}
        for key,m in prediction['models'].items():
            pr=m['probabilities'].get(n,m['probabilities'].get(str(n)))
            models[key]={'probability':pr,'fair_odds':1/pr if pr else None,'ev':pr*c-1,'implied_raw':1/c,'difference_pp':100*(pr-1/c),'version':m['version']}
        rows.append({'number':n,'name':p['nom'],'odds':c,'models':models})
    place_result={'status':'EV placé non calculable'}
    pq=quotes.get('place_quote');place=prediction.get('place',{})
    if pq and 'probability' in place:
        if pq.get('number')!=place['number'] or pq.get('paid_places')!=3 or pq.get('kind')!='probable' or pq.get('includes_stake') is not True:
            raise ValueError('Place quote outside calibrated scope')
        low,high=pq['total_return_low'],pq['total_return_high']
        if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (low,high)) or not 1<=low<=high:
            raise ValueError('Invalid probable place range')
        pr=place['probability'];place_result={'status':'PRESTART_PRICE_SCENARIOS_ONLY','number':place['number'],'probability':pr,'ev_low':pr*low-1,'ev_high':pr*high-1,'note':'Probable range is not a guaranteed final payout interval; only classic top selection calibrated.'}
    return {'race_id':prediction['race_id'],'observed_at':quotes['observed_at'],'calculated_at':now.isoformat(),
        'status':'PRESTART_ESTIMATE' if now<start else 'RETROSPECTIVE_QUOTE_COMPARISON',
        'rows':sorted(rows,key=lambda r:-r['models'][prediction['primary_model']]['ev']),
        'place':place_result,'limits':'Observed odds may change; field must be rechecked; positive estimated EV is not guaranteed.'}
