"""Frozen chronological protocol, validation selection, untouched final test."""
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from turf_lab.evidence import dump
from turf_lab.pilot import FEATURES, fit, metrics, probabilities


def main():
    protocol=json.loads(Path('config/pilot_protocol.json').read_text())
    manifest=json.loads(Path('data/pilot_v1/manifest.json').read_text())
    if manifest.get('status')!='COMPLETE': raise ValueError('Incomplete pilot cannot train')
    races=[]
    for item in manifest['partitions']:
        raw=gzip.decompress(Path(item['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest()!=item['sha256']: raise ValueError('Partition digest mismatch')
        races.append(json.loads(raw))
    splits={k:[r for r in races if protocol[k]['from']<=r['date']<=protocol[k]['to']] for k in ['train','validation','test']}
    assert all(splits.values()) and sum(map(len,splits.values()))==len(races)
    assert max(r['date'] for r in splits['train'])<min(r['date'] for r in splits['validation'])
    assert max(r['date'] for r in splits['validation'])<min(r['date'] for r in splits['test'])
    models=[{'kind':'uniform'}]+[fit(splits['train'],l2) for l2 in protocol['l2_candidates']]
    validation=[metrics(splits['validation'],m) for m in models]
    selected=min(range(len(models)),key=lambda i:validation[i]['log_loss']);model=models[selected]
    output={'status':'EXPERIMENTAL_NO_BET','protocol':protocol,'split_races':{k:len(v) for k,v in splits.items()},
        'validation_candidates':[{'model':m,'metrics':v} for m,v in zip(models,validation)],'selected_candidate':selected,
        'test':{'selected':metrics(splits['test'],model),'uniform':metrics(splits['test'],models[0])},
        'limitations':['Only 46 races and 9 dates; final test is a single day.','Historical publication time unproven.','Up to five historical runs, not complete careers.','No odds input, ROI or profitability estimate.','No test-based tuning or production validation.'],'subgroups':{}}
    # Feature contribution assessed on validation only, never used to retune on test.
    best_logit=min(models[1:],key=lambda m:metrics(splits['validation'],m)['log_loss'])
    full_loss=metrics(splits['validation'],best_logit)['log_loss']
    output['validation_ablation']={name:metrics(splits['validation'],fit(splits['train'],best_logit['l2'],omit=i))['log_loss']-full_loss for i,name in enumerate(FEATURES)}
    for field in ['venue','distance_m','category','start_type']:
        groups=defaultdict(list)
        for race in splits['test']:groups[str(race[field])].append(race)
        output['subgroups'][field]={g:metrics(v,model) for g,v in groups.items()}
    model.update(validation_status='experimental',feature_names=FEATURES,protocol_version=protocol['version'],training_period=protocol['train'],selection_period=protocol['validation'])
    dump('models/pilot_v1.json',model);dump('reports/backtest_pilot_v1.json',output)
    predictions=[{'race_id':r['race_id'],'probabilities':probabilities(r,model)} for r in splits['test']]
    dump('reports/test_predictions_pilot_v1.json',predictions)
    selected_metrics=output['test']['selected'];base=output['test']['uniform']
    lines=['# Pilote V1 — backtest chronologique','', '**Statut : expérimental, NO BET.**', '',
      'Entraînement : 16 courses de 2024. Validation : 16 courses de 2025. Test : 14 courses du 05/10/2026.',
      'La sélection utilise seulement la log loss de validation. Le modèle retenu reste inchangé sur le test.',
      '', '| Modèle, test uniquement | Log loss | Brier multiclasses | Favori correct |','|---|---:|---:|---:|',
      f"| Retenu ({model['kind']}) | {selected_metrics['log_loss']:.4f} | {selected_metrics['brier_multiclass']:.4f} | {selected_metrics['top1_accuracy']:.1%} |",
      f"| Uniforme | {base['log_loss']:.4f} | {base['brier_multiclass']:.4f} | {base['top1_accuracy']:.1%} |",'',
      'Brier = somme des erreurs quadratiques des partants, puis moyenne par course. Les égalités de probabilité sont départagées par numéro croissant : le top-1 uniforme dépend donc de cette convention.',
      '', 'Calibration, effectifs et sous-groupes figurent dans backtest_pilot_v1.json. L’ablation mesure la variation de log loss de validation lorsqu’une variable est retirée (positif : retrait défavorable).', '',
      'Un seul jour de test ne permet pas d’estimer une généralisation fiable ni un intervalle de confiance entre journées. Les résultats sont exploratoires. Aucun Elo/arbre ajouté sur cet échantillon trop faible.', '',
      'Les résultats historiques sont datés avant la cible ; leur disponibilité réelle au moment du départ ancien n’est pas prouvée. Une validation prospective reste nécessaire. Aucun ROI calculé.']
    Path('reports/BACKTEST_PILOT_V1.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'selected':model['kind'],'test':output['test']}))

if __name__=='__main__': main()
