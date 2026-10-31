"""Isolated offline ablations; frozen operational feature builders stay unchanged."""
from collections import defaultdict, deque
from datetime import date, timedelta
from itertools import groupby
from copy import deepcopy
from turf_lab.month_history import identity
from turf_lab.pilot import features


def recent_values(history, day):
    values = features(history, day)
    if any(h['rank'] is None and not h['status'] for h in history):
        values[1] = None
    return values


def available_features(records, frames, strength=10):
    targets = {r['race_id']: r for r in frames}
    if len(targets) != len(frames) or len({r['race_id'] for r in records}) != len(records):
        raise ValueError('Duplicate race')
    if not targets.keys() <= {r['race_id'] for r in records}:
        raise ValueError('Missing source race')
    history = defaultdict(lambda: deque(maxlen=20))
    faults = defaultdict(lambda: deque(maxlen=20))
    total = dq = 0
    output = {}
    audit = dict(races=len(frames), active_runners=0, changed_recent_vectors=0,
                 history_empty_at_60_days_but_available=0, missing_both=0)
    for day, group in groupby(sorted(records, key=lambda r:(r['date'],r['race_id'])), key=lambda r:r['date']):
        batch = list(group)
        for race in batch:
            if race['race_id'] not in targets:
                continue
            row = deepcopy(targets[race['race_id']])
            source = {p['numPmu']: p for p in race['participants']}
            if len(source) != len(race['participants']) or set(source) != {r['number'] for r in row['runners']}:
                raise ValueError('Runner mismatch')
            for runner in row['runners']:
                p = source[runner['number']]
                key = identity(p)
                if (runner['horse_id'] != key or runner['won'] != int(p.get('ordreArrivee') == 1)
                        or runner['non_runner'] != (p.get('statut') == 'NON_PARTANT')):
                    raise ValueError('Target/source mismatch')
                prior = list(reversed(history[key]))
                cutoff = (date.fromisoformat(day)-timedelta(days=60)).isoformat()
                old = recent_values([h for h in prior if h['date'] >= cutoff][:5], day)
                if old != runner['features'][:5]:
                    raise ValueError('Frozen history reproduction mismatch: '+race['race_id'])
                new = recent_values(prior[:5], day)
                runner['available_recent'] = new
                known = list(faults[key]); trailing = 0
                for value in reversed(known):
                    if not value: break
                    trailing += 1
                runner['dq20_features'] = [(sum(known)+strength*(dq/total if total else .2))/(len(known)+strength),
                                           len(known)/20, float(known[-1]) if known else None, trailing/20]
                if not runner['non_runner']:
                    audit['active_runners'] += 1
                    audit['changed_recent_vectors'] += old != new
                    audit['history_empty_at_60_days_but_available'] += old[4] == 0 and new[4] > 0
                    audit['missing_both'] += new[4] == 0
            output[row['race_id']] = row
        # Never let any result from the target day enter its features.
        for race in batch:
            for p in race['participants']:
                if p.get('statut') == 'NON_PARTANT': continue
                key = identity(p); incident = str(p.get('incident') or '')
                fault = incident.startswith('DISQUALIFIE') or incident == 'DISTANCE'
                rank = p.get('ordreArrivee')
                history[key].append(dict(date=day, rank=rank, status=incident, dq=fault))
                if fault or isinstance(rank, int) and rank > 0:
                    faults[key].append(int(fault)); total += 1; dq += int(fault)
    return [output[r['race_id']] for r in frames], audit


def variant(rows, name):
    if name not in ('classic_recalibrated','last5_available','last5_available_dq20'):
        raise ValueError('Unknown variant')
    result = []
    for row in rows:
        runners = []
        for runner in row['runners']:
            r = {k:v for k,v in runner.items() if k not in ('available_recent','dq20_features')}
            r['features'] = list(runner['features'])
            if name != 'classic_recalibrated': r['features'][:5] = runner['available_recent']
            if name.endswith('dq20'): r['features'] += runner['dq20_features']
            runners.append(r)
        result.append(dict(row, runners=runners))
    return result


def calibrate_temperature(rows, predictions):
    import numpy as np
    from scipy.optimize import minimize_scalar
    from scipy.special import logsumexp
    if not rows or len(rows) != len(predictions): raise ValueError('Invalid calibration data')
    logs=[]; winners=[]
    for row,p in zip(rows,predictions):
        active=[r for r in row['runners'] if not r['non_runner']]
        if sum(r['won'] for r in active)!=1: raise ValueError('Single winner required')
        logs.append(np.log([max(1e-15,p[r['number']]) for r in active]))
        winners.append(next(i for i,r in enumerate(active) if r['won']))
    def objective(t):
        return float(np.mean([logsumexp(x/t)-x[w]/t for x,w in zip(logs,winners)]))
    fit=minimize_scalar(objective,bounds=(.5,3),method='bounded')
    if not fit.success: raise ValueError('Calibration failed')
    return float(fit.x)
