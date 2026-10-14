"""Bounded chronological ranker search; evaluation cannot select the model."""
import json
from pathlib import Path
from statistics import mean
from scripts.v6_holdout import verify
from scripts.backtest_connections import prepare, split, digest
from scripts.backtest_extension import load_sources
from turf_lab.demographics_tandem import augment, candidate
from turf_lab.pilot import probabilities, metrics as baseline_metrics
from turf_lab.xgb_model import metrics, paired
from turf_lab.xgb_rank import fit, scores, predictions, chronological, choose
from turf_lab.evidence import dump


def main():
    import xgboost as xgb
    protocol=Path('config/xgboost_rank_v2_protocol.json')
    p=json.loads(protocol.read_text())
    _,lock,base,models=verify()
    target=Path('reports/xgboost_rank_v2.json')
    if target.exists():
        old=json.loads(target.read_text())
        if old['protocol_sha256']!=digest(protocol) or old['baseline_frozen']!=lock:
            raise ValueError('Existing experiment under another protocol')
        print('Existing rank experiment retained; no retuning')
        return
    if any(m[:4] not in ('2024','2025') or int(m[5:])>5 for m in base['development_months']):
        raise ValueError('Only January-May development allowed')
    rows,source_hash,_=prepare(base,'validate')
    if source_hash!=lock['v5_frozen']['sources_sha256']:
        raise ValueError('Development sources changed')
    records,_=load_sources({'months':base['development_months'],'minimum_retained_fraction_per_month':.98})
    vp=json.loads(Path('config/demographics_tandem_v6_protocol.json').read_text())
    rows=candidate(augment(rows,records,vp['tandem_window_days'],vp['prior_strength']),'combined')
    folds=[]
    for f in p['folds']:
        train=split(rows,f['train'],p['minimum_races_per_month'])
        val=split(rows,f['validation'],p['minimum_races_per_month'])
        chronological(train,val)
        if any(r['date'][:4]!='2024' for r in train+val):
            raise ValueError('Tuning must use 2024 only')
        folds.append((train,val))
    trials=[]
    for config in p['candidates']:
        temp_trials=[{'candidate':config['name'],'temperature':t,'fold_log_losses':[]} for t in p['temperatures']]
        for train,val in folds:
            model=fit(train,config,p)
            raw=scores(val,model)
            for trial in temp_trials:
                trial['fold_log_losses'].append(metrics(val,predictions(val,raw,trial['temperature']))['log_loss'])
        trials.extend(temp_trials)
        print(json.dumps(temp_trials),flush=True)
    selected=choose(trials)
    config=next(c for c in p['candidates'] if c['name']==selected['candidate'])
    train=split(rows,p['final_train'],p['minimum_races_per_month'])
    val=split(rows,p['development_evaluation'],p['minimum_races_per_month'])
    chronological(train,val)
    model=fit(train,config,p)
    model_path='models/xgboost_rank_v2.json'
    model.save_model(model_path)
    # Lock choice and model before computing any 2025 evaluation predictions.
    selection={'status':'SELECTED_ON_2024_ONLY','selected':selected,'trials':trials,
        'protocol_sha256':digest(protocol),'models_sha256':digest(model_path),'baseline_frozen':lock,
        'sources_sha256':source_hash,'code_sha256':{path:digest(path) for path in ('turf_lab/xgb_rank.py','turf_lab/xgb_model.py','scripts/backtest_xgb_rank.py')},
        'xgboost_version':xgb.__version__}
    dump('models/xgboost_rank_v2_frozen.json',selection)
    loaded=xgb.Booster();loaded.load_model(model_path)
    raw=scores(val,loaded)
    if raw!=scores(val,model):
        raise ValueError('Reloaded model scores differ')
    probs={'v6':[probabilities(r,models['v6']) for r in val],
        'xgboost_rank':predictions(val,raw,selected['temperature'])}
    results={n:metrics(val,v) for n,v in probs.items()}
    if results['v6']!=baseline_metrics(val,models['v6']):
        raise ValueError('V6 metrics reproduction failed')
    expected=json.loads(Path('reports/demographics_tandem_v6.json').read_text())['validation']['combined']
    if abs(results['v6']['log_loss']-expected['log_loss'])>1e-10:
        raise ValueError('V6 reference changed')
    months={}
    for n,values in probs.items():
        months[n]={}
        for month in sorted({r['date'][:7] for r in val}):
            indexes=[i for i,r in enumerate(val) if r['date'][:7]==month]
            months[n][month]=metrics([val[i] for i in indexes],[values[i] for i in indexes])
    monthly_mean={n:mean(m['log_loss'] for m in v.values()) for n,v in months.items()}
    comparison=paired(val,probs['v6'],probs['xgboost_rank'])
    report=dict(selection,status='EXPLORATORY_2025_EVALUATION_NO_BET',
        train_races=len(train),evaluation_races=len(val),validation=results,by_month=months,
        monthly_mean_log_loss=monthly_mean,paired=comparison,test_evaluated=False,prospective_changed=False,limits=p['limits'])
    dump(target,report)
    lines=['# XGBoost Rank V2 — sélection chronologique','','**NO BET. Aucun changement V6/V7. Évaluation 2025 exploratoire.**',
        'Quatre variantes et trois températures ; choix exclusivement sur deux fenêtres chronologiques de 2024. Groupes = courses, vainqueur = 1, autres = 0.',
        'Sélection : '+json.dumps(selected),'',f"Entraînement final : {len(train)} courses ; évaluation : {len(val)} courses.",'',
        '| Modèle | Log loss mensuelle moyenne | Brier | Top-1 |','|---|---:|---:|---:|']
    for n,m in results.items():
        lines.append(f"| {n} | {monthly_mean[n]:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines+=['','Comparaison appariée : '+json.dumps(comparison),'',
        'Un score de classement n’est pas une probabilité. La conversion softmax et sa température sont figées avant évaluation 2025 ; la calibration reste à vérifier.',
        'Aucun test indépendant nouveau chargé, aucun ajustement après évaluation. Les périodes déjà consultées ne deviennent pas des tests vierges.',
        'Documentation : https://xgboost.readthedocs.io/en/release_3.0.0/tutorials/learning_to_rank.html']
    Path('reports/XGBOOST_RANK_V2.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'selected':selected,'scores':monthly_mean,'paired':comparison}),flush=True)


if __name__=='__main__':
    main()
