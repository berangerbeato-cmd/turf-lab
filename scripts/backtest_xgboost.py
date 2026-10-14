"""One fixed XGBoost experiment on exactly the V6 development features."""
import json
from pathlib import Path
from statistics import mean
from scripts.v6_holdout import verify
from scripts.backtest_connections import prepare, split, digest
from scripts.backtest_extension import load_sources
from turf_lab.demographics_tandem import augment, candidate
from turf_lab.pilot import probabilities, metrics as baseline_metrics
from turf_lab.xgb_model import fit, predict, metrics, paired
from turf_lab.evidence import dump


def main():
    import xgboost as xgb
    import numpy as np
    protocol=Path('config/xgboost_v1_protocol.json')
    p=json.loads(protocol.read_text())
    _,lock,base,models=verify()
    target=Path('reports/xgboost_v1.json')
    if target.exists():
        old=json.loads(target.read_text())
        if old['protocol_sha256']!=digest(protocol) or old['baseline_frozen']!=lock:
            raise ValueError('Existing experiment under another protocol')
        print('Existing XGBoost experiment retained; no retuning')
        return
    if any(m[:4] not in ('2024','2025') or int(m[5:])>5 for m in base['development_months']):
        raise ValueError('Only January-May development allowed')
    rows,source_hash,_=prepare(base,'validate')
    if source_hash!=lock['v5_frozen']['sources_sha256']:
        raise ValueError('Development data changed')
    records,_=load_sources({'months':base['development_months'],'minimum_retained_fraction_per_month':.98})
    vp=json.loads(Path('config/demographics_tandem_v6_protocol.json').read_text())
    rows=candidate(augment(rows,records,vp['tandem_window_days'],vp['prior_strength']),'combined')
    train=split(rows,p['train'],p['minimum_races_per_month'])
    val=split(rows,p['validation'],p['minimum_races_per_month'])
    print('Training fixed XGBoost configuration on '+str(len(train))+' races',flush=True)
    model=fit(train,p)
    model_path='models/xgboost_v1.json'
    model.save_model(model_path)
    restored=xgb.Booster();restored.load_model(model_path)
    predictions={'v6':[probabilities(r,models['v6']) for r in val],'xgboost':predict(val,restored)}
    if predictions['xgboost']!=predict(val,model):
        raise ValueError('Serialized model predictions changed')
    results={n:metrics(val,values) for n,values in predictions.items()}
    expected=json.loads(Path('reports/demographics_tandem_v6.json').read_text())['validation']['combined']
    if abs(results['v6']['log_loss']-expected['log_loss'])>1e-10 or results['v6']!=baseline_metrics(val,models['v6']):
        raise ValueError('V6 metrics not exactly reproduced')
    months={}
    for n,values in predictions.items():
        months[n]={}
        for month in sorted({r['date'][:7] for r in val}):
            indexes=[i for i,r in enumerate(val) if r['date'][:7]==month]
            months[n][month]=metrics([val[i] for i in indexes],[values[i] for i in indexes])
    scores={n:mean(m['log_loss'] for m in by_month.values()) for n,by_month in months.items()}
    comparison=paired(val,predictions['v6'],predictions['xgboost'])
    report={'status':'EXPLORATORY_REUSED_VALIDATION_NO_BET','protocol_sha256':digest(protocol),
        'baseline_frozen':lock,'sources_sha256':source_hash,'models_sha256':digest(model_path),
        'code_sha256':{path:digest(path) for path in ('turf_lab/xgb_model.py','scripts/backtest_xgboost.py')},
        'versions':{'xgboost':xgb.__version__,'numpy':np.__version__},'train_races':len(train),'validation_races':len(val),
        'validation':results,'by_month':months,'monthly_mean_log_loss':scores,'paired':comparison,
        'test_evaluated':False,'prospective_changed':False,'limits':p['limits']}
    dump(target,report)
    lines=['# XGBoost V1 — comparaison exploratoire à V6','','**NO BET. Aucun changement au suivi prospectif. Validation déjà consultée.**',
        f"Train : {len(train)} courses. Validation : {len(val)} courses. Même information en entrée : 38 variables V6.",'',
        '| Modèle | Log loss mensuelle moyenne | Brier | Top-1 |','|---|---:|---:|---:|']
    for n,m in results.items():
        lines.append(f"| {n} | {scores[n]:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines+=['','Comparaison appariée : '+json.dumps(comparison),'',
        '200 arbres, profondeur 3, un seul réglage prépublié. Objectif binaire pondéré par course, puis normalisation des odds entre partants. Pas de réglage de calibration ni de température.',
        'Ce premier essai ne constitue pas une recherche exhaustive du meilleur XGBoost. L’objectif binaire diffère de la log loss conditionnelle de V6.',
        'Aucun résultat juillet–octobre 2025 ni 2026 chargé. Nouveau test indépendant nécessaire avant toute conclusion de gain.',
        'Documentation : https://xgboost.readthedocs.io/en/stable/parameter.html']
    Path('reports/XGBOOST_V1.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'scores':scores,'paired':comparison}),flush=True)


if __name__=='__main__':
    main()
