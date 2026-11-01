"""Four prespecified ranking challengers; frozen sports V3 remains operational."""
import gzip,json,math
from pathlib import Path
from collections import Counter
import numpy as np
import xgboost as xgb
from scipy.optimize import minimize_scalar
from scripts.train_available_history_v3 import sources,read,save,digest
from turf_lab.available_history_research import available_features,variant
from turf_lab.available_history_operational import verify_active
from turf_lab.pilot import probabilities,active
from turf_lab.rank45 import ordered_probability
from turf_lab.ranking_research import finish,weights,unordered,portfolio
ROOT=Path('reports/ranking_v1');MODELS=Path('models/ranking_v1')
def raw_scores(rows,model):
    return [np.log([probabilities(r,model)[p['number']] for p in active(r)]).tolist() for r in rows]
def matrix(rows,label=None):
    xs=[];ys=[];sizes=[]
    for row in rows:
        rr=active(row);sizes.append(len(rr))
        for p in rr:
            xs.append([np.nan if v is None else v for v in p['features']])
            rank=row['truth'].index(p['number'])+1 if p['number'] in row['truth'] else 6
            ys.append(6-rank if label=='rank' else int(rank<=int(label)) if label else 0)
    d=xgb.DMatrix(np.array(xs,dtype=np.float32),label=np.array(ys),nthread=1)
    if label=='rank':d.set_group(sizes)
    elif label:d.set_weight(np.repeat([1/n for n in sizes],sizes))
    return d,sizes
def chunks(flat,sizes):
    output=[];offset=0
    for n in sizes:output.append(flat[offset:offset+n].tolist());offset+=n
    return output
def ordered_loss(rows,scores,t,k):
    total=0
    for r,s in zip(rows,scores):
        p=dict(zip([x['number'] for x in active(r)],weights(s,t)))
        total-=math.log(max(1e-300,ordered_probability(p,r['truth'][:k])))
    return total/len(rows)
def summarize(rows,scores,t,k,details=False):
    values=[];saved=[]
    for r,s in zip(rows,scores):
        numbers=[x['number'] for x in active(r)];p=dict(zip(numbers,weights(s,t)))
        order=sorted(numbers,key=lambda n:(-p[n],n))[:k];truth=r['truth'][:k]
        pr=unordered(p,order);hit=set(order)==set(truth)
        values.append([int(order==truth),int(hit),len(set(order)&set(truth)),pr,(pr-hit)**2,
            -math.log(max(1e-300,ordered_probability(p,truth))),-math.log(max(1e-300,unordered(p,truth)))])
        if details:saved.append(dict(race_id=r['race_id'],date=r['date'],selection=order,truth=truth,
            ordered_probability=ordered_probability(p,order),**portfolio(p,[order])))
    a=np.array(values)
    result=dict(races=len(rows),**{n:float(a[:,i].mean()) for i,n in enumerate(['ordered_hit','unordered_hit','found','predicted_unordered','selection_brier','ordered_log_loss','unordered_log_loss'])})
    return result,saved
def main():
    if (ROOT/'evaluation.json').exists():raise ValueError('Completed experiment; no overwrite')
    protocol=read('config/ranking_v1.json');policy,base_temp=verify_active()
    if xgb.__version__!=protocol['xgboost_version']:raise ValueError('XGBoost mismatch')
    dm=read('reports/full_history/datasets/manifest.json');frames={}
    for n,info in dm['splits'].items():
        if digest(info['file'])!=info['sha256']:raise ValueError('Dataset changed')
        with gzip.open(info['file'],'rt') as f:frames[n]=[json.loads(s) for s in f]
    records,manifests=sources();by_id={r['race_id']:r for r in records}
    all_rows,audit=available_features(records,sum(frames.values(),[]))
    all_rows=variant(all_rows,policy['variant']);excluded=Counter();kept={}
    for r in all_rows:
        source=by_id[r['race_id']]
        truth=finish(source['participants'])
        if truth is None:excluded[r['date'][:4]]+=1;continue
        if {p['number'] for p in active(r)}!={p['numPmu'] for p in source['participants'] if p.get('statut')!='NON_PARTANT'}:raise ValueError('Field mismatch')
        r['truth']=truth;kept[r['race_id']]=r
    groups={n:[kept[r['race_id']] for r in rs if r['race_id'] in kept] for n,rs in frames.items()}
    selection=[r for r in groups['validation'] if r['date']<'2025-07-01'];calibration=[r for r in groups['validation'] if r['date']>='2025-07-01']
    groups.update(selection=selection,calibration=calibration)
    save(ROOT/'data_audit.json',dict(counts={n:len(rs) for n,rs in groups.items()},excluded=dict(excluded),features=audit,source_manifests=manifests,datasets=dm['splits']))
    del records,by_id,all_rows,kept,frames
    model=read(policy['model_file']);models={};scores={n:{} for n in ['selection','calibration','test']}
    for split in ['selection','calibration']:
        scores[split]['v3']=raw_scores(groups[split],model)
    MODELS.mkdir(parents=True,exist_ok=True)
    for name,label in [('rank','rank'),('top3','3'),('top4','4'),('top5','5')]:
        print('Training',name,len(groups['train']),flush=True)
        d,_=matrix(groups['train'],label)
        params=dict(protocol['params'],objective='rank:pairwise' if label=='rank' else 'binary:logistic')
        m=xgb.train(params,d,num_boost_round=protocol['rounds']);m.save_model(MODELS/(name+'.json'));models[name]=m
        for split in ['selection','calibration']:
            d,sizes=matrix(groups[split]);scores[split][name]=chunks(m.predict(d,output_margin=True),sizes)
    selected={};temps={};development={}
    for k in (3,4,5):
        development[str(k)]={n:summarize(selection,s,base_temp if n=='v3' else 1,k)[0] for n,s in scores['selection'].items()}
        selected[str(k)]=min(development[str(k)],key=lambda n:(-development[str(k)][n]['unordered_hit'],development[str(k)][n]['ordered_log_loss']))
        temps[str(k)]={}
        for n,s in scores['calibration'].items():
            if n=='v3':temps[str(k)][n]=base_temp;continue
            opt=minimize_scalar(lambda t:ordered_loss(calibration,s,t,k),bounds=(.25,4),method='bounded',options={'xatol':.01})
            if not opt.success:raise ValueError('Joint projection calibration failed')
            temps[str(k)][n]=float(opt.x)
    save(MODELS/'frozen_before_test.json',dict(selected=selected,temperatures=temps,development=development,
        models_sha256={n:digest(MODELS/(n+'.json')) for n in models},protocol_sha256=digest('config/ranking_v1.json'),
        active_policy_sha256=digest('config/active_model.json'),code_sha256={p:digest(p) for p in ['scripts/train_ranking_v1.py','turf_lab/ranking_research.py']}))
    print('Frozen; evaluating test',flush=True)
    scores['test']['v3']=raw_scores(groups['test'],model)
    for n,m in models.items():
        d,sizes=matrix(groups['test']);scores['test'][n]=chunks(m.predict(d,output_margin=True),sizes)
    results={};events=[]
    for k in (3,4,5):
        results[str(k)]={}
        for n,s in scores['test'].items():
            metrics,detail=summarize(groups['test'],s,temps[str(k)][n],k,details=n==selected[str(k)])
            results[str(k)][n]=metrics
            events.extend(dict(x,k=k,model=n) for x in detail)
    save(ROOT/'evaluation.json',dict(status='COMPLETED_EXPLORATORY',selected_before_test=selected,results=results,counts={n:len(rs) for n,rs in groups.items()},
        recommendations_allowed=False,production_changed=False,limitations=protocol['limitations']))
    with gzip.open(ROOT/'selected_combinations.jsonl.gz','wt') as f:
        for e in events:f.write(json.dumps(e)+'\n')
    lines=['# Classements et combinaisons — expérience V1','',
        'Aucun changement du V3 actif. Modèles sélectionnés sur le premier semestre 2025, projection jointe ajustée sur le second.',
        '2026 a déjà été examiné : évaluation exploratoire. Cohorte commune avec cinq premières places non ambiguës.',
        '', '| Objectif | Modèle | Courses | Ordre | Désordre | Trouvés | Probabilité désordre moyenne |',
        '|---|---|---:|---:|---:|---:|---:|']
    for k in (3,4,5):
        for n,m in results[str(k)].items():
            lines.append(f"| Top{k} | {n}{' (retenu sur 2025)' if n==selected[str(k)] else ''} | {m['races']} | {m['ordered_hit']:.2%} | {m['unordered_hit']:.2%} | {m['found']:.2f} | {m['predicted_unordered']:.2%} |")
    lines+=['','Les scores Topk ne sont pas multipliés entre eux : une distribution Plackett-Luce est ajustée sur 2025 pour les événements conjoints. Cette hypothèse reste à valider.',
        'Les seuils de rentabilité sauvegardés sont théoriques : coût / probabilité, sans rapports commerciaux ni bonus. Aucune EV ou rentabilité inventée.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':
    try:main()
    except Exception as e:save(ROOT/'failure.json',dict(status='FAILED',reason=str(e)));raise
