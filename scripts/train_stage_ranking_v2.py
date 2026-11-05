"""One fixed position-specific challenger, calibration on 2025 only."""
import gzip,json,math
from pathlib import Path
import numpy as np
from scripts.train_available_history_v3 import read,save,digest,sources
from turf_lab.available_history_research import available_features,variant
from turf_lab.available_history_operational import verify_active
from turf_lab.pilot import active,probabilities
from turf_lab.ranking_research import finish
from turf_lab.stage_ranking import fit_choice,temperature,strengths,ordered,unordered,greedy
ROOT=Path('reports/stage_ranking_v2');MODELS=Path('models/stage_ranking_v2')

def features(row):
    return np.asarray([[np.nan if v is None else v for v in p['features']] for p in active(row)],float)

def transform(x,mean,scale):
    missing=np.isnan(x)
    return np.c_[np.where(missing,0,(x-mean)/scale),missing.astype(float)]

def main():
    if (ROOT/'evaluation.json').exists():raise ValueError('Completed experiment: no overwrite')
    protocol=read('config/stage_ranking_v2.json');policy,base_temp=verify_active()
    print('Loading verified existing history',flush=True)
    dm=read('reports/full_history/datasets/manifest.json');frames={}
    for split,info in dm['splits'].items():
        if digest(info['file'])!=info['sha256']:raise ValueError('Dataset hash mismatch')
        with gzip.open(info['file'],'rt') as f:frames[split]=[json.loads(line) for line in f]
    records,manifests=sources();truths={r['race_id']:finish(r['participants']) for r in records}
    rows,audit=available_features(records,sum(frames.values(),[]))
    rows=variant(rows,policy['variant']);kept={}
    for r in rows:
        truth=truths[r['race_id']]
        if truth is None:continue
        numbers=[p['number'] for p in active(r)]
        r['truth_indices']=[numbers.index(n) for n in truth];kept[r['race_id']]=r
    groups={s:[kept[r['race_id']] for r in rr if r['race_id'] in kept] for s,rr in frames.items()}
    save(ROOT/'data_audit.json',dict(counts={s:len(rr) for s,rr in groups.items()},features=audit,datasets=dm,source_manifests=manifests))
    del records,rows,kept,frames,truths
    raw=np.concatenate([features(r) for r in groups['train']])
    mean=np.nanmean(raw,axis=0);mean=np.nan_to_num(mean)
    scale=np.nanstd(raw,axis=0);scale=np.where(np.isfinite(scale)&(scale>1e-8),scale,1)
    matrices={s:[transform(features(r),mean,scale) for r in rr] for s,rr in groups.items()}
    coefficients=[];fits=[]
    for stage in range(5):
        xx=[];sizes=[];winners=[]
        for r,x in zip(groups['train'],matrices['train']):
            y=r['truth_indices'];keep=[j for j in range(len(x)) if j not in y[:stage]]
            xx.append(x[keep]);sizes.append(len(keep));winners.append(keep.index(y[stage]))
        print('Fitting conditional position',stage+1,flush=True)
        coef,fit=fit_choice(np.concatenate(xx),sizes,winners,protocol['ridge']);coefficients.append(coef);fits.append(fit)
    coef=np.asarray(coefficients)
    val_scores=[coef@x.T for x in matrices['validation']]
    val_truth=[r['truth_indices'] for r in groups['validation']]
    temps=[temperature(val_scores,val_truth,j) for j in range(5)]
    save(MODELS/'model.json',dict(mean=mean.tolist(),scale=scale.tolist(),coefficients=coef.tolist(),temperatures=temps,fits=fits))
    save(MODELS/'frozen_before_test.json',dict(model_sha256=digest(MODELS/'model.json'),protocol_sha256=digest('config/stage_ranking_v2.json'),active_policy_sha256=digest('config/active_model.json'),code_sha256={p:digest(p) for p in ['scripts/train_stage_ranking_v2.py','turf_lab/stage_ranking.py']},calibration='2025 only; conditional likelihood per position',test_status='2026 previously inspected; exploratory only'))
    print('Frozen; evaluating paired test',flush=True)
    base=read(policy['model_file']);events=[]
    for r,x in zip(groups['test'],matrices['test']):
        numbers=[p['number'] for p in active(r)];p=probabilities(r,base)
        baseline=strengths(np.tile(np.log([p[n] for n in numbers]),(5,1)),[base_temp]*5)
        score=coef@x.T
        distributions={'v3':baseline,'stage_raw':strengths(score,[1]*5),'stage_calibrated':strengths(score,temps)}
        for k in (3,4,5):
            truth=r['truth_indices'][:k];fixed=greedy(baseline,k)
            for name,w in distributions.items():
                selection=greedy(w,k)
                events.append(dict(race_id=r['race_id'],date=r['date'],k=k,model=name,
                    selection=[numbers[j] for j in selection],hit=int(set(selection)==set(truth)),
                    probability=unordered(w,selection),found=len(set(selection)&set(truth)),
                    ordered_loss=-math.log(max(1e-300,ordered(w,truth))),
                    unordered_loss=-math.log(max(1e-300,unordered(w,truth))),
                    fixed_probability=unordered(w,fixed),fixed_hit=int(set(fixed)==set(truth))))
    with gzip.open(ROOT/'events.jsonl.gz','wt') as f:
        for e in events:f.write(json.dumps(e)+'\n')
    results={};rng=np.random.default_rng(20261106)
    for k in (3,4,5):
        results[str(k)]={}
        for name in ('v3','stage_raw','stage_calibrated'):
            es=[e for e in events if e['k']==k and e['model']==name]
            results[str(k)][name]=dict(races=len(es),hits=sum(e['hit'] for e in es),expected=sum(e['probability'] for e in es),
                ordered_loss=np.mean([e['ordered_loss'] for e in es]),unordered_loss=np.mean([e['unordered_loss'] for e in es]),
                fixed_event_brier=np.mean([(e['fixed_probability']-e['fixed_hit'])**2 for e in es]))
        bs=[e for e in events if e['k']==k and e['model']=='v3']
        cs=[e for e in events if e['k']==k and e['model']=='stage_calibrated']
        from datetime import date
        weeks={}
        for b,c in zip(bs,cs):
            assert b['race_id']==c['race_id']
            week=tuple(date.fromisoformat(b['date']).isocalendar()[:2])
            weeks.setdefault(week,[]).append([c['hit']-b['hit'],c['unordered_loss']-b['unordered_loss']])
        totals=np.array([np.sum(v,axis=0) for v in weeks.values()]);counts=np.array([len(v) for v in weeks.values()])
        idx=rng.integers(0,len(weeks),(2000,len(weeks)))
        boot=totals[idx].sum(axis=1)/counts[idx].sum(axis=1)[:,None]
        results[str(k)]['paired_weekly_95_ci']=np.quantile(boot,[.025,.975],axis=0).tolist()
    save(ROOT/'evaluation.json',dict(status='COMPLETED_EXPLORATORY',results=results,temperatures=temps,production_changed=False,recommendations_allowed=False,limitations=protocol['limitations']))
    lines=['# Classement conditionnel V2 et calibration','',
        'Un seul candidat, cinq modèles de choix conditionnel. Apprentissage 2022–2024, températures sur 2025 uniquement. V3 inchangée.',
        '2026 est une comparaison exploratoire déjà consultée, pas une validation indépendante.',
        '', '| Arrivée | Modèle | Réussites | Attendues | Perte désordre (plus bas = mieux) |', '|---|---|---:|---:|---:|']
    for k,result in results.items():
        for name in ('v3','stage_raw','stage_calibrated'):
            m=result[name];lines.append(f"| Top{k} | {name} | {m['hits']}/{m['races']} | {m['expected']:.1f} | {m['unordered_loss']:.4f} |")
    lines+=['','Les probabilités désordre somment toutes les permutations par calcul exact. Les températures corrigent toute la distribution conditionnelle : elles ne multiplient pas des probabilités marginales.',
        'La calibration conserve ici la sélection gloutonne : elle corrige la confiance, sans fabriquer de réussites supplémentaires.',
        'Sélection gloutonne des places, pas recherche de la combinaison désordre optimale. Cohorte avec cinq places uniques connues ; les résultats ambigus sont exclus.',
        'Comparer les Brier uniquement sur le même événement (sélection V3), champ fixed_event_brier. Intervalles hebdomadaires appariés dans evaluation.json.',
        'Pas de promotion automatique, rapports commerciaux, bonus ou rentabilité. Une période future gelée reste nécessaire.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(results,indent=2),flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:save(ROOT/'failure.json',dict(status='FAILED',reason=str(e)));raise
