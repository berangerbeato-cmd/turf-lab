"""Offline evaluation of exact top-four/top-five finishes, not bookmaker settlements."""
import gzip,hashlib,json,math
from collections import Counter
from pathlib import Path
from turf_lab.rank45 import forecast,ordered_probability,unordered_probability
from turf_lab.available_history_operational import verify_active

def main():
    policy,_=verify_active()
    path=Path('reports/available_history_v3/test_predictions.jsonl.gz')
    with gzip.open(path,'rt') as f: predictions=[json.loads(x) for x in f]
    entries={e['race_id']:e for p in Path('data').glob('month_*/manifest.json') for e in json.loads(p.read_text())['partitions']}
    rows={4:[],5:[]};excluded={4:Counter(),5:Counter()}
    for prediction in predictions:
        e=entries[prediction['race_id']];raw=gzip.decompress(Path(e['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest()!=e['sha256']: raise ValueError('Source changed')
        race=json.loads(raw)
        p={int(n):v for n,v in prediction['probabilities'][policy['variant']].items() if v>0}
        participants=[r for r in race['participants'] if r.get('statut')!='NON_PARTANT']
        if set(p)!={r['numPmu'] for r in participants}:raise ValueError('Field mismatch')
        for k in (4,5):
            ranked={rank:[r['numPmu'] for r in participants if r.get('ordreArrivee')==rank] for rank in range(1,k+1)}
            if len(p)<k or any(len(v)!=1 for v in ranked.values()):
                excluded[k]['missing_or_tied_top_k']+=1;continue
            truth=[ranked[i][0] for i in range(1,k+1)]
            if any(str(r.get('incident') or '').startswith('DISQUALIFIE') or r.get('incident')=='DISTANCE' for r in participants if r['numPmu'] in truth):
                excluded[k]['conflicting_finish']+=1;continue
            f=forecast(p,k);chosen=f['order'];hit=set(chosen)==set(truth)
            rows[k].append(dict(race_id=race['race_id'],month=race['date'][:7],
                ordered_hit=int(chosen==truth),unordered_hit=int(hit),found=len(set(chosen)&set(truth)),
                predicted_unordered=f['unordered_probability'],
                unordered_brier=(f['unordered_probability']-hit)**2,
                ordered_log_loss=-math.log(max(1e-300,ordered_probability(p,truth))),
                unordered_log_loss=-math.log(max(1e-300,unordered_probability(p,truth))),
                uniform_ordered_log_loss=math.log(math.perm(len(p),k)),
                uniform_unordered_log_loss=math.log(math.comb(len(p),k))))
    def summarize(rs):
        if not rs:return dict(races=0)
        names=['ordered_hit','unordered_hit','found','predicted_unordered','unordered_brier','ordered_log_loss','unordered_log_loss','uniform_ordered_log_loss','uniform_unordered_log_loss']
        return dict(races=len(rs),**{n:sum(r[n] for r in rs)/len(rs) for n in names})
    result=dict(status='EXPLORATORY_RANKING_BASELINE',base_model=policy['primary_model'],prediction_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        recommendations_allowed=False,limitations=['Previously examined 2026 test, not virgin validation','Win probabilities do not establish calibrated finish probabilities','Plackett-Luce assumes constant relative strength after each place; DQ dependence not modeled','All eligible archived harness races, not restricted to official Quarte/Quinte events','Exact four/five finishes only; no bonus payouts, settlements, stakes or ROI','No new collection or refit'],
        scores={str(k):dict(overall=summarize(rows[k]),excluded=dict(excluded[k]),by_month={m:summarize([r for r in rows[k] if r['month']==m]) for m in sorted({r['month'] for r in rows[k]})}) for k in (4,5)})
    root=Path('reports/rank45_v1');root.mkdir(parents=True,exist_ok=True)
    (root/'evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Quarté / Quinté : première référence de classement','',
        'Extension expérimentale du modèle de base. Aucune recommandation de pari.',
        'Mesure des arrivées exactes ; ne reproduit pas les rapports ni bonus des produits commerciaux.','',
        '| Objectif | Courses | Ordre exact | Désordre exact | Chevaux trouvés en moyenne |',
        '|---|---:|---:|---:|---:|']
    for k in (4,5):
        s=result['scores'][str(k)]['overall']
        lines.append(f"| Top {k} | {s['races']} | {s['ordered_hit']:.2%} | {s['unordered_hit']:.2%} | {s['found']:.2f}/{k} |")
    lines+=['','Étape suivante : entraîner un classement sur les positions 1 à 5, sélectionner sur 2025 et comparer à cette référence. Les probabilités conjointes restent non validées.']
    (root/'RESULTS.md').write_text('\n'.join(lines)+'\n');print(json.dumps(result['scores']),flush=True)
if __name__=='__main__':main()
