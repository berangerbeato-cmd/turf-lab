"""Frozen V2 evaluation, run only after all nine monthly quality gates pass."""
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from turf_lab.evidence import dump
from turf_lab.month_history import build_history
from turf_lab.pilot import FEATURES, fit, metrics, probabilities


def load_sources(protocol):
    records=[];coverage=[]
    for month in protocol['months']:
        manifest=json.loads(Path(f'data/month_{month}/manifest.json').read_text())
        if manifest['status'] not in ('COLLECTED','COLLECTED_WITH_GAPS') or any(d['status']!='OK' for d in manifest['days']):
            raise ValueError('Incomplete monthly programmes: '+month)
        from scripts.collect_month import month_days
        if [d['date'] for d in manifest['days']]!=month_days(month):raise ValueError('Incomplete calendar: '+month)
        fraction=len(manifest['partitions'])/max(1,manifest['candidate_races'])
        if fraction<protocol['minimum_retained_fraction_per_month']:raise ValueError('Coverage gate failed: '+month)
        coverage.append({'month':month,'candidates':manifest['candidate_races'],'retained':len(manifest['partitions']),
            'quarantine':manifest['quarantine'],'venues':manifest['venues']})
        for entry in manifest['partitions']:
            raw=gzip.decompress(Path(entry['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Source digest mismatch')
            records.append(json.loads(raw))
    return records,coverage


def main():
    protocol_path=Path('config/history_extension_protocol.json')
    protocol=json.loads(protocol_path.read_text())
    records,coverage=load_sources(protocol)
    races=build_history(records,lookback_days=protocol['lookback_days'])
    splits={k:[r for r in races if protocol[k]['from']<=r['date']<=protocol[k]['to']] for k in ('train','validation','test')}
    if any(len(v)<protocol['minimum_races_per_split'] for v in splits.values()):raise ValueError('Insufficient split size')
    if not max(r['date'] for r in splits['train'])<min(r['date'] for r in splits['validation'])<min(r['date'] for r in splits['test']):
        raise ValueError('Chronological split violation')
    source_digests=[{'race_id':r['race_id'],'sha256':hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()} for r in records]
    provenance={'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        'sources_sha256':hashlib.sha256(json.dumps(source_digests,sort_keys=True).encode()).hexdigest()}
    existing=Path('reports/backtest_extension_v2.json')
    if existing.exists():
        previous=json.loads(existing.read_text())
        if previous.get('provenance')==provenance:
            print('Existing frozen evaluation retained; no repeat test tuning.');return
        raise ValueError('Frozen evaluation exists with different inputs; new version and review required')
    models=[{'kind':'uniform'}]+[fit(splits['train'],l2) for l2 in protocol['l2_candidates']]
    validation=[metrics(splits['validation'],m) for m in models]
    selected=min(range(len(models)),key=lambda i:validation[i]['log_loss']);model=models[selected]
    output={'status':'EXPERIMENTAL_NO_BET','provenance':provenance,'protocol':protocol,'coverage':coverage,
        'split_races':{k:len(v) for k,v in splits.items()},'validation_candidates':[{'kind':m['kind'],'l2':m.get('l2'),'metrics':v} for m,v in zip(models,validation)],
        'selected_candidate':selected,'test':{'selected':metrics(splits['test'],model),'uniform':metrics(splits['test'],models[0])},'subgroups':{},
        'limitations':['French PMU-listed attelé only; unlisted starts unknown.','Sixty-day observed histories, maximum five starts; missing history explicit.',
        'Winter/spring sample only, not full-year generalization.','Retrospective snapshots; original publication time unproven.',
        'No odds, ROI, profitability claim, test tuning or automatic replacement of prospective pilot.']}
    for field in ('venue','distance_m','category','start_type'):
        groups=defaultdict(list)
        for race in splits['test']:groups[str(race[field])].append(race)
        output['subgroups'][field]={key:metrics(rows,model) for key,rows in groups.items()}
    model.update(validation_status='experimental',feature_names=FEATURES,protocol_version=protocol['version'],provenance=provenance)
    dump('models/history_v2.json',model)
    dump('reports/test_predictions_extension_v2.json',[{'race_id':r['race_id'],'probabilities':probabilities(r,model)} for r in splits['test']])
    dest=Path('data/history_v2');dest.mkdir(parents=True,exist_ok=True)
    for name,rows in splits.items():
        (dest/(name+'.jsonl.gz')).write_bytes(gzip.compress(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows).encode(),mtime=0))
    dump(existing,output)
    Path('reports/BACKTEST_EXTENSION_V2.md').write_text('# Backtest historique V2\n\n**Expérimental — NO BET.**\n\n'+
        'Découpage : '+json.dumps(output['split_races'])+'\n\n'+
        '| Test mars 2026 | Log loss | Brier | Top-1 |\n|---|---:|---:|---:|\n'+
        ''.join(f"| {name} | {m['log_loss']:.4f} | {m['brier_multiclass']:.4f} | {m['top1_accuracy']:.1%} |\n" for name,m in output['test'].items())+
        '\nSélection uniquement sur mars 2025. Janvier–février servent à construire les historiques, pas à évaluer.\n'+
        '\nLe modèle prospectif V1 reste inchangé. Résultats saisonniers, historiques incomplets hors périmètre PMU ; aucune rentabilité établie.\n')
    print(json.dumps({'status':output['status'],'splits':output['split_races'],'test':output['test']}))

if __name__=='__main__':
    try:
        main()
        dump('reports/history_extension_status.json', {'status':'EVALUATED_EXPERIMENTAL_NO_BET'})
    except (ValueError, FileNotFoundError) as error:
        dump('reports/history_extension_status.json', {'status':'BLOCKED_NO_TRAINING_OR_UPDATE', 'reason':str(error)})
        raise
