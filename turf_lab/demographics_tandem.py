"""Exploratory V6 features, separate from frozen V5."""
import math
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from itertools import groupby
from turf_lab.opposition import is_dq
from turf_lab.connections import candidate as v5_candidate


def augment(rows, records, window=60, strength=20):
    if window <= 0 or strength <= 0:
        raise ValueError('Invalid tandem parameters')
    sources = {r['race_id']: {p['numPmu']: p for p in r['participants']} for r in records}
    pairs = defaultdict(list)
    population = []
    output = []
    for day, items in groupby(sorted(rows, key=lambda r: (r['date'], r['race_id'])), key=lambda r: r['date']):
        batch = deepcopy(list(items))
        cutoff = (date.fromisoformat(day)-timedelta(days=window)).isoformat()
        population = [e for e in population if e['day'] >= cutoff]
        known = [e['dq'] for e in population if e['dq'] is not None]
        prior = sum(known)/len(known) if known else .2
        for race in batch:
            for r in race['runners']:
                p = sources[race['race_id']][r['number']]
                age = p.get('age')
                age = age if isinstance(age, int) and not isinstance(age, bool) and 2 <= age <= 20 else None
                sex = p.get('sexe')
                r['age_sex_features'] = [age, age*age if age is not None else None] + [float(sex == s) if sex in ('MALES', 'FEMELLES', 'HONGRES') else None for s in ('MALES', 'FEMELLES', 'HONGRES')]
                driver = r['connection_entities']['driver']
                events = [e for e in pairs[(r['horse_id'], driver)] if cutoff <= e['day'] < day] if driver else []
                residuals = [e['residual'] for e in events if e['residual'] is not None]
                dq = [e['dq'] for e in events if e['dq'] is not None]
                r['tandem_features'] = [sum(residuals)/(len(residuals)+strength) if residuals else None,
                    math.log1p(len(residuals)), (sum(dq)+strength*prior)/(len(dq)+strength) if driver else None,
                    math.log1p(len(dq))]
            output.append(race)
        for race in batch:
            active = [r for r in race['runners'] if not r['non_runner']]
            classified = [r for r in active if not is_dq(r) and isinstance(r.get('rank'), int) and r['rank'] > 0]
            for r in active:
                residual = None
                if r in classified and len(classified) > 1:
                    residual = sum((1 if r['rank'] < q['rank'] else .5 if r['rank'] == q['rank'] else 0)
                        - 1/(1+10**(q['opposition_features'][0]-r['opposition_features'][0]))
                        for q in classified if q is not r)/(len(classified)-1)
                event = {'day': day, 'residual': residual,
                         'dq': True if is_dq(r) else False if isinstance(r.get('rank'), int) and r['rank'] > 0 else None}
                population.append(event)
                driver = r['connection_entities']['driver']
                if driver:
                    pairs[(r['horse_id'], driver)].append(event)
    return output


def candidate(rows, name):
    if name not in ('v5', 'age_sex', 'tandem', 'combined'):
        raise ValueError('Unknown V6 candidate')
    result = v5_candidate(rows, 'combined')
    for race in result:
        for r in race['runners']:
            if name in ('age_sex', 'combined'):
                r['features'] += r['age_sex_features']
            if name in ('tandem', 'combined'):
                r['features'] += r['tandem_features']
    return result
