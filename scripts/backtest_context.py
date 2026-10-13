"""Validate departure and course aptitude without reopening observed test periods."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from scripts.backtest_extension import load_sources
from scripts.backtest_opposition import day_bootstrap
from turf_lab.context import augment_context,candidate,DEPARTURE_NAMES,APTITUDE_NAMES
from turf_lab.evidence import dump
from turf_lab.month_history import build_history
from turf_lab.opposition import augment,NAMES
from turf_lab.pilot import FEATURES,fit,metrics


def main():
    path=Path('config/context_v4_protocol.json');p=json.loads(path.read_text())
    if any(m.startswith('2026') for m in p['source_months']):raise ValueError('Observed test years forbidden')
    records,coverage=load_sources({'months':p['source_months'],'minimum_retained_fraction_per_month':p['minimum_retained_fraction_per_month']})
    rows=augment_context(augment(build_history(records,lookback_days=p['lookback_days'])),records,
        lookback_days=p['lookback_days'],prior_strength=p['aptitude_prior_strength'],distance_tolerance=p['distance_tolerance_m'])
    splits={s:[r for r in rows if p[s]['from']<=r['date']<=p[s]['to']] for s in ('train','validation')}
    if any(len(v)<200 for v in splits.values()):raise ValueError('Insufficient split')
    results={};models={};frames={}
    for name in p['candidates']:
        train=candidate(splits['train'],name);val=candidate(splits['validation'],name)
        if name=='v3':model=json.loads(Path('models/opposition_v3_candidates.json').read_text())['models']['combined']
        else:model=fit(train,p['l2'])
        models[name]=model;frames[name]=val;results[name]=metrics(val,model)
        print(json.dumps({'candidate':name,'validation':results[name]['log_loss']}),flush=True)
    comparisons={name:day_bootstrap((frames['v3'],frames[name]),models['v3'],models[name]) for name in p['candidates'] if name!='v3'}
    names={name:FEATURES+NAMES+(DEPARTURE_NAMES if name in ('departure','combined') else [])+
        (APTITUDE_NAMES if name in ('aptitude','combined') else []) for name in p['candidates']}
    output={'status':'VALIDATION_ONLY_NO_BET','protocol':p,'protocol_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_records_sha256':hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest(),
        'split_races':{k:len(v) for k,v in splits.items()},'validation':results,'paired_comparisons':comparisons,
        'selected':min(results,key=lambda n:results[n]['log_loss']),
        'departure_provenance':dict(Counter(r['departure_provenance'] for race in rows for r in race['runners'])),
        'test_evaluated':False,'prospective_model_changed':False,
        'limitations':['Retrospective inputs do not prove original pre-race publication.',
            'Validation period reused for successive research iterations; independent holdout needed.',
            'Residual aptitude is conditional on classified finishers, not a causal effect.',
            'No verified autostart slot; unknown start type is not a standing start.']}
    dump('reports/context_v4_validation.json',output)
    dump('models/context_v4_candidates.json',{'status':'VALIDATION_ONLY_NOT_DEPLOYED','models':models,'feature_names':names})
    lines=['# Départ et aptitude au parcours — validation V4','','**Validation seulement, NO BET.**',
        '496 courses d’entraînement (mars 2024), 537 de validation (mars 2025). Aucun résultat 2026 chargé.','',
        '| Variante | Log loss | Brier | Premier choix gagnant |','|---|---:|---:|---:|']
    for name,m in results.items():lines.append(f"| {name} | {m['log_loss']:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines+=['','Écarts à V3 (négatif = mieux), intervalles exploratoires par journées :']
    for name,c in comparisons.items():lines.append(f"- {name} : {c['delta_log_loss']:.5f}, intervalle 95 % {c['day_bootstrap_95_percent']}.")
    lines+=['','Sélection selon le critère gelé : '+output['selected']+'.',
        'Les distances négatives non corroborées sont manquantes. Aucune position autostart déduite du numéro.',
        'L’aptitude compare la performance passée aux attentes Elo avant cette course, avec régularisation et une fenêtre de 60 jours.',
        'Le type de départ inconnu reste inconnu. Résultats du même jour exclus.',
        'La validation a été réutilisée pour plusieurs itérations : résultat exploratoire, nécessitant une nouvelle période indépendante.',
        'Mars et avril 2026 ont déjà été observés ; aucun réemploi pour choisir V4. Modèle prospectif inchangé.']
    Path('reports/CONTEXT_V4_VALIDATION.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
