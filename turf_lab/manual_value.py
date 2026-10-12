"""Offline manual-quote comparison. No scraping and no bet placement.

Prediction JSON and a verified screenshot transcription are separate inputs.
This code never trains a model or changes its probabilities from the odds.
"""
import argparse
import json
import math
import re
from datetime import datetime, timezone

from turf_lab.evidence import dump


def timestamp(text):
    if not isinstance(text,str):
        raise ValueError('Missing timestamp')
    value=datetime.fromisoformat(text.replace('Z','+00:00'))
    if value.tzinfo is None:
        raise ValueError('A timezone offset is required')
    return value.astimezone(timezone.utc)


def finite_number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def compare(prediction, quotes, now=None, minimum_ev=0.10, max_quote_age_minutes=15):
    """Conservative eligibility policy, not a calibrated investment rule."""
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('now must have a timezone')
    result={'race_id':prediction.get('race_id'),'status':'NO BET','reasons':[],
            'rows':[],'real_bet':False,'evaluated_at':now.isoformat()}
    reasons=result['reasons']
    if prediction.get('race_id')!=quotes.get('race_id') or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_R\d+C\d+',prediction.get('race_id','')):
        reasons.append('race_identity_mismatch')
    if quotes.get('source')!='PMU_MANUAL_SCREENSHOT' or quotes.get('transcription_verified') is not True:
        reasons.append('unverified_manual_transcription')
    if not re.fullmatch(r'[0-9a-f]{64}',quotes.get('image_sha256','')):
        reasons.append('missing_screenshot_provenance')
    if quotes.get('odds_format')!='DECIMAL_TOTAL_RETURN':
        reasons.append('ambiguous_odds_convention')
    try:
        observed=timestamp(quotes.get('observed_at'))
        departure=timestamp(prediction.get('scheduled_start'))
        predicted=timestamp(prediction.get('predicted_at'))
        cutoff=timestamp(prediction.get('feature_cutoff'))
        verified=timestamp(quotes.get('runners_verified_at'))
        if not cutoff <= predicted <= observed <= verified <= now < departure:
            reasons.append('invalid_chronology_or_race_started')
        if (now-observed).total_seconds()>max_quote_age_minutes*60:
            reasons.append('stale_quote')
        result['observed_at']=observed.isoformat()
    except (ValueError,TypeError):
        reasons.append('missing_or_invalid_timestamp')
    runners=prediction.get('runners',[])
    active=[r for r in runners if r.get('status')=='PARTANT']
    if any(r.get('status') not in ('PARTANT','NON_PARTANT') for r in runners):
        reasons.append('unknown_runner_status')
    ids=[r.get('horse_id') for r in runners]
    numbers=[r.get('number') for r in runners]
    if not active or any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)) or len(numbers)!=len(set(numbers)):
        reasons.append('invalid_runner_identifiers')
    if any(not finite_number(r.get('probability')) or not 0<=r['probability']<=1 for r in runners):
        reasons.append('invalid_probability')
    elif abs(sum(r['probability'] for r in active)-1)>1e-8 or any(r['probability']!=0 for r in runners if r.get('status')=='NON_PARTANT'):
        reasons.append('probabilities_not_normalized_for_active_field')
    observations=quotes.get('quotes',[])
    qids=[q.get('horse_id') for q in observations]
    if len(qids)!=len(set(qids)) or set(qids)!={r.get('horse_id') for r in active}:
        reasons.append('quote_field_does_not_match_active_runners')
    mapping={q.get('horse_id'):q for q in observations}
    for r in active:
        q=mapping.get(r.get('horse_id'))
        if q is None:
            continue
        if q.get('number')!=r.get('number') or q.get('name','').strip().casefold()!=r.get('name','').strip().casefold():
            reasons.append('runner_number_or_name_mismatch')
        if not finite_number(q.get('decimal_odds')) or q['decimal_odds']<=1:
            reasons.append('invalid_decimal_odds')
    if reasons:
        result['reasons']=sorted(set(reasons))
        return result
    for r in sorted(active,key=lambda r:(-r['probability'],r['number'])):
        odds=mapping[r['horse_id']]['decimal_odds']
        result['rows'].append({'number':r['number'],'horse_id':r['horse_id'],'name':r['name'],
             'probability':r['probability'],'decimal_odds':odds,'ev':r['probability']*odds-1,
             'break_even_decimal_odds':1/r['probability'] if r['probability']>0 else None})
    if prediction.get('validation_status')!='validated_out_of_time':
        reasons.append('model_not_validated_out_of_time')
    if prediction.get('uncertainty')!='acceptable' or prediction.get('data_quality_pass') is not True:
        reasons.append('insufficient_data_or_high_uncertainty')
    result['minimum_ev_policy']=minimum_ev
    result['candidates']=[r['number'] for r in result['rows'] if r['ev']>=minimum_ev] if not reasons else []
    if not reasons and result['candidates']:
        result['status']='CANDIDATS FICTIFS A EXAMINER'
    elif not reasons:
        reasons.append('insufficient_value')
    result['note']='EV indicative avec les cotes observées ; rapports PMU variables jusqu’au départ. Aucun pari réel.'
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prediction',required=True)
    parser.add_argument('--quotes',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    with open(args.prediction) as f: prediction=json.load(f)
    with open(args.quotes) as f: quotes=json.load(f)
    result=compare(prediction,quotes)
    dump(args.output,result)
    print(result['status'],', '.join(result['reasons']))


if __name__=='__main__':main()
