"""Verified PMU calendar inventory; coverage is never inferred from sample counts."""
import argparse
import calendar
import csv
import gzip
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from turf_lab.coverage import cancelled_evidence, coverage_counts
from turf_lab.evidence import races, dump
from turf_lab.quality import assess


def inventory(root, start=2022, end=2026, through='2026-10', as_of='2026-10-14'):
    root = Path(root)
    cutoff = date.fromisoformat(as_of)
    result = []
    for year in range(start, end + 1):
        for month in range(1, 13):
            key = f'{year:04d}-{month:02d}'
            if key > through:
                continue
            expected = {f'{key}-{d:02d}' for d in range(1, calendar.monthrange(year, month)[1]+1)}
            row = dict(month=key, status='MISSING', days=0, expected_days=len(expected),
                       candidate_races=0, retained_races=0, quarantined_races=0,
                       cancelled_races=0, participants=0, coverage_fraction=None,
                       first_date=None, last_date=None, venues={}, issues=[], warnings=0,
                       manifest_sha256=None, source_timestamps=[], source_verified=False)
            path = root / f'month_{key}' / 'manifest.json'
            if not path.exists():
                result.append(row)
                continue
            raw = path.read_bytes()
            row['manifest_sha256'] = hashlib.sha256(raw).hexdigest()
            data = json.loads(raw)
            if data.get('month') != key:
                raise ValueError(f'Month mismatch: {path}')
            days = data.get('days', [])
            dates = [d.get('date') for d in days]
            if len(dates) != len(set(dates)):
                raise ValueError(f'Duplicate dates: {path}')
            if not set(dates).issubset(expected):
                raise ValueError(f'Dates outside month: {path}')
            parts = data.get('partitions', [])
            row.update(days=len(days), candidate_races=sum(d.get('candidate_races',0) for d in days),
                       retained_races=len(parts), quarantined_races=len(data.get('quarantine', [])),
                       first_date=min(dates) if dates else None, last_date=max(dates) if dates else None)
            evidence = root.parent / 'evidence'
            try:
                if data.get('candidate_races') != row['candidate_races']:
                    raise ValueError('Candidate total mismatch')
                cancels = cancelled_evidence(key, data.get('quarantine', []), evidence)
                counts = coverage_counts(data, cancels)
                row.update(cancelled_races=counts['cancelled'], coverage_fraction=counts['fraction'])
                evroot = evidence / f'month_{key}'
                ev = json.loads((evroot / 'manifest.json').read_text())
                verified = {}
                def read_source(name):
                    meta = ev[name]
                    if meta['status'] != 200:
                        raise ValueError('Unavailable source: '+name)
                    source = gzip.decompress((evroot / meta['file']).read_bytes())
                    if hashlib.sha256(source).hexdigest() != meta['sha256']:
                        raise ValueError('Source SHA256 mismatch: '+name)
                    row['source_timestamps'].append(meta['fetched_at_utc'])
                    return json.loads(source)
                for day in days:
                    if day['status'] != 'OK':
                        raise ValueError('Programme unavailable: '+day['date'])
                    programme = read_source(day['date']+'_programme')
                    candidates = {f"{day['date']}_R{r['numOfficiel']}C{c['numOrdre']}":(r,c)
                                  for r,c in races(programme)}
                    if len(candidates) != day['candidate_races']:
                        raise ValueError('Programme count mismatch: '+day['date'])
                    verified.update(candidates)
                if set(verified) != {p['race_id'] for p in parts} | {q['race_id'] for q in data['quarantine']}:
                    raise ValueError('Programme race IDs disagree with inventory')
                venues = Counter()
                retained_dates = []
                for entry in parts:
                    p = Path(entry['file'])
                    if not p.is_absolute():
                        p = root.parent / p
                    payload = gzip.decompress(p.read_bytes())
                    if hashlib.sha256(payload).hexdigest() != entry['sha256']:
                        raise ValueError('Partition SHA256 mismatch: '+entry['race_id'])
                    record = json.loads(payload)
                    rid = entry['race_id']
                    if record['race_id'] != rid or record['date'] not in expected or not rid.startswith(record['date']+'_'):
                        raise ValueError('Partition identity mismatch: '+rid)
                    if record['country'] != 'FRA' or record['course']['discipline'] not in ('ATTELE','TROT_ATTELE'):
                        raise ValueError('Ineligible race: '+rid)
                    source_participants = read_source(rid+'_participants')
                    source_detail = read_source(rid+'_course_detail')
                    if record['participants'] != source_participants['participants'] or record['detail'] != source_detail or record['course'] != verified[rid][1]:
                        raise ValueError('Partition differs from raw evidence: '+rid)
                    diag = assess([record])
                    if diag['issues'] or diag['counts']['single_winner_races'] != 1:
                        raise ValueError('Result quality failure: '+rid)
                    row['participants'] += len(record['participants'])
                    row['warnings'] += len(diag['warnings'])
                    venues[record['venue']] += 1
                    retained_dates.append(record['date'])
                row['venues'] = dict(venues)
                if row['participants'] != data['participants']:
                    raise ValueError('Participant total mismatch')
                row['source_verified'] = True
            except (ValueError, KeyError, OSError, TypeError) as error:
                row['issues'].append(str(error))
            stamps = row['source_timestamps']
            row['source_timestamps'] = [min(stamps), max(stamps)] if stamps else []
            complete = (set(dates) == expected and all(d['status']=='OK' for d in days)
                        and row['coverage_fraction'] is not None and row['coverage_fraction'] >= .98
                        and row['source_verified'] and not row['issues'])
            row['status'] = 'COMPLETE' if complete else 'PARTIAL'
            if key >= cutoff.strftime('%Y-%m'):
                row['status'] = 'CURRENT_PARTIAL' if key == cutoff.strftime('%Y-%m') else 'FUTURE'
            result.append(row)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=Path('data'))
    p.add_argument('--output',type=Path,default=Path('reports/history_inventory'))
    p.add_argument('--through',default='2026-10');p.add_argument('--as-of',default='2026-10-14')
    a=p.parse_args();rows=inventory(a.data,through=a.through,as_of=a.as_of)
    dump(a.output.with_suffix('.json'),rows)
    with a.output.with_suffix('.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    print(json.dumps(dict(months=len(rows),statuses=dict(Counter(r['status'] for r in rows)),
                         retained=sum(r['retained_races'] for r in rows),issues={r['month']:r['issues'] for r in rows if r['issues']})))

if __name__ == '__main__':main()
