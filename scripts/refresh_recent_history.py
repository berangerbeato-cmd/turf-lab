"""Daily French harness results, separate from frozen research datasets/models."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from turf_lab.evidence import EvidenceStore, dump, races, start_type
from turf_lab.quality import assess

FIRST_DAY = date(2026, 10, 14)
ROOT = Path('data/recent_history')


def required_days(today):
    return [(FIRST_DAY + timedelta(days=i)).isoformat() for i in range(max(0, (today-FIRST_DAY).days))]


def read_day(day):
    path = ROOT / (day + '.json')
    if not path.exists(): return None
    value = json.loads(path.read_text())
    if value['date'] != day: raise ValueError('Wrong history date')
    records = value['records']
    raw = json.dumps(records, sort_keys=True, ensure_ascii=False).encode()
    if hashlib.sha256(raw).hexdigest() != value['records_sha256']: raise ValueError('Daily history checksum mismatch')
    if any(r['date'] != day for r in records): raise ValueError('Wrong record date')
    if len({r['race_id'] for r in records}) != len(records): raise ValueError('Duplicate daily race')
    return value


def refresh_day(day):
    previous = read_day(day)
    if previous and previous['status'] == 'COMPLETE': return previous
    batch = datetime.now().strftime('%Y%m%dT%H%M%S%f')
    base = Path('evidence/recent_history') / day / batch
    store = EvidenceStore(base / 'programme', max_requests=1)
    programme = store.programme(day)
    body = programme.get('programme', programme) if isinstance(programme, dict) else None
    if not isinstance(body, dict) or not isinstance(body.get('reunions'), list):
        raise ValueError('Programme unavailable: ' + day)
    candidates = list(races(programme))
    def fetch(item):
        meeting, course = item
        rn, cn = meeting['numOfficiel'], course['numOrdre']
        rid = f'{day}_R{rn}C{cn}'
        s = EvidenceStore(base / rid, max_requests=2)
        participants = s.race(day, rn, cn, 'participants')
        detail = s.race(day, rn, cn, '')
        if not isinstance(detail, dict) or not isinstance(participants, dict):
            return None, dict(race_id=rid, reason='missing_response')
        if detail.get('statut') == 'COURSE_ANNULEE' or detail.get('categorieStatut') == 'ANNULEE':
            return None, dict(race_id=rid, reason='cancelled', resolved=True)
        if not (detail.get('arriveeDefinitive') or detail.get('isArriveeDefinitive')):
            return None, dict(race_id=rid, reason='arrival_not_final')
        record = dict(date=day, race_id=rid, reunion=rn, course_number=cn,
            venue=meeting['hippodrome']['libelleCourt'], country='FRA', start_type=start_type(course),
            distance_m=course['distance'], scheduled_start_ms=course['heureDepart'],
            course=course, participants=participants.get('participants', []), detail=detail)
        diagnostic = assess([record])
        if diagnostic['issues'] or diagnostic['counts'].get('single_winner_races') != 1:
            return None, dict(race_id=rid, reason='quality', issues=diagnostic['issues'])
        return record, None
    records, exclusions = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for record, exclusion in pool.map(fetch, candidates):
            if record: records.append(record)
            if exclusion: exclusions.append(exclusion)
    records.sort(key=lambda r:r['race_id'])
    raw = json.dumps(records, sort_keys=True, ensure_ascii=False).encode()
    result = dict(date=day, status='INCOMPLETE' if any(not e.get('resolved') for e in exclusions) else 'COMPLETE',
        candidates=len(candidates), records=records, exclusions=exclusions,
        records_sha256=hashlib.sha256(raw).hexdigest(), evidence_root=str(base))
    dump(ROOT / (day+'.json'), result)
    return result


def require_fresh(today):
    values = [read_day(day) for day in required_days(today)]
    if any(v is None or v['status'] != 'COMPLETE' for v in values):
        raise ValueError('HISTORY_STALE_OR_INCOMPLETE: daily results must be complete through yesterday')
    return [r for v in values for r in v['records']]


def main():
    # Keep the existing command as a compatibility entrypoint for the strict full calendar sync.
    from scripts.sync_history import main as sync
    sync()


if __name__ == '__main__': main()
