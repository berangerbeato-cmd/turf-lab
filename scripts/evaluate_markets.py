"""Frozen 2026 exploratory market probabilities; never infer ROI without prices."""
import gzip,hashlib,json,math
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from turf_lab.market_probabilities import markets
from turf_lab.full_history_evaluation import season
from turf_lab.evidence import dump

ROOT=Path('reports/market_evaluation')
MODELS=('classic','xgboost','ensemble','uniform')


def new_stats():
    return {'races':0,'brier_sum':0.,'logloss_sum':0.,'hits':0,'selected_probability_sum':0.,
            'loss_streak':0,'longest_loss_streak':0,'bins':[[0.,0.,0.] for _ in range(10)]}


def update(s, probabilities, labels):
    s['races']+=1; n=len(labels);p=np.clip(probabilities,1e-12,1-1e-12)
    s['brier_sum']+=float(np.mean((p-labels)**2))
    s['logloss_sum']+=float(np.mean(-labels*np.log(p)-(1-labels)*np.log(1-p)))
    best=int(np.argmax(probabilities));hit=int(labels[best]);s['hits']+=hit
    s['selected_probability_sum']+=float(probabilities[best])
    s['loss_streak']=0 if hit else s['loss_streak']+1
    s['longest_loss_streak']=max(s['longest_loss_streak'],s['loss_streak'])
    for pi,yi in zip(p,labels):
        b=s['bins'][min(9,int(pi*10))];b[0]+=1/n;b[1]+=float(pi)/n;b[2]+=float(yi)/n
    return best,hit


def finish(s):
    n=s['races']
    if not n:return {'races':0}
    return {'races':n,'race_weighted_binary_brier':s['brier_sum']/n,'race_weighted_binary_logloss':s['logloss_sum']/n,
        'top_probability_hit_rate':s['hits']/n,'top_probability_mean_prediction':s['selected_probability_sum']/n,
        'longest_loss_streak':s['longest_loss_streak'],
        'ece':sum(abs(b[1]-b[2]) for b in s['bins'])/n,
        'calibration':[{'weight':b[0],'prediction':b[1]/b[0],'frequency':b[2]/b[0]} for b in s['bins'] if b[0]]}


def main():
    source=Path('reports/full_history/test_predictions.jsonl.gz')
    predictions=[json.loads(line) for line in gzip.decompress(source.read_bytes()).splitlines()]
    entries={}
    for month in sorted({p['date'][:7] for p in predictions}):
        manifest=json.loads(Path(f'data/month_{month}/manifest.json').read_text())
        entries.update({p['race_id']:p for p in manifest['partitions']})
    stats=defaultdict(new_stats);sub=defaultdict(new_stats);excluded=Counter();tickets=[];digests={}
    for ix,row in enumerate(sorted(predictions,key=lambda p:(p['date'],p['race_id']))):
        entry=entries[row['race_id']];raw=gzip.decompress(Path(entry['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Race digest mismatch')
        r=json.loads(raw);ps=r['participants'];n=len(ps)
        if n<10 or n>20:excluded['outside_10_to_20_runners']+=1;continue
        if any(p.get('statut')=='NON_PARTANT' for p in ps):excluded['non_runner_present']+=1;continue
        arrival=r.get('course',{}).get('ordreArrivee',[])
        if len(arrival)<4 or any(len(a)!=1 for a in arrival[:4]):excluded['missing_or_tied_top4']+=1;continue
        top=[a[0] for a in arrival[:4]]
        if len(set(top))!=4:raise ValueError('Repeated arrival number')
        numbers=sorted(p['numPmu'] for p in ps)
        if not set(top)<=set(numbers):raise ValueError('Arrival outside field')
        ranks={p['numPmu']:p.get('ordreArrivee') for p in ps}
        if any(ranks[num]!=rank for rank,num in enumerate(top,1)):excluded['arrival_participant_disagreement']+=1;continue
        digests[row['race_id']]=entry['sha256']
        for model in MODELS:
            pred=row['probabilities'][model]
            if set(map(int,pred))!=set(numbers):raise ValueError('Prediction field mismatch')
            probabilities=markets(numbers,[pred[str(num)] for num in numbers])
            for market,(selections,probs) in probabilities.items():
                target=set(top[:1] if market=='win' else top[:4] if market=='pair_top4' else top[:3])
                labels=np.array([int(set(s if isinstance(s,tuple) else (s,))<=target) for s in selections])
                best,hit=update(stats[(model,market)],probs,labels)
                update(sub[(model,market,season(row['date']))],probs,labels)
                p=float(probs[best])
                tickets.append({'race_id':row['race_id'],'date':row['date'],'model':model,'market':market,
                    'selection':selections[best],'probability':p,'observed_hit':hit,
                    'break_even_total_return':1/p,'total_return_for_5pct_scenario_ev':1.05/p,
                    'status':'NO_BET_NO_ZETURF_PRICE','selection_rule':'maximum probability, NOT maximum value'})
        if ix%500==0:print('Evaluated',ix,'source races',flush=True)
    ROOT.mkdir(parents=True,exist_ok=True)
    result={'status':'PROBABILITY_BASELINE_ONLY_VALUE_UNVALIDATED','source_races':len(predictions),
      'eligible_races':len(digests),'exclusions':dict(excluded),'models':{},
      'provenance':{'prediction_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'race_digests':digests,'method':'Exact Plackett-Luce top-4 set probabilities from frozen winner probabilities'},
      'limitations':['Rank/placement extension not trained or calibrated for these markets; IIA/strength assumptions may fail, especially DQ.',
       '2026 holdout previously inspected; exploratory only. No new fitting or model selection on test.',
       'Common retrospective cohort: 10-20 runners, no non-runners, unambiguous top4. Actual ZEturf market opening/availability unverified.',
       'No time-stamped ZEturf pre-race quotes or final dividends joined: no EV/ROI/drawdown claim.',
       'Maximum-probability tickets do not identify value; reciprocal probabilities are model thresholds, not validated fair prices.',
       'Binary metrics have different base rates across markets: compare models WITHIN a market, not raw Brier across markets.',
       'Loss streaks follow date/race-id order, not guaranteed intraday chronological order; bets on one race are correlated.']}
    for model in MODELS:
        result['models'][model]={market:{'overall':finish(stats[(model,market)]),
           'season':{s:finish(sub[(model,market,s)]) for s in ('winter','spring','summer','autumn')}}
           for market in ('win','place3','pair_place3','pair_top4')}
    dump(ROOT/'comparison.json',result)
    (ROOT/'tickets.jsonl.gz').write_bytes(gzip.compress(('\n'.join(json.dumps(x) for x in tickets)+'\n').encode(),mtime=0))
    lines=['# Market probability baseline','','Value and profitability are NOT established. No real bets.',
           f"Common test cohort: {len(digests)} of {len(predictions)} races.",'',
           '| Model | Market | Hit rate of most probable ticket | Predicted rate | Binary Brier |',
           '|---|---|---:|---:|---:|']
    for model,mm in result['models'].items():
        for market,details in mm.items():
            s=details['overall'];lines.append(f"| {model} | {market} | {s['top_probability_hit_rate']:.2%} | {s['top_probability_mean_prediction']:.2%} | {s['race_weighted_binary_brier']:.5f} |")
    lines+=['','## Limits']+['- '+s for s in result['limitations']]
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'eligible_races':len(digests),'exclusions':excluded,'status':result['status']}))

if __name__=='__main__':main()
