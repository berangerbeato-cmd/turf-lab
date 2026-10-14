"""Past-only contextual pace proxy; not a causal correction for track conditions."""
import math
from collections import defaultdict, Counter
from copy import deepcopy
from datetime import date, timedelta
from itertools import groupby
from statistics import median
from turf_lab.month_history import identity
from turf_lab.opposition import is_dq
from turf_lab.demographics_tandem import candidate as v6_candidate


def positive(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def pace(p, race, policy):
    if p.get('statut') != 'PARTANT' or is_dq(p):
        return None
    rank = p.get('ordreArrivee')
    if not isinstance(rank, int) or isinstance(rank, bool) or rank <= 0:
        return None
    value, elapsed = p.get('reductionKilometrique'), p.get('tempsObtenu')
    distance = p.get('handicapDistance') or race.get('distance_m')
    if not all(positive(x) for x in (value, elapsed, distance)):
        return None
    if not policy['pace_min'] <= value <= policy['pace_max']:
        return None
    if abs(value/(elapsed*1000/distance)-1) > policy['joint_time_distance_tolerance']:
        return None
    return value


def augment(rows, records, policy):
    sources = {r['race_id']: r for r in records}
    history = defaultdict(list)
    groups = defaultdict(list)
    global_paces = []
    year = None
    output, counts = [], Counter()
    for day, items in groupby(sorted(rows, key=lambda r: (r['date'], r['race_id'])), key=lambda r: r['date']):
        if year != day[:4]:
            history.clear()
            groups.clear()
            global_paces.clear()
            year = day[:4]
        cutoff = (date.fromisoformat(day)-timedelta(days=policy['history_days'])).isoformat()
        batch = deepcopy(list(items))
        updates = []
        for row in batch:
            raw = sources[row['race_id']]
            if raw['date'] != day:
                raise ValueError('Speed source date mismatch')
            for runner in row['runners']:
                prior = [x for x in history[runner['horse_id']] if cutoff <= x[0] < day][-policy['last_starts']:]
                runner['speed_features'] = [median(x[1] for x in prior) if prior else None]
                runner['speed_history_count'] = len(prior)
                if not runner['non_runner']:
                    counts['active'] += 1
                    counts['with_speed'] += bool(prior)
            distance = raw.get('distance_m')
            if not positive(distance):
                continue
            key = (raw.get('venue'), int(distance)//policy['distance_bucket_metres'], raw.get('start_type'))
            valid = [(p, pace(p, raw, policy)) for p in raw['participants']]
            valid = [(p,v) for p,v in valid if v is not None]
            if len(valid) < policy['minimum_timed_per_race']:
                counts['race_insufficient_times'] += 1
                continue
            expected = None
            if len(global_paces) >= policy['minimum_context_races']:
                prior = sum(global_paces)/len(global_paces)
                local = groups[key]
                strength = policy['context_prior_strength']
                expected = (sum(local)+strength*prior)/(len(local)+strength)
                counts['race_context_available'] += 1
            updates.append((key, median(v for _,v in valid), valid, expected))
        output.extend(batch)
        # Every feature above is emitted before any result from this day is ingested.
        for key, race_median, valid, expected in updates:
            if expected is not None:
                for p,v in valid:
                    history[identity(p)].append((day, (expected-v)/1000))
            groups[key].append(race_median)
            global_paces.append(race_median)
    return output, dict(counts)


def candidate(rows, name):
    if name not in ('v6', 'v7_speed'):
        raise ValueError('Unknown speed candidate')
    frames = v6_candidate(rows, 'combined')
    if name == 'v7_speed':
        for r in frames:
            for p in r['runners']:
                p['features'] += p['speed_features']
    return frames
