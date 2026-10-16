"""Strictly verified historical inputs; frozen model fit data is never rewritten."""
import json
from pathlib import Path
from turf_lab.history_sync import audit, summarize
from turf_lab.evidence import dump


def check_prediction_history(states, today, accepted_dates):
    from datetime import timedelta
    # Exceptions never waive yesterday's freshness, even if misconfigured.
    yesterday = (today-timedelta(days=1)).isoformat()
    if not any(s['date'] == yesterday and s['status'] == 'OK' for s in states):
        raise ValueError('HISTORY_STALE_OR_INCOMPLETE: yesterday is not complete')
    blocking = [s['date'] for s in states if s['status'] != 'OK' and s['date'] not in accepted_dates]
    if blocking:
        raise ValueError('HISTORY_STALE_OR_INCOMPLETE: unapproved gaps '+str(blocking))
    return [s['date'] for s in states if s['status'] != 'OK']


def load_available_history(today):
    states = audit(today)
    report = summarize(states, today)
    exceptions = json.loads(Path('config/history_prediction_exceptions.json').read_text())
    warnings = check_prediction_history(states, today, exceptions['dates'])
    dump('reports/live/prediction_history_status.json', dict(
        history_status=report['status'], prediction_inputs_status='READY_WITH_DOCUMENTED_GAPS' if warnings else 'READY',
        required_through=report['required_through'], accepted_incomplete_dates=warnings,
        verified_races=report['verified_races']))
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
