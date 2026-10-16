"""Strict calendar coverage, immutable legacy inputs and incremental daily overlays."""
import gzip
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from turf_lab.evidence import EvidenceStore, dump, races, start_type
from turf_lab.quality import assess

START = date(2022, 1, 1)
OVERLAYS = Path('data/history_updates')


def days_until(today):
    return [(START + timedelta(days=i)).isoformat() for i in range((today-START).days)]


def cancelled(detail):
    return (isinstance(detail, dict) and detail.get('statut') == 'COURSE_ANNULEE'
            and detail.get('categorieStatut') == 'ANNULEE' and not detail.get('ordreArrivee')
            and not detail.get('arriveeDefinitive'))


def validate(record):
    try:
        diag = assess([record])
        if not record['participants'] or diag['issues']:
            return diag['issues'] or ['empty_participants']
        if not (diag['counts'].get('single_winner_races') or diag['counts'].get('dead_heat_races')):
            return ['missing_winner']
        return []
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        return [str(error)]


def read_gzip(path, digest):
    raw = gzip.decompress(Path(path).read_bytes())
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Checksum mismatch: '+str(path))
    return json.loads(raw)


class History:
    def __init__(self):
        self.entries = {}
        self.sources = {}
        for path in sorted(Path('data').glob('month_*/manifest.json')):
            manifest = json.loads(path.read_text())
            for entry in manifest['partitions']:
                rid = entry['race_id']
                if rid in self.entries: raise ValueError('Duplicate partition: '+rid)
                self.entries[rid] = entry
        for path in sorted(Path('evidence').glob('month_*/manifest.json')):
            self.sources[path.parent.name[6:]] = (path.parent, json.loads(path.read_text()))

    def source(self, day, key):
        folder, manifest = self.sources.get(day[:7], (None, {}))
        meta = manifest.get(key, {})
        if meta.get('status') != 200: return None
        return read_gzip(folder / meta['file'], meta['sha256'])

    def day(self, day):
        records, problems = {}, []
        overlay = OVERLAYS / (day+'.json')
        recent = Path('data/recent_history') / (day+'.json')
        compressed = overlay.with_suffix('.json.gz')
        value = (json.loads(gzip.decompress(compressed.read_bytes())) if compressed.exists()
                 else json.loads(overlay.read_text()) if overlay.exists() else None)
        if value:
            if value['date'] != day: raise ValueError('Overlay date mismatch')
            programme = value['programme']
            records = {r['race_id']:r for r in value['records']}
            if len(records) != len(value['records']): raise ValueError('Duplicate overlay race')
            cancellations = value.get('cancellations', {})
        elif recent.exists():
            value = json.loads(recent.read_text())
            raw = json.dumps(value['records'], sort_keys=True, ensure_ascii=False).encode()
            if hashlib.sha256(raw).hexdigest() != value['records_sha256']:
                raise ValueError('Recent history checksum mismatch')
            if value['date'] != day: raise ValueError('Recent history date mismatch')
            records = {r['race_id']:r for r in value['records']}
            if len(records) != len(value['records']): raise ValueError('Duplicate recent race')
            store = EvidenceStore(Path(value['evidence_root'])/'programme', max_requests=0)
            programme = store.programme(day)
            cancellations = {}
            for item in value.get('exclusions', []):
                if item.get('reason') == 'cancelled':
                    rid = item['race_id']; rn, cn = rid.split('_R')[1].split('C')
                    s = EvidenceStore(Path(value['evidence_root'])/rid, max_requests=0)
                    cancellations[rid] = s.race(day, int(rn), int(cn), '')
        else:
            programme = self.source(day, day+'_programme')
            cancellations = {}
        body = programme.get('programme', programme) if isinstance(programme, dict) else None
        if not isinstance(body, dict) or not isinstance(body.get('reunions'), list):
            return dict(date=day, programme=None, records=[], cancellations={}, pending=[],
                        issues=['programme_unavailable'], status='PARTIEL', expected=None)
        stamp = body.get('date')
        if stamp is not None and datetime.fromtimestamp(stamp/1000, ZoneInfo('Europe/Paris')).date().isoformat() != day:
            raise ValueError('Programme date mismatch: '+day)
        candidates = list(races(programme))
        ids = [f"{day}_R{r['numOfficiel']}C{c['numOrdre']}" for r,c in candidates]
        if len(ids) != len(set(ids)): raise ValueError('Duplicate programme race')
        if set(records)-set(ids): raise ValueError('Unexpected stored race')
        verified, pending, confirmed_cancel = [], [], {}
        for rid, (meeting, course) in zip(ids, candidates):
            record = records.get(rid)
            try:
                if record is None and rid in self.entries:
                    entry = self.entries[rid]
                    record = read_gzip(entry['file'], entry['sha256'])
                detail = cancellations.get(rid)
                if detail is None and record is None:
                    detail = self.source(day, rid+'_course_detail')
                    participants = self.source(day, rid+'_participants')
                    if isinstance(detail, dict) and isinstance(participants, dict):
                        record = make_record(day, meeting, course, participants, detail)
                if cancelled(detail):
                    confirmed_cancel[rid] = detail
                    continue
                errors = validate(record) if record else ['missing_record']
                if record and (record['race_id'] != rid or record['date'] != day
                               or record['course'] != course or record['country'] != 'FRA'):
                    errors.append('record_programme_mismatch')
                if errors:
                    pending.append(dict(race_id=rid, reasons=errors))
                else: verified.append(record)
            except (ValueError, OSError, KeyError, TypeError) as error:
                pending.append(dict(race_id=rid, reasons=[str(error)]))
        return dict(date=day, programme=programme, records=verified, cancellations=confirmed_cancel,
                    pending=pending, issues=problems, expected=len(ids),
                    status='PARTIEL' if pending or problems else 'OK')


def make_record(day, meeting, course, participants, detail):
    rn, cn = meeting['numOfficiel'], course['numOrdre']
    return dict(date=day, race_id=f'{day}_R{rn}C{cn}', reunion=rn, course_number=cn,
                venue=meeting['hippodrome']['libelleCourt'], country='FRA', start_type=start_type(course),
                distance_m=course['distance'], scheduled_start_ms=course['heureDepart'],
                course=course, participants=participants.get('participants', []), detail=detail)


def audit(today):
    history = History()
    output = []
    for day in days_until(today):
        try: output.append(history.day(day))
        except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
            output.append(dict(date=day, status='PARTIEL', programme=None, records=[],
                               cancellations={}, pending=[], expected=None, issues=[str(error)]))
    return output


class Collector:
    def __init__(self, budget=800):
        self.remaining = budget
        self.requests = 0
        self.recovered = 0
        self.stopped = False
        self.batch = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')

    def fetch(self, day, rn=None, cn=None, endpoint=''):
        if self.remaining <= 0 or self.stopped: raise RuntimeError('Request budget exhausted or source unavailable')
        store = EvidenceStore(Path('evidence/history_updates')/self.batch/day, max_requests=self.remaining, delay=1)
        try:
            result = store.programme(day) if rn is None else store.race(day, rn, cn, endpoint)
        finally:
            self.remaining -= store.requests
            self.requests += store.requests
        if result is None:
            # Stop the batch after transport, rate-limit or access failures; next scheduled run retries.
            self.stopped = True
            raise RuntimeError('Source unavailable; batch stopped, evidence preserved')
        return result

    def repair(self, state):
        day = state['date']
        if state['status'] == 'OK': return state
        try:
            programme = state['programme'] or self.fetch(day)
            body = programme.get('programme', programme) if isinstance(programme, dict) else None
            if not isinstance(body, dict) or not isinstance(body.get('reunions'), list):
                raise ValueError('Invalid programme')
            records = {r['race_id']:r for r in state['records']}
            cancellations = dict(state['cancellations'])
            save_day(day, dict(date=day, programme=programme,
                 records=list(records.values()), cancellations=cancellations))
            for meeting, course in races(programme):
                rn, cn = meeting['numOfficiel'], course['numOrdre']
                rid = f'{day}_R{rn}C{cn}'
                if rid in records or rid in cancellations: continue
                detail = self.fetch(day, rn, cn)
                if cancelled(detail): cancellations[rid] = detail
                else:
                    participants = self.fetch(day, rn, cn, 'participants')
                    record = make_record(day, meeting, course, participants, detail)
                    if not validate(record):
                        records[rid] = record
                        self.recovered += 1
                # Atomic checkpoint after each race, including incomplete source responses.
                save_day(day, dict(date=day, programme=programme,
                     records=list(records.values()), cancellations=cancellations))
            save_day(day, dict(date=day, programme=programme,
                 records=list(records.values()), cancellations=cancellations))
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as error:
            state['issues'].append(str(error))
        return state


def save_day(day, value):
    path = OVERLAYS/(day+'.json.gz')
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(gzip.compress(raw, mtime=0))
    temporary.replace(path)


def summarize(states, today, collector=None):
    missing = [s for s in states if s['status'] != 'OK']
    complete = [s['date'] for s in states if s['status'] == 'OK']
    collected = [s['date'] for s in states if s['records']]
    contiguous = None
    for state in states:
        if state['status'] != 'OK': break
        contiguous = state['date']
    return dict(status='PARTIEL' if missing else 'OK', checked_at=datetime.now(timezone.utc).isoformat(),
        required_through=(today-timedelta(days=1)).isoformat(), last_complete_day=max(complete, default=None),
        last_collected_day=max(collected, default=None), complete_continuously_through=contiguous,
        verified_races=sum(len(s['records']) for s in states),
        recovered_races=collector.recovered if collector else 0, requests=collector.requests if collector else 0,
        missing_days=len(missing), unknown_programme_days=sum(s['expected'] is None for s in states),
        missing_races=sum(len(s['pending']) for s in states),
        cancelled_races=sum(len(s['cancellations']) for s in states),
        scope='PMU-listed French harness races, 2022-01-01 through yesterday',
        days=[{k:v for k,v in s.items() if k not in ('programme','records','cancellations')} |
              dict(verified_races=len(s['records']),cancelled_races=len(s['cancellations'])) for s in states])
