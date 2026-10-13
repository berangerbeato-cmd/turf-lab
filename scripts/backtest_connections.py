"""Expanded V5 selection, then separate hash-locked independent evaluation."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from scripts.backtest_extension import load_sources
from scripts.backtest_opposition import day_bootstrap
from turf_lab.evidence import dump
from turf_lab.month_history import build_history
from turf_lab.opposition import augment,NAMES
from turf_lab.connections import augment_connections,candidate,BLOCK_NAMES
from turf_lab.fast_logit import fit
from turf_lab.pilot import FEATURES,metrics,probabilities

PROTOCOL=Path('config/connections_v5_protocol.json')
MODELS=Path('models/connections_v5_candidates.json')
FROZEN=Path('models/connections_v5_frozen.json')
CODE=['turf_lab/connections.py','turf_lab/opposition.py','turf_lab/month_history.py',
      'turf_lab/pilot.py','turf_lab/fast_logit.py','scripts/backtest_connections.py']


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def monthly(rows,model,minimum):
    months=sorted({r['date'][:7] for r in rows});out={}
    for month in months:
        subset=[r for r in rows if r['date'].startswith(month)]
        if len(subset)<minimum:raise ValueError('Insufficient races in '+month)
        out[month]=metrics(subset,model)
    return out


def split(rows,bounds,minimum):
    selected=[r for r in rows if bounds['from']<=r['date']<=bounds['to']]
    first=int(bounds['from'][5:7]);last=int(bounds['to'][5:7]);year=bounds['from'][:4]
    if bounds['to'][:4]!=year:raise ValueError('Expected within-year split')
    expected={f'{year}-{m:02d}' for m in range(first,last+1)}
    counts=Counter(r['date'][:7] for r in selected)
    if set(counts)!=expected or any(n<minimum for n in counts.values()):raise ValueError('Incomplete evaluation months')
    return selected


def prepare(p,phase):
    months=p['development_months'] if phase=='validate' else p['test_source_months']
    if phase=='validate' and any(m.startswith('2026') for m in months):raise ValueError('Test outcomes forbidden during selection')
    records,coverage=load_sources({'months':months,'minimum_retained_fraction_per_month':p['minimum_retained_fraction_per_month']})
    source_hash=hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest()
    rows=augment_connections(augment(build_history(records,lookback_days=p['lookback_days'])),records,
        window=p['connections_window_days'],strength=p['connections_prior_strength'],equipment_days=p['equipment_history_days'])
    return rows,source_hash,coverage


def verify_frozen(p):
    f=json.loads(FROZEN.read_text())
    if f['protocol_sha256']!=digest(PROTOCOL) or f['models_sha256']!=digest(MODELS):raise ValueError('Frozen model/protocol mismatch')
    if any(digest(path)!=sha for path,sha in f['code_sha256'].items()):raise ValueError('Frozen feature code mismatch')
    if f['selected'] not in p['candidates']:raise ValueError('Invalid frozen selection')
    return f,json.loads(MODELS.read_text())['models']


def validate(p):
    if FROZEN.exists():
        verify_frozen(p)
        print('Existing V5 selection retained; no repeated tuning');return
    rows,source_hash,coverage=prepare(p,'validate')
    train=split(rows,p['train'],p['minimum_races_per_month'])
    val=split(rows,p['validation'],p['minimum_races_per_month'])
    results={};models={};frames={};by_month={};scores={}
    for name in p['candidates']:
        model=fit(candidate(train,name),p['l2'],p['iterations'],p['learning_rate'])
        frame=candidate(val,name);models[name]=model;frames[name]=frame
        results[name]=metrics(frame,model);by_month[name]=monthly(frame,model,p['minimum_races_per_month'])
        scores[name]=mean(x['log_loss'] for x in by_month[name].values())
        print(json.dumps({'candidate':name,'monthly_mean_log_loss':scores[name]}),flush=True)
    selected=min(p['candidates'],key=lambda name:scores[name])
    comparisons={n:day_bootstrap((frames['v3'],frames[n]),models['v3'],models[n]) for n in p['candidates'] if n!='v3'}
    names={n:FEATURES+NAMES+sum([BLOCK_NAMES[g] for g in (list(BLOCK_NAMES) if n=='combined' else [] if n=='v3' else [n])],[]) for n in p['candidates']}
    dump(MODELS,{'status':'EXPERIMENTAL_NOT_DEPLOYED','models':models,'feature_names':names})
    output={'status':'VALIDATION_ONLY_NO_BET','protocol_sha256':digest(PROTOCOL),'sources_sha256':source_hash,
        'train_races':len(train),'validation_races':len(val),'selected':selected,'validation':results,
        'by_month':by_month,'selection_scores':scores,'paired_comparisons':comparisons,'coverage':coverage,
        'equipment_counts':dict(Counter(r['equipment_code'] for race in rows for r in race['runners'])),
        'limitations':['Retrospective publication unproven globally; missing equipment is unknown.',
          'Named people may have homonyms; no fabricated identity merge.',
          'Residual form is associative and conditional on classified finishers, not causal.',
          'March 2025 reused from earlier work, April-May 2025 expand validation.',
          'Seasonal sample, no odds, ROI or automatic prospective model replacement.']}
    dump('reports/connections_v5_validation.json',output)
    lines=['# Driver, entraîneur, ferrure — validation élargie V5','','**Expérimental — NO BET.**',
        f"Entraînement : {len(train)} courses, mars–mai 2024. Validation : {len(val)} courses, mars–mai 2025.",
        'V3 est réentraîné sur les mêmes données élargies pour une comparaison équitable.','',
        '| Variante | Moyenne mensuelle log loss | Brier global | Top-1 |','|---|---:|---:|---:|']
    for n in p['candidates']:lines.append(f"| {n} | {scores[n]:.5f} | {results[n]['brier_multiclass']:.5f} | {results[n]['top1_accuracy']:.1%} |")
    lines+=['','Choix gelé avant test : '+selected+'.','Les résultats par mois, intervalles exploratoires et limites sont dans le JSON.',
            'Aucune sélection ou modification sur mai–juin 2026. Modèle prospectif V1 inchangé.']
    Path('reports/CONNECTIONS_V5_VALIDATION.md').write_text('\n'.join(lines)+'\n')
    # Commit this record in its own workflow job before collecting any test month.
    dump(FROZEN,{'protocol_sha256':digest(PROTOCOL),'models_sha256':digest(MODELS),'selected':selected,
        'sources_sha256':source_hash,'code_sha256':{path:digest(path) for path in CODE}})


def test(p):
    frozen,models=verify_frozen(p)
    target=Path('reports/connections_v5_test.json')
    if target.exists():
        if json.loads(target.read_text())['frozen']!=frozen:raise ValueError('Test already evaluated under another freeze')
        print('Existing independent test retained unchanged');return
    rows,source_hash,coverage=prepare(p,'test')
    test_rows=split(rows,p['test'],p['minimum_races_per_month'])
    results={};by_month={};predictions={}
    for name in dict.fromkeys(['v3',frozen['selected']]):
        frame=candidate(test_rows,name);model=models[name]
        results[name]=metrics(frame,model);by_month[name]=monthly(frame,model,p['minimum_races_per_month'])
        predictions[name]=[{'race_id':r['race_id'],'probabilities':probabilities(r,model)} for r in frame]
    uniform=metrics(candidate(test_rows,'v3'),{'kind':'uniform'})
    dump(target,{'status':'EVALUATED_EXPERIMENTAL_NO_BET','frozen':frozen,'sources_sha256':source_hash,
        'test_races':len(test_rows),'test':results,'uniform':uniform,'by_month':by_month,'coverage':coverage,
        'refitted':False,'prospective_model_changed':False})
    dump('reports/connections_v5_test_predictions.json',predictions)
    lines=['# Test indépendant V5 — mai–juin 2026','','**NO BET. Modèles gelés avant collecte du test ; aucun réentraînement.**',
        f"{len(test_rows)} courses. Choix antérieur : {frozen['selected']}.",'',
        '| Modèle | Log loss | Brier | Top-1 |','|---|---:|---:|---:|']
    for n,m in results.items():lines.append(f"| {n} | {m['log_loss']:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines+=['','Aucune nouvelle sélection sur ce test. Le pilote prospectif V1 reste inchangé ; aucune rentabilité démontrée.']
    Path('reports/CONNECTIONS_V5_TEST.md').write_text('\n'.join(lines)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['validate','test'],required=True);args=parser.parse_args()
    try:
        p=json.loads(PROTOCOL.read_text())
        (validate if args.phase=='validate' else test)(p)
    except (ValueError,FileNotFoundError,RuntimeError) as error:
        dump(f'reports/connections_v5_{args.phase}_status.json',{'status':'BLOCKED','reason':str(error)})
        raise
    dump(f'reports/connections_v5_{args.phase}_status.json',{'status':'SUCCESS_NO_BET'})

if __name__=='__main__':main()
