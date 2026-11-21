"""Isolated prestart-evidence replay for repairing the five recent-history features.

This is NOT a production model, a new fitted model, or a betting signal.
All data must come from immutable evidence fetched BEFORE the original start.
Do not change frozen model or archived original predictions.
"""
import copy
import gzip
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote
from turf_lab.available_history_operational import verify_active
from turf_lab.available_history_research import recent_values
from turf_lab.individual_history_check import normalize_history, venue_key
from turf_lab.pilot import probabilities


def checked_prestart_stamp(value, start):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None or start.tzinfo is None or not stamp < start:
        raise ValueError('History evidence is not timestamped before the race')
    return stamp


def archive_key(h):
    match = re.search(r'C([0-9]+)$', h.get('race_id', ''))
    if not match:
        raise ValueError('Unusable archive history race identity')
    return h['date'], venue_key(h['venue']), int(match.group(1))


def official_key(h):
    return h['date'], venue_key(h['venue']), h['race_number']


def merged_recent(official, old_history, excluded, target_day):
    """Five latest distinct pre-day starts, with conservative conflict rejection."""
    merged = {}
    for h in old_history:
        if h['date'] >= target_day:
            raise ValueError('Future archived horse history')
        key = archive_key(h)
        if key in merged and merged[key] != h:
            raise ValueError('Conflicting archived race')
        merged[key] = {'date': h['date'], 'rank': h['rank'],
                       'dq': bool(h['dq']), 'status': h.get('status')}
    for h in official:
        if h['date'] >= target_day:
            raise ValueError('Future official horse history')
        key = official_key(h)
        record = {'date': h['date'], 'rank': h['rank'],
                  'dq': bool(h['disqualified']), 'status': h['arrival_status']}
        if key in merged:
            earlier = merged[key]
            if (earlier['rank'], earlier['dq']) != (record['rank'], record['dq']):
                raise ValueError('Archived and individual results disagree')
        else:
            merged[key] = record
    ordered = sorted(merged.items(), key=lambda pair: pair[0], reverse=True)
    # An unexplained excluded start among the latest five makes a history
    # feature unknowable; skipping it would artificially improve form.
    if len(ordered) < 5:
        return None, 'FEWER_THAN_FIVE_VERIFIED_STARTS'
    selected = ordered[:5]
    cutoff = selected[-1][0][0]
    if any(e['reason'] == 'unknown_outcome' and cutoff <= e['date'] < target_day for e in excluded):
        return None, 'UNRESOLVED_RECENT_OUTCOME'
    if len({key[0] for key, _ in selected}) < len(selected):
        return None, 'MULTIPLE_STARTS_SAME_DAY'
    return [v for _, v in selected], None


def tempered(p, temperature):
    power = {n: v ** (1.0 / temperature) for n, v in p.items()}
    total = sum(power.values())
    return {n: v / total for n, v in power.items()}


def replay(prediction_path, result_path=None):
    path = Path(prediction_path)
    frozen = json.loads(path.read_text())
    if frozen.get('primary_model') != 'available_history_v3' or frozen.get('status') != 'PRESTART_RESEARCH':
        raise ValueError('Expected archived prospective V3 prediction')
    start = datetime.fromisoformat(frozen['scheduled_start'])
    checked_prestart_stamp(frozen['predicted_at'], start)
    policy, temperature = verify_active()
    original = frozen['models']['available_history_v3']
    if original['model_sha256'] != policy['files_sha256'][policy['model_file']]:
        raise ValueError('Different frozen model')
    model = json.loads(Path(policy['model_file']).read_text())
    rows = copy.deepcopy(original['runners'])
    frame = {'runners': rows}
    original_recomputed = tempered(probabilities(frame, model), temperature)
    for n, old in original['probabilities'].items():
        if not math.isclose(original_recomputed[int(n)], old, abs_tol=1e-10, rel_tol=0):
            raise ValueError('Archived V3 probabilities cannot be reproduced')

    target = frozen['target_snapshot']
    day = target['date']
    if frozen['race_id'] != target['race_id']:
        raise ValueError('Race identity mismatch')
    participants = {p['numPmu']: p for p in target['participants']}
    v6 = {r['number']: r for r in frozen['models']['v6']['runners']}
    if set(participants) != {r['number'] for r in rows} or set(participants) != set(v6):
        raise ValueError('Participant mismatch')
    root = path.parent / 'individual_history_evidence'
    manifest = json.loads((root / 'manifest.json').read_text())
    audit = []
    for r in rows:
        n = r['number']
        if r['non_runner']:
            audit.append({'number': n, 'status': 'NON_RUNNER'})
            continue
        participant = participants[n]
        key = 'horse_' + str(n)
        meta = manifest.get(key)
        if not meta or meta.get('status') != 200:
            audit.append({'number': n, 'status': 'NO_PRESTART_SOURCE'})
            continue
        checked_prestart_stamp(meta['fetched_at_utc'], start)
        if not meta['file'].startswith(key + '.') or meta['file'] != key + '.json.gz':
            raise ValueError('Unexpected evidence path')
        url_horse = unquote(meta['url'].split('/program/')[-1].split('/light-performances')[0])
        if url_horse != participant.get('idCheval'):
            raise ValueError('Evidence horse identifier mismatch')
        blob = gzip.decompress((root / meta['file']).read_bytes())
        if hashlib.sha256(blob).hexdigest() != meta['sha256'] or len(blob) != meta['bytes_uncompressed']:
            raise ValueError('Individual history evidence hash mismatch')
        try:
            official, excluded = normalize_history(json.loads(blob), participant, day)
            candidate, reason = merged_recent(official, v6[n].get('history', []), excluded, day)
            if reason:
                audit.append({'number': n, 'status': reason,
                              'individual_prior_starts': len(official)})
                continue
            values = recent_values(candidate, day)
            old_values = r['features'][:5]
            changed = values != old_values
            if changed:
                r['features'][:5] = values
            audit.append({'number': n, 'status': 'UPDATED' if changed else 'UNCHANGED',
                          'old_recent5': old_values, 'candidate_recent5': values,
                          'individual_prior_starts': len(official)})
        except (ValueError, KeyError, TypeError) as error:
            audit.append({'number': n, 'status': 'ABSTAIN_CONFLICT',
                          'reason': str(error)})
    candidate_probs = tempered(probabilities(frame, model), temperature)
    if not math.isclose(sum(candidate_probs.values()), 1.0, abs_tol=1e-10):
        raise ValueError('Invalid candidate probabilities')
    changes = sum(r['status'] == 'UPDATED' for r in audit)
    old_top = sorted(original_recomputed, key=lambda n: (-original_recomputed[n], n))
    new_top = sorted(candidate_probs, key=lambda n: (-candidate_probs[n], n))
    report = {
        'race_id': frozen['race_id'],
        'status': 'RETROSPECTIVE_REPLAY_OF_ORIGINAL_PRESTART_EVIDENCE',
        'research_only': True,
        'is_independent_prospective_validation': False,
        'recommendations_allowed': False,
        'candidate': 'history_repair_shadow_v1_recent5_only',
        'frozen_v3_model_sha256': original['model_sha256'],
        'original_predicted_at': frozen['predicted_at'],
        'scheduled_start': frozen['scheduled_start'],
        'candidate_evidence_origin': 'Immutable original prestart individual_history_evidence',
        'source_prediction': str(path),
        'runners_changed_recent5': changes,
        'runner_audit': audit,
        'v3_baseline': {'probabilities': original_recomputed, 'top4': old_top[:4],
                        'top5': old_top[:5]},
        'candidate': 'history_repair_shadow_v1_recent5_only',
        'research_candidate': {'probabilities': candidate_probs, 'top4': new_top[:4],
                               'top5': new_top[:5]},
        'limitations': [
            'Reuses frozen V3 model coefficients and temperature, only patches first five recent form features.',
            'Elo, driver, trainer and 20-start DQ features remain archive-based.',
            'Individual API source might not contain all career starts; unresolved recent outcomes abstain.',
            'Prestart replay is not independent forward validation. No promotion or betting.'
        ]
    }
    if result_path:
        settled = json.loads(Path(result_path).read_text())
        if settled['race_id'] != frozen['race_id']:
            raise ValueError('Different race result file')
        finish = settled['result_reported_by_user_screenshot']
        if len(finish) < 5 or len(set(finish)) != len(finish):
            raise ValueError('Invalid reported finish')
        winner = finish[0]
        if winner not in candidate_probs:
            raise ValueError('Result not in runners')
        report['postrace_check'] = {
            'result_source': str(result_path),
            'result_status': settled.get('result_status', 'USER_REPORTED'),
            'winner': winner,
            'v3_winner_probability': original_recomputed[winner],
            'candidate_winner_probability': candidate_probs[winner],
            'v3_log_loss': -math.log(original_recomputed[winner]),
            'candidate_log_loss': -math.log(candidate_probs[winner]),
            'v3_top4_overlap': len(set(old_top[:4]) & set(finish[:4])),
            'candidate_top4_overlap': len(set(new_top[:4]) & set(finish[:4])),
            'v3_top5_overlap': len(set(old_top[:5]) & set(finish[:5])),
            'candidate_top5_overlap': len(set(new_top[:5]) & set(finish[:5])),
        }
    return report
