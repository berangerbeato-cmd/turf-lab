"""One grounded check of the official detailed historical opposition endpoint."""
import gzip
import json
from pathlib import Path
from urllib.parse import quote, urlencode
from turf_lab.evidence import EvidenceStore, dump
from turf_lab.history import before_target


def main():
    root=Path('evidence/horse_audit_2026-10-12')
    manifest=json.loads((root/'manifest.json').read_text())
    history=json.loads(gzip.decompress((root/manifest['history_R1C1_8']['file']).read_bytes()))
    report=json.loads(Path('reports/five_horse_histories.json').read_text())
    horse=next(h for h in report['horses'] if h['name']=='LORD ON WAY')
    runs,_,_=before_target(history,'2026-10-05')
    run=runs[0]
    params={'date':run['raceDate'],'racecourseCode':run['racecourseCode'],'raceNumber':run['raceNumber'],'language':'fr'}
    url='https://offline.turfinfo.api.pmu.fr/rest/client/7/program/'+quote(horse['horse_id'],safe='')+'/performance-details?'+urlencode(params)
    store=EvidenceStore('evidence/opposition_audit_2026-10-12',max_requests=1)
    data=store.get(url,'lord_on_way_2026-09-21_details')
    summary={'horse_id':horse['horse_id'],'parameters':params,'available':data is not None}
    if data:
        rr=data.get('runner',{}).get('racesRun',[])
        summary['runs']=[{'race_date':r.get('raceDate'),'field_size':r.get('runnersCount'),
                         'opponents_returned':len(r.get('raceRunParticipants',[])),
                         'participant_fields':sorted({k for p in r.get('raceRunParticipants',[]) for k in p})} for r in rr]
    dump('reports/opposition_audit.json',summary)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
