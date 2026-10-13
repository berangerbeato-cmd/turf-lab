"""V3 ablations: train 2024, validation 2025; never load test-year outcomes."""
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from scripts.backtest_extension import load_sources
from turf_lab.evidence import dump
from turf_lab.month_history import build_history
from turf_lab.opposition import augment,candidate,NAMES
from turf_lab.pilot import FEATURES,fit,metrics,probabilities


def day_bootstrap(races,baseline,challenger):
    by_day=defaultdict(list)
    for base,other in zip(races[0],races[1]):
        assert base['race_id']==other['race_id']
        winner=next(r['number'] for r in base['runners'] if r['won'])
        delta=-math.log(probabilities(other,challenger)[winner])+math.log(probabilities(base,baseline)[winner])
        by_day[base['date']].append(delta)
    days=sorted(by_day); rng=random.Random(20261013); estimates=[]
    for _ in range(1000):
        values=[x for d in rng.choices(days,k=len(days)) for x in by_day[d]]
        estimates.append(sum(values)/len(values))
    estimates.sort()
    return {'delta_log_loss':sum(sum(v) for v in by_day.values())/sum(map(len,by_day.values())),
            'day_bootstrap_95_percent':[estimates[24],estimates[974]],'days':len(days),
            'interpretation':'Validation only; exploratory interval, not adjusted for selecting multiple candidates'}


def main():
    p=json.loads(Path('config/opposition_v3_protocol.json').read_text())
    base=json.loads(Path('config/history_extension_protocol.json').read_text())
    base['months']=[m for m in base['months'] if int(m[:4]) in p['source_years']]
    if any(m.startswith('2026') for m in base['months']):raise ValueError('Test year forbidden')
    records,coverage=load_sources(base)
    races=augment(build_history(records,lookback_days=60),k=p['elo_k'],scale=p['elo_scale'],
                  prior_strength=p['dq_prior_strength'],initial_prior=p['initial_dq_prior'])
    train=[r for r in races if p['train']['from']<=r['date']<=p['train']['to']]
    validation=[r for r in races if p['validation']['from']<=r['date']<=p['validation']['to']]
    if len(train)<200 or len(validation)<200:raise ValueError('Insufficient split')
    results={}; models={}; frames={}
    for name in p['candidates']:
        training=candidate(train,name);testing=candidate(validation,name)
        model=fit(training,p['l2']);models[name]=model;frames[name]=testing
        results[name]=metrics(testing,model)
        print(json.dumps({'candidate':name,'validation_log_loss':results[name]['log_loss']}),flush=True)
    comparisons={n:day_bootstrap((frames['baseline'],frames[n]),models['baseline'],models[n]) for n in p['candidates'] if n!='baseline'}
    selected=min(results,key=lambda n:results[n]['log_loss'])
    output={'status':'VALIDATION_ONLY_NO_BET','protocol':p,'split_races':{'train':len(train),'validation':len(validation)},
            'validation':results,'paired_comparisons':comparisons,'lowest_validation_log_loss':selected,
            'source_months':base['months'],'test_evaluated':False,
            'source_records_sha256':hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest(),
            'protocol_sha256':hashlib.sha256(Path('config/opposition_v3_protocol.json').read_bytes()).hexdigest()}
    dump('reports/opposition_v3_validation.json',output)
    dump('models/opposition_v3_candidates.json',{'status':'VALIDATION_ONLY_NOT_DEPLOYED','models':models,
         'feature_names':{'baseline':FEATURES,'opposition':FEATURES+NAMES[:2],'dq':FEATURES+NAMES[2:],'combined':FEATURES+NAMES}})
    lines=['# Opposition et risque de faute — validation V3','',
           '**Validation seulement ; aucun test indépendant ni déploiement. NO BET.**','',
           f"Entraînement : {len(train)} courses de mars 2024. Validation : {len(validation)} courses de mars 2025.",'',
           '| Modèle | Log loss | Brier | Premier choix gagnant |','|---|---:|---:|---:|']
    for name,m in results.items():lines.append(f"| {name} | {m['log_loss']:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines+=['','Écarts de log loss à la référence : négatif = amélioration. Intervalles exploratoires par rééchantillonnage des journées.']
    for name,c in comparisons.items():lines.append(f"- {name} : {c['delta_log_loss']:.5f}, intervalle 95 % {c['day_bootstrap_95_percent']}.")
    lines+=['','Pas de nouveauté mathématique revendiquée : Elo et régularisation sont des références établies.',
            'DQ et rangs inconnus exclus des duels Elo ; NP exclus de toutes les mises à jour.',
            'Mises à jour après chaque journée uniquement. Notes réinitialisées chaque année pour ne pas inventer les mois non observés.',
            'Le test V2 de mars 2026 n’a pas été chargé. Une nouvelle période indépendante est nécessaire avant toute validation finale.']
    Path('reports/OPPOSITION_V3_VALIDATION.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
