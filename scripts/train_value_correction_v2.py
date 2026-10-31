"""Frozen active sports model plus separately fitted market correction; research only."""
import gzip,json
from pathlib import Path
from scripts.train_available_history_v3 import sources,read,save,digest
from scripts.train_market_repair import dataset,evaluate,paired
from turf_lab.available_history_research import available_features,variant
from turf_lab.available_history_operational import verify_active
from turf_lab.full_history_evaluation import temper
from turf_lab.pilot import probabilities
from turf_lab.market_repair import fit
ROOT=Path('reports/value_correction_v2')
MODELS=Path('models/value_correction_v2')
def main():
    if (ROOT/'evaluation.json').exists():raise ValueError('Completed experiment must not be overwritten')
    active,temp=verify_active();protocol=read('config/value_correction_v2.json')
    info=read('reports/full_history/datasets/manifest.json')['splits']['validation']
    if digest(info['file'])!=info['sha256']:raise ValueError('Dataset changed')
    with gzip.open(info['file'],'rt') as f:frames=[json.loads(s) for s in f]
    records,manifests=sources()
    records=[r for r in records if r['date']<'2026-01-01']
    augmented,audit=available_features(records,frames)
    frames=variant(augmented,active['variant'])
    model=read(active['model_file'])
    predictions=temper(frames,[probabilities(r,model) for r in frames],temp)
    by_id={r['race_id']:p for r,p in zip(frames,predictions)}
    train,excluded_fit,fit_sources=dataset('validation',protocol)
    for r in train:r['sport']=[by_id[r['race_id']][n] for n in r['numbers']]
    print('Fitting on 2025',len(train),flush=True)
    hybrid=fit(train,protocol);market=fit(train,protocol,True)
    save(MODELS/'hybrid.json',hybrid);save(MODELS/'market_only.json',market)
    save(MODELS/'frozen_before_test.json',dict(protocol_sha256=digest('config/value_correction_v2.json'),
        active_policy_sha256=digest('config/active_model.json'),model_hashes={n:digest(MODELS/(n+'.json')) for n in ['hybrid','market_only']},
        fit_sources=fit_sources,excluded_fit=excluded_fit,feature_audit=audit,
        note='2025 is development data, previously used for sports selection and temperature; 2026 already inspected. No fresh holdout claim.'))
    del records,augmented,frames,predictions,by_id
    print('Frozen; evaluating 2026',flush=True)
    test,excluded_test,test_sources=dataset('test',protocol)
    with gzip.open('reports/available_history_v3/test_predictions.jsonl.gz','rt') as f:
        pp={r['race_id']:r['probabilities'][active['variant']] for r in map(json.loads,f)}
    if max(r['date'] for r in train)>=min(r['date'] for r in test):raise ValueError('Chronology')
    for r in test:r['sport']=[pp[r['race_id']][str(n)] for n in r['numbers']]
    result=dict(status='COMPLETED_EXPLORATORY',fit_races=len(train),test_races=len(test),weights=dict(hybrid=hybrid['weights'],market_only=market['weights']),
        models={},paired={},excluded_test=excluded_test,test_sources=test_sources,protocol=protocol,production_changed=False,recommendations_allowed=False)
    scores={}
    for n,w in [('sport',None),('market_normalized',[1,0]),('market_calibrated',market['weights']),('hybrid',hybrid['weights'])]:
        result['models'][n],scores[n]=evaluate(test,w)
    for n in ['sport','market_normalized','market_calibrated']:
        result['paired'][n]=paired(scores['hybrid'],scores[n],protocol['bootstrap_days'])
    save(ROOT/'evaluation.json',result)
    lines=['# Correction de la value — modèle de base V3','',
        f"Ajustement sur {len(train)} courses de 2025 ; évaluation sur {len(test)} courses de 2026 déjà examinées.",
        'La version hybride utilise explicitement les cotes. Aucun changement du modèle sportif actif, aucun ROI.',
        '', '| Modèle | Log loss ↓ | Brier ↓ | Victoires prévues parmi EV positives | Observées |',
        '|---|---:|---:|---:|---:|']
    for n,m in result['models'].items():
        d=m['positive_ev_diagnostic']
        lines.append(f"| {n} | {m['log_loss']:.6f} | {m['brier']:.6f} | {d.get('expected_wins',0):.1f} | {d.get('wins',0)} |")
    lines+=['',f"Poids hybride [marché, sport] : {hybrid['weights']}.",'',
        'Les groupes EV positives diffèrent selon les modèles : comparer leur calibration, pas seulement leur nombre de victoires.',
        'Prix PMU de référence archivés ; pas de prix ZEturf exécutable ni de rapports payés. Les cotes finales peuvent changer.',
        'Le bilan face au marché calibré figure dans evaluation.json. Pas de sélection de seuil sur le test ni de promotion automatique.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(result['weights']),flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:
        save(ROOT/'failure.json',dict(status='FAILED',reason=str(e)));raise
