"""Outcome-blind sampling and dated, conservative history reconciliation."""
import hashlib
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from turf_lab.pilot import dated_history, features, norm_name


def select(rows, protocol):
    groups = defaultdict(list)
    for row in rows:
        if any(protocol[s][0] <= row['date'] <= protocol[s][1] for s in ('train', 'validation', 'test')):
            groups[row['date'][:7]].append(row)
    result = []
    for month, races in sorted(groups.items()):
        ranked = sorted(races, key=lambda r: hashlib.sha256((protocol['version'] + ':' + r['race_id']).encode()).hexdigest())
        result.extend(ranked[:protocol['races_per_month']])
    return sorted(result, key=lambda r: (r['date'], r['race_id']))


def repair(frame, baseline, payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('participants'), list):
        raise ValueError('Individual history unavailable')
    by = {p['numPmu']: p for p in payload['participants']}
    if len(by) != len(payload['participants']):
        raise ValueError('Duplicate history runner')
    old = {p['number']: p for p in baseline['runners']}
    if len(old) != len(baseline['runners']) or set(old) != {p['number'] for p in frame['runners']}:
        raise ValueError('Runner set mismatch')
    out = deepcopy(frame)
    changed = []; added = 0
    cutoff = (date.fromisoformat(frame['date']) - timedelta(days=60)).isoformat()
    for r in out['runners']:
        if r['non_runner']:
            continue
        original = old[r['number']]
        h = by.get(r['number'])
        if h is None or norm_name(h['nomCheval']) != norm_name(original['name']):
            raise ValueError('History identity mismatch')
        if original['horse_id'] != r['horse_id'] or original['features'] != r['features'][:5]:
            raise ValueError('Archived baseline does not reproduce')
        rows = dated_history(h, frame['date'])
        # Date+venue is conservative: refuse conflicting outcomes and multiple starts.
        merged = {}
        for prior in original['history']:
            key = (prior['date'], norm_name(prior['venue']))
            if key in merged:
                raise ValueError('Ambiguous same-day historical starts')
            merged[key] = prior
        seen = set()
        for prior in rows:
            if prior['date'] < cutoff:
                continue
            key = (prior['date'], norm_name(prior['venue']))
            if not prior['venue'] or key in seen:
                raise ValueError('Ambiguous individual race identity')
            seen.add(key)
            if prior['rank'] is None and not prior['status']:
                raise ValueError('Unknown historical outcome')
            if key in merged:
                existing = merged[key]
                if existing['rank'] != prior['rank'] or bool(existing['dq']) != bool(prior['dq']):
                    raise ValueError('Conflicting historical outcome')
            else:
                merged[key] = prior
                added += 1
        recent = sorted(merged.values(), key=lambda x: x['date'], reverse=True)[:5]
        values = features(recent, frame['date'])
        if values != r['features'][:5]:
            changed.append(r['number'])
        r['features'][:5] = values
    return out, {'changed_runners': changed, 'added_starts': added}
