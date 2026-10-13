"""Descriptive frozen-test diagnostics; never tune or refit on this test."""
import json
from pathlib import Path
from scripts.backtest_connections import PROTOCOL, verify_frozen, prepare, split
from scripts.backtest_opposition import day_bootstrap
from turf_lab.connections import candidate
from turf_lab.pilot import metrics
from turf_lab.evidence import dump


def calibration_summary(bins):
    n = sum(b['count'] for b in bins)
    if not n:
        raise ValueError('Empty calibration')
    return {'runner_weighted_ece': sum(b['count'] * abs(b['mean_probability'] - b['win_frequency']) for b in bins) / n,
            'runner_count': n, 'bins': bins,
            'warning': 'Descriptive fixed bins; runners are dependent within races. Sparse high probabilities remain uncertain.'}


def main():
    p = json.loads(PROTOCOL.read_text())
    frozen, models = verify_frozen(p)
    saved = json.loads(Path('reports/connections_v5_test.json').read_text())
    if saved['frozen'] != frozen:
        raise ValueError('Test/freeze mismatch')
    rows, source_hash, _ = prepare(p, 'test')
    if source_hash != saved['sources_sha256']:
        raise ValueError('Test source changed')
    rows = split(rows, p['test'], p['minimum_races_per_month'])
    selected = frozen['selected']
    frames = {n: candidate(rows, n) for n in ('v3', selected)}
    for n, frame in frames.items():
        actual = metrics(frame, models[n])
        for key in ('log_loss', 'brier_multiclass', 'top1_accuracy'):
            if abs(actual[key] - saved['test'][n][key]) > 1e-10:
                raise ValueError('Test reproduction mismatch')
    paired = day_bootstrap((frames['v3'], frames[selected]), models['v3'], models[selected])
    paired['interpretation'] = 'Descriptive paired day bootstrap on the frozen independent test; no retuning. Does not establish future profitability.'
    monthly = []
    for month, base in saved['by_month']['v3'].items():
        other = saved['by_month'][selected][month]
        monthly.append({'month': month, 'races': base['races'], 'v3': base['log_loss'],
                        'v5': other['log_loss'], 'delta': other['log_loss'] - base['log_loss'],
                        'top1_v3': base['top1_accuracy'], 'top1_v5': other['top1_accuracy']})
    calibration = {n: calibration_summary(saved['test'][n]['calibration']) for n in frames}
    dump('reports/connections_v5_audit.json', {'status': 'DESCRIPTIVE_NO_BET', 'frozen': frozen,
         'monthly': monthly, 'paired': paired, 'calibration': calibration, 'refitted': False})
    lines = ['# V5 — stabilité et calibration', '', 'Modèle et code gelés vérifiés ; test reproduit sans réentraînement. NO BET.', '',
             '| Mois | Courses | Log loss V3 | Log loss V5 | Écart V5−V3 |', '|---|---:|---:|---:|---:|']
    for m in monthly:
        lines.append(f"| {m['month']} | {m['races']} | {m['v3']:.5f} | {m['v5']:.5f} | {m['delta']:.5f} |")
    lines += ['', f"Écart global : {paired['delta_log_loss']:.5f}. Intervalle descriptif à 95 % par journées : {paired['day_bootstrap_95_percent']}.", '',
              '| Probabilité V5 moyenne | Victoires observées | Participations |', '|---:|---:|---:|']
    for b in calibration[selected]['bins']:
        lines.append(f"| {b['mean_probability']:.1%} | {b['win_frequency']:.1%} | {b['count']} |")
    lines += ['', 'Calibration descriptive, non recalibrée sur le test. Les classes élevées sont trop peu fournies pour conclure.',
              'Deux mois de printemps/été ne valident pas la stabilité annuelle. Disponibilité historique avant-course non prouvée globalement.',
              'Prochaine étape : compléter les historiques récents puis enregistrer de nouvelles prédictions avant départ. Aucun pari ni promotion automatique.']
    Path('reports/CONNECTIONS_V5_AUDIT.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'monthly': monthly, 'paired': paired, 'ece': {n: c['runner_weighted_ece'] for n, c in calibration.items()}}))


if __name__ == '__main__':
    main()
