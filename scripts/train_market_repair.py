"""One prespecified market correction experiment; no change to operational models."""
import gzip,hashlib,json,math
from collections import defaultdict,Counter
from pathlib import Path
from datetime import date
import numpy as np
from turf_lab.market_repair import fit,predict
from turf_lab.pilot import probabilities
from turf_lab.month_history import identity
from scripts.audit_value_market import odds_band,summarize

ROOT=Path('reports/market_repair_v1');MODEL=Path('models/market_repair_v1')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def dataset(split,protocol):
    dm=json.loads(Path('reports/full_history/datasets/manifest.json').read_text())['splits'][split]
    if digest(dm['file'])!=dm['sha256']:raise ValueError('Dataset checksum mismatch')
    classic=json.loads(Path('models/full_history/classic.json').read_text())
    lock=json.loads(Path('models/full_history/frozen.json').read_text())
    if digest('models/full_history/classic.json')!=lock['model_hashes']['classic.json'] or lock['temperatures']['classic']!=1:
        raise ValueError('Frozen Classic changed')
    entries={e['race_id']:e for p in Path('data').glob('month_*/manifest.json') for e in json.loads(p.read_text())['partitions']}
    result=[];excluded=Counter();sources={}
    with gzip.open(dm['file'],'rt') as f:
        for line in f:
            frame=json.loads(line);rid=frame['race_id'];e=entries[rid]
            raw=gzip.decompress(Path(e['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest()!=e['sha256']:raise ValueError('Partition checksum')
            r=json.loads(raw);parts={p['numPmu']:p for p in r['participants'] if p['statut']!='NON_PARTANT'}
            active=[p for p in frame['runners'] if not p['non_runner']]
            if len(active)!=len(frame['runners']):excluded['nonrunner_price_field_uncertain']+=1;continue
            if set(parts)!={p['number'] for p in active}:raise ValueError('Field mismatch')
            odds=[];valid=True
            for runner in active:
                p=parts[runner['number']];q=p.get(protocol['price']) or {};c=q.get('rapport');ts=q.get('dateRapport')
                if identity(p)!=runner['horse_id'] or runner['won']!=int(p.get('ordreArrivee')==1):raise ValueError('Identity/outcome mismatch')
                if (q.get('typePari')!='SIMPLE_GAGNANT' or q.get('numPmu1')!=p['numPmu'] or
                    isinstance(c,bool) or not isinstance(c,(int,float)) or not math.isfinite(c) or c<=1):valid=False;reason='incomplete_price';break
                if (isinstance(ts,bool) or not isinstance(ts,(int,float)) or not math.isfinite(ts)
                    or not 0<r['scheduled_start_ms']-ts<=protocol['max_price_age_hours']*3600000):valid=False;reason='not_prestart_or_stale';break
                odds.append(c)
            if not valid:excluded[reason]+=1;continue
            if sum(1/c for c in odds)<protocol['minimum_inverse_odds_sum']-1e-9:
                excluded['inconsistent_underround_board']+=1;continue
            if sum(p['won'] for p in active)!=1:raise ValueError('Winner ambiguity')
            sport=probabilities(frame,classic)
            result.append({'race_id':rid,'date':frame['date'],'odds':odds,'numbers':[p['number'] for p in active],
                'sport':[sport[p['number']] for p in active],'winner_index':next(i for i,p in enumerate(active) if p['won']),
                'history_n':[round(p['features'][4]*5) for p in active]})
            sources[rid]=e['sha256']
    return result,dict(excluded),sources

def evaluate(rows,weights):
    metrics=[];runners=[]
    for r in rows:
        p=r['sport'] if weights is None else predict(r['odds'],r['sport'],weights)
        y=r['winner_index'];metrics.append({'race_id':r['race_id'],'day':r['date'],'ll':-math.log(p[y]),
             'brier':sum((v-int(i==y))**2 for i,v in enumerate(p)), 'top1':int(max(range(len(p)),key=lambda i:p[i])==y)})
        for i,v in enumerate(p):
            runners.append({'race_id':r['race_id'],'day':r['date'],'p':v,'y':int(i==y), 'odds':r['odds'][i],
                'history_n':r['history_n'][i]})
    def stats(rs):
        if not rs:return {'n':0}
        return {'n':len(rs),'p':sum(r['p'] for r in rs)/len(rs),'observed':sum(r['y'] for r in rs)/len(rs),
            'expected_wins':sum(r['p'] for r in rs),'wins':sum(r['y'] for r in rs)}
    bins=defaultdict(list)
    for r in runners:bins[odds_band(r['odds'])].append(r)
    return {'races':len(rows),'log_loss':float(np.mean([r['ll'] for r in metrics])),
        'brier':float(np.mean([r['brier'] for r in metrics])),'top1':float(np.mean([r['top1'] for r in metrics])),
        'by_odds':{b:stats(rs) for b,rs in bins.items()},
        'positive_ev_diagnostic':stats([r for r in runners if r['p']*r['odds']>1]),
        'ev_at_least_100pct_diagnostic':stats([r for r in runners if r['p']*r['odds']>=2]),
        'by_month':{m: {'races':sum(r['day'].startswith(m) for r in metrics), 'log_loss':float(np.mean([r['ll'] for r in metrics if r['day'].startswith(m)]))} for m in sorted({r['day'][:7] for r in metrics})}},metrics

def paired(a,b,reps):
    days=defaultdict(list)
    if [r['race_id'] for r in a]!=[r['race_id'] for r in b]:raise ValueError('Unpaired')
    for x,y in zip(a,b):days[x['day']].append(x['ll']-y['ll'])
    totals=np.array([sum(v) for v in days.values()]);counts=np.array([len(v) for v in days.values()]);rng=np.random.default_rng(20261029)
    sample=[]
    for _ in range(reps):
        ix=rng.integers(0,len(counts),len(counts));sample.append(totals[ix].sum()/counts[ix].sum())
    return {'challenger_minus_baseline_logloss':float(totals.sum()/counts.sum()),'descriptive_day_95':np.quantile(sample,[.025,.975]).tolist(),'days':len(days)}

def main():
    protocol=json.loads(Path('config/market_repair_v1.json').read_text());ROOT.mkdir(exist_ok=True);MODEL.mkdir(exist_ok=True)
    if (MODEL/'frozen.json').exists():raise ValueError('Experiment already frozen; do not overwrite')
    print('Loading 2025 fit data',flush=True);train,excluded_train,sources_train=dataset('validation',protocol)
    print('Fitting prespecified corrections',len(train),flush=True)
    hybrid=fit(train,protocol);market=fit(train,protocol,True)
    save(MODEL/'candidate.json',hybrid);save(MODEL/'market_baseline.json',market)
    save(MODEL/'frozen.json',{'protocol_sha256':digest('config/market_repair_v1.json'),
        'classic_sha256':digest('models/full_history/classic.json'),
        'candidate_sha256':digest(MODEL/'candidate.json'),'market_baseline_sha256':digest(MODEL/'market_baseline.json'),
        'fit_sources':sources_train,'excluded_fit':excluded_train,'test_not_used_for_fit':True})
    print('Frozen. Loading separate 2026 evaluation',flush=True);test,excluded_test,sources_test=dataset('test',protocol)
    if max(r['date'] for r in train)>=min(r['date'] for r in test):raise ValueError('Chronology')
    result={'status':'EXPLORATORY_REUSED_CHRONOLOGICAL_EVALUATION_NO_BET','fit_races':len(train),'test_races':len(test),
        'test_exclusions':excluded_test,'test_sources':sources_test,'protocol':protocol,'models':{},'paired':{}}
    scores={}
    for name,w in [('classic_frozen',None),('market_normalized',[1,0]),('market_calibrated',market['weights']),('candidate',hybrid['weights'])]:
        result['models'][name],scores[name]=evaluate(test,w)
    for name in ['classic_frozen','market_normalized','market_calibrated']:
        result['paired'][name]=paired(scores['candidate'],scores[name],protocol['bootstrap_days'])
    result['weights']={'candidate':hybrid['weights'],'market_calibrated':market['weights']}
    save(ROOT/'evaluation.json',result)
    lines=['# Correction expérimentale des probabilités','','**Recherche uniquement — recommandations suspendues.**',
        f"Ajustement sur {len(train)} courses de 2025 ; évaluation chronologique sur {len(test)} courses de 2026, déjà inspectées. Aucun nouveau test vierge.",
        '',f"Poids [log marché, log Classic] : {hybrid['weights']}.",'',
        '| Variante | Log loss (plus bas = mieux) | Brier | Premier choix gagnant |','|---|---:|---:|---:|']
    for name,m in result['models'].items():lines.append(f"| {name} | {m['log_loss']:.5f} | {m['brier']:.5f} | {m['top1']:.2%} |")
    lines+=['','## Calibration par cote de référence PMU','','| Cote | Classic prévu | Nouveau prévu | Observé |','|---|---:|---:|---:|']
    for b in ['1-3','3-5','5-10','10-20','20-50','50-80','80+']:
        old=result['models']['classic_frozen']['by_odds'].get(b);new=result['models']['candidate']['by_odds'].get(b)
        if new:lines.append(f"| {b} | {old['p']:.2%} | {new['p']:.2%} | {new['observed']:.2%} |")
    lines+=['','## Limites','']+['- '+s for s in protocol['limitations']]
    lines+=['','Le candidat utilise explicitement les cotes. Ce n’est pas une estimation sportive indépendante. Les cotes complètes d’un même opérateur sont indispensables. Aucun ROI calculé.',
        '', 'Paramètres figés avant chargement de 2026. Aucune promotion automatique ni modification de V6/Classic.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n');print(json.dumps(result['weights']),flush=True)
if __name__=='__main__':main()
