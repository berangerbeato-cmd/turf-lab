"""Audit apparent SG value of the active sports model, without fitting or ROI."""
import gzip,json,hashlib
from collections import defaultdict
from pathlib import Path
import numpy as np
from scripts.train_market_repair import dataset,evaluate
from turf_lab.available_history_operational import verify_active

def summarize(rows):
    if not rows:return {'participations':0}
    p=sum(r['p'] for r in rows);wins=sum(r['y'] for r in rows)
    days=defaultdict(lambda:np.zeros(3))
    for r in rows:days[r['date']]+=np.array([r['p'],r['y'],1])
    blocks=np.array(list(days.values()));rng=np.random.default_rng(20261031);samples=[]
    for _ in range(1000):
        s=blocks[rng.integers(0,len(blocks),len(blocks))].sum(axis=0)
        samples.append((s[0]-s[1])/s[2])
    return dict(participations=len(rows),races=len({r['race_id'] for r in rows}),expected_wins=p,observed_wins=wins,
        predicted=p/len(rows),observed=wins/len(rows),overprediction_day_95=np.quantile(samples,[.025,.975]).tolist())

def main():
    policy,_=verify_active()
    price_policy=json.loads(Path('config/market_repair_v1.json').read_text())
    rows,excluded,sources=dataset('test',price_policy)
    path=Path('reports/available_history_v3/test_predictions.jsonl.gz')
    with gzip.open(path,'rt') as f: predictions={r['race_id']:r for r in map(json.loads,f)}
    runners=[]
    for r in rows:
        pp=predictions[r['race_id']]['probabilities'][policy['variant']]
        r['sport']=[pp[str(n)] for n in r['numbers']]
        for i,(p,c) in enumerate(zip(r['sport'],r['odds'])):
            runners.append(dict(race_id=r['race_id'],date=r['date'],p=p,odds=c,y=int(i==r['winner_index']),ev=p*c-1))
    metrics,_=evaluate(rows,None)
    thresholds=[0,.2,.5,1.]
    diagnostic={str(t):summarize([r for r in runners if r['ev']>t]) for t in thresholds}
    stress={str(drop):summarize([r for r in runners if r['p']*r['odds']*(1-drop)>1]) for drop in [0,.1,.2]}
    result=dict(status='COMPLETED_RETROSPECTIVE_DIAGNOSTIC',model=policy['primary_model'],variant=policy['variant'],
        races=len(rows),excluded=excluded,metrics=metrics,apparent_ev_thresholds=diagnostic,price_drop_sensitivity=stress,
        source_map_sha256=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        predictions_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),recommendations_allowed=False,
        limitations=['2026 outcomes already examined; descriptive not a fresh validation',
        'Archived PMU reference prices, not executable prices or settlement reports',
        'Thresholds fixed for diagnosis only, no best threshold selected',
        'Bootstrap groups days; repeated horses may remain dependent',
        'No stakes, profit, ROI or betting eligibility inferred',
        'No collection, no refit, no change to active weights'])
    root=Path('reports/value_active_v1');root.mkdir(parents=True,exist_ok=True)
    (root/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Fausses values du modèle de base — simple gagnant','',
       f"{len(rows)} courses avec tableaux de référence archivés admissibles. Diagnostic rétrospectif, aucun ROI.",
       '', '| EV apparente supérieure à | Participations | Victoires prévues | Victoires observées |',
       '|---|---:|---:|---:|']
    for t in thresholds:
        d=diagnostic[str(t)]
        if d['participations']:lines.append(f"| {t:.0%} | {d['participations']} | {d['expected_wins']:.1f} | {d['observed_wins']} |")
    lines+=['','Un excès de victoires prévues parmi les EV positives indique une mauvaise calibration conditionnelle, pas une preuve de rentabilité.',
        'Les simulations de baisse de cote ne prédisent pas le prix final. Aucune règle de pari retenue.',
        'Suite : ajustement séparé sur 2025, comparaison sportive / marché / hybride sur 2026 réutilisé, puis validation prospective.']
    (root/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(diagnostic),flush=True)
if __name__=='__main__':main()
