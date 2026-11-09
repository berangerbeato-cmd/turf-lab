"""Post-evaluation price buckets, descriptive only; never select or fit a model."""
import gzip
import hashlib
import json
import math
from pathlib import Path
from turf_lab.evidence import dump

ROOT=Path('reports/sport_retrain_v1')
BINS=[1,3,5,10,20,50,80,float('inf')]


def main():
    result=json.loads((ROOT/'results.json').read_text())
    predictions={r['race_id']:r for r in json.loads((ROOT/'evaluation_predictions.json').read_text())}
    buckets={n:[{'range':[lo,hi if math.isfinite(hi) else None],'runners':0,'sum_probability':0.,'wins':0} for lo,hi in zip(BINS,BINS[1:])] for n in ('baseline','repaired')}
    included=0;missing=0
    coverage=json.loads((ROOT/'coverage.json').read_text())
    for month in range(1,10):
        path=Path(f'data/month_2026-{month:02d}/manifest.json')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=coverage['monthly_manifests'][str(path)]:
            raise ValueError('Manifest changed')
        for entry in json.loads(path.read_text())['partitions']:
            raw=gzip.decompress(Path(entry['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Partition changed')
            race=json.loads(raw)
            if race['race_id'] not in predictions:continue
            included+=1
            p=predictions[race['race_id']]
            for runner in race['participants']:
                if runner.get('statut')=='NON_PARTANT':continue
                price=runner.get('dernierRapportDirect',{}).get('rapport')
                if type(price) not in (int,float) or not math.isfinite(price) or price<1:
                    missing+=1;continue
                ix=next(i for i,(lo,hi) in enumerate(zip(BINS,BINS[1:])) if lo<=price<hi)
                for name in buckets:
                    b=buckets[name][ix];b['runners']+=1;b['wins']+=runner.get('ordreArrivee')==1
                    b['sum_probability']+=p[name][str(runner['numPmu'])]
    if included!=result['races']['test']:raise ValueError('Evaluation race coverage mismatch')
    for values in buckets.values():
        for b in values:
            b['mean_probability']=b['sum_probability']/b['runners'] if b['runners'] else None
            b['observed_win_frequency']=b['wins']/b['runners'] if b['runners'] else None
    dump(ROOT/'price_buckets.json',{'status':'DESCRIPTIVE_POSTRACE_PRICES_NOT_EXECUTABLE','races':included,
                                  'missing_runner_prices':missing,'buckets':buckets,'used_for_training_or_selection':False,
                                  'roi_calculated':False,'source':'dernierRapportDirect; retrospective archive; price timestamps not prestart validated'})

if __name__=='__main__':main()
