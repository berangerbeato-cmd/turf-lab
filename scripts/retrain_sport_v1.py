"""Reproducible fixed sports-only experiment; no prices and no production writes."""
import gzip
import hashlib
import json
from collections import defaultdict, Counter
from itertools import groupby
from pathlib import Path
from turf_lab.evidence import dump
from turf_lab.month_history import identity
from turf_lab.sport_retrain import replace_features
from turf_lab.fast_logit import fit
from turf_lab.pilot import probabilities
from turf_lab.full_history_evaluation import chronological, tune, temper, score, paired

ROOT = Path('reports/sport_retrain_v1')
POLICY = Path('config/sport_retrain_v1.json')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_frames():
    manifest = json.loads(Path('reports/full_history/datasets/manifest.json').read_text())
    splits = {}
    for name, meta in manifest['splits'].items():
        if digest(meta['file']) != meta['sha256']:
            raise ValueError('Frozen dataset hash mismatch')
        with gzip.open(meta['file'], 'rt') as stream:
            splits[name] = [json.loads(line) for line in stream]
    chronological(splits['train'], splits['validation'], splits['test'])
    return splits, manifest


def rebuild(splits, manifest, policy):
    frames = {r['race_id']: r for rows in splits.values() for r in rows}
    patched = {}; history = defaultdict(list); counts = Counter(); sources = {}
    for month, expected in sorted(manifest['provenance']['source_manifests'].items()):
        if month in policy['excluded_months']:
            continue
        path = Path(f'data/month_{month}/manifest.json')
        if digest(path) != expected:
            raise ValueError('Monthly manifest changed')
        sources[str(path)] = expected
        entries = json.loads(path.read_text())['partitions']
        records = []
        for entry in entries:
            raw = gzip.decompress(Path(entry['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise ValueError('Raw partition hash mismatch')
            record = json.loads(raw)
            if record['race_id'] not in policy['excluded_races']:
                records.append(record)
        for day, grouped in groupby(sorted(records,key=lambda r:(r['date'],r['race_id'])),key=lambda r:r['date']):
            batch = list(grouped)
            for r in batch:
                if r['race_id'] not in frames:
                    continue
                frame = frames[r['race_id']]
                participants = {p['numPmu']: p for p in r['participants']}
                runners = []
                for runner in frame['runners']:
                    h = identity(participants[runner['number']])
                    if h != runner['horse_id']:
                        raise ValueError('Horse identity mismatch')
                    new = replace_features(runner['features'], history[h], day)
                    counts['runner_rows'] += 1
                    counts['changed_first_five'] += new[:5] != runner['features'][:5]
                    counts['unknown_recent_outcome'] += bool(new[-2])
                    counts['stopped_or_fallen_recent'] += bool(new[-1])
                    runners.append({**runner, 'features': new})
                patched[r['race_id']] = {**frame, 'runners': runners}
            # No same-day result enters the feature construction above.
            for r in batch:
                for p in r['participants']:
                    if p.get('statut') == 'NON_PARTANT':
                        continue
                    h = identity(p)
                    history[h].append({'date':day, 'race_id':r['race_id'], 'rank':p.get('ordreArrivee'), 'incident':p.get('incident')})
                    history[h] = history[h][-5:]
    if set(patched) != set(frames):
        raise ValueError('Missing reconstructed race')
    return {k:[patched[r['race_id']] for r in rows] for k,rows in splits.items()}, dict(counts), sources


def main():
    policy = json.loads(POLICY.read_text())
    ROOT.mkdir(parents=True,exist_ok=True)
    if (ROOT/'results.json').exists():
        raise ValueError('Completed experiment retained; do not retune against evaluation')
    lock = ROOT/'protocol.json'
    if lock.exists() and json.loads(lock.read_text()) != policy:
        raise ValueError('Protocol changed')
    dump(lock,policy)
    splits,manifest = load_frames()
    print('Rebuilding histories with verified source hashes',flush=True)
    repaired,counts,sources = rebuild(splits,manifest,policy)
    dump(ROOT/'coverage.json', {'counts':counts,'monthly_manifests':sources,'original_splits':manifest['splits']})
    print('Training baseline and repaired candidate: '+str(counts),flush=True)
    models={}; temperatures={}; validation={}
    for name, data in [('baseline',splits),('repaired',repaired)]:
        model=fit(data['train'],policy['l2'],policy['iterations'],policy['learning_rate'])
        raw=[probabilities(r,model) for r in data['validation']]
        t,p=tune(data['validation'],raw,policy['temperatures'])
        models[name]=model; temperatures[name]=t; validation[name]=score(data['validation'],p)
        dump(ROOT/(name+'_model.json'),model)
        print(name+' trained; validation log loss '+str(validation[name]['overall']['log_loss']),flush=True)
    frozen={'model_hashes':{n:digest(ROOT/(n+'_model.json')) for n in models},'temperatures':temperatures,
            'protocol_sha256':digest(POLICY), 'source_manifest_sha256':digest('reports/full_history/datasets/manifest.json'),
            'code_sha256':{p:digest(p) for p in ('scripts/retrain_sport_v1.py','turf_lab/sport_retrain.py','turf_lab/fast_logit.py','turf_lab/pilot.py','turf_lab/full_history_evaluation.py')}}
    dump(ROOT/'frozen_before_evaluation.json',frozen)
    predictions={}; evaluation={}
    for name,data in [('baseline',splits),('repaired',repaired)]:
        predictions[name]=temper(data['test'],[probabilities(r,models[name]) for r in data['test']],temperatures[name])
        evaluation[name]=score(data['test'],predictions[name])
    comparison=paired(splits['test'],predictions['baseline'],predictions['repaired'],repetitions=1000)
    result={'status':'EXPLORATORY_REUSED_HOLDOUT_NO_PROMOTION','training_completed':True,'recommendations_allowed':False,
            'protocol':policy,'frozen':frozen,'counts':counts,'races':{k:len(v) for k,v in splits.items()},
            'validation':validation,'evaluation':evaluation,'paired_week':comparison,
            'limitations':['Unknown non-PMU starts remain missing; no claim of complete individual histories.',
                          'Other 33 features retained, including potentially incomplete Elo/entourage histories.',
                          '2025 and 2026 previously observed; not independent validation. No odds or ROI.']}
    dump(ROOT/'results.json',result)
    dump(ROOT/'evaluation_predictions.json',[{'race_id':r['race_id'],**{n:p[i] for n,p in predictions.items()}} for i,r in enumerate(splits['test'])])
    print(json.dumps({'evaluation':{n:v['overall'] for n,v in evaluation.items()},'paired':comparison}),flush=True)

if __name__=='__main__':main()
