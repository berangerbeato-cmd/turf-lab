"""Departure geometry and past-only contextual performance residuals."""
import math
import re
from collections import defaultdict
from copy import deepcopy
from datetime import date,timedelta
from itertools import groupby
from turf_lab.opposition import is_dq

DEPARTURE_NAMES=['signed_handicap_25m','signed_handicap_distance_percent']
APTITUDE_NAMES=['venue_residual','log_venue_starts','distance_residual','log_distance_starts',
                'autostart_residual','log_autostart_starts']


def departure(course,runner):
    base=course.get('distance');own=runner.get('handicapDistance')
    if (not isinstance(base,(int,float)) or isinstance(base,bool) or base<=0
            or not isinstance(own,(int,float)) or isinstance(own,bool) or own<=0):
        return [None,None], 'missing_distance'
    delta=own-base
    if delta not in (-25,0,25,50):return [None,None], 'unvalidated_offset'
    if delta<0 and not re.search(r'avance\s+de\s+25\s*m',course.get('conditions',''),re.I):
        return [None,None], 'uncorroborated_advance'
    return [delta/25,100*delta/base], 'explicit_advance' if delta<0 else 'distance_difference'


def augment_context(races,records,lookback_days=60,prior_strength=5,distance_tolerance=250):
    if lookback_days<=0 or prior_strength<=0 or distance_tolerance<0:raise ValueError('Invalid context settings')
    sources={r['race_id']:r for r in records}
    if len(sources)!=len(records) or len({r['race_id'] for r in races})!=len(races):raise ValueError('Duplicate source race')
    history=defaultdict(list);out=[]
    for day,group in groupby(sorted(races,key=lambda r:(r['date'],r['race_id'])),key=lambda r:r['date']):
        batch=deepcopy(list(group));cutoff=(date.fromisoformat(day)-timedelta(days=lookback_days)).isoformat()
        for race in batch:
            raw=sources[race['race_id']];runners={p['numPmu']:p for p in raw['participants']}
            for r in race['runners']:
                r['departure_features'],r['departure_provenance']=departure(raw['course'],runners[r['number']])
                prior=[h for h in history[r['horse_id']] if cutoff<=h['day']<day]
                groups=[[h for h in prior if h['venue']==race['venue']],
                        [h for h in prior if isinstance(h['distance'],(int,float)) and isinstance(race['distance_m'],(int,float))
                         and abs(h['distance']-race['distance_m'])<=distance_tolerance],
                        [h for h in prior if h['start_type']=='AUTOSTART'] if race['start_type']=='AUTOSTART' else []]
                values=[]
                for rows in groups:
                    values += [sum(h['residual'] for h in rows)/(len(rows)+prior_strength) if rows else None,math.log1p(len(rows))]
                r['aptitude_features']=values
            out.append(race)
        # Update only after EVERY race's features for this day have been computed.
        for race in batch:
            classified=[r for r in race['runners'] if not r['non_runner'] and not is_dq(r)
                        and isinstance(r.get('rank'),int) and r['rank']>0]
            if len(classified)<2:continue
            for r in classified:
                residual=0
                for other in classified:
                    if other is r:continue
                    observed=1 if r['rank']<other['rank'] else 0.5 if r['rank']==other['rank'] else 0
                    # Relative Elo is already divided by the Elo scale; the common field mean cancels.
                    exponent=other['opposition_features'][0]-r['opposition_features'][0]
                    expected=1/(1+10**exponent)
                    residual+=(observed-expected)/(len(classified)-1)
                history[r['horse_id']].append({'day':day,'venue':race['venue'],'distance':race['distance_m'],
                    'start_type':race['start_type'],'residual':residual})
    return out


def candidate(races,name):
    if name not in ('v3','departure','aptitude','combined'):raise ValueError('Unknown candidate')
    rows=deepcopy(races)
    for race in rows:
        for r in race['runners']:
            r['features']+=r['opposition_features']
            if name in ('departure','combined'):r['features']+=r['departure_features']
            if name in ('aptitude','combined'):r['features']+=r['aptitude_features']
    return rows
