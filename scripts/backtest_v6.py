"""One predeclared exploratory comparison; no independent test or promotion."""
import json
from pathlib import Path
from statistics import mean
from scripts.backtest_connections import PROTOCOL, verify_frozen, prepare, split, monthly, digest
from scripts.backtest_extension import load_sources
from scripts.backtest_opposition import day_bootstrap
from turf_lab.demographics_tandem import augment, candidate
from turf_lab.fast_logit import fit
from turf_lab.pilot import metrics
from turf_lab.evidence import dump


def main():
    protocol_path = Path('config/demographics_tandem_v6_protocol.json')
    p = json.loads(protocol_path.read_text())
    v5 = json.loads(PROTOCOL.read_text())
    frozen, baselines = verify_frozen(v5)
    target = Path('reports/demographics_tandem_v6.json')
    if target.exists():
        old = json.loads(target.read_text())
        if old['protocol_sha256'] != digest(protocol_path) or old['v5_frozen'] != frozen:
            raise ValueError('Existing V6 report under another protocol')
        print('Existing V6 result retained; no retuning')
        return
    if any(m.startswith('2026') for m in v5['development_months']):
        raise ValueError('Test outcomes forbidden')
    rows, source_hash, _ = prepare(v5, 'validate')
    if source_hash != frozen['sources_sha256']:
        raise ValueError('V5 development sources changed')
    records, _ = load_sources({'months': v5['development_months'], 'minimum_retained_fraction_per_month': .98})
    rows = augment(rows, records, p['tandem_window_days'], p['prior_strength'])
    train = split(rows, p['train'], p['minimum_races_per_month'])
    val = split(rows, p['validation'], p['minimum_races_per_month'])
    models, results, months, frames, scores = {}, {}, {}, {}, {}
    for name in p['candidates']:
        model = baselines['combined'] if name == 'v5' else fit(candidate(train, name), p['l2'], p['iterations'], p['learning_rate'])
        frame = candidate(val, name)
        models[name], frames[name] = model, frame
        results[name] = metrics(frame, model)
        months[name] = monthly(frame, model, p['minimum_races_per_month'])
        scores[name] = mean(m['log_loss'] for m in months[name].values())
        print(json.dumps({'candidate': name, 'monthly_log_loss': scores[name]}), flush=True)
    old = json.loads(Path('reports/connections_v5_validation.json').read_text())['validation']['combined']
    if abs(old['log_loss'] - results['v5']['log_loss']) > 1e-10:
        raise ValueError('V5 reference not reproduced')
    selected = min(p['candidates'], key=lambda n: scores[n])
    paired = {n: day_bootstrap((frames['v5'], frames[n]), models['v5'], models[n]) for n in p['candidates'] if n != 'v5'}
    model_path = 'models/demographics_tandem_v6_candidates.json'
    dump(model_path, {'status': 'EXPLORATORY_NOT_DEPLOYED', 'models': models})
    report = {'status': 'EXPLORATORY_REUSED_VALIDATION_NO_BET', 'protocol_sha256': digest(protocol_path),
        'v5_frozen': frozen, 'sources_sha256': source_hash, 'models_sha256': digest(model_path),
        'code_sha256': {path: digest(path) for path in ('turf_lab/demographics_tandem.py', 'scripts/backtest_v6.py')},
        'train_races': len(train), 'validation_races': len(val), 'selected': selected,
        'validation': results, 'by_month': months, 'selection_scores': scores, 'paired_comparisons': paired,
        'test_evaluated': False, 'prospective_changed': False}
    dump(target, report)
    lines = ['# V6 âge/sexe et tandem — comparaison exploratoire', '',
        '**Validation 2025 déjà consultée : ni test indépendant ni promotion. NO BET.**',
        f"Train : {len(train)} courses (mars–mai 2024). Validation : {len(val)} courses (mars–mai 2025). V5 reproduit avec ses poids gelés.", '',
        '| Variante | Log loss mensuelle moyenne | Brier global | Top-1 |', '|---|---:|---:|---:|']
    for n in p['candidates']:
        lines.append(f"| {n} | {scores[n]:.5f} | {results[n]['brier_multiclass']:.5f} | {results[n]['top1_accuracy']:.1%} |")
    lines += ['', 'Meilleure variante selon le critère prépublié : '+selected+'.',
              'Résultats mensuels et intervalles exploratoires dans le JSON. Aucun résultat 2026 chargé. Aucun ajustement après observation.',
              'Nouvelle période indépendante nécessaire avant de conclure à un gain. Les six captures V5 sont inchangées.']
    Path('reports/DEMOGRAPHICS_TANDEM_V6.md').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    main()
