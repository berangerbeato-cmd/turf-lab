"""One bounded polling tick; the workflow supplies the resident minute loop."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.capture_pmu_quotes import validate, window
from scripts.prospective_cohort import verify
from scripts.backtest_connections import digest
from turf_lab.evidence import EvidenceStore, dump

POLICY = Path('config/pmu_quotes_cohort.json')


def authorized(now, policy):
    day = now.astimezone(ZoneInfo('Europe/Paris')).date().isoformat()
    return policy['from'] <= day <= policy['through']


def due(now, start, state, policy):
    if state.get('status') == 'CAPTURED' or not window(now, start, policy):
        return False
    if state.get('attempts', 0) >= policy['maximum_attempts_per_race']:
        return False
    previous = state.get('last_attempt')
    return previous is None or (now-datetime.fromisoformat(previous)).total_seconds() >= policy['retry_seconds']


def main():
    policy = json.loads(POLICY.read_text())
    now = datetime.now(timezone.utc)
    if not authorized(now, policy):
        print('Outside authorized dates; no PMU requests')
        return
    _, lock = verify()
    day = now.astimezone(ZoneInfo('Europe/Paris')).date().isoformat()
    folder = Path('predictions_cohort')/day
    plan_path = folder/'plan.json'
    if not plan_path.exists():
        print('WAITING: no frozen cohort plan yet', flush=True)
        return
    plan = json.loads(plan_path.read_text())
    if plan['frozen'] != lock or plan['date'] != day:
        raise ValueError('Plan freeze or date mismatch')
    ids = [f"{day}_R{m['numOfficiel']}C{c['numOrdre']}" for m,c in plan['selection']]
    if len(ids) != len(set(ids)) or len(ids) > policy['max_races_per_day']:
        raise ValueError('Invalid bounded selection')
    for rid in ids:
        now = datetime.now(timezone.utc)
        state_path = Path('reports/pmu_cohort')/day/(rid+'.json')
        output = Path('quotes_pmu/cohort')/day/(rid+'.json')
        state = json.loads(state_path.read_text()) if state_path.exists() else {'race_id':rid, 'attempts':0}
        if output.exists():
            # A saved quote is immutable, even on restart or a later market move.
            if state.get('status') != 'CAPTURED':
                dump(state_path, dict(state, status='CAPTURED', path=str(output)))
            continue
        source = folder/(rid+'.json')
        if not source.exists():
            print('WAITING_FORECAST', rid, flush=True)
            continue
        prediction = json.loads(source.read_text())
        if prediction['frozen'] != lock or prediction['race_id'] != rid:
            raise ValueError('Forecast freeze or identity mismatch')
        if prediction['status'] != 'SHADOW_NO_BET':
            if state.get('status') != 'BLOCKED_FORECAST':
                dump(state_path, dict(state, status='BLOCKED_FORECAST', reason=prediction.get('reason')))
            continue
        start = datetime.fromisoformat(prediction['scheduled_start'])
        if datetime.fromisoformat(prediction['predicted_at']) >= start:
            raise ValueError('Forecast was not captured before departure')
        if not due(now, start, state, policy):
            if (start-now).total_seconds() < policy['minimum_minutes_before_start']*60:
                if state.get('status') not in ('MISSED_WINDOW','REJECTED_FINAL'):
                    dump(state_path, dict(state, status='REJECTED_FINAL' if state['attempts'] else 'MISSED_WINDOW'))
            continue
        batch = now.strftime('%Y%m%dT%H%M%S%fZ')
        state.update(status='ATTEMPTING', attempts=state['attempts']+1, last_attempt=now.isoformat())
        dump(state_path, state)
        store = EvidenceStore('evidence/pmu_cohort/'+batch, max_requests=2, delay=.5)
        _, rn, cn = re.fullmatch(r'(\d{4}-\d{2}-\d{2})_R(\d+)C(\d+)', rid).groups()
        try:
            detail = store.race(day, int(rn), int(cn), '')
            raw = store.race(day, int(rn), int(cn), 'participants')
            if not isinstance(detail, dict) or not isinstance(raw, dict):
                raise ValueError('Response unavailable')
            checked = datetime.now(timezone.utc)
            result = validate(prediction, detail, raw.get('participants'), checked, policy)
            dump(output, dict(result, race_id=rid, status='INDICATIVE_QUOTES_NO_BET',
                captured_at=checked.isoformat(), prediction_path=str(source), prediction_sha256=digest(source),
                policy_sha256=digest(POLICY), code_sha256=digest(__file__),
                validator_sha256=digest('scripts/capture_pmu_quotes.py'), evidence_manifest=str(store.manifest_path)))
            state.update(status='CAPTURED', path=str(output))
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            state.update(status='REJECTED', reason=str(error))
        dump(state_path, state)
        print(json.dumps(state), flush=True)


if __name__ == '__main__':
    main()
