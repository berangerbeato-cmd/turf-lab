"""Offline descriptive audit of frozen predictions; never fit or recommend bets.

Archived PMU prices are retrospective market descriptors, NOT executable prices.
Use both DIRECT and REFERENCE separately. No price fallback, posthoc tuning or ROI.
"""
import gzip
import hashlib
import json
import math
import random
import subprocess
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

from turf_lab.month_history import identity
from turf_lab.opposition import is_dq
from turf_lab.pilot import probabilities, vector

ROOT = Path('reports/value_audit_2026-10-29')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_jsonl(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def odds_band(c):
    for limit, label in [(3, '1-3'), (5, '3-5'), (10, '5-10'), (20, '10-20'),
                         (50, '20-50'), (80, '50-80')]:
        if c < limit:
            return label
    return '80+'


def coverage_band(n):
    return str(n) if n < 2 else '2-3' if n < 4 else '4-5'


def summarize(rows):
    if not rows:
        return {'n': 0}
    days = defaultdict(lambda: [0., 0])
    for r in rows:
        days[r['day']][0] += r['p'] - r['y']
        days[r['day']][1] += 1
    interval = None
    if len(days) >= 30 and len(rows) >= 100:
        rng = random.Random(20261029)
        blocks = list(days.values())
        samples = []
        for _ in range(400):
            selected = rng.choices(blocks, k=len(blocks))
            samples.append(sum(v[0] for v in selected) / sum(v[1] for v in selected))
        samples.sort()
        interval = [samples[9], samples[389]]
    return {'n': len(rows), 'races': len({r['race_id'] for r in rows}), 'days': len(days),
            'wins': sum(r['y'] for r in rows), 'expected_wins': sum(r['p'] for r in rows),
            'mean_probability': mean(r['p'] for r in rows), 'win_frequency': mean(r['y'] for r in rows),
            'overprediction_pp': 100*mean(r['p']-r['y'] for r in rows),
            'p_minus_y_day_bootstrap_95': interval,
            'dq_frequency': mean(r['dq'] for r in rows),
            'mean_past_dq_proxy': mean(r['dq_proxy'] for r in rows) if all(r['dq_proxy'] is not None for r in rows) else None,
            'mean_normalized_market_probability': mean(r['market_p'] for r in rows)}


def group(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    return {k: summarize(v) for k, v in sorted(groups.items())}


def archive_price(p, kind):
    q = p.get('dernierRapport'+kind) or {}
    c = q.get('rapport')
    if (q.get('typePari') != 'SIMPLE_GAGNANT' or q.get('numPmu1') != p['numPmu']
            or isinstance(c, bool) or not isinstance(c, (int, float)) or not math.isfinite(c) or c <= 1):
        return None
    return c


def joined_race(record, probabilities_by_number, features=None, kind='Direct'):
    active = [p for p in record['participants'] if p['statut'] != 'NON_PARTANT']
    probs = {int(n): p for n, p in probabilities_by_number.items()}
    numbers = {p['numPmu'] for p in active}
    if len(numbers) != len(active) or not numbers <= probs.keys():
        raise ValueError('Runner mismatch: '+record['race_id'])
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in probs.values()):
        raise ValueError('Invalid probability')
    if abs(sum(probs[n] for n in numbers)-1) > 1e-8:
        raise ValueError('Probability normalization mismatch')
    if any(probs[n] != 0 for n in probs.keys()-numbers):
        raise ValueError('Nonrunner has probability')
    if sum(p.get('ordreArrivee') == 1 for p in active) != 1:
        raise ValueError('Ambiguous winner')
    prices = {p['numPmu']: archive_price(p, kind) for p in active}
    if any(c is None for c in prices.values()):
        return None  # whole race; never normalize an incomplete market
    z = sum(1/c for c in prices.values())
    result = []
    for p in active:
        n = p['numPmu']; f = features.get(n) if features else None
        if f and identity(p) != f['horse_id']:
            raise ValueError('Horse identity mismatch')
        if f and f['won'] != int(p.get('ordreArrivee') == 1):
            raise ValueError('Outcome mismatch')
        v = f['features'] if f else None
        c = prices[n]; probability = probs[n]
        result.append(dict(race_id=record['race_id'], day=record['date'], number=n,
            p=probability, y=int(p.get('ordreArrivee') == 1), dq=is_dq(p),
            odds=c, odds_band=odds_band(c), market_p=(1/c)/z,
            age=p.get('age'), history_n=round(v[4]*5) if v else None,
            dq_proxy=v[7] if v else None, diagnostic_ev=probability*c-1,
            favorite=c == min(prices.values()),
            quote_after_start=(p['dernierRapport'+kind].get('dateRapport') or 0) >= record['scheduled_start_ms']))
    return result


def analyze(predictions, entries, features=None, kind='Direct'):
    rows=[]; excluded=[]; input_hashes={}; race_metrics=[]
    for rid, probs in predictions.items():
        e=entries.get(rid)
        if not e:
            excluded.append({'race_id':rid,'reason':'missing_partition'});continue
        raw=gzip.decompress(Path(e['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest()!=e['sha256']:
            raise ValueError('Source hash mismatch: '+rid)
        record=json.loads(raw);input_hashes[rid]=e['sha256']
        if record['race_id']!=rid:raise ValueError('Race mismatch')
        joined=joined_race(record,probs,features.get(rid) if features else None,kind)
        if joined is None:
            excluded.append({'race_id':rid,'reason':'incomplete_or_invalid_'+kind+'_prices'});continue
        rows.extend(joined)
        win=next(r for r in joined if r['y'])
        race_metrics.append({'model_logloss':-math.log(max(win['p'],1e-15)),
            'market_logloss':-math.log(win['market_p']),
            'model_brier':sum((r['p']-r['y'])**2 for r in joined),
            'market_brier':sum((r['market_p']-r['y'])**2 for r in joined)})
    result={'input_races':len(predictions),'included_races':len(race_metrics),'excluded':excluded,
        'source_partition_hashes':input_hashes,'overall':summarize(rows),
        'race_metrics':{k:mean(r[k] for r in race_metrics) for k in race_metrics[0]} if race_metrics else {},
        'quotes_timestamp_at_or_after_start':sum(r['quote_after_start'] for r in rows),
        'by_odds':group(rows,lambda r:r['odds_band']),
        'by_age':group(rows,lambda r:str(r['age'])),
        'favorites':summarize([r for r in rows if r['favorite']]),
        'diagnostic_positive_ev':summarize([r for r in rows if r['diagnostic_ev']>0]),
        'diagnostic_ev_at_least_100pct':summarize([r for r in rows if r['diagnostic_ev']>=1]),
        'positive_ev_by_odds':group([r for r in rows if r['diagnostic_ev']>0],lambda r:r['odds_band'])}
    if features:
        result['by_history_count']=group(rows,lambda r:coverage_band(r['history_n']))
        result['by_odds_and_history_count']=group(rows,lambda r:r['odds_band']+' / '+coverage_band(r['history_n']))
        result['by_past_dq_proxy']=group(rows,lambda r:'<10%' if r['dq_proxy']<.1 else '10-20%' if r['dq_proxy']<.2 else '20-30%' if r['dq_proxy']<.3 else '30%+')
        result['positive_ev_by_history_count']=group([r for r in rows if r['diagnostic_ev']>0],lambda r:coverage_band(r['history_n']))
    return result


def case_audit():
    path='predictions_operational/2026-10-29/2026-10-29_R4C8_20261029T183552548416Z/prediction.json'
    p=json.loads(Path(path).read_text())
    if p['race_id']!='2026-10-29_R4C8':raise ValueError('Case snapshot changed')
    result={'prediction':path,'sha256':sha(path),'runners':[],'reproduction':{}}
    for key,m in p['models'].items():
        model=json.loads(Path(m['model_file']).read_text())
        if sha(m['model_file'])!=m['model_sha256']:raise ValueError('Model changed')
        if key=='v6':model=model['models']['combined']
        computed=probabilities({'runners':m['runners']},model)
        delta=max(abs(computed[int(n)]-v) for n,v in m['probabilities'].items())
        if delta>1e-10:raise ValueError('Saved probability not reproduced')
        result['reproduction'][key]={'max_absolute_error':delta,'model_sha256':m['model_sha256']}
    before={x['numPmu']:x for x in p['target_snapshot']['participants']}
    for r in p['models']['v6']['runners']:
        s=before[r['number']]
        result['runners'].append({'number':r['number'],'name':r['name'],
            'source_music':s.get('musique'),'source_career_starts':s.get('nombreCourses'),
            'recent_starts_used':len(r['history']),'recent_history':r['history'],
            'features_first_five':r['features'][:5], 'past_dq_proxy':r['opposition_features'][2]})
    # Explain score difference, not a causal effect or a counterfactual bet probability.
    result['feature_catalog_reference']='reports/operational/model_files.json'
    contributions={}
    for key,m in p['models'].items():
        model=json.loads(Path(m['model_file']).read_text())
        if key=='v6':model=model['models']['combined']
        runners={r['number']:r for r in m['runners']}
        a=vector(runners[10]['features'],model['transform']); b=vector(runners[2]['features'],model['transform'])
        values=[(x-y)*w for x,y,w in zip(a,b,model['weights'])]
        contributions[key]={'log_score_10_minus_2':sum(values),
            'recent_form_and_missingness':sum(values[i]+values[i+38] for i in range(5)),
            'other_features':sum(values)-sum(values[i]+values[i+38] for i in range(5)),
            'all_indexed_contributions':values}
    result['score_contributions']=contributions
    # Trace actual accepted source records, not a guess from the current music.
    from turf_lab.history_sync import History
    history=History(); names={r['name'] for r in result['runners']}
    matches={n:[] for n in names}; missing=[]; checked=0
    start=date(2026,1,1)
    for i in range((date(2026,10,29)-start).days):
        day=(start+timedelta(days=i)).isoformat();state=history.day(day)
        if state['status']!='OK':missing.append(day)
        checked+=len(state['records'])
        for record in state['records']:
            for runner in record['participants']:
                if runner['nom'] in names and runner['statut']!='NON_PARTANT':
                    matches[runner['nom']].append({'date':day,'race_id':record['race_id'],
                        'horse_id':identity(runner),'rank':runner.get('ordreArrivee'),
                        'incident':runner.get('incident'),
                        'record_sha256':hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest()})
    result['accepted_history_trace']={'from':'2026-01-01','through':'2026-10-28',
        'verified_races_scanned':checked,'incomplete_days':missing,'same_name_matches':matches,
        'limit':'Absence from collected PMU scope does not mean the horse did not race. Music has no dated identities and is not injected into frozen features.'}
    return result


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    entries={}; manifests={}
    for path in sorted(Path('data').glob('month_*/manifest.json')):
        manifests[str(path)]=sha(path)
        for e in json.loads(path.read_text())['partitions']:
            if e['race_id'] in entries:raise ValueError('Duplicate partition')
            entries[e['race_id']]=e
    dataset='reports/full_history/datasets/test.jsonl.gz'
    dm=json.loads(Path('reports/full_history/datasets/manifest.json').read_text())
    if sha(dataset)!=dm['splits']['test']['sha256']:raise ValueError('Dataset checksum')
    frames=read_jsonl(dataset)
    features={r['race_id']:{p['number']:p for p in r['runners']} for r in frames}
    cp='reports/full_history/test_predictions.jsonl.gz'
    if sha(cp)!=json.loads(Path('reports/full_history/status.json').read_text())['prediction_sha256']:
        raise ValueError('Prediction checksum')
    classic={r['race_id']:r['probabilities']['classic'] for r in read_jsonl(cp)}
    if set(classic)!=set(features):raise ValueError('Dataset/prediction race mismatch')
    # Reproduce all Classic test probabilities from unchanged features and weights.
    model=json.loads(Path('models/full_history/classic.json').read_text())
    frozen=json.loads(Path('models/full_history/frozen.json').read_text())
    if sha('models/full_history/classic.json')!=frozen['model_hashes']['classic.json']:
        raise ValueError('Classic model checksum')
    max_error=0.
    for frame in frames:
        probs=probabilities(frame,model);t=frozen['temperatures']['classic']
        probs={n:v**(1/t) for n,v in probs.items()};z=sum(probs.values())
        max_error=max(max_error,max(abs(v/z-classic[frame['race_id']].get(str(n),0)) for n,v in probs.items()))
    if max_error>1e-10:raise ValueError('Classic historical reproduction mismatch')
    from scripts.v6_holdout import verify
    verify()  # verify the frozen V6 weights and dependencies, no fit
    for report in ['reports/v6_holdout.json','reports/v7_holdout.json']:
        for month,expected in json.loads(Path(report).read_text())['source_manifests_sha256'].items():
            if sha('data/month_'+month+'/manifest.json')!=expected:raise ValueError('V6 source manifest changed')
    v6={}
    for file in ['reports/v6_holdout_predictions.json','reports/v7_holdout_predictions.json']:
        for r in json.loads(Path(file).read_text())['v6']:
            if r['race_id'] in v6:raise ValueError('Duplicate V6 race')
            v6[r['race_id']]=r['probabilities']
    output={'status':'DESCRIPTIVE_REUSED_HOLDOUT_NO_BET','code_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'script_sha256':sha(__file__),'classic_reproduced_races':len(frames),'classic_max_reproduction_error':max_error,'source_manifests':manifests,
        'prediction_files_sha256':{f:sha(f) for f in [cp,dataset,'reports/v6_holdout_predictions.json','reports/v7_holdout_predictions.json']},
        'limits':['Historical PMU snapshots downloaded retrospectively. Availability at decision time unproven.',
                  'DIRECT and REFERENCE are separate retrospective descriptors; neither is a guaranteed settlement.',
                  'No ROI, no ZEturf execution claim, no fitting, no threshold selection.',
                  'V6 July-October 2025 and Classic January-September 2026 are different cohorts; no model ranking.',
                  'Intervals descriptive day-cluster bootstrap; repeated horses across days and multiple subgroup comparisons remain.',
                  'Past DQ feature is a shrunk historical proxy, not a calibrated DQ prediction.',
                  'Coverage cross-tabs use frozen Classic features only; V6 historic feature rows not fabricated.'],
        'cohorts':{}}
    for model,preds,fs in [('classic',classic,features),('v6',v6,None)]:
        for kind in ['Direct','Reference']:
            print('Analyzing',model,kind,flush=True)
            output['cohorts'][model+'_'+kind]=analyze(preds,entries,fs,kind)
    output['case']=case_audit()
    (ROOT/'audit.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    lines=['# Audit des probabilités face au marché — 29 octobre 2026','','**RECOMMANDATIONS SUSPENDUES.** Analyse descriptive exécutée sur les sorties figées ; aucun modèle réentraîné.',
        '', 'Les cotes PMU archivées sont des observations rétrospectives. Aucun ROI ni prix ZEturf exécutable ne peut être déduit de cet audit.',
        '', '| Cohorte / cotes | Courses | Log loss modèle | Log loss marché normalisé |', '|---|---:|---:|---:|']
    for name,c in output['cohorts'].items():
        m=c['race_metrics'];lines.append(f"| {name} | {c['included_races']} | {m.get('model_logloss',0):.4f} | {m.get('market_logloss',0):.4f} |")
    for name in ['classic_Direct','v6_Direct']:
        c=output['cohorts'][name]
        lines+=['', '## '+name, '', '| Cote [borne basse, borne haute) | Partants | P moyenne | Gagnants observés | DQ |', '|---|---:|---:|---:|---:|']
        for band in ['1-3','3-5','5-10','10-20','20-50','50-80','80+']:
            r=c['by_odds'].get(band)
            if r:lines.append(f"| {band} | {r['n']} | {r['mean_probability']:.2%} | {r['win_frequency']:.2%} | {r['dq_frequency']:.2%} |")
        for selection in ['diagnostic_positive_ev','diagnostic_ev_at_least_100pct']:
            r=c[selection];lines+=['',f"{selection} : {r['n']} chevaux, {r.get('expected_wins',0):.1f} victoires attendues, {r.get('wins',0)} observées. Sélection rétrospective de diagnostic, pas un backtest de paris exécutables."]
    lines+=['','## Limites et reproductibilité','']+['- '+v for v in output['limits']]
    lines+=['','Commande : `python -m scripts.audit_value_market`. Détails, exclusions, empreintes et intervalles : `audit.json`.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
