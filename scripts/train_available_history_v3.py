"""Run the predeclared full-data research offline, leaving production untouched."""
import gzip
import hashlib
import json
from pathlib import Path
from turf_lab.available_history_research import available_features, variant, calibrate_temperature
from turf_lab.fast_logit import fit
from turf_lab.pilot import probabilities
from turf_lab.full_history_evaluation import chronological, score, temper, paired

ROOT=Path('reports/available_history_v3')
MODELS=Path('models/available_history_v3')
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def save(path, data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def stage(status, **kw):
    save(ROOT/'status.json',dict(status=status,production_changed=False,recommendations_allowed=False,**kw))
    print(status,kw,flush=True)
def predict(rows, model): return [probabilities(r,model) for r in rows]

def sources():
    old=read('config/full_history_protocol.json'); records=[]; manifests={}
    fields=('numPmu','nom','nomMere','nomPere','idCheval','statut','ordreArrivee','incident','driver','entraineur','deferre','age','sexe')
    for path in sorted(Path('data').glob('month_*/manifest.json')):
        month=path.parent.name[6:]
        if not '2022-01' <= month <= '2026-09' or month in old['excluded_months']: continue
        manifests[month]=digest(path)
        for item in read(path)['partitions']:
            if item['race_id'] in old['excluded_races']: continue
            raw=gzip.decompress(Path(item['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest()!=item['sha256']: raise ValueError('Source SHA mismatch')
            r=json.loads(raw)
            r={k:r[k] for k in ('date','race_id','venue','country','start_type','distance_m','scheduled_start_ms','course','participants')}
            r['participants']=[{k:p.get(k) for k in fields} for p in r['participants']]
            records.append(r)
    return records,manifests

def v6_predictions(records, test):
    from scripts.v6_holdout import verify
    from turf_lab.month_history import build_history
    from turf_lab.opposition import augment as opposition
    from turf_lab.connections import augment_connections
    from turf_lab.demographics_tandem import augment, candidate
    _,_,p,models=verify()
    records=[r for r in records if r['date'].startswith('2026')]
    rows=augment_connections(opposition(build_history(records,lookback_days=p['lookback_days'])),records,
        window=p['connections_window_days'],strength=p['connections_prior_strength'],equipment_days=p['equipment_history_days'])
    dp=read('config/demographics_tandem_v6_protocol.json')
    rows=candidate(augment(rows,records,dp['tandem_window_days'],dp['prior_strength']),'combined')
    by_id={r['race_id']:r for r in rows}; ordered=[]
    for target in test:
        row=by_id[target['race_id']]
        signature=lambda r:sorted((x['number'],x['horse_id'],x['won'],x['non_runner']) for x in r['runners'])
        if signature(row)!=signature(target): raise ValueError('V6 common cohort mismatch')
        ordered.append(row)
    return predict(ordered,models['v6'])

def main():
    if (ROOT/'evaluation.json').exists():
        raise ValueError('Existing completed experiment; do not overwrite after test inspection')
    policy=read('config/available_history_v3.json'); manifest=read('reports/full_history/datasets/manifest.json')
    frames={}
    stage('LOADING_EXISTING_DATA')
    for name,info in manifest['splits'].items():
        if digest(info['file'])!=info['sha256']: raise ValueError('Dataset hash mismatch')
        with gzip.open(info['file'],'rt') as f: frames[name]=[json.loads(line) for line in f]
        if len(frames[name])!=info['races']: raise ValueError('Dataset count mismatch')
    chronological(frames['train'],frames['validation'],frames['test'])
    records,manifests=sources()
    save(ROOT/'source_lock.json',dict(protocol_sha256=digest('config/available_history_v3.json'),datasets=manifest['splits'],
         source_manifests=manifests,code_sha256={p:digest(p) for p in ['turf_lab/available_history_research.py','scripts/train_available_history_v3.py']},network_requests=0))
    augmented,audit=available_features(records,sum(frames.values(),[]),policy['dq_prior_strength'])
    save(ROOT/'feature_audit.json',audit); stage('FEATURES_VERIFIED',**audit)
    partitions={n:{r['race_id'] for r in rows} for n,rows in frames.items()}
    groups={n:[r for r in augmented if r['race_id'] in ids] for n,ids in partitions.items()}
    classic_path='models/full_history/classic.json'; frozen=read('models/full_history/frozen.json')
    if digest(classic_path)!=frozen['model_hashes']['classic.json']: raise ValueError('Classic lock mismatch')
    models={}; development={}; temperatures={}
    for name in policy['variants']:
        stage('FITTING',variant=name,train_races=len(groups['train']))
        models[name]=read(classic_path) if name=='classic_recalibrated' else fit(variant(groups['train'],name),policy['l2'],policy['iterations'],policy['learning_rate'])
        save(MODELS/(name+'.json'),models[name])
        selection=variant([r for r in groups['validation'] if r['date']<=policy['selection'][1]],name)
        calibration=variant([r for r in groups['validation'] if r['date']>=policy['calibration'][0]],name)
        temperatures[name]=calibrate_temperature(calibration,predict(calibration,models[name]))
        development[name]=dict(selection=score(selection,predict(selection,models[name])),temperature=temperatures[name],selection_races=len(selection),calibration_races=len(calibration))
        save(ROOT/('development_'+name+'.json'),development[name])
    selected=min(development,key=lambda n:development[n]['selection']['overall']['log_loss'])
    save(ROOT/'selection_frozen_before_test.json',dict(selected=selected,temperatures=temperatures,development=development,
        model_sha256={n:digest(MODELS/(n+'.json')) for n in models},source_lock_sha256=digest(ROOT/'source_lock.json')))
    stage('EVALUATING_FIXED_CANDIDATES',selected=selected)
    test=frames['test']; predictions={}
    for name in models:
        rows=variant(groups['test'],name)
        predictions[name]=temper(rows,predict(rows,models[name]),temperatures[name])
    predictions['classic_operational']=temper(test,predict(test,read(classic_path)),frozen['temperatures']['classic'])
    predictions['v6_operational']=v6_predictions(records,test)
    results=dict(selected_before_test=selected,test_status=policy['test_status'],counts={n:len(r) for n,r in frames.items()},
        test={n:score(test,p) for n,p in predictions.items()},paired_vs_classic={n:paired(test,predictions['classic_operational'],p,repetitions=policy['bootstrap_repetitions']) for n,p in predictions.items() if n!='classic_operational'},
        production_changed=False,recommendations_allowed=False,network_requests=0,limits=policy['limits'])
    save(ROOT/'evaluation.json',results)
    with gzip.open(ROOT/'test_predictions.jsonl.gz','wt') as f:
        for i,r in enumerate(test): f.write(json.dumps(dict(race_id=r['race_id'],date=r['date'],probabilities={n:p[i] for n,p in predictions.items()}))+'\n')
    lines=['# Available history V3 — exploratory full-data experiment','',
      'All 17,532 training races used; no additional collection. Production unchanged. No betting recommendation.',
      '2025 first half selects the variant; second half calibrates. 2026 was previously examined, not a virgin holdout.',
      '',f'Selected before test: **{selected}**.','',
      '| Model | Test races | Log loss | Brier | Top 1 | ECE |','|---|---:|---:|---:|---:|---:|']
    for n,data in results['test'].items():
        m=data['overall']; lines.append(f"| {n} | {len(test)} | {m['log_loss']:.6f} | {m['brier_multiclass']:.6f} | {m['top1_accuracy']:.2%} | {m['runner_ece']:.6f} |")
    lines+=['','Paired weekly bootstrap intervals and monthly results: evaluation.json. No automatic promotion.',
            'Operational V6 uses its actual frozen weights and annual history reset, not the continuous-history Classic inputs.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    stage('COMPLETED_EXPLORATORY',selected=selected,models_retrained=True)

if __name__=='__main__':
    try: main()
    except Exception as e:
        stage('FAILED',reason=str(e)); raise
