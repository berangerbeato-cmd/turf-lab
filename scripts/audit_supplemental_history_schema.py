"""Measure supplemental source limitations without assuming complete race fields."""
import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from turf_lab.evidence import dump


def audit(root):
    root = Path(root)
    manifest_path = root/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    counts = Counter()
    keys = set()
    for meta in manifest.values():
        if meta['status'] != 200:
            continue
        raw = gzip.decompress((root/meta['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest() != meta['sha256']:
            raise ValueError('Source checksum mismatch')
        obj = json.loads(raw)
        counts['successful_responses'] += 1
        for horse in obj.get('participants', []):
            for race in horse.get('coursesCourues', []):
                counts['historical_rows_with_repetitions'] += 1
                runners = race.get('participants', [])
                n = race.get('nbParticipants')
                counts['rows_with_declared_field_size'] += isinstance(n, int)
                counts['rows_with_fewer_listed_than_declared'] += isinstance(n, int) and len(runners) < n
                for runner in runners:
                    counts['listed_participants'] += 1
                    keys.update(runner)
                    counts['participants_with_trainer_field'] += any('entrain' in k.lower() or 'trainer' in k.lower() for k in runner)
    return {'source_manifest':str(manifest_path),'source_manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'counts':dict(counts),'participant_keys':sorted(keys),
            'interpretation':'Rows and participants may repeat across horse and target histories. Counts are not unique races or people. Partial opponent lists and missing trainers do not support full Elo/connection reconstruction.',
            'production_changed':False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',default='evidence/sport_history_cohort_v1')
    parser.add_argument('--output',default='reports/sport_history_cohort_v2/source_schema_audit.json')
    args = parser.parse_args()
    result = audit(args.root)
    dump(args.output,result)
    print(json.dumps(result))
