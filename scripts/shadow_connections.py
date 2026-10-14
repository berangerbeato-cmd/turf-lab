"""One bounded V3/V5 prospective batch. No fitting, betting or V1 changes."""
import argparse
import gzip
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.backtest_connections import PROTOCOL, verify_frozen
from scripts.backtest_extension import load_sources
from scripts.collect_month import collect, git_checkpoint, month_days
from turf_lab.coverage import cancelled_evidence, coverage_counts
from turf_lab.evidence import EvidenceStore, dump, races, start_type
from turf_lab.month_history import build_history, identity
from turf_lab.opposition import augment
from turf_lab.connections import augment_connections, candidate
from turf_lab.pilot import probabilities
from turf_lab.shadow_quarantine import apply_quarantine

CONFIG = Path('config/connections_v5_prospective.json')


def live_record(day, meeting, course, participants, now):
    start = datetime.fromtimestamp(course['heureDepart'] / 1000, timezone.utc)
    if start <= now or course.get('arriveeDefinitive') or course.get('ordreArrivee'):
        raise ValueError('Race started or results present')
    if start.astimezone(ZoneInfo('Europe/Paris')).date().isoformat() != day:
        raise ValueError('Start date mismatch')
    if not participants:
        raise ValueError('No participants')
    numbers, ids = set(), set()
    for p in participants:
        if p.get('statut') not in ('PARTANT', 'NON_PARTANT'):
            raise ValueError('Unknown runner status')
        if any(p.get(k) not in (None, '', []) for k in ('ordreArrivee', 'tempsObtenu', 'commentaireApresCourse', 'incident')):
            raise ValueError('Post-race fields present')
        number = p['numPmu']
        key = identity(p)
        if number in numbers or key in ids:
            raise ValueError('Duplicate runner')
        numbers.add(number)
        ids.add(key)
    if sum(p['statut'] == 'PARTANT' for p in participants) < 2:
        raise ValueError('Insufficient active runners')
    return {'date': day, 'race_id': f"{day}_R{meeting['numOfficiel']}C{course['numOrdre']}",
            'venue': meeting['hippodrome']['libelleCourt'], 'country': 'FRA',
            'start_type': start_type(course), 'distance_m': course['distance'],
            'scheduled_start_ms': course['heureDepart'], 'course': course, 'participants': participants}


def compute(history, target, p, models, selected):
    if any(r['date'] >= target['date'] for r in history):
        raise ValueError('History must precede target day')
    records = history + [target]
    rows = augment_connections(augment(build_history(records, lookback_days=p['lookback_days'])), records,
        window=p['connections_window_days'], strength=p['connections_prior_strength'],
        equipment_days=p['equipment_history_days'])
    row = next(r for r in rows if r['race_id'] == target['race_id'])
    result = {}
    for name in dict.fromkeys(['v3', selected]):
        frame = candidate([row], name)[0]
        probs = probabilities(frame, models[name])
        if abs(sum(probs.values()) - 1) > 1e-9:
            raise ValueError('Probabilities not normalized')
        result[name] = {'probabilities': probs, 'runners': frame['runners']}
    return result


def load_partial(month, through, minimum):
    manifest = json.loads(Path(f'data/month_{month}/manifest.json').read_text())
    expected = [d for d in month_days(month) if d <= through]
    if manifest['status'] not in ('COLLECTED', 'COLLECTED_WITH_GAPS') or [d['date'] for d in manifest['days']] != expected or any(d['status'] != 'OK' for d in manifest['days']):
        raise ValueError('Incomplete recent history')
    coverage = coverage_counts(manifest, cancelled_evidence(month, manifest['quarantine']))
    if coverage['fraction'] < minimum:
        raise ValueError('Recent history coverage failed')
    records = []
    for entry in manifest['partitions']:
        raw = gzip.decompress(Path(entry['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Recent history digest mismatch')
        record = json.loads(raw)
        if record['date'] not in expected:
            raise ValueError('Recent history out of bounds')
        records.append(record)
    return records, coverage


def write_status(state):
    dump('reports/connections_v5_prospective_status.json', state)
    if state.get('batch'):
        dump('reports/v5_shadow_runs/' + state['batch'] + '.json', state)


def record_failure(state, error):
    state.update(status='BLOCKED_NO_BET', reason=str(error),
        checked_at=datetime.now(timezone.utc).isoformat(),
        note='Current-attempt diagnostics retained; old captures remain immutable.')
    write_status(state)


def main(state=None, target_date=None):
    state = state if state is not None else {}
    state.update(batch=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'), saved=[], rejected=[])
    policy = json.loads(CONFIG.read_text())
    p = json.loads(PROTOCOL.read_text())
    frozen, models = verify_frozen(p)
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo('Europe/Paris')).date()
    # A one-shot snapshot for tomorrow, not a recurring or open-ended collector.
    day = target_date or (today + timedelta(days=1)).isoformat()
    if day not in (today.isoformat(), (today + timedelta(days=1)).isoformat()):
        raise ValueError('Only today or tomorrow can be captured')
    if not policy['prediction_from'] <= day <= policy['prediction_to']:
        raise ValueError('Outside bounded prospective window')
    history, coverage = load_sources({'months': policy['completed_months'],
        'minimum_retained_fraction_per_month': policy['minimum_coverage']})
    history, coverage, quarantines = apply_quarantine(history, coverage,
        policy.get('history_quarantine', []), policy['minimum_coverage'])
    state.update(coverage=coverage, history_quarantine=quarantines)
    through = (today - timedelta(days=1)).isoformat()
    if through[:7] != policy['partial_month']:
        raise ValueError('Recent history month outside authorization')
    root = Path('evidence/month_' + policy['partial_month'])
    output = Path('data/month_' + policy['partial_month'])
    store = EvidenceStore(root, max_requests=policy['max_history_requests'], delay=.5)
    report = collect(policy['partial_month'], store, output, lambda: git_checkpoint(root, output), through=through)
    if report['status'] == 'PAUSED_REQUEST_BUDGET':
        raise RuntimeError('History request budget reached; resume from checkpoint')
    recent, partial_coverage = load_partial(policy['partial_month'], through, policy['minimum_coverage'])
    history += recent
    source_sha = hashlib.sha256(json.dumps(history, sort_keys=True).encode()).hexdigest()
    batch = state['batch']
    evidence = EvidenceStore('evidence/v5_shadow/' + batch, max_requests=1 + policy['max_races'], delay=.5)
    programme = evidence.programme(day)
    if not isinstance(programme, dict):
        raise ValueError('Future programme unavailable')
    eligible = sorted(races(programme), key=lambda rc: (rc[1]['heureDepart'], rc[0]['numOfficiel'], rc[1]['numOrdre']))
    saved, rejected = state['saved'], state['rejected']
    if target_date:
        fixed = json.loads(Path('config/v5_followup.json').read_text())['race_ids']
        selected_races = [(m, c) for m, c in eligible if f"{day}_R{m['numOfficiel']}C{c['numOrdre']}" in fixed]
        found = {f"{day}_R{m['numOfficiel']}C{c['numOrdre']}" for m,c in selected_races}
        rejected.extend({'race_id': rid, 'reason': 'predeclared_race_missing_from_programme'} for rid in fixed if rid.startswith(day) and rid not in found)
    else:
        selected_races = eligible[:policy['max_races']]
    for meeting, course in selected_races:
        rid = f"{day}_R{meeting['numOfficiel']}C{course['numOrdre']}"
        try:
            raw = evidence.race(day, meeting['numOfficiel'], course['numOrdre'], 'participants')
            target = live_record(day, meeting, course, (raw or {}).get('participants'), datetime.now(timezone.utc))
            prediction = compute(history, target, p, models, frozen['selected'])
            calculated = datetime.now(timezone.utc)
            if calculated.timestamp() * 1000 >= course['heureDepart']:
                raise ValueError('Start passed during computation')
            path = Path('predictions_v5') / day / (rid + '_' + batch) / 'prediction.json'
            dump(path, {'status': 'SHADOW_NO_BET', 'race_id': rid, 'date': day,
                'scheduled_start': datetime.fromtimestamp(course['heureDepart']/1000, timezone.utc).isoformat(),
                'predicted_at': calculated.isoformat(), 'history_through': through,
                'history_gap_days': (date.fromisoformat(day)-date.fromisoformat(through)).days-1,
                'history_gap_note': 'Same-day results excluded; current field can still change before departure.',
                'history_sha256': source_sha, 'frozen': frozen, 'models': prediction,
                'history_quarantine': quarantines,
                'target_snapshot': target, 'evidence_manifest': str(evidence.manifest_path),
                'capture_code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'policy_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
                'requires_runner_recheck': True, 'v1_changed': False})
            saved.append(str(path))
            # Separate sidecar: V6 failure cannot erase a valid V5 capture.
            from scripts.shadow_v6 import capture as capture_v6
            try:
                state.setdefault('v6_saved', []).append(capture_v6(history, path))
            except (ValueError, RuntimeError, FileNotFoundError, KeyError, TypeError) as error:
                state.setdefault('v6_rejected', []).append({'race_id': rid, 'reason': str(error)})
        except (ValueError, KeyError, TypeError) as error:
            rejected.append({'race_id': rid, 'reason': str(error)})
            print(json.dumps(rejected[-1]), flush=True)
    state.update({'status': 'CAPTURED_NO_BET' if saved else 'NO_VALID_CAPTURE',
        'batch': batch, 'date': day, 'history_through': through, 'saved': saved, 'rejected': rejected,
        'coverage': coverage, 'partial_coverage': partial_coverage,
        'selection': 'First six French harness races by scheduled start; no replacement of rejected races; not representative of all courses.'})
    write_status(state)
    if not saved:
        raise ValueError('No valid prospective capture')
    print(json.dumps({'captured': len(saved), 'rejected': rejected, 'day': day}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date')
    args = parser.parse_args()
    state = {}
    try:
        main(state, args.date)
    except (ValueError, RuntimeError, FileNotFoundError, KeyError, TypeError) as error:
        record_failure(state, error)
        raise
