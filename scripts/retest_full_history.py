"""Full historical retest, fail closed until every required month is verified."""
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from turf_lab.evidence import dump
from scripts.history_inventory import inventory
from scripts.backtest_extension import load_sources
from turf_lab.full_history_features import prepare, seasonal
from turf_lab.full_history_evaluation import (chronological, tree_fit, tree_predict, tune,
    temper, mix, score, paired, season)
from turf_lab.fast_logit import fit
from turf_lab.pilot import probabilities, active
from turf_lab.xgb_model import metrics

ROOT=Path('reports/full_history')
MODELS=Path('models/full_history')
PROTOCOL=Path('config/full_history_protocol.json')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def gate(rows,p):
    by={r['month']:r for r in rows}
    expected=[f'{y}-{m:02d}' for y in range(2022,2027) for m in range(1,13)
              if p['months']['from']<=f'{y}-{m:02d}'<=p['months']['through']]
    return [m for m in expected if m not in by or by[m]['status']!='COMPLETE'
            or not by[m].get('source_verified') or by[m].get('issues')
            or (by[m].get('coverage_fraction') or 0)<p['minimum_coverage']]


def bounds(rows, limits):return [r for r in rows if limits[0]<=r['date']<=limits[1]]


def learn(train, val, p):
    classic=fit(train,p['l2'],p['iterations'],p['learning_rate'])
    trees={n:tree_fit(train,p,ranking=n=='xgboost_rank') for n in ('xgboost','xgboost_rank')}
    raw={'classic':[probabilities(r,classic) for r in val],**{n:tree_predict(val,m) for n,m in trees.items()}}
    temperatures={};pred={}
    for name,values in raw.items():temperatures[name],pred[name]=tune(val,values,p['temperatures'])
    alpha=min(p['ensemble_weights'],key=lambda a:metrics(val,mix(pred['classic'],pred['xgboost'],a))['log_loss'])
    pred['ensemble']=mix(pred['classic'],pred['xgboost'],alpha)
    return classic,trees,temperatures,alpha,pred,raw


def predict(rows,classic,trees,temperatures,alpha):
    raw={'classic':[probabilities(r,classic) for r in rows],**{n:tree_predict(rows,m) for n,m in trees.items()}}
    pred={n:temper(rows,v,temperatures[n]) for n,v in raw.items()}
    pred['ensemble']=mix(pred['classic'],pred['xgboost'],alpha)
    pred['uniform']=[probabilities(r,{'kind':'uniform'}) for r in rows]
    return pred,raw


def represent(records):
    groups=defaultdict(list)
    for r in records:groups[r['date'][:7]].append(r)
    out={}
    for month,rows in groups.items():
        runners=[p for r in rows for p in r['participants']]
        out[month]={'races':len(rows),'dates':len({r['date'] for r in rows}),
          'season':season(rows[0]['date']), 'venues':dict(Counter(r['venue'] for r in rows)),
          'start_type':dict(Counter(r['start_type'] for r in rows)),
          'field_size':dict(Counter(str(sum(p.get('statut')!='NON_PARTANT' for p in r['participants'])) for r in rows)),
          'age':dict(Counter(str(p.get('age','UNKNOWN')) for p in runners)),
          'warning':'PMU-listed retained sample; representativeness outside PMU not established'}
    return out


def save_dataset(rows,name):
    out=ROOT/'datasets';out.mkdir(parents=True,exist_ok=True)
    path=out/(name+'.jsonl.gz')
    content=''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rows).encode()
    path.write_bytes(gzip.compress(content,mtime=0))
    return {'file':str(path),'sha256':digest(path),'races':len(rows),'from':min(r['date'] for r in rows),'to':max(r['date'] for r in rows)}


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    p=json.loads(PROTOCOL.read_text())
    inv=inventory(Path('data'),through=p['months']['through'],as_of=p['as_of'])
    dump(ROOT/'verified_inventory.json',inv)
    missing=gate(inv,p)
    if missing:
        dump(ROOT/'status.json',{'status':'BLOCKED_INCOMPLETE_HISTORY','months_requiring_work':missing,
              'models_retrained':False,'production_changed':False})
        print('Full retest blocked: '+str(len(missing))+' required months incomplete. No model trained.')
        raise SystemExit(2)
    provenance={'protocol_sha256':digest(PROTOCOL),
       'source_manifests':{r['month']:r['manifest_sha256'] for r in inv},
       'code_sha256':{str(f):digest(f) for f in list(Path('turf_lab').glob('*.py'))+[Path('scripts/retest_full_history.py')]}}
    target=ROOT/'comparison.json'
    if target.exists():
        if json.loads(target.read_text())['provenance']!=provenance:raise ValueError('Existing experiment has different inputs; new version required')
        print('Existing verified experiment preserved.');return
    records,coverage=load_sources({'months':[r['month'] for r in inv],
                                  'minimum_retained_fraction_per_month':p['minimum_coverage']})
    dump(ROOT/'representativeness.json',represent(records))
    rows=prepare(records);del records
    splits={name:bounds(rows,p[name]) for name in ('train','validation','test')}
    chronological(splits['train'],splits['validation'],splits['test'])
    dataset={name:save_dataset(v,name) for name,v in splits.items()}
    dump(ROOT/'datasets/manifest.json',{'provenance':provenance,'splits':dataset,'protocol':p})
    train,val,test=(splits[k] for k in ('train','validation','test'))
    MODELS.mkdir(parents=True,exist_ok=True)
    classic,trees,temps,alpha,vpred,vraw=learn(train,val,p)
    dump(MODELS/'classic.json',classic)
    for n,m in trees.items():m.save_model(MODELS/(n+'.json'))
    # Lock learned parameters before reading test performance.
    lock={'provenance':provenance,'temperatures':temps,'ensemble_weight':alpha,
          'model_hashes':{f.name:digest(f) for f in MODELS.glob('*.json') if f.name!='frozen.json'}}
    dump(MODELS/'frozen.json',lock)
    tpred,traw=predict(test,classic,trees,temps,alpha)
    results={'provenance':provenance,'status':'EXPLORATORY_REUSED_HOLDOUT_NO_PROMOTION',
        'splits':dataset,'frozen':lock,'validation':{n:score(val,v) for n,v in vpred.items()},
        'test':{n:score(test,v) for n,v in tpred.items()},
        'test_uncalibrated':{n:metrics(test,v) for n,v in traw.items()},
        'paired':{n:{b:paired(test,tpred['classic'],tpred[n],b) for b in ('day','week')}
                  for n in ('xgboost','xgboost_rank','ensemble')},'limits':p['limits']}
    dump(ROOT/'primary_comparison.json',results)
    # Day-blocked rolling-origin robustness, fixed settings, no validation retuning.
    rolling=[]
    for fold in p['rolling_origin']:
        tr=bounds(rows,[p['train'][0],fold['train_end']])
        te=bounds(rows,[fold['evaluate_year']+'-01-01',fold['evaluate_year']+'-12-31'])
        if not tr or not te or max(r['date'] for r in tr)>=min(r['date'] for r in te):raise ValueError('Rolling fold overlap')
        c=fit(tr,p['l2'],p['iterations'],p['learning_rate']);x=tree_fit(tr,p)
        cp=[probabilities(r,c) for r in te];xp=tree_predict(te,x)
        rolling.append({'fold':fold,'train_races':len(tr),'test_races':len(te),
                        'classic':score(te,cp),'xgboost':score(te,xp),'paired_week':paired(te,cp,xp)})
    results['rolling_origin']=rolling
    dump(ROOT/'rolling_origin.json',rolling)
    # Fixed seasonality ablation on identical splits, no test-driven choice.
    st,sv,se=seasonal(train),seasonal(val),seasonal(test)
    sc=fit(st,p['l2'],p['iterations'],p['learning_rate']);sx=tree_fit(st,p)
    sraw={'classic':[probabilities(r,sc) for r in sv],'xgboost':tree_predict(sv,sx)}
    stemps={n:tune(sv,v,p['temperatures'])[0] for n,v in sraw.items()}
    sp={'classic':temper(se,[probabilities(r,sc) for r in se],stemps['classic']),
        'xgboost':temper(se,tree_predict(se,sx),stemps['xgboost'])}
    results['seasonality_ablation']={n:{'temperature':stemps[n],'test':score(se,v),
       'paired_against_no_calendar':paired(test,tpred[n],v)} for n,v in sp.items()}
    dump(ROOT/'comparison.json',results)
    prediction_file=ROOT/'test_predictions.jsonl.gz'
    prediction_file.write_bytes(gzip.compress(''.join(json.dumps({'race_id':r['race_id'],'date':r['date'],
          'probabilities':{n:v[i] for n,v in tpred.items()}})+'\n' for i,r in enumerate(test)).encode(),mtime=0))
    dump(ROOT/'status.json',{'status':'COMPLETED_EXPLORATORY','production_changed':False,
          'report_sha256':digest(target),'prediction_sha256':digest(prediction_file)})
    lines=['# Full-history model comparison','','Exploratory: 2025 and some 2026 outcomes were previously inspected.',
           'No real bets or automatic deployment.','', '| Model | Test races | Log loss | Brier | Top-1 | ECE |',
           '|---|---:|---:|---:|---:|---:|']
    for n,v in results['test'].items():
        m=v['overall'];lines.append(f"| {n} | {m['races']} | {m['log_loss']:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.2%} | {m['runner_ece']:.5f} |")
    lines+=['','Full subgroup results, calibration bins, day/week intervals and rolling-origin checks: comparison.json.',
            'Credibility requires consistent gains across folds/seasons; confidence intervals do not prove profitability.',
            'Autumn 2026 is September only. Future prospective validation remains necessary.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
