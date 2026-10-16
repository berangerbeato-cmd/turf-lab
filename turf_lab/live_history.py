"""Strictly verified historical inputs; frozen model fit data is never rewritten."""
import json
from pathlib import Path
from turf_lab.history_sync import audit, summarize


def load_available_history(today):
    states = audit(today)
    report = summarize(states, today)
    if report['status'] != 'OK':
        raise ValueError('HISTORY_STALE_OR_INCOMPLETE: '+str(report['missing_days'])+' days incomplete')
    policy = json.loads(Path('config/full_history_protocol.json').read_text())
    records = []
    for state in states:
        for race in state['records']:
            if race['date'][:7] in policy['excluded_months'] or race['race_id'] in policy['excluded_races']:
                continue
            # Preserve fitted-model eligibility without erasing official dead heats from the archive.
            winners = [p for p in race['participants'] if p.get('ordreArrivee') == 1]
            if len(winners) == 1: records.append(race)
    if len({r['race_id'] for r in records}) != len(records): raise ValueError('Duplicate history race')
    return records
