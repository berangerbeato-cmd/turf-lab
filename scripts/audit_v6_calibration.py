"""Descriptive audit of existing frozen holdouts; no model or calibration fitting."""
import gzip
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from scripts.v6_holdout import verify
from scripts.backtest_connections import digest
from turf_lab.evidence import dump
from turf_lab.xgb_model import metrics


def summarize(entries):
    boundaries=[0,.1,.2,.3,.4,1.00000001]
    output=[]
    for lo,hi in zip(boundaries,boundaries[1:]):
        values=[e for e in entries if lo<=e['p']<hi]
        if not values:
            continue
        by_day=defaultdict(list)
        for e in values:
            by_day[e['date']].append(e)
        # Resample all observed dates, including those with zero entries in this bin.
        days=sorted({e['date'] for e in entries});rng=random.Random(20261014)
        stats={d:(sum(e['won']-e['p'] for e in by_day[d]),len(by_day[d])) for d in days}
        deltas=[]
        for _ in range(1000):
            sample=[stats[d] for d in rng.choices(days,k=len(days))]
            count=sum(n for _,n in sample)
            if count:
                deltas.append(sum(s for s,_ in sample)/count)
        deltas.sort()
        output.append({'bin':[lo,min(hi,1)],'count':len(values),'wins':sum(e['won'] for e in values),
            'mean_probability':mean(e['p'] for e in values),'win_frequency':mean(e['won'] for e in values),
            'observed_minus_predicted':mean(e['won']-e['p'] for e in values),
            'descriptive_day_bootstrap_95':([deltas[int(.025*(len(deltas)-1))],deltas[int(.975*(len(deltas)-1))]] if len(values)>=30 and len({e['date'] for e in values})>=10 else None),
            'small_sample':len(values)<30 or len({e['date'] for e in values})<10})
    return {'count':len(entries),'mean_probability':mean(e['p'] for e in entries),'win_frequency':mean(e['won'] for e in entries),
        'ece_fixed_bins':sum(b['count']*abs(b['observed_minus_predicted']) for b in output)/len(entries),'bins':output}


def main():
    _,v6_lock,_,_=verify()
    all_entries,top_entries=[],[]
    sources={};periods={};seen=set()
    for name in ('v6_holdout','v7_holdout'):
        report_path='reports/'+name+'.json'
        predictions_path='reports/'+name+'_predictions.json'
        report=json.loads(Path(report_path).read_text())
        if name=='v6_holdout' and report['frozen']!=v6_lock:
            raise ValueError('V6 holdout freeze mismatch')
        if name=='v7_holdout' and report['frozen']['v7_frozen']['baseline_frozen']!=v6_lock:
            raise ValueError('V7 holdout baseline freeze mismatch')
        predictions=json.loads(Path(predictions_path).read_text())['v6']
        manifests={}
        for month,sha in report['source_manifests_sha256'].items():
            path='data/month_'+month+'/manifest.json'
            if digest(path)!=sha:
                raise ValueError('Source manifest changed')
            manifests.update({r['race_id']:r for r in json.loads(Path(path).read_text())['partitions']})
        rows,probs,entries,tops=[],[],[],[]
        for item in predictions:
            rid=item['race_id']
            if rid in seen:
                raise ValueError('Overlapping evaluation races')
            seen.add(rid)
            part=manifests[rid]
            raw=gzip.decompress(Path(part['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest()!=part['sha256']:
                raise ValueError('Raw source digest mismatch')
            record=json.loads(raw)
            probability={int(k):v for k,v in item['probabilities'].items()}
            runners=[{'number':p['numPmu'],'non_runner':p.get('statut')=='NON_PARTANT','won':p.get('ordreArrivee')==1} for p in record['participants']]
            rows.append({'runners':runners});probs.append(probability)
            active=[p for p in runners if not p['non_runner']]
            race_entries=[{'date':rid[:10],'p':probability[p['number']],'won':int(p['won']),'race_id':rid,'number':p['number']} for p in active]
            entries.extend(race_entries)
            tops.append(min(race_entries,key=lambda e:(-e['p'],e['number'])))
        actual=metrics(rows,probs)
        expected=report['test']['v6']
        for key in ('log_loss','brier_multiclass','top1_accuracy'):
            if abs(actual[key]-expected[key])>1e-10:
                raise ValueError('Frozen evaluation metrics not reproduced')
        periods[name]={'races':len(rows),'all_runners':summarize(entries),'top_choice':summarize(tops)}
        all_entries.extend(entries);top_entries.extend(tops)
        sources[report_path]=digest(report_path);sources[predictions_path]=digest(predictions_path)
    result={'status':'DESCRIPTIVE_ONLY_NO_BET','races':len(seen),'sources_sha256':sources,'periods':periods,
        'all_runners':summarize(all_entries),'top_choice':summarize(top_entries),'refitted':False,
        'limits':['Coarse-bin ECE depends on bins and is dominated by low probabilities','Bootstrap is descriptive; no multiple-comparison correction',
                  'Retrospective snapshots do not prove original pre-race availability','No odds or profitability','No calibration learned from holdouts']}
    dump('reports/v6_calibration_audit.json',result)
    lines=['# Calibration V6 — audit des tests figés','','**Analyse descriptive seulement. Aucun coefficient modifié ni recalibration. NO BET.**',
        f"{len(seen)} courses, juillet–octobre 2025. Les métriques d’origine et les empreintes des sources sont reproduites."]
    for key,title in [('all_runners','Tous les partants'),('top_choice','Premier choix de chaque course')]:
        s=result[key]
        lines+=['','## '+title,'','| Probabilité annoncée | Effectif | Moyenne annoncée | Fréquence gagnante |','|---|---:|---:|---:|']
        for b in s['bins']:
            lo,hi=b['bin']
            lines.append(f"| {lo:.0%}–{hi:.0%} | {b['count']} | {b['mean_probability']:.1%} | {b['win_frequency']:.1%} |")
        lines+=['',f"Moyenne annoncée : {s['mean_probability']:.2%}. Fréquence observée : {s['win_frequency']:.2%}. Écart absolu moyen par tranches (ECE) : {s['ece_fixed_bins']:.2%}."]
    lines+=['','La moyenne globale de tous les partants égale mécaniquement la fréquence gagnante : chaque course totalise une probabilité de 1 et possède un gagnant. Cette égalité ne constitue pas une preuve de calibration.',
        'Les intervalles descriptifs par journées et les deux périodes séparées figurent dans le JSON. Intervalles masqués pour moins de 30 observations ou 10 journées distinctes. Les faibles effectifs ne permettent pas de conclure à une calibration fiable des fortes probabilités.',
        'Ces tests ne servent pas à corriger les probabilités après coup. La confirmation doit venir du suivi prospectif. Aucun avantage face aux cotes démontré.']
    Path('reports/V6_CALIBRATION_AUDIT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'races':len(seen),'all_runners':result['all_runners'],'top_choice':result['top_choice']}),flush=True)


if __name__=='__main__':
    main()
