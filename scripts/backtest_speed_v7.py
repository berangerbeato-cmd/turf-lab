"""Predeclared single-feature development experiment; no promotion or holdout reuse."""
import json
from pathlib import Path
from statistics import mean
from scripts.v6_holdout import verify
from scripts.backtest_connections import prepare, split, monthly, digest
from scripts.backtest_extension import load_sources
from scripts.backtest_opposition import day_bootstrap
from turf_lab.demographics_tandem import augment as demographics
from turf_lab.context_speed import augment, candidate
from turf_lab.fast_logit import fit
from turf_lab.pilot import metrics
from turf_lab.evidence import dump


def main():
    protocol = Path('config/speed_v7_protocol.json')
    p = json.loads(protocol.read_text())
    _, lock, base, models = verify()
    target = Path('reports/speed_v7.json')
    if target.exists():
        old = json.loads(target.read_text())
        if old['protocol_sha256'] != digest(protocol) or old['baseline_frozen'] != lock:
            raise ValueError('Existing speed experiment has another freeze')
        print('Existing experiment retained; no retuning')
        return
    if any(m[:4] not in ('2024','2025') or int(m[5:]) > 5 for m in base['development_months']):
        raise ValueError('Only January-May development permitted')
    rows, source_hash, _ = prepare(base, 'validate')
    if source_hash != lock['v5_frozen']['sources_sha256']:
        raise ValueError('Development sources changed')
    records, _ = load_sources({'months': base['development_months'], 'minimum_retained_fraction_per_month': .98})
    vp = json.loads(Path('config/demographics_tandem_v6_protocol.json').read_text())
    rows = demographics(rows, records, vp['tandem_window_days'], vp['prior_strength'])
    rows, audit = augment(rows, records, p)
    train = split(rows,p['train'],p['minimum_races_per_month'])
    val = split(rows,p['validation'],p['minimum_races_per_month'])
    models = {'v6': models['v6'], 'v7_speed': fit(candidate(train,'v7_speed'), p['l2'], p['iterations'], p['learning_rate'])}
    frames = {n: candidate(val,n) for n in p['candidates']}
    results = {n: metrics(frames[n],models[n]) for n in p['candidates']}
    months = {n: monthly(frames[n],models[n],p['minimum_races_per_month']) for n in p['candidates']}
    old = json.loads(Path('reports/demographics_tandem_v6.json').read_text())['validation']['combined']
    if abs(results['v6']['log_loss']-old['log_loss']) > 1e-10:
        raise ValueError('Frozen V6 validation not reproduced')
    scores = {n: mean(m['log_loss'] for m in months[n].values()) for n in p['candidates']}
    paired = day_bootstrap((frames['v6'], frames['v7_speed']), models['v6'], models['v7_speed'])
    coverage = {}
    for label, split_rows in [('train',train),('validation',val)]:
        active = [r for row in split_rows for r in row['runners'] if not r['non_runner']]
        coverage[label] = {'active':len(active), 'with_speed':sum(r['speed_features'][0] is not None for r in active)}
    model_path = 'models/speed_v7_candidates.json'
    dump(model_path, {'status':'EXPLORATORY_NOT_DEPLOYED','models':models})
    report = {'status':'EXPLORATORY_REUSED_VALIDATION_NO_BET','protocol_sha256':digest(protocol),
        'baseline_frozen':lock,'sources_sha256':source_hash,'models_sha256':digest(model_path),
        'code_sha256':{path:digest(path) for path in ('turf_lab/context_speed.py','scripts/backtest_speed_v7.py')},
        'train_races':len(train),'validation_races':len(val),'validation':results,'by_month':months,
        'monthly_mean_log_loss':scores,'paired':paired,'coverage':coverage,'audit':audit,
        'test_evaluated':False,'prospective_changed':False,'limits':p['limits']}
    dump(target,report)
    lines = ['# V7 : chrono corrigé du contexte — essai exploratoire','','**NO BET. V6 prospectif inchangé. Validation réutilisée, pas de test indépendant.**','',
        f"Entraînement : {len(train)} courses. Validation : {len(val)} courses.",'',
        '| Variante | Log loss mensuelle moyenne | Brier | Top-1 |','|---|---:|---:|---:|']
    for n in p['candidates']:
        m=results[n]
        lines.append(f"| {n} | {scores[n]:.5f} | {m['brier_multiclass']:.5f} | {m['top1_accuracy']:.1%} |")
    lines += ['', 'Couverture de la variable : '+json.dumps(coverage), '',
        'Comparaison appariée exploratoire : '+json.dumps(paired), '',
        'Une seule variable supplémentaire. Correction partielle : hippodrome, classe de distance et départ, estimés sur les journées antérieures. Qualité de course, météo et état réel de piste restent confondus.',
        'Aucun ajustement après lecture. Juillet–août 2025 non utilisés. Nouvelle période indépendante nécessaire pour confirmer tout gain.']
    Path('reports/SPEED_V7.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'scores':scores,'coverage':coverage,'paired':paired}),flush=True)


if __name__ == '__main__':
    main()
