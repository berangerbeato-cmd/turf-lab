"""Outcome-blind date cohort; retrospective source coverage, never betting advice.

Only five dated sporting features are exported. No market or current-form fields.
A returned window is not proof of an exhaustive career; completeness remains unknown.
"""
import argparse
import gzip
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import tarfile

from collect import BASE
from turf_lab.evidence import EvidenceStore, dump, races
from turf_lab.individual_history_check import normalize_history
from turf_lab.pilot import features

POLICY = Path('config/sport_enriched_cohort.json')


def restore_evidence(root):
    root = Path(root)
    bundle = root/'evidence.tar.gz'
    if bundle.exists() and not (root/'evidence'/'manifest.json').exists():
        with tarfile.open(bundle, 'r:gz') as archive:
            for member in archive.getmembers():
                parts = Path(member.name).parts
                if not member.isfile() or len(parts) != 2 or parts[0] != 'evidence' or '..' in parts:
                    raise ValueError('Unsafe evidence bundle member')
            archive.extractall(root, filter='data')


def bundle_evidence(root):
    root = Path(root)
    temporary = root/'evidence.tar.gz.tmp'
    with temporary.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode='w') as archive:
            for path in sorted((root/'evidence').iterdir()):
                if path.is_file():
                    info = archive.gettarinfo(path, arcname='evidence/'+path.name)
                    info.mtime = info.uid = info.gid = 0
                    info.uname = info.gname = ''
                    info.mode = 0o644
                    with path.open('rb') as stream:
                        archive.addfile(info, stream)
    temporary.replace(root/'evidence.tar.gz')


def prefetch(policy, root, max_requests):
    """Independent per-horse stores; only this main thread writes shared manifest."""
    root = Path(root)
    lock = root / 'protocol.json'
    if lock.exists() and json.loads(lock.read_text()) != policy:
        raise ValueError('Cohort protocol changed')
    dump(lock, policy)
    store = EvidenceStore(root / 'evidence', max_requests=0)
    jobs = {}
    for day in policy['dates']:
        archive = json.loads(gzip.decompress((Path('data/history_updates')/(day+'.json.gz')).read_bytes()))
        if archive['date'] != day:
            raise ValueError('Archive date mismatch')
        for record in archive['records']:
            if record['country'] != 'FRA' or record['course']['discipline'] not in ('ATTELE','TROT_ATTELE'):
                continue
            for runner in record['participants']:
                horse_id = runner.get('idCheval')
                if runner['statut'] != 'PARTANT' or not horse_id:
                    continue
                key = 'horse_' + hashlib.sha256(horse_id.encode()).hexdigest()[:24]
                if key not in store.manifest:
                    jobs[key] = BASE.rsplit('/',1)[0]+'/program/'+quote(horse_id,safe='')+'/light-performances'
    def fetch(item):
        key, url = item
        shard = EvidenceStore(root/'pending'/key, max_requests=1)
        shard.get(url, key)
        return key, shard
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(fetch, item) for item in list(jobs.items())[:max_requests]]
        for future in as_completed(futures):
            key, shard = future.result()
            meta = shard.manifest[key]
            if meta.get('file'):
                shutil.copyfile(shard.root/meta['file'], store.root/meta['file'])
            store.manifest[key] = meta
            dump(store.manifest_path, store.manifest)
            shutil.rmtree(shard.root)


def sporting_row(payload, runner, day):
    rows, excluded = normalize_history(payload, runner, day)
    cutoff = (date.fromisoformat(day) - timedelta(days=60)).isoformat()
    recent = [r for r in rows if r['date'] >= cutoff][:5]
    # Future rows must not contribute to window coverage either.
    reaches_boundary = any(r['date'] <= cutoff for r in rows)
    history = [{'date': r['date'], 'rank': r['rank'], 'dq': r['disqualified']} for r in recent]
    return {'number': runner['numPmu'], 'name': runner['nom'],
            'features': features(history, day), 'history': history,
            'window_supported': len(recent) == 5 or reaches_boundary,
            'completeness': 'UNKNOWN_SOURCE_MAY_OMIT_STARTS',
            'excluded_target_or_future': sum(r['reason'] == 'target_or_future_day' for r in excluded),
            'unknown_outcomes': sum(r['reason'] == 'unknown_outcome' and r['date'] >= cutoff for r in excluded)}


def collect(policy, root, max_requests):
    root = Path(root)
    lock = root / 'protocol.json'
    if lock.exists() and json.loads(lock.read_text()) != policy:
        raise ValueError('Cohort protocol changed; use a new version and output directory')
    dump(lock, policy)  # Freeze selection before retrieving any individual history.
    store = EvidenceStore(root / 'evidence', max_requests=max_requests)
    ledger, dataset, sources = [], [], {}
    for day in policy['dates']:
        source = Path('data/history_updates') / (day + '.json.gz')
        raw = source.read_bytes()
        sources[str(source)] = hashlib.sha256(raw).hexdigest()
        archive = json.loads(gzip.decompress(raw))
        if archive['date'] != day:
            raise ValueError('Archive date mismatch')
        records = {r['race_id']: r for r in archive['records']}
        if len(records) != len(archive['records']):
            raise ValueError('Duplicate archived race')
        planned = sorted((int(m['numOfficiel']), int(c['numOrdre'])) for m,c in races(archive['programme']))
        if len(set(planned)) != len(planned):
            raise ValueError('Duplicate race identity')
        for rn, cn in planned:
            rid = f'{day}_R{rn}C{cn}'
            state = {'race_id': rid, 'runners': []}
            record = records.get(rid)
            if record is None:
                state['status'] = 'MISSING_ARCHIVED_RACE'
                ledger.append(state)
                continue
            if not record['course'].get('arriveeDefinitive'):
                state['status'] = 'RESULT_NOT_FINAL'
                ledger.append(state)
                continue
            runners = [r for r in record['participants'] if r['statut'] == 'PARTANT']
            if len({r['numPmu'] for r in runners}) != len(runners) or len(runners) < 2:
                raise ValueError('Invalid field')
            outputs = []
            for runner in runners:
                try:
                    horse_id = runner['idCheval']
                    key = 'horse_' + hashlib.sha256(horse_id.encode()).hexdigest()[:24]
                    payload = store.get(BASE.rsplit('/',1)[0]+'/program/'+quote(horse_id,safe='')+'/light-performances', key)
                    row = sporting_row(payload, runner, day)
                    # Labels attached only after feature creation, never passed into it.
                    row.update(non_runner=False, won=runner.get('ordreArrivee') == 1,
                               age_for_coverage_audit=runner.get('age'),
                               disqualified=str(runner.get('incident','')).startswith('DISQUALIF') or runner.get('incident') == 'DISTANCE',
                               evidence_key=key)
                    outputs.append(row)
                    state['runners'].append({'number':runner['numPmu'], 'status':'WINDOW_SUPPORTED' if row['window_supported'] else 'WINDOW_UNSUPPORTED'})
                except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
                    state['runners'].append({'number':runner['numPmu'], 'status':'UNVERIFIED', 'reason':str(error)})
            valid = len(outputs) == len(runners) and sum(r['won'] for r in outputs) == 1
            state['status'] = 'EXPLORATORY_COMPLETE_FIELD' if valid else 'BLOCKED_FIELD'
            state['all_windows_supported'] = valid and all(r['window_supported'] and not r['unknown_outcomes'] for r in outputs)
            if valid:
                dataset.append({'race_id':rid, 'date':day, 'runners':outputs,
                                'all_windows_supported':state['all_windows_supported']})
            ledger.append(state)
            dump(root/'checkpoint.json', {'ledger':ledger, 'requests_this_run':store.requests})
    by_age = {}
    for race in dataset:
        for runner in race['runners']:
            stats = by_age.setdefault(str(runner['age_for_coverage_audit']), {'runners':0, 'unsupported_windows':0})
            stats['runners'] += 1
            stats['unsupported_windows'] += not runner['window_supported']
    result = {'protocol':policy, 'source_sha256':sources, 'planned_races':len(ledger),
              'complete_fields':len(dataset), 'supported_fields':sum(r['all_windows_supported'] for r in dataset),
              'runner_rows':sum(len(r['runners']) for r in dataset), 'coverage_by_age':by_age, 'ledger':ledger,
              'training_status':'BLOCKED_COVERAGE_REVIEW_AND_REPRESENTATIVE_SPLITS_REQUIRED',
              'recommendations_allowed':False, 'retrospective':True}
    dump(root/'dataset.json', dataset)
    result['dataset_sha256'] = hashlib.sha256((root/'dataset.json').read_bytes()).hexdigest()
    result['evidence_manifest_sha256'] = hashlib.sha256(store.manifest_path.read_bytes()).hexdigest()
    dump(root/'coverage.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('ledger','protocol','source_sha256')}))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-requests', type=int, default=500)
    args = parser.parse_args()
    if not 0 <= args.max_requests <= 1000:
        parser.error('max-requests must be 0..1000')
    policy = json.loads(POLICY.read_text())
    restore_evidence('reports/sport_enriched_cohort_v1')
    prefetch(policy, 'reports/sport_enriched_cohort_v1', args.max_requests)
    collect(policy, 'reports/sport_enriched_cohort_v1', 0)
    bundle_evidence('reports/sport_enriched_cohort_v1')

if __name__ == '__main__':
    main()
