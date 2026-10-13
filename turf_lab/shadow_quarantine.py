"""Explicit evidence-locked exclusions for shadow inputs, not model changes."""
import hashlib
import json
from copy import deepcopy


def apply_quarantine(records, coverage, exclusions, minimum):
    remaining = list(records)
    adjusted = deepcopy(coverage)
    audit = []
    if len({e['race_id'] for e in exclusions}) != len(exclusions):
        raise ValueError('Duplicate shadow quarantine')
    for exclusion in exclusions:
        rid = exclusion['race_id']
        matches = [r for r in remaining if r['race_id'] == rid]
        if len(matches) != 1:
            raise ValueError('Quarantine target absent or duplicated: ' + rid)
        raw = (json.dumps(matches[0], ensure_ascii=False, sort_keys=True) + '\n').encode()
        if hashlib.sha256(raw).hexdigest() != exclusion['source_sha256']:
            raise ValueError('Quarantine source changed: ' + rid)
        month = next(c for c in adjusted if c['month'] == rid[:7])
        counts = month['coverage_counts']
        counts['retained'] -= 1
        counts['unresolved'] += 1
        counts['fraction'] = counts['retained'] / counts['eligible'] if counts['eligible'] else 0
        month['retained'] -= 1
        month['quarantine'].append({'race_id': rid, 'issues': [exclusion['reason']], 'scope': 'V5 shadow only'})
        if counts['fraction'] < minimum:
            raise ValueError('Coverage gate failed after shadow quarantine: ' + rid[:7])
        remaining = [r for r in remaining if r['race_id'] != rid]
        audit.append(dict(exclusion))
    return remaining, adjusted, audit
