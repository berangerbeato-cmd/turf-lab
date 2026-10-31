"""Market-conditional diagnostic only; never change fitted models or selection."""
import hashlib
import gzip
import json
from collections import defaultdict
from pathlib import Path
from scripts.train_market_repair import dataset
from scripts.audit_value_market import odds_band
from scripts.train_available_history_v3 import ROOT, read, save
from turf_lab.full_history_evaluation import score


def main():
    market,excluded,sources=dataset('test',read('config/market_repair_v1.json'))
    with gzip.open(ROOT/'test_predictions.jsonl.gz','rt') as f:
        predictions={r['race_id']:r['probabilities'] for r in map(json.loads,f)}
    manifest=read('reports/full_history/datasets/manifest.json')['splits']['test']
    with gzip.open(manifest['file'],'rt') as f:
        frames={r['race_id']:r for r in map(json.loads,f)}
    rows=[frames[r['race_id']] for r in market]
    names=list(next(iter(predictions.values())))
    output={}
    for name in names+['market_normalized']:
        preds=[]; bins=defaultdict(list)
        for r in market:
            if name=='market_normalized':
                denom=sum(1/c for c in r['odds']); p={n:(1/c)/denom for n,c in zip(r['numbers'],r['odds'])}
            else: p={int(k):v for k,v in predictions[r['race_id']][name].items()}
            preds.append(p)
            for i,(n,c) in enumerate(zip(r['numbers'],r['odds'])):
                bins[odds_band(c)].append((p[n],int(i==r['winner_index'])))
        output[name]=dict(metrics=score(rows,preds)['overall'],by_odds={b:dict(participations=len(v),mean_predicted=sum(x for x,y in v)/len(v),observed=sum(y for x,y in v)/len(v)) for b,v in bins.items()})
    save(ROOT/'market_diagnostic.json',dict(races=len(rows),excluded=excluded,source_map_sha256=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        price_protocol_sha256=hashlib.sha256(Path('config/market_repair_v1.json').read_bytes()).hexdigest(),models=output,
        interpretation='Retrospective archived PMU reference prices, no executable ZEturf/ROI claim. No market inputs to sports models; no selection from this diagnostic.'))
    print('Market diagnostic saved:',len(rows),flush=True)

if __name__=='__main__': main()
