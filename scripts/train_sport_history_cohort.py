"""Resumable independent-history experiment; never replaces operational models."""
import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from turf_lab.evidence import EvidenceStore, dump
from turf_lab.month_history import build_history
from turf_lab.sport_history_cohort import select, repair
from turf_lab.fast_logit import fit
from turf_lab.pilot import probabilities
from turf_lab.full_history_evaluation import chronological, score, paired

ROOT = Path('reports/sport_history_cohort_v1')
MODEL = Path('models/sport_history_cohort_v1')
PROTOCOL = Path('config/sport_history_cohort_v1.json')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def frozen_write(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError('Immutable experiment differs: ' + str(path))
    else:
        dump(path, value)


def load_frames():
    manifest = json.loads(Path('reports/full_history/datasets/manifest.json').read_text())
    rows = []
    for entry in manifest['splits'].values():
        if sha(entry['file']) != entry['sha256']:
            raise ValueError('Dataset checksum mismatch')
        with gzip.open(entry['file'], 'rt') as handle:
            rows.extend(json.loads(line) for line in handle)
    return rows, manifest


def load_baselines(selected):
    # Reuse dated archived results, retaining only fields needed for recent form.
    policy = json.loads(Path('reports/full_history/coverage_policy.json').read_text())
    records = []; sources = {}
    for month in sorted(Path('data').glob('month_*/manifest.json')):
        m = month.parent.name[6:]
        if not '2023-11' <= m <= '2026-09' or m in policy['excluded_months']:
            continue
        sources[str(month)] = sha(month)
        manifest = json.loads(month.read_text())
        for entry in manifest['partitions']:
            raw = gzip.decompress(Path(entry['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise ValueError('Source checksum mismatch')
            r = json.loads(raw)
            if r['race_id'] == '2026-07-04_R6C7':
                continue
            r['participants'] = [{k: p.get(k) for k in ('numPmu','nom','nomMere','nomPere','idCheval','statut','ordreArrivee','incident')} for p in r['participants']]
            records.append({k: r[k] for k in ('date','race_id','venue','country','start_type','distance_m','scheduled_start_ms','participants')})
    ids = {r['race_id'] for r in selected}
    return {r['race_id']:r for r in build_history(records, lookback_days=60) if r['race_id'] in ids}, sources


def run(max_requests):
    protocol = json.loads(PROTOCOL.read_text())
    frames, manifest = load_frames()
    chosen = select(frames, protocol)
    selection = {'protocol_sha256': sha(PROTOCOL), 'source_datasets': manifest['splits'],
                 'race_ids': [r['race_id'] for r in chosen]}
    frozen_write(ROOT/'selection.json', selection)
    print('Selected',len(chosen),'races before individual-history retrieval',flush=True)
    baseline, sources = load_baselines(chosen)
    frozen_write(ROOT/'source_lock.json', sources)
    store = EvidenceStore('evidence/sport_history_cohort_v1', max_requests=max_requests, delay=0.5)
    originals = []; repaired = []; audit = []; pending = []
    for frame in chosen:
        rid = frame['race_id']; day, meeting, course = re.fullmatch(r'(\d{4}-\d{2}-\d{2})_R(\d+)C(\d+)',rid).groups()
        ds = datetime.fromisoformat(day).strftime('%d%m%Y')
        url = f'https://offline.turfinfo.api.pmu.fr/rest/client/7/programme/{ds}/R{meeting}/C{course}/performances-detaillees/pretty'
        key = rid + '_performances_pretty'
        if key not in store.manifest and store.requests >= max_requests:
            pending.append(rid); continue
        payload = store.get(url, key)
        # Stop on access denial, rather than issuing further requests.
        if store.manifest[key]['status'] in (401,403,429):
            raise RuntimeError('Source denied or rate limited; checkpoint preserved')
        try:
            enriched, detail = repair(frame, baseline[rid], payload)
            originals.append(frame); repaired.append(enriched)
            audit.append({'race_id':rid,'status':'ELIGIBLE',**detail})
        except (ValueError, KeyError, TypeError) as error:
            audit.append({'race_id':rid,'status':'QUARANTINED','reason':str(error)})
        dump(ROOT/'progress.json', {'attempted':len(audit),'selected':len(chosen),'eligible':len(repaired),
              'requests_this_run':store.requests,'production_changed':False})
    dump(ROOT/'collection.json', {'audit':audit,'pending':pending,'evidence_manifest':str(store.manifest_path),
         'recommendations_allowed':False})
    if pending:
        dump(ROOT/'status.json', {'status':'COLLECTION_PARTIAL','pending':len(pending),'models_retrained':False})
        return
    planned = Counter(r['date'][:7] for r in chosen); kept = Counter(r['date'][:7] for r in repaired)
    splits = {s:[r for r in repaired if protocol[s][0]<=r['date']<=protocol[s][1]] for s in ('train','validation','test')}
    blocked = [m for m,n in planned.items() if kept[m]/n < protocol['minimum_month_fraction']]
    if blocked or any(len(splits[s])<protocol['minimum_races'][s] for s in splits):
        dump(ROOT/'status.json', {'status':'BLOCKED_INSUFFICIENT_COHORT','months':blocked,'split_counts':{s:len(v) for s,v in splits.items()},'models_retrained':False})
        return
    chronological(*[splits[s] for s in ('train','validation','test')])
    datasets = {}
    for name,rows in [('original',originals),('enriched',repaired)]:
        path = ROOT/(name+'.jsonl.gz')
        path.write_bytes(gzip.compress(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows).encode(),mtime=0))
        datasets[name] = sha(path)
    lock = {'protocol_sha256':sha(PROTOCOL),'datasets':datasets,'code_sha256':{p:sha(p) for p in ('turf_lab/sport_history_cohort.py','scripts/train_sport_history_cohort.py','turf_lab/fast_logit.py','turf_lab/pilot.py')}}
    if (ROOT/'evaluation.json').exists():
        if json.loads((ROOT/'evaluation.json').read_text())['provenance'] != lock:
            raise ValueError('Existing experiment differs; create a new version')
        print('Existing evaluation retained');return
    models = {};validation = {};all_splits = {}
    for name,rows in [('original',originals),('enriched',repaired)]:
        ss = {s:[r for r in rows if protocol[s][0]<=r['date']<=protocol[s][1]] for s in splits}
        all_splits[name] = ss
        candidates = [fit(ss['train'], l2, protocol['iterations'], protocol['learning_rate']) for l2 in protocol['l2_candidates']]
        metrics = [score(ss['validation'],[probabilities(r,m) for r in ss['validation']]) for m in candidates]
        best = min(range(len(metrics)),key=lambda i:metrics[i]['overall']['log_loss'])
        models[name] = candidates[best];validation[name] = {'candidates':metrics,'selected_l2':protocol['l2_candidates'][best]}
        dump(MODEL/(name+'.json'),models[name])
    frozen_write(MODEL/'frozen.json',{'provenance':lock,'hashes':{n:sha(MODEL/(n+'.json')) for n in models}})
    # Test metrics read only after parameter selection and file locking.
    test = splits['test'];pred = {n:[probabilities(r,m) for r in all_splits[n]['test']] for n,m in models.items()}
    result = {'status':protocol['status'],'provenance':lock,'split_counts':{s:len(v) for s,v in splits.items()},
              'planned_by_month':dict(planned),'eligible_by_month':dict(kept),'validation':validation,
              'test':{n:score(test,p) for n,p in pred.items()},'paired_week':paired(test,pred['original'],pred['enriched']),
              'limits':protocol['limits'],'production_changed':False,'recommendations_allowed':False}
    dump(ROOT/'evaluation.json',result)
    dump(ROOT/'status.json',{'status':'COMPLETED_EXPLORATORY','models_retrained':True,'production_changed':False,'recommendations_allowed':False})
    lines=['# Réentraînement sportif sur historiques enrichis','',
      'Expérience rétrospective, sans cotes. Modèles opérationnels inchangés. Aucune reprise des paris.',
      '',str(result['split_counts']),'','| Variante | Log loss | Brier | Premier choix gagnant |','|---|---:|---:|---:|']
    for n,v in result['test'].items():
        m=v['overall'];lines.append(f"| {n} | {m['log_loss']:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.2%} |")
    lines += ['',*protocol['limits']]
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'status':result['status'],'splits':result['split_counts'],'test':{n:v['overall'] for n,v in result['test'].items()}}),flush=True)

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--max-requests',type=int,default=400)
    args=parser.parse_args()
    if not 0<=args.max_requests<=400:parser.error('max-requests must be 0..400')
    try:run(args.max_requests)
    except Exception as error:
        dump(ROOT/'status.json',{'status':'FAILED','reason':type(error).__name__+': '+str(error),'production_changed':False})
        raise
