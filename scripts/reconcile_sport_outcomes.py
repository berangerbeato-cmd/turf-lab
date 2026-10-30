"""Offline official-result reconciliation; frozen inputs are never modified."""
import gzip
import hashlib
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from scripts.collect_sport_cohort import restore_evidence
from turf_lab.evidence import dump, EvidenceStore
from turf_lab.history import race_day, summarize_run
from turf_lab.individual_history_check import normalized_name

ROOT = Path('reports/sport_enriched_cohort_v1')
OUTPUT = Path('reports/sport_outcome_reconciliation_v1')


def resolve(raw, horse_id, records):
    """Require exact date/track/course and horse ID, then independent rank agreement."""
    day = race_day(raw).isoformat()
    candidates = []
    for record, source, digest in records:
        course = record['course']
        if (record['date'] != day or
                course.get('hippodrome', {}).get('codeHippodrome') != raw.get('racecourseCode') or
                record['course_number'] != raw.get('raceNumber')):
            continue
        if not course.get('arriveeDefinitive') or course.get('discipline') != 'ATTELE':
            continue
        for runner in record['participants']:
            if (runner.get('idCheval') != horse_id or
                    normalized_name(runner.get('nom')) != normalized_name(raw['raceRunParticipant'].get('horseName'))):
                continue
            number = runner['numPmu']
            rank = runner.get('ordreArrivee')
            order = course.get('ordreArrivee', [])
            official_ranks = []
            position = 1
            for group in order:
                if number in group:
                    official_ranks.append(position)
                position += len(group)
            incident = runner.get('incident')
            incidents = {i['type'] for i in course.get('incidents', []) if number in i.get('numeroParticipants', [])}
            if incident:
                incidents.add(incident)
            if len(incidents) > 1:
                return {'status': 'CONFLICT', 'reason': 'incompatible_incidents'}
            incident = next(iter(incidents), None)
            if type(rank) is int and rank > 0 and official_ranks == [rank] and not incident:
                outcome = {'rank': rank, 'dq': False, 'finished': True}
            elif not official_ranks and not (type(rank) is int and rank > 0) and incident in ('ARRETE', 'TOMBE'):
                outcome = {'rank': None, 'dq': False, 'finished': False, 'incident': incident}
            elif not official_ranks and not (type(rank) is int and rank > 0) and isinstance(incident, str) and (incident.startswith('DISQUALIF') or incident == 'DISTANCE'):
                outcome = {'rank': None, 'dq': True, 'finished': False, 'incident': incident}
            else:
                return {'status': 'UNRESOLVED_OFFICIAL_OUTCOME', 'reason': 'official_rank_or_incident_not_reconciled',
                        'evidence': [{'race_id': record['race_id'], 'source': source, 'sha256': digest}]}
            if runner.get('statut') != 'PARTANT':
                return {'status': 'CONFLICT', 'reason': 'nonrunner_in_history'}
            original_status = raw['raceRunParticipant'].get('place', {}).get('arrivalStatus')
            if original_status in ('ARRETE', 'TOMBE') and outcome.get('incident') != original_status:
                return {'status': 'CONFLICT', 'reason': 'individual_official_status_mismatch'}
            if original_status == 'PLACE' and not outcome['finished']:
                return {'status': 'CONFLICT', 'reason': 'individual_official_status_mismatch'}
            candidates.append({'outcome': outcome, 'race_id': record['race_id'], 'source': source, 'sha256': digest})
    if not candidates:
        return {'status': 'UNRESOLVED_NO_EXACT_ARCHIVE'}
    if any(c['outcome'] != candidates[0]['outcome'] for c in candidates):
        return {'status': 'CONFLICT', 'reason': 'archive_versions_disagree'}
    return {'status': 'RESOLVED', 'outcome': candidates[0]['outcome'], 'evidence': candidates}


def main():
    restore_evidence(ROOT)
    store = EvidenceStore(ROOT/'evidence', max_requests=0)
    dataset = json.loads((ROOT/'dataset.json').read_text())
    pending = []
    for race in dataset:
        cutoff = (date.fromisoformat(race['date'])-timedelta(days=60)).isoformat()
        for runner in race['runners']:
            meta = store.manifest[runner['evidence_key']]
            payload = store.get(meta['url'], runner['evidence_key'])
            from urllib.parse import unquote
            horse_id = unquote(meta['url'].split('/program/')[1].split('/light-performances')[0])
            for raw in payload['runner']['racesRun']:
                day = race_day(raw).isoformat()
                if not cutoff <= day < race['date'] or raw.get('discipline') != 'ATTELE':
                    continue
                p = raw['raceRunParticipant']
                if p.get('place', {}).get('arrivalStatus') == 'NON_PARTANT':
                    continue
                summary = summarize_run(raw)
                if summary['disqualified'] or type(summary['rank']) is int:
                    continue
                pending.append((race, runner, raw, horse_id))
    needed = {race_day(raw).isoformat() for _, _, raw, _ in pending}
    records = []
    for day in sorted(needed):
        paths = list(Path('data').glob(f'month_{day[:7]}/races/{day}_*.json.gz'))
        daily = Path('data/history_updates')/(day+'.json.gz')
        if daily.exists():
            paths.append(daily)
        for path in sorted(paths):
            content = path.read_bytes()
            decoded = json.loads(gzip.decompress(content))
            digest = hashlib.sha256(content).hexdigest()
            for record in decoded.get('records', [decoded]):
                records.append((record, str(path), digest))
    ledger = []
    for race, runner, raw, horse_id in pending:
        result = resolve(raw, horse_id, records)
        ledger.append({'target_race': race['race_id'], 'number': runner['number'], 'name': runner['name'],
                       'prior_date': race_day(raw).isoformat(), 'track': raw.get('racecourseCode'),
                       'course': raw.get('raceNumber'), 'individual_status': raw['raceRunParticipant']['place'].get('arrivalStatus'),
                       **result})
    counts = dict(Counter(r['status'] for r in ledger))
    report = {'counts': counts, 'affected_target_runners': len({(r['target_race'], r['number']) for r in ledger}),
              'unique_prior_starts': len({(r['name'], r['prior_date'], r['track'], r['course']) for r in ledger}),
              'dataset_sha256': hashlib.sha256((ROOT/'dataset.json').read_bytes()).hexdigest(),
              'individual_manifest_sha256': hashlib.sha256(store.manifest_path.read_bytes()).hexdigest(),
              'ledger': ledger, 'network_requests': 0, 'frozen_features_changed': False,
              'training_performed': False, 'recommendations_allowed': False}
    dump(OUTPUT/'reconciliation.json', report)
    print(json.dumps({k:v for k,v in report.items() if k != 'ledger'}))


if __name__ == '__main__':
    main()
