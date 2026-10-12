"""Build a leakage-controlled exploratory dataset, without fitting any model."""
import gzip
import hashlib
import json
from pathlib import Path
from turf_lab.evidence import dump
from turf_lab.month_history import build_history


def main():
    source = Path('data/month_2024-01/manifest.json')
    manifest = json.loads(source.read_text())
    if manifest['status'] not in ('COLLECTED', 'COLLECTED_WITH_GAPS') or len(manifest['days']) != 31:
        raise ValueError('Monthly collection must finish before dataset construction')
    records = []
    for entry in manifest['partitions']:
        raw = gzip.decompress(Path(entry['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Source digest mismatch')
        records.append(json.loads(raw))
    rows = build_history(records)
    raw = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in rows).encode()
    dest = Path('data/month_2024-01/history_features.jsonl.gz')
    dest.write_bytes(gzip.compress(raw, mtime=0))
    runners = [r for race in rows for r in race['runners'] if not r['non_runner']]
    coverage_by_day = {}
    for race in rows:
        day = coverage_by_day.setdefault(race['date'], {'races': 0, 'active_runners': 0, 'with_prior_observation': 0})
        day['races'] += 1
        for runner in race['runners']:
            if not runner['non_runner']:
                day['active_runners'] += 1
                day['with_prior_observation'] += bool(runner['history'])
    summary = {'coverage_by_day': coverage_by_day,
        'distinct_horses': len({r['horse_id'] for r in runners}), 'status': 'EXPLORATORY_NOT_TRAINED', 'source_manifest_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'dataset_sha256': hashlib.sha256(raw).hexdigest(), 'races': len(rows), 'active_runners': len(runners),
        'runners_with_prior_observations': sum(bool(r['history']) for r in runners),
        'runners_with_five_prior_observations': sum(len(r['history'])==5 for r in runners),
        'cutoff': 'Strictly earlier calendar day; same-day results excluded',
        'limitations': ['Only performances in retained PMU races within January 2024.',
            'Missing earlier/out-of-scope races; rest means days since last OBSERVED race.',
            'Cold starts explicit; no claim of complete form or career history.',
            'No new training, validation, test, ROI or promotion of frozen pilot.']}
    dump('reports/month_history_features.json', summary)
    print(json.dumps(summary))

if __name__ == '__main__':
    main()
