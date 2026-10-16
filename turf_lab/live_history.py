"""Verified historical inputs for future predictions; never rewrites model fit data."""
import gzip
import hashlib
import json
from pathlib import Path
from scripts.refresh_recent_history import require_fresh


def load_available_history(today):
    recent = require_fresh(today)  # fail before expensive feature construction
    policy = json.loads(Path('config/full_history_protocol.json').read_text())
    records = []
    for path in sorted(Path('data').glob('month_*/manifest.json')):
        month = path.parent.name[6:]
        if month in policy['excluded_months']: continue
        for entry in json.loads(path.read_text())['partitions']:
            raw = gzip.decompress(Path(entry['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise ValueError('Historical source checksum mismatch')
            race = json.loads(raw)
            if race['race_id'] in policy['excluded_races'] or race['date'] >= today.isoformat(): continue
            # Daily collection owns dates starting October 14; never duplicate snapshots.
            if race['date'] >= '2026-10-14': continue
            records.append(race)
    records.extend(recent)
    if len({r['race_id'] for r in records}) != len(records): raise ValueError('Duplicate history race')
    return records
