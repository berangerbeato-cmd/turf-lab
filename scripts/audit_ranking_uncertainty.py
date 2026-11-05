"""Paired uncertainty for the models selected BEFORE the ranking test."""
import gzip,json,hashlib
from collections import defaultdict
from datetime import date
from pathlib import Path
import numpy as np
def readlines(path):
    with gzip.open(path,'rt') as f:return [json.loads(s) for s in f]
def main():
    root=Path('reports/ranking_v1')
    events=readlines(root/'selected_combinations.jsonl.gz')
    base={r['race_id']:r for r in readlines('reports/available_history_v3/test_predictions.jsonl.gz')}
    evaluation=json.loads((root/'evaluation.json').read_text())
    variant='last5_available_dq20';report={}
    for k in (3,4,5):
        rows=[r for r in events if r['k']==k];groups=defaultdict(list);seen=set()
        for r in rows:
            if r['race_id'] in seen:raise ValueError('Duplicate event')
            seen.add(r['race_id'])
            if r['model']!=evaluation['selected_before_test'][str(k)]:raise ValueError('Selection mismatch')
            pp={int(n):p for n,p in base[r['race_id']]['probabilities'][variant].items() if p>0}
            old=sorted(pp,key=lambda n:(-pp[n],n))[:k];truth=r['truth']
            hit=int(set(r['selection'])==set(truth));oldhit=int(set(old)==set(truth))
            groups[date.fromisoformat(r['date']).isocalendar()[:2]].append([hit-oldhit,r['probability']-hit,hit,oldhit,r['probability']])
        totals=np.array([np.sum(v,axis=0) for v in groups.values()]);counts=np.array([len(v) for v in groups.values()])
        rng=np.random.default_rng(20261105);samples=[]
        for _ in range(2000):
            ix=rng.integers(0,len(counts),len(counts));samples.append(totals[ix].sum(axis=0)/counts[ix].sum())
        interval=np.quantile(samples,[.025,.975],axis=0);means=totals.sum(axis=0)/counts.sum()
        if len(rows)!=evaluation['counts']['test']:raise ValueError('Cohort size changed')
        report[str(k)]=dict(model=evaluation['selected_before_test'][str(k)],races=len(rows),
            hits=int(totals[:,2].sum()),baseline_hits=int(totals[:,3].sum()),expected_hits=float(totals[:,4].sum()),
            hit_delta=float(means[0]),hit_delta_week_95=interval[:,0].tolist(),
            overprediction=float(means[1]),overprediction_week_95=interval[:,1].tolist(),
            promotion='NOT_VALIDATED',combination_value='UNVALIDATED_PROBABILITIES_AND_NO_PAYOUT_MODEL')
    result=dict(status='COMPLETED',report=report,recommendations_allowed=False,
        limitations=['Exploratory weekly block bootstrap; reused test and repeated horses across weeks','No selection of a different model after viewing 2026','Exact unordered finish events, not commercial settlements or bonus payouts'],
        input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'selected_combinations.jsonl.gz',root/'evaluation.json']})
    (root/'uncertainty.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Décision : modèles de classement et combinaisons','',
      'Quatre candidats entraînés ; comparaison achevée sur 4 574 courses. La sélection des candidats provient de 2025, pas des résultats 2026.',
      '', '| Objectif | Candidat retenu sur 2025 | Arrivées complètes | V3 | Écart, intervalle exploratoire 95 % |',
      '|---|---|---:|---:|---:|']
    for k,r in report.items():
        lo,hi=r['hit_delta_week_95']
        lines.append(f"| Top{k} | {r['model']} | {r['hits']} | {r['baseline_hits']} | {100*r['hit_delta']:.2f} point [{100*lo:.2f} ; {100*hi:.2f}] |")
    lines+=['','## Probabilités conjointes','']
    for k,r in report.items():lines.append(f"- Top{k} : {r['expected_hits']:.1f} arrivées prévues, {r['hits']} observées.")
    lines+=['','## Décision','',
      'Conserver V3 comme base opérationnelle ; archiver les quatre candidats et leur sélection expérimentale. Aucun remplacement automatique sur la base du meilleur score observé après coup.',
      'Le calcul de combinaisons et de coût existe, mais les seuils coût/probabilité sont théoriques : les probabilités conjointes restent à valider et les rapports payés/bonus ne sont pas modélisés.',
      'Le Brier calculé sur la sélection propre à chaque modèle ne doit pas servir à les classer directement : les événements prédits changent.',
      'Suite utile : calibration des événements conjoints sur développement seulement, comparaison sur une période future ; intégrer ensuite des rapports documentés avant toute affirmation de value.',
      'Ne pas relancer cet entraînement pour combler quelques trous historiques. Modèles et résultats sont déjà sauvegardés.']
    (root/'DECISION.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
