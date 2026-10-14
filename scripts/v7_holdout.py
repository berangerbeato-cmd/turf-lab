"""One newly reserved V6/V7 holdout. No fitting and no parameter selection."""
import argparse
import json
from pathlib import Path
from scripts.shadow_v7 import verify as verify_models
from scripts.backtest_connections import digest, split, monthly
from scripts.backtest_extension import load_sources
from scripts.backtest_opposition import day_bootstrap
from scripts.collect_month import collect, git_checkpoint
from turf_lab.evidence import EvidenceStore, dump
from turf_lab.month_history import build_history
from turf_lab.opposition import augment as opposition
from turf_lab.connections import augment_connections
from turf_lab.demographics_tandem import augment as demographics
from turf_lab.context_speed import augment, candidate
from turf_lab.pilot import metrics, probabilities

POLICY = Path('config/v7_holdout_protocol.json')
LOCK = Path('models/v7_holdout_frozen.json')


def verify():
    p = json.loads(POLICY.read_text())
    lock = json.loads(LOCK.read_text())
    frozen, base, models = verify_models()
    if lock['v7_frozen'] != frozen or lock['policy_sha256'] != digest(POLICY):
        raise ValueError('V7 holdout policy or model changed')
    if any(digest(path) != sha for path,sha in lock['files_sha256'].items()):
        raise ValueError('V7 holdout code changed')
    return p, lock, base, models


def collect_one(month):
    p, _, _, _ = verify()
    if month not in p['collection_months']:
        raise ValueError('Month outside reserved V7 holdout')
    root, output = Path('evidence/month_'+month), Path('data/month_'+month)
    store = EvidenceStore(root, max_requests=p['max_requests_per_month'], delay=.5)
    report = collect(month, store, output, lambda: git_checkpoint(root, output))
    dump('reports/month_'+month+'.json', report)
    if report['status'] == 'PAUSED_REQUEST_BUDGET':
        raise RuntimeError('Collection budget reached; resume cached evidence')
    load_sources({'months':[month], 'minimum_retained_fraction_per_month':p['minimum_retained_fraction_per_month']})


def evaluate():
    p, lock, base, models = verify()
    target = Path('reports/v7_holdout.json')
    if target.exists():
        if json.loads(target.read_text())['frozen'] != lock:
            raise ValueError('Existing result under another freeze')
        print('Existing V7 holdout retained; no repeated selection')
        return
    records, coverage = load_sources({'months':p['source_months'], 'minimum_retained_fraction_per_month':p['minimum_retained_fraction_per_month']})
    rows = augment_connections(opposition(build_history(records, lookback_days=base['lookback_days'])), records,
        window=base['connections_window_days'], strength=base['connections_prior_strength'], equipment_days=base['equipment_history_days'])
    vp = json.loads(Path('config/demographics_tandem_v6_protocol.json').read_text())
    rows = demographics(rows, records, vp['tandem_window_days'], vp['prior_strength'])
    rows, audit = augment(rows, records, json.loads(Path('config/speed_v7_protocol.json').read_text()))
    rows = split(rows, p['test'], p['minimum_races_per_month'])
    frames = {n:candidate(rows,n) for n in p['models']}
    results = {n:metrics(frames[n],models[n]) for n in p['models']}
    months = {n:monthly(frames[n],models[n],p['minimum_races_per_month']) for n in p['models']}
    paired = day_bootstrap((frames['v6'],frames['v7_speed']), models['v6'],models['v7_speed'])
    paired['interpretation'] = 'Fixed paired holdout; descriptive day bootstrap, no annual stability or profitability claim.'
    active = [r for row in rows for r in row['runners'] if not r['non_runner']]
    speed_coverage = {'active':len(active),'with_speed':sum(r['speed_features'][0] is not None for r in active)}
    dump(target, {'status':'FIXED_HOLDOUT_NO_BET','frozen':lock,
        'source_manifests_sha256':{m:digest('data/month_'+m+'/manifest.json') for m in p['source_months']},
        'test_races':len(rows),'test':results,'by_month':months,'paired':paired,'coverage':coverage,
        'speed_coverage':speed_coverage,'audit':audit,'refitted':False,'prospective_changed':False})
    dump('reports/v7_holdout_predictions.json', {n:[{'race_id':r['race_id'],'probabilities':probabilities(r,models[n])} for r in frames[n]] for n in p['models']})
    lines = ['# V7 — test figé septembre–octobre 2025','','**NO BET. Aucun réentraînement, aucun ajustement sur ce test.**',
        f"{len(rows)} courses. Historique janvier–août utilisé uniquement comme passé.",'',
        '| Modèle | Log loss | Brier | Top-1 |','|---|---:|---:|---:|']
    for n,m in results.items():
        lines.append(f"| {n} | {m['log_loss']:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines += ['', 'Écart apparié V7−V6 : '+json.dumps(paired), '', 'Couverture du chrono : '+json.dumps(speed_coverage), '',
        'Aucune promotion automatique. Deux mois ne démontrent ni stabilité annuelle ni rentabilité. Suivi prospectif inchangé.']
    Path('reports/V7_HOLDOUT.md').write_text('\n'.join(lines)+'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--month')
    parser.add_argument('--evaluate',action='store_true')
    args = parser.parse_args()
    if bool(args.month) == bool(args.evaluate):
        raise ValueError('Choose collection OR evaluation')
    stage = args.month or 'evaluation'
    try:
        collect_one(args.month) if args.month else evaluate()
    except (ValueError, RuntimeError, FileNotFoundError, KeyError) as error:
        dump('reports/v7_holdout_status_'+stage+'.json',{'status':'BLOCKED','reason':str(error)})
        raise
    dump('reports/v7_holdout_status_'+stage+'.json',{'status':'SUCCESS_NO_BET'})


if __name__ == '__main__':
    main()
