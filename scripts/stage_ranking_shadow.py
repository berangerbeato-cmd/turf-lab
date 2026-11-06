"""Collect paired, frozen prestart Top4/Top5 forecasts and score verified finishes."""
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

import numpy as np

from scripts.predict_operational import classic_frame, load_history
from scripts.shadow_connections import live_record
from scripts.train_stage_ranking_v2 import features, transform
from turf_lab.available_history_operational import compute, verify_active
from turf_lab.evidence import EvidenceStore, dump, races
from turf_lab.history_sync import History
from turf_lab.month_history import identity
from turf_lab.ranking_research import finish
from turf_lab.stage_ranking import greedy, strengths, unordered

ROOT = Path('reports/stage_ranking_shadow')
MODEL = Path('models/stage_ranking_v2/model.json')
LOCK = MODEL.with_name('frozen_before_test.json')
BEGIN = date(2026, 11, 6)
END = date(2027, 3, 6)
MAX_RACES = 8
PARIS = ZoneInfo('Europe/Paris')
BINS = (0, .005, .01, .02, .04, .08, .16, 1)


def now():
    return datetime.now(timezone.utc)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen():
    lock = json.loads(LOCK.read_text())
    if lock['model_sha256'] != 'a4a46232c8d06740eeb062049155e311baa25dd2f17a8880f24057ce7850679d':
        raise ValueError('Unexpected stage model')
    checks = {
        **lock['code_sha256'],
        str(MODEL): lock['model_sha256'],
        'config/active_model.json': lock['active_policy_sha256'],
        'config/stage_ranking_v2.json': lock['protocol_sha256'],
    }
    for path, expected in checks.items():
        if digest(path) != expected:
            raise ValueError('Frozen dependency changed: ' + path)
    policy, _ = verify_active()
    return json.loads(MODEL.read_text()), {
        'v3': digest(policy['model_file']),
        'stage': lock['model_sha256'],
    }


def field(participants):
    return sorted([p['numPmu'], identity(p), p['statut']] for p in participants)


def predict(v3, model):
    from turf_lab.pilot import active

    row = {'runners': v3['runners']}
    numbers = [p['number'] for p in active(row)]
    if len(numbers) < 6:
        raise ValueError('Fewer than six starters')
    x = transform(features(row), np.asarray(model['mean']), np.asarray(model['scale']))
    score = np.asarray(model['coefficients']) @ x.T
    baseline = np.tile(np.log([v3['probabilities'][n] for n in numbers]), (5, 1))
    distributions = {
        'v3': strengths(baseline, [1] * 5),
        'stage_raw': strengths(score, [1] * 5),
        'stage_calibrated': strengths(score, model['temperatures']),
    }
    results = {}
    for k in (4, 5):
        selections = {name: greedy(distributions[name], k) for name in ('v3', 'stage_raw')}
        results[str(k)] = {
            selector: {
                'selection': [numbers[i] for i in chosen],
                'probabilities': {name: unordered(w, chosen) for name, w in distributions.items()},
            }
            for selector, chosen in selections.items()
        }
    return results


def capture(today, model, hashes):
    day = today.isoformat()
    folder = ROOT / 'forecasts' / day
    existing = list(folder.glob('*.json'))
    if len(existing) >= MAX_RACES:
        return
    with TemporaryDirectory() as tmp:
        store = EvidenceStore(Path(tmp), max_requests=1 + MAX_RACES)
        programme = store.programme(day)
        if not programme:
            raise RuntimeError('Programme unavailable')
        candidates = sorted(races(programme), key=lambda pair: pair[1]['heureDepart'])
        candidates = [
            (meeting, course) for meeting, course in candidates
            if course['heureDepart'] / 1000 >= now().timestamp() + 1200
            and not (folder / f"R{meeting['numOfficiel']}C{course['numOrdre']}.json").exists()
        ][:MAX_RACES - len(existing)]
        if not candidates:
            print('No eligible upcoming races')
            return
        history, coverage = load_history(today, day)
        policy = json.loads(Path('config/full_history_protocol.json').read_text())
        history = [r for r in history if r['date'][:7] not in policy['excluded_months']]
        history_hash = hashlib.sha256(json.dumps(history, sort_keys=True).encode()).hexdigest()
        for meeting, course in candidates:
            reunion, number = meeting['numOfficiel'], course['numOrdre']
            start = datetime.fromtimestamp(course['heureDepart'] / 1000, timezone.utc)
            if now() >= start:
                continue
            response = store.race(day, reunion, number, 'participants')
            captured = now()
            try:
                target = live_record(day, meeting, course, (response or {}).get('participants'), captured)
            except ValueError as error:
                print(f'R{reunion}C{number}: {error}')
                continue
            participants = target['participants']
            if sum(p['statut'] == 'PARTANT' for p in participants) < 6:
                continue
            records = history + [target]
            row = classic_frame(records, target['race_id'])
            v3, _ = compute(records, row)
            combinations = predict(v3, model)
            finished = now()
            if finished >= start:
                continue
            dump(folder / f'R{reunion}C{number}.json', {
                'race_id': target['race_id'], 'date': day, 'status': 'PRESTART_SHADOW',
                'captured_at': captured.isoformat(), 'predicted_at': finished.isoformat(),
                'scheduled_start': start.isoformat(), 'field': field(participants),
                'models': hashes, 'history_sha256': history_hash,
                'history_through': coverage['last_collected_day'],
                'combinations': combinations,
            })
            print('Captured', target['race_id'], flush=True)


def metrics(rows):
    return {
        'n': len(rows), 'observed': sum(y for p, y in rows),
        'expected': sum(p for p, y in rows),
        'brier': sum((p-y)**2 for p, y in rows) / len(rows),
    }


def settle(hashes, today):
    history = History()
    rows = defaultdict(list)
    coverage = defaultdict(list)
    cached = {}
    for path in sorted((ROOT / 'forecasts').glob('*/*.json')):
        forecast = json.loads(path.read_text())
        day, rid = forecast['date'], forecast['race_id']
        predicted = datetime.fromisoformat(forecast['predicted_at'])
        start = datetime.fromisoformat(forecast['scheduled_start'])
        if forecast['models'] != hashes or forecast['status'] != 'PRESTART_SHADOW' or predicted >= start:
            coverage['invalid'].append(rid)
            continue
        if day not in cached:
            official = history.day(day)
            cached[day] = ({r['race_id']: r for r in official['records']}, official['cancellations'])
        results, cancelled = cached[day]
        if rid in cancelled:
            coverage['cancelled'].append(rid)
            continue
        actual = results.get(rid)
        if actual is None:
            coverage['pending'].append(rid)
            continue
        if predicted.timestamp() * 1000 >= actual['scheduled_start_ms'] or forecast['field'] != field(actual['participants']):
            coverage['late_or_field_changed'].append(rid)
            continue
        truth = finish(actual['participants'])
        if truth is None:
            coverage['ambiguous_top_five'].append(rid)
            continue
        coverage['scored'].append(rid)
        for k, selections in forecast['combinations'].items():
            for selector, event in selections.items():
                hit = int(set(event['selection']) == set(truth[:int(k)]))
                for name, p in event['probabilities'].items():
                    rows[k, selector, name].append((p, hit))
    summary = {}
    for (k, selector, name), values in sorted(rows.items()):
        bins = []
        for lo, hi in zip(BINS, BINS[1:]):
            group = [(p, y) for p, y in values if lo <= p < hi or p == hi == 1]
            if group:
                bins.append({'range': [lo, hi], **metrics(group)})
        summary.setdefault(k, {}).setdefault(selector, {})[name] = {
            **metrics(values), 'calibration': bins,
        }
    dump(ROOT / 'scores.json', {
        'as_of_paris': today.isoformat(), 'scope': 'Research only. Exact unordered Top4 and Top5',
        'models': hashes, 'summary': summary, 'coverage': dict(coverage),
    })


def main():
    today = now().astimezone(PARIS).date()
    model, hashes = frozen()
    if BEGIN <= today < END:
        try:
            capture(today, model, hashes)
        finally:
            settle(hashes, today)
    elif today >= END:
        settle(hashes, today)


if __name__ == '__main__':
    main()
