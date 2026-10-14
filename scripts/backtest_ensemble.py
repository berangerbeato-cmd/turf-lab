"""Fixed mixtures of V6 and grouped XGBoost; no fitting or new test outcomes."""
import json
from pathlib import Path
from statistics import mean
from scripts.v6_holdout import verify
from scripts.backtest_connections import prepare, split, digest
from scripts.backtest_extension import load_sources
from turf_lab.demographics_tandem import augment, candidate
from turf_lab.pilot import probabilities, active
from turf_lab.xgb_rank import scores, predictions
from turf_lab.xgb_model import metrics, paired
from turf_lab.ensemble import blend
from turf_lab.evidence import dump


def main():
    import xgboost as xgb
    path=Path('config/ensemble_v1_protocol.json')
    p=json.loads(path.read_text())
    _,v6_lock,base,models=verify()
    rank_lock=json.loads(Path('models/xgboost_rank_v2_frozen.json').read_text())
    model_path='models/xgboost_rank_v2.json'
    if rank_lock['baseline_frozen']!=v6_lock or rank_lock['models_sha256']!=digest(model_path):
        raise ValueError('Ranker baseline or weights changed')
    if rank_lock['protocol_sha256']!=digest('config/xgboost_rank_v2_protocol.json') or any(digest(f)!=sha for f,sha in rank_lock['code_sha256'].items()):
        raise ValueError('Ranker protocol or code changed')
    if xgb.__version__!=rank_lock['xgboost_version']:
        raise ValueError('XGBoost version changed')
    target=Path('reports/ensemble_v1.json')
    if target.exists():
        old=json.loads(target.read_text())
        if old['protocol_sha256']!=digest(path) or old['rank_frozen']!=rank_lock:
            raise ValueError('Existing ensemble under another freeze')
        print('Existing ensemble result retained; no new weights')
        return
    if any(m[:4] not in ('2024','2025') or int(m[5:])>5 for m in base['development_months']):
        raise ValueError('Only development data allowed')
    rows,source_hash,_=prepare(base,'validate')
    if source_hash!=rank_lock['sources_sha256']:
        raise ValueError('Development sources changed')
    records,_=load_sources({'months':base['development_months'],'minimum_retained_fraction_per_month':.98})
    vp=json.loads(Path('config/demographics_tandem_v6_protocol.json').read_text())
    rows=candidate(augment(rows,records,vp['tandem_window_days'],vp['prior_strength']),'combined')
    val=split(rows,p['evaluation'],p['minimum_races_per_month'])
    model=xgb.Booster();model.load_model(model_path)
    baseline=[probabilities(r,models['v6']) for r in val]
    challenger=predictions(val,scores(val,model),rank_lock['selected']['temperature'])
    old=json.loads(Path('reports/xgboost_rank_v2.json').read_text())['validation']
    for n,values in [('v6',baseline),('xgboost_rank',challenger)]:
        if metrics(val,values)!=old[n]:
            raise ValueError('Frozen model evaluation not reproduced')
    results,monthly,comparisons,averages={},{},{},{}
    for weight in p['xgboost_weights']:
        key=f'{weight:.1f}'
        mixed=[blend(a,b,weight) for a,b in zip(baseline,challenger)]
        results[key]=metrics(val,mixed)
        monthly[key]={}
        for month in sorted({r['date'][:7] for r in val}):
            ix=[i for i,r in enumerate(val) if r['date'][:7]==month]
            monthly[key][month]=metrics([val[i] for i in ix],[mixed[i] for i in ix])
        averages[key]=mean(m['log_loss'] for m in monthly[key].values())
        comparisons[key]=paired(val,baseline,mixed)
    best=min(p['xgboost_weights'],key=lambda w:averages[f'{w:.1f}'])
    counts={'both_correct':0,'v6_only_correct':0,'xgboost_only_correct':0,'both_wrong':0}
    for race,a,b in zip(val,baseline,challenger):
        runners=active(race)
        winner=next(r['number'] for r in runners if r['won'])
        first=lambda p:min((r['number'] for r in runners),key=lambda n:(-p[n],n))
        ca,cb=first(a)==winner,first(b)==winner
        counts['both_correct' if ca and cb else 'v6_only_correct' if ca else 'xgboost_only_correct' if cb else 'both_wrong']+=1
    report={'status':'EXPLORATORY_REUSED_VALIDATION_NO_BET','protocol_sha256':digest(path),
        'rank_frozen':rank_lock,'sources_sha256':source_hash,'evaluation_races':len(val),
        'selected_xgboost_weight':best,'validation':results,'by_month':monthly,'monthly_mean_log_loss':averages,
        'paired':comparisons,'top1_complementarity':counts,'refitted':False,'test_evaluated':False,'prospective_changed':False,
        'code_sha256':{f:digest(f) for f in ('turf_lab/ensemble.py','scripts/backtest_ensemble.py')}}
    dump(target,report)
    dump('models/ensemble_v1_frozen.json',{'status':'EXPLORATORY_NOT_DEPLOYED','xgboost_weight':best,
        'rank_frozen':rank_lock,'protocol_sha256':digest(path),'report_sha256':digest(target),'code_sha256':report['code_sha256']})
    lines=['# Mélange V6 et XGBoost regroupé — essai exploratoire','','**Validation déjà consultée. Aucun réentraînement, aucune mise, aucun changement du suivi réel.**',
        f"{len(val)} courses. Poids testés prépubliés : 0 %, 10 %, 20 %, 30 % de XGBoost.",'',
        '| Part XGBoost | Log loss mensuelle moyenne | Brier | Gagnant premier |','|---|---:|---:|---:|']
    for weight in p['xgboost_weights']:
        key=f'{weight:.1f}';m=results[key]
        lines.append(f"| {weight:.0%} | {averages[key]:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines+=['',f"Poids retenu selon le critère prépublié : {best:.0%} de XGBoost.",'',
        'Complémentarité des premiers choix : '+json.dumps(counts),'',
        'Intervalles et résultats mensuels dans le JSON. Les premiers choix différents ne garantissent pas un meilleur mélange de probabilités.',
        'Tout gain éventuel nécessite une nouvelle période indépendante. Aucun ajustement supplémentaire après lecture.']
    Path('reports/ENSEMBLE_V1.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'scores':averages,'selected':best,'complementarity':counts}),flush=True)


if __name__=='__main__':
    main()
