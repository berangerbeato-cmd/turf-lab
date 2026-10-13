"""Collect one unseen month and evaluate already frozen models, without fitting."""
import hashlib
import json
from pathlib import Path
from scripts.collect_month import collect,git_checkpoint
from scripts.backtest_extension import load_sources
from turf_lab.evidence import EvidenceStore,dump
from turf_lab.month_history import build_history
from turf_lab.opposition import augment,candidate
from turf_lab.pilot import metrics,probabilities


def checked_json(path,expected):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Frozen file mismatch: '+str(path))
    return json.loads(raw)


def main():
    p=json.loads(Path('config/opposition_v3_holdout.json').read_text())
    models=checked_json(p['models_file'],p['models_sha256'])['models']
    f=checked_json('config/opposition_v3_protocol.json',p['feature_protocol_sha256'])
    protocol_digest=hashlib.sha256(Path('config/opposition_v3_holdout.json').read_bytes()).hexdigest()
    dest=Path('reports/opposition_v3_holdout.json')
    if dest.exists():
        if json.loads(dest.read_text())['protocol_sha256']!=protocol_digest:raise ValueError('Holdout already frozen differently')
        print('Frozen holdout already evaluated; retained unchanged');return
    evidence=Path('evidence/month_'+p['month']);output=Path('data/month_'+p['month'])
    report=collect(p['month'],EvidenceStore(evidence,max_requests=p['max_requests'],delay=0.5),output,
                   lambda:git_checkpoint(evidence,output))
    dump('reports/month_'+p['month']+'.json',report)
    source_protocol={'months':p['source_months'],'minimum_retained_fraction_per_month':p['minimum_retained_fraction_per_month']}
    records,coverage=load_sources(source_protocol)
    rows=augment(build_history(records,lookback_days=60),k=f['elo_k'],scale=f['elo_scale'],
                 prior_strength=f['dq_prior_strength'],initial_prior=f['initial_dq_prior'])
    test=[r for r in rows if p['test_from']<=r['date']<=p['test_to']]
    if len(test)<p['minimum_test_races']:raise ValueError('Insufficient holdout size')
    results={};predictions={}
    for name in p['comparisons']:
        frame=candidate(test,'baseline' if name=='uniform' else name)
        model={'kind':'uniform'} if name=='uniform' else models[name]
        results[name]=metrics(frame,model)
        predictions[name]=[{'race_id':r['race_id'],'probabilities':probabilities(r,model)} for r in frame]
    result={'status':'EXPERIMENTAL_NO_BET','protocol':p,'protocol_sha256':protocol_digest,
            'test_races':len(test),'metrics':results,'coverage':coverage,
            'source_records_sha256':hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest(),
            'selected_before_test':p['selected_candidate'],'refitted':False,'prospective_model_changed':False}
    dump(dest,result);dump('reports/opposition_v3_holdout_predictions.json',predictions)
    lines=['# Test indépendant V3 — avril 2026','','**Expérimental, NO BET ; aucun remplacement du modèle prospectif.**','',
           f"{len(test)} courses. Modèles et choix de combined gelés avant collecte de ce mois.",'',
           '| Modèle | Log loss | Brier | Premier choix gagnant |','|---|---:|---:|---:|']
    for name,m in results.items():lines.append(f"| {name} | {m['log_loss']:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines+=['','Pas de réentraînement ni de nouvelle sélection sur ces résultats. Pas de cotes ni de ROI.']
    Path('reports/OPPOSITION_V3_HOLDOUT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'test_races':len(test),'metrics':results}))

if __name__=='__main__':
    try:main()
    except (ValueError,FileNotFoundError,RuntimeError) as error:
        dump('reports/opposition_v3_holdout_status.json',{'status':'BLOCKED','reason':str(error)})
        raise
    else:dump('reports/opposition_v3_holdout_status.json',{'status':'EVALUATED_NO_BET'})
