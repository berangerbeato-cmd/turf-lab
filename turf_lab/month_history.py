"""Features derived only from earlier collected race results, never pretty/odds."""
from collections import defaultdict
from itertools import groupby
from turf_lab.pilot import features


def identity(runner):
    parts = [runner.get(k) for k in ('nom', 'nomMere', 'nomPere')]
    if all(isinstance(x, str) and x.strip() for x in parts):
        return 'pedigree:' + repr(tuple(' '.join(x.upper().split()) for x in parts))
    if runner.get('idCheval'):
        return 'pmu:' + str(runner['idCheval'])
    raise ValueError('Missing reliable horse identity')


def build_history(records):
    """Do not infer unobserved starts; cold starts remain explicit missing values."""
    records = sorted(records, key=lambda r: (r['date'], r['race_id']))
    if len({r['race_id'] for r in records}) != len(records):
        raise ValueError('Duplicate source race')
    # Detect conflicting identities rather than mixing their performances.
    official = {}
    for race in records:
        keys = [identity(p) for p in race['participants']]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate horse identity in race')
        for p in race['participants']:
            if p.get('idCheval') and identity(p).startswith('pedigree:'):
                old = official.setdefault(str(p['idCheval']), identity(p))
                if old != identity(p):
                    raise ValueError('Conflicting official horse identity')
    history = defaultdict(list)
    result = []
    for day, races_on_day in groupby(records, key=lambda r: r['date']):
        batch = list(races_on_day)
        # All features for a day are computed BEFORE any of its results are added.
        for race in batch:
            normalized = {k: race[k] for k in ('date', 'race_id', 'venue', 'country', 'start_type', 'distance_m', 'scheduled_start_ms')}
            normalized.update(feature_cutoff=day, runners=[])
            for p in race['participants']:
                key = identity(p)
                prior = sorted(history[key], key=lambda h: (h['date'], h['race_id']), reverse=True)[:5]
                normalized['runners'].append({'number': p['numPmu'], 'name': p['nom'], 'horse_id': key,
                    'non_runner': p.get('statut') == 'NON_PARTANT',
                    'features': features(prior, day), 'history': prior,
                    'won': int(p.get('ordreArrivee') == 1), 'rank': p.get('ordreArrivee'), 'incident': p.get('incident')})
            result.append(normalized)
        for race in batch:
            for p in race['participants']:
                if p.get('statut') == 'NON_PARTANT':
                    continue
                incident = str(p.get('incident') or '')
                history[identity(p)].append({'date': day, 'race_id': race['race_id'],
                    'venue': race['venue'], 'distance_m': race['distance_m'],
                    'rank': p.get('ordreArrivee'), 'dq': incident.startswith('DISQUALIFIE') or incident == 'DISTANCE'})
    return result
