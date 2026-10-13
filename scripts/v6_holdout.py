"""Fixed additional holdout; freeze is required before any collection."""
import argparse
import json
from pathlib import Path
from scripts.backtest_connections import PROTOCOL, verify_frozen, digest, split, monthly
from scripts.backtest_extension import load_sources
from scripts.backtest_opposition import day_bootstrap
from scripts.collect_month import collect, git_checkpoint
from turf_lab.evidence import EvidenceStore, dump
from turf_lab.month_history import build_history
from turf_lab.opposition import augment as opposition
from turf_lab.connections import augment_connections
from turf_lab.demographics_tandem import augment, candidate
from turf_lab.pilot import metrics, probabilities

POLICY = Path('config/v6_holdout_protocol.json')
LOCK = Path('models/v6_holdout_frozen.json')
V6_MODELS = Path('models/demographics_tandem_v6_candidates.json')


def verify():
    p = json.loads(POLICY.read_text())
    lock = json.loads(LOCK.read_text())
    v5p = json.loads(PROTOCOL.read_text())
    frozen, v5models = verify_frozen(v5p)
    if lock['v5_frozen'] != frozen or lock['policy_sha256'] != digest(POLICY):
        raise ValueError('Holdout policy or V5 changed')
    if any(digest(path) != sha for path,sha in lock['files_sha256'].items()):
        raise ValueError('V6 holdout model/code changed')
    report = json.loads(Path('reports/demographics_tandem_v6.json').read_text())
    if report['selected'] != p['v6_selected'] or report['models_sha256'] != digest(V6_MODELS):
        raise ValueError('V6 selected model mismatch')
    models = {'v5': v5models['combined'], 'v6': json.loads(V6_MODELS.read_text())['models'][p['v6_selected']]}
    return p, lock, v5p, models


def collect_one(month):
    p, _, _, _ = verify()
    if month not in p['collection_months']:
        raise ValueError('Month outside fixed holdout collection')
    root, output = Path('evidence/month_'+month), Path('data/month_'+month)
    store = EvidenceStore(root, max_requests=p['max_requests_per_month'], delay=.5)
    report = collect(month, store, output, lambda: git_checkpoint(root, output))
    dump('reports/month_'+month+'.json', report)
    if report['status'] == 'PAUSED_REQUEST_BUDGET':
        raise RuntimeError('Collection budget reached; resume cached evidence')
    load_sources({'months': [month], 'minimum_retained_fraction_per_month': p['minimum_retained_fraction_per_month']})


def evaluate():
    p, lock, v5p, models = verify()
    target = Path('reports/v6_holdout.json')
    if target.exists():
        if json.loads(target.read_text())['frozen'] != lock:
            raise ValueError('Existing holdout under another freeze')
        print('Existing holdout retained; no repeated selection')
        return
    records, coverage = load_sources({'months': p['source_months'], 'minimum_retained_fraction_per_month': p['minimum_retained_fraction_per_month']})
    v6p = json.loads(Path('config/demographics_tandem_v6_protocol.json').read_text())
    rows = augment_connections(opposition(build_history(records, lookback_days=v5p['lookback_days'])), records,
        window=v5p['connections_window_days'], strength=v5p['connections_prior_strength'], equipment_days=v5p['equipment_history_days'])
    rows = augment(rows, records, v6p['tandem_window_days'], v6p['prior_strength'])
    rows = split(rows, p['test'], p['minimum_races_per_month'])
    frames = {'v5': candidate(rows, 'v5'), 'v6': candidate(rows, p['v6_selected'])}
    results = {n: metrics(frames[n], models[n]) for n in p['models']}
    by_month = {n: monthly(frames[n], models[n], p['minimum_races_per_month']) for n in p['models']}
    paired = day_bootstrap((frames['v5'], frames['v6']), models['v5'], models['v6'])
    paired['interpretation'] = 'Fixed paired holdout comparison; exploratory day bootstrap, not proof of profitability or annual robustness.'
    sources = {m: digest('data/month_'+m+'/manifest.json') for m in p['source_months']}
    dump(target, {'status': 'FIXED_HOLDOUT_NO_BET', 'frozen': lock, 'source_manifests_sha256': sources,
        'test_races': len(rows), 'test': results, 'by_month': by_month, 'paired': paired,
        'coverage': coverage, 'refitted': False, 'prospective_changed': False})
    dump('reports/v6_holdout_predictions.json', {n: [{'race_id': r['race_id'], 'probabilities': probabilities(r, models[n])} for r in frames[n]] for n in p['models']})
    lines = ['# V6 — test figé juillet–août 2025', '', '**NO BET. Aucun réentraînement, aucune sélection sur ce test.**',
        f"{len(rows)} courses. Juin sert uniquement à compléter les historiques.", '',
        '| Modèle | Log loss | Brier | Top-1 |', '|---|---:|---:|---:|']
    for n,m in results.items():
        lines.append(f"| {n} | {m['log_loss']:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines += ['', f"Écart V6−V5 : {paired['delta_log_loss']:.5f} ; intervalle descriptif par journées : {paired['day_bootstrap_95_percent']}.",
        'Les résultats mensuels et la calibration sont dans le JSON. Deux mois ne démontrent ni stabilité annuelle ni rentabilité.',
        'V5 prospectif inchangé. Aucune promotion automatique, quel que soit le résultat.']
    Path('reports/V6_HOLDOUT.md').write_text('\n'.join(lines)+'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--month')
    parser.add_argument('--evaluate', action='store_true')
    args = parser.parse_args()
    if bool(args.month) == bool(args.evaluate):
        raise ValueError('Choose collection OR evaluation')
    stage = args.month or 'evaluation'
    try:
        collect_one(args.month) if args.month else evaluate()
    except (ValueError, RuntimeError, FileNotFoundError, KeyError) as error:
        dump('reports/v6_holdout_status_'+stage+'.json', {'status': 'BLOCKED', 'reason': str(error)})
        raise
    dump('reports/v6_holdout_status_'+stage+'.json', {'status': 'SUCCESS_NO_BET'})


if __name__ == '__main__':
    main()
