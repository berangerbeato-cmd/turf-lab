"""Coverage of races actually eligible for results; cancellation requires evidence."""
import gzip
import hashlib
import json
from pathlib import Path


def cancelled_evidence(month, quarantines, root=Path('evidence')):
    folder = root / ('month_' + month)
    if not quarantines:
        return []
    manifest = json.loads((folder / 'manifest.json').read_text())
    excluded = []
    for item in quarantines:
        key = item['race_id'] + '_course_detail'
        meta = manifest.get(key, {})
        if meta.get('status') != 200:
            continue
        raw = gzip.decompress((folder / meta['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest() != meta['sha256']:
            raise ValueError('Cancellation evidence digest mismatch: ' + key)
        detail = json.loads(raw)
        if (detail.get('statut') == 'COURSE_ANNULEE'
                and detail.get('categorieStatut') == 'ANNULEE'
                and not detail.get('ordreArrivee')
                and not detail.get('arriveeDefinitive')):
            excluded.append({'race_id': item['race_id'], 'evidence_sha256': meta['sha256'],
                             'reason': 'Explicit PMU cancellation; not a missing result'})
    return excluded


def coverage_counts(manifest, cancellations):
    retained = [p['race_id'] for p in manifest['partitions']]
    quarantine = [q['race_id'] for q in manifest['quarantine']]
    cancelled = [c['race_id'] for c in cancellations]
    if (len(set(retained + quarantine)) != len(retained) + len(quarantine)
            or len(retained) + len(quarantine) != manifest['candidate_races']
            or len(set(cancelled)) != len(cancelled)
            or not set(cancelled).issubset(quarantine)):
        raise ValueError('Inconsistent coverage accounting')
    eligible = manifest['candidate_races'] - len(cancelled)
    return {'scheduled': manifest['candidate_races'], 'cancelled': len(cancelled),
            'eligible': eligible, 'retained': len(retained),
            'unresolved': len(quarantine) - len(cancelled),
            'fraction': len(retained) / eligible if eligible else 0.0}
