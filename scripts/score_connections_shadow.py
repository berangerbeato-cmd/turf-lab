"""Bounded scoring of the six predeclared races; no market endpoint."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo
from scripts.backtest_connections import PROTOCOL, verify_frozen
from turf_lab.evidence import EvidenceStore, dump
from turf_lab.shadow_v5_score import score, choose_snapshot


def main(v6=False):
    policy = json.loads(Path('config/v5_followup.json').read_text())
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo('Europe/Paris')).date().isoformat()
    if not policy['from'] <= today <= policy['through']:
        print('Outside bounded follow-up window: no requests')
        return
    frozen, _ = verify_frozen(json.loads(PROTOCOL.read_text()))
    label = 'v6' if v6 else 'v5'
    names = ['v3', frozen['selected']]
    if v6:
        from scripts.v6_holdout import verify
        _, frozen, _, _ = verify()
        names = ['v5', 'v6']
    batch = now.strftime('%Y%m%dT%H%M%S%fZ')
    store = EvidenceStore('evidence/'+label+'_results/'+batch, max_requests=policy['max_requests'], delay=.5)
    output = []
    for rid in policy['race_ids']:
        candidates = [(path, json.loads(path.read_text())) for path in Path('predictions_'+label).glob(rid[:10]+'/'+rid+'_*/prediction.json')]
        chosen = choose_snapshot(candidates)
        if chosen is None:
            output.append({'race_id': rid, 'status': 'QUARANTINE', 'reason': 'no_prestart_snapshot'})
            continue
        path, prediction = chosen
        info = {'race_id': rid, 'snapshot': str(path), 'snapshot_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'snapshot_count': len(candidates), 'history_gap_days': prediction['history_gap_days']}
        if prediction['frozen'] != frozen:
            output.append(dict(info, status='QUARANTINE', reason='frozen_model_mismatch'))
            continue
        if v6:
            source = Path(prediction['v5_snapshot'])
            if not source.exists() or hashlib.sha256(source.read_bytes()).hexdigest() != prediction['v5_snapshot_sha256']:
                output.append(dict(info, status='QUARANTINE', reason='v5_snapshot_changed'))
                continue
        if now <= datetime.fromisoformat(prediction['scheduled_start']):
            output.append(dict(info, status='PENDING', reason='race_not_started'))
            continue
        day, rn, cn = re.fullmatch(r'(\d{4}-\d{2}-\d{2})_R(\d+)C(\d+)', rid).groups()
        detail = store.race(day, int(rn), int(cn), '')
        runners = store.race(day, int(rn), int(cn), 'participants')
        if not isinstance(detail, dict) or not isinstance(runners, dict) or not runners.get('participants'):
            result = {'status': 'PENDING', 'reason': 'response_unavailable'}
        else:
            try:
                result = score(prediction, detail, runners['participants'], model_names=names)
            except (ValueError, KeyError, TypeError) as error:
                result = {'status': 'QUARANTINE', 'reason': str(error)}
        output.append(dict(info, **result))
    scored = [r for r in output if r['status'] == 'SCORED']
    aggregate = {n: {key: mean(r['models'][n][key] for r in scored) for key in ('log_loss','brier_multiclass','top1_hit')}
                 for n in names} if scored else {}
    report = {'status': 'OBSERVATION_ONLY_NO_BET', 'checked_at': now.isoformat(),
              'scored': len(scored), 'planned': len(policy['race_ids']), 'races': output,
              'metrics': aggregate, 'evidence_manifest': str(store.manifest_path),
              'limits': 'Six selected races only, no profitability claim, no post-result probability changes.'}
    dump('reports/'+label+'_prospective_scores.json', report)
    dump('reports/'+label+'_score_runs/'+batch+'.json', report)
    lines = ['# Suivi prospectif '+('/'.join(names)), '', '**Observation uniquement — NO BET.**',
             f"Courses évaluées : {len(scored)}/{len(policy['race_ids'])}. Vérification : {now.isoformat()}.", '',
             '| Course | État | Motif |', '|---|---|---|']
    for r in output:
        lines.append(f"| {r['race_id']} | {r['status']} | {r.get('reason', 'Arrivée définitive concordante')} |")
    if aggregate:
        lines += ['', '| Modèle | Log loss | Brier | Top-1 |', '|---|---:|---:|---:|']
        for n,m in aggregate.items():
            lines.append(f"| {n} | {m['log_loss']:.5f} | {m['brier_multiclass']:.5f} | {m['top1_hit']:.1%} |")
    lines += ['', 'Dernière capture sauvegardée avant départ retenue sans consulter les résultats. Partants, driver, entraîneur et ferrure doivent concorder.',
              'Aucune renormalisation après non-partant. Les exclusions sont visibles. Six courses ne démontrent ni robustesse ni rentabilité.']
    Path('reports/'+label.upper()+'_PROSPECTIVE_SCORES.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'scored': len(scored), 'statuses': [r['status'] for r in output]}))


if __name__ == '__main__':
    main()
