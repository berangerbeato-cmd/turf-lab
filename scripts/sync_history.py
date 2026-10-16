"""Daily strict audit and missing-only catch-up. Exit nonzero on ANY remaining gap."""
import argparse
import gzip
import hashlib
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from turf_lab.evidence import dump
from turf_lab.history_sync import audit, summarize, Collector, History


def write_report(report):
    dump('reports/history_sync/status.json', report)
    lines = ['# Historique des courses', '',
        f"État de l’actualisation : {report['status']}",
        f"Dernière journée complète : {report.get('last_complete_day') or 'inconnue'}",
        f"Dernière journée collectée : {report.get('last_collected_day') or 'inconnue'}",
        f"Continuité complète depuis 2022-01-01 : {report.get('complete_continuously_through') or 'non établie'}",
        f"Courses récupérées : {report.get('recovered_races', 0)} ; vérifiées : {report.get('verified_races', 0)}",
        f"Journées incomplètes : {report.get('missing_days', 'inconnu')} ; courses connues manquantes : {report.get('missing_races', 'inconnu')}",
        f"Journées sans programme vérifiable : {report.get('unknown_programme_days', 'inconnu')} (nombre de courses inconnu)",
        f"Cible : {report['required_through']}", '',
        'Périmètre : trot attelé français répertorié par PMU. Les annulations sont justifiées par la source.',
        'Un résultat ex æquo est conservé ; les exclusions du modèle ne masquent pas les trous historiques.', '',
        '| Journée | Courses attendues | Vérifiées | Manquantes | Diagnostic |',
        '|---|---:|---:|---:|---|']
    for row in report.get('days', []):
        if row['status'] != 'OK':
            reasons = row['issues'] + [p['race_id']+': '+str(p['reasons']) for p in row['pending']]
            lines.append(f"| {row['date']} | {row['expected']} | {row['verified_races']} | {len(row['pending'])} | {'; '.join(map(str,reasons))} |")
    if report.get('error'): lines += ['', report['error']]
    text = '\n'.join(lines)+'\n'
    Path('reports/history_sync/status.md').write_text(text)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f: f.write(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--today', default=datetime.now(ZoneInfo('Europe/Paris')).date().isoformat())
    parser.add_argument('--audit-only', action='store_true')
    parser.add_argument('--max-requests', type=int, default=800)
    args = parser.parse_args()
    today = date.fromisoformat(args.today)
    if today > datetime.now(ZoneInfo('Europe/Paris')).date() or today <= date(2022,1,1):
        raise ValueError('Invalid cutoff')
    report = dict(status='ÉCHEC',required_through=(today-timedelta(days=1)).isoformat())
    try:
        states = audit(today)
        collector = Collector(args.max_requests)
        report = summarize(states, today, collector)
        write_report(report)  # preserve starting inventory even if interrupted
        if not args.audit_only:
            # Most recent first, then older holes: stale historical days never starve yesterday.
            history = History()
            for i in reversed(range(len(states))):
                if states[i]['status'] == 'OK': continue
                collector.repair(states[i])
                errors = states[i]['issues'][:]
                states[i] = history.day(states[i]['date'])
                if states[i]['status'] != 'OK': states[i]['issues'].extend(errors)
                if collector.stopped or collector.remaining <= 0: break
            report = summarize(states, today, collector)
        # Feature inputs are refreshed only after a fully verified calendar.
        # Existing predictor computes past-only features from this loader, with frozen weights.
        report['prediction_inputs_status'] = 'READY' if report['status']=='OK' else 'BLOCKED_INCOMPLETE_HISTORY'
        if not args.audit_only and report['status'] == 'OK':
            records = [r for s in states for r in s['records']]
            payload = json.dumps(records, ensure_ascii=False, sort_keys=True).encode()
            path = Path('data/history_updates/prediction_inputs.json.gz')
            digest = hashlib.sha256(payload).hexdigest()
            lock = Path('data/history_updates/prediction_inputs_manifest.json')
            old = json.loads(lock.read_text()) if lock.exists() else {}
            if old.get('sha256') != digest or not path.exists():
                temp = path.with_suffix('.tmp'); temp.parent.mkdir(parents=True, exist_ok=True)
                temp.write_bytes(gzip.compress(payload, mtime=0)); temp.replace(path)
            dump(lock, dict(through=report['required_through'], sha256=digest, races=len(records)))
        write_report(report)
    except Exception as error:
        report.update(status='ÉCHEC', error=str(error), prediction_inputs_status='BLOCKED')
        write_report(report)
        raise
    print(json.dumps({k:v for k,v in report.items() if k!='days'}, ensure_ascii=False))
    if report['status'] != 'OK': raise SystemExit(2)

if __name__ == '__main__': main()
