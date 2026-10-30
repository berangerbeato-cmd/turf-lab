"""Explicit opt-in paper comparison. Never alter the operational V6/Classic output."""
import argparse,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from turf_lab.market_repair import predict
from turf_lab.operational_quotes import compare

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def paper_comparison(prediction,quotes,replay=False):
    lock=json.loads(Path('models/market_repair_v1/frozen.json').read_text())
    for path,key in [('config/market_repair_v1.json','protocol_sha256'),('models/market_repair_v1/candidate.json','candidate_sha256')]:
        if digest(path)!=lock[key]:raise ValueError('Research model/protocol changed')
    if prediction['models']['classic_full']['model_sha256']!=lock['classic_sha256']:
        raise ValueError('Unmatched Classic model')
    checked=compare(prediction,quotes)
    start=datetime.fromisoformat(prediction['scheduled_start'].replace('Z','+00:00'));now=datetime.now(timezone.utc)
    observed=datetime.fromisoformat(quotes['observed_at'].replace('Z','+00:00'))
    if not replay and (now>=start or (now-observed).total_seconds()>900):
        raise ValueError('Past race or stale quote; use explicit replay for retrospective research')
    parts=prediction['target_snapshot']['participants'];numbers={p['numPmu'] for p in parts if p['statut']=='PARTANT'}
    if len(numbers)!=len(parts) or {r['number'] for r in checked['rows']}!=numbers:
        raise ValueError('Complete field without nonrunners required')
    rows=sorted(checked['rows'],key=lambda r:r['number']);odds=[r['odds'] for r in rows]
    if sum(1/c for c in odds)<1-1e-9:raise ValueError('Inconsistent underround quote board')
    sport=[r['models']['classic_full']['probability'] for r in rows]
    if abs(sum(sport)-1)>1e-8:raise ValueError('Classic probabilities not normalized')
    weights=json.loads(Path('models/market_repair_v1/candidate.json').read_text())['weights']
    values=predict(odds,sport,weights)
    return {'status':'RETROSPECTIVE_RESEARCH_REPLAY' if replay else 'PAPER_ONLY_UNVALIDATED',
        'race_id':prediction['race_id'],'calculated_at':now.isoformat(),'observed_at':quotes['observed_at'],
        'market_informed':True,'operator':quotes['operator'],'recommendations_allowed':False,
        'model_sha256':lock['candidate_sha256'],'weights':weights,
        'rows':[{'number':r['number'],'name':r['name'],'odds':r['odds'],'classic_probability':s,
                 'research_probability':p,'diagnostic_ev':p*r['odds']-1} for r,s,p in zip(rows,sport,values)],
        'limits':['Fitted to retrospective PMU reference quotes; no validated ZEturf transfer or ROI.',
                  'This model uses market odds and is not an independent sporting probability.',
                  'Individual history warnings remain; no stakes or betting recommendation.']}

def main():
    p=argparse.ArgumentParser();p.add_argument('prediction');p.add_argument('quotes');p.add_argument('--replay',action='store_true');p.add_argument('--output',required=True);a=p.parse_args()
    result=paper_comparison(json.loads(Path(a.prediction).read_text()),json.loads(Path(a.quotes).read_text()),a.replay)
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
