"""Bounded monthly coverage experiment; never trains or fetches market endpoints."""
import argparse
import calendar
import collections
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from turf_lab.evidence import EvidenceStore, dump, races, start_type
from turf_lab.quality import assess


def month_days(month):
    year, number = map(int, month.split('-'))
    if f'{year:04d}-{number:02d}' != month:
        raise ValueError('Use YYYY-MM')
    return [f'{month}-{day:02d}' for day in range(1, calendar.monthrange(year, number)[1]+1)]


def valid_programme(value):
    body = value.get('programme', value) if isinstance(value, dict) else None
    return isinstance(body, dict) and isinstance(body.get('reunions'), list)


def git_checkpoint(evidence, output):
    """Used only in authenticated Actions; preserve a week before proceeding."""
    subprocess.run(['git', 'add', str(evidence), str(output), 'reports/test_results.txt'], check=True)
    changed = subprocess.run(['git', 'diff', '--cached', '--quiet'])
    if changed.returncode == 0:
        return
    if changed.returncode != 1:
        raise RuntimeError('Cannot inspect staged checkpoint')
    subprocess.run(['git', 'commit', '-m', 'Checkpoint bounded monthly collection'], check=True)
    for attempt in range(3):
        subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'], check=True)
        pushed = subprocess.run(['git', 'push', 'origin', 'HEAD:main'])
        if pushed.returncode == 0:
            return
    raise RuntimeError('Checkpoint push failed after three non-forcing attempts')


def collect(month, store, output, checkpoint=None, through=None):
    days = month_days(month)
    if through is not None:
        if through not in days:
            raise ValueError('Through date must belong to month')
        days = [day for day in days if day <= through]
    saved = output / 'manifest.json'
    if saved.exists():
        previous = json.loads(saved.read_text())
        if (previous.get('month') == month
                and previous.get('status') in ('COLLECTED', 'COLLECTED_WITH_GAPS')
                and [d['date'] for d in previous['days']] == days
                and all(d['status'] == 'OK' for d in previous['days'])):
            for entry in previous['partitions']:
                raw = gzip.decompress(Path(entry['file']).read_bytes())
                if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                    raise ValueError('Completed month digest mismatch: ' + entry['race_id'])
            print('Verified completed month from cache; no requests or checkpoint rewrites: '+month)
            return previous
    report = {'month': month, 'status': 'RUNNING', 'days': [], 'partitions': [],
              'quarantine': [], 'fields_nonempty': {}, 'participants': 0,
              'historical_snapshot': 'Retrospective; original pre-race publication unproven',
              'model_status': 'NO BET; no training in this experiment'}
    field_counts = collections.Counter()
    try:
        for day in days:
            programme = store.programme(day)
            if not valid_programme(programme):
                report['days'].append({'date': day, 'status': 'PROGRAMME_UNAVAILABLE'})
                continue
            candidates = list(races(programme))
            report['days'].append({'date': day, 'status': 'OK', 'candidate_races': len(candidates)})
            for reunion, course in candidates:
                rn, cn = reunion['numOfficiel'], course['numOrdre']
                race_id = f'{day}_R{rn}C{cn}'
                participants = store.race(day, rn, cn, 'participants')
                detail = store.race(day, rn, cn, '')
                runners = participants.get('participants', []) if isinstance(participants, dict) else []
                record = {'date': day, 'race_id': race_id, 'reunion': rn, 'course_number': cn,
                          'venue': reunion.get('hippodrome', {}).get('libelleCourt'),
                          'country': 'FRA', 'start_type': start_type(course),
                          'distance_m': course.get('distance'), 'scheduled_start_ms': course.get('heureDepart'),
                          'course': course, 'participants': runners, 'detail': detail}
                if not isinstance(runners, list) or not runners or not isinstance(detail, dict):
                    report['quarantine'].append({'race_id': race_id, 'issues': ['missing_response']})
                    continue
                try:
                    diagnostic = assess([record])
                except (KeyError, TypeError, AttributeError) as error:
                    report['quarantine'].append({'race_id': race_id, 'issues': ['malformed_response: '+str(error)]})
                    continue
                if diagnostic['issues'] or diagnostic['counts'].get('single_winner_races') != 1:
                    report['quarantine'].append({'race_id': race_id, 'issues': diagnostic['issues'] or ['not_single_winner']})
                    continue
                raw = (json.dumps(record, ensure_ascii=False, sort_keys=True)+'\n').encode()
                path = output / 'races' / (race_id+'.json.gz')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(gzip.compress(raw, mtime=0))
                report['partitions'].append({'race_id': race_id, 'file': str(path),
                    'sha256': hashlib.sha256(raw).hexdigest(), 'venue': record['venue'],
                    'start_type': record['start_type'], 'warnings': diagnostic['warnings']})
                report['participants'] += len(runners)
                for runner in runners:
                    for key in ('idCheval','nomMere','nomPere','driver','entraineur','musique','ferrure',
                                'reductionKilometrique','tempsObtenu','age','sexe','gainsParticipant'):
                        field_counts[key] += runner.get(key) not in (None, '', [], {})
                report['fields_nonempty'] = dict(field_counts)
                dump(output/'manifest.json', report)
            if checkpoint and (len(report['days']) % 7 == 0 or day == days[-1]):
                dump(output/'manifest.json', report)
                checkpoint()
        report['status'] = 'COLLECTED_WITH_GAPS' if report['quarantine'] or any(d['status']!='OK' for d in report['days']) else 'COLLECTED'
    except RuntimeError as error:
        if 'request budget' not in str(error):
            raise
        report['status'] = 'PAUSED_REQUEST_BUDGET'
    finally:
        report['field_availability_retained_participants'] = {
            key: {'nonempty': value, 'denominator': report['participants'],
                  'fraction': value/report['participants'] if report['participants'] else None}
            for key, value in field_counts.items()}
        report['requests_this_run'] = store.requests
        report['venues'] = dict(collections.Counter(p['venue'] for p in report['partitions']))
        report['candidate_races'] = sum(d.get('candidate_races', 0) for d in report['days'])
        dump(output/'manifest.json', report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', default='2024-01', choices=['2024-01'])
    parser.add_argument('--max-requests', type=int, default=1800)
    parser.add_argument('--git-checkpoints', action='store_true')
    args = parser.parse_args()
    output = Path('data/month_'+args.month)
    evidence = Path('evidence/month_'+args.month)
    checkpoint = (lambda: git_checkpoint(evidence, output)) if args.git_checkpoints else None
    report = collect(args.month, EvidenceStore(evidence, args.max_requests, delay=0.5), output, checkpoint)
    dump('reports/month_coverage.json', report)
    lines = ['# Monthly collection coverage', '', f"Month: {args.month}; status: {report['status']}",
             f"Programmes examined: {len(report['days'])}; candidate races: {report['candidate_races']}",
             f"Quality-controlled races: {len(report['partitions'])}; quarantined: {len(report['quarantine'])}",
             f"Participants in retained races: {report['participants']}", '',
             'This is PMU programme coverage, not proof of coverage of every French race.',
             'Retrospective snapshots are not evidence of historical publication before departure.',
             'Race results and times are labels/history only, never same-race predictors.',
             'No expanded training or multi-year collection is authorized by an automatic quality pass.']
    Path('reports/MONTH_COVERAGE.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:report[k] for k in ('status','candidate_races','participants','requests_this_run')}))
    if report['status']=='PAUSED_REQUEST_BUDGET':
        raise SystemExit(2)

if __name__ == '__main__':
    main()
