"""Capture a tiny prospective sample to contrast with late-fetched archives."""
from datetime import datetime, timezone

from turf_lab.evidence import EvidenceStore, dump, races


def main():
    store = EvidenceStore('evidence/prospective_audit_2026-10-12', max_requests=5)
    day = '2026-10-13'
    programme = store.programme(day)
    selected, venues = [], set()
    for r, c in races(programme):
        venue = r.get('hippodrome',{}).get('code')
        if venue not in venues:
            selected.append((r,c)); venues.add(venue)
        if len(selected) == 2:
            break
    report = {'target_date':day, 'races':[]}
    for r,c in selected:
        rn,cn=r['numOfficiel'],c['numOrdre']
        data=store.race(day,rn,cn,'participants')
        if not data:
            continue
        meta=store.manifest[f'{day}_R{rn}C{cn}_participants']
        observed=datetime.fromisoformat(meta['fetched_at_utc']).timestamp()*1000
        start=c.get('heureDepart')
        runners=data.get('participants',[])
        post_fields=('ordreArrivee','tempsObtenu','reductionKilometrique','commentaireApresCourse')
        report['races'].append({'race_id':f'{day}_R{rn}C{cn}', 'venue':r['hippodrome']['libelleCourt'],
           'retrieved_before_scheduled_start':bool(start and observed<start),
           'fetched_at_utc':meta['fetched_at_utc'],'scheduled_start_ms':start,
           'definitive_result':c.get('arriveeDefinitive'), 'runners':len(runners),
           'post_field_nonempty_counts':{k:sum(p.get(k) is not None and p.get(k)!='' for p in runners) for k in post_fields},
           'runner_fields':sorted({k for p in runners for k in p}),
           'note':'Prospective evidence only when timestamp is before start and no result is present; no prediction yet.'})
    dump('reports/prospective_audit.json',report)
    print(report)


if __name__=='__main__':main()
