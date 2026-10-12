"""46-race bounded pilot. Reuse audit raws, fetch only missing history responses."""
import gzip
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from turf_lab.evidence import EvidenceStore, dump
from turf_lab.pilot import dated_history, features, norm_name


def main():
    races=json.loads(Path('reports/audit_phase_a.json').read_text())['races']
    assert len(races)==46
    store=EvidenceStore('evidence/pilot_v1',max_requests=48,delay=0.5)
    old=EvidenceStore('evidence/temporal_audit_2026-10-12',max_requests=0)
    manifest={'version':'pilot-v1','historical_snapshot_status':'retrospective; original publication time unproven','partitions':[],'errors':[]}
    for race in sorted(races,key=lambda r:r['race_id']):
        key=race['race_id']+'_performances_pretty';day=race['date']
        ds=datetime.fromisoformat(day).strftime('%d%m%Y')
        url=f"https://offline.turfinfo.api.pmu.fr/rest/client/7/programme/{ds}/R{race['reunion']}/C{race['course_number']}/performances-detaillees/pretty"
        source=old if key in old.manifest else store
        raw=source.get(url,key)
        # One recorded retry for transport/empty-body errors; never retry access denial.
        if raw is None and source.manifest[key]['status']=='error':
            key=key+'_retry1'
            source=store
            raw=source.get(url,key)
        try:
            if not isinstance(raw,dict) or not raw.get('participants'): raise ValueError('History endpoint unavailable')
            by_number={h['numPmu']:h for h in raw['participants']}
            if len(by_number)!=len(raw['participants']): raise ValueError('Duplicate history runner')
            normalized={k:race[k] for k in ['date','race_id','venue','country','start_type','distance_m','scheduled_start_ms']}
            normalized.update(category=race['course'].get('categorieParticularite','UNKNOWN'),runners=[],feature_cutoff=day,history_source=source.manifest[key])
            # Preserve known engagement text as metadata, not as a model variable.
            normalized['conditions']=race['course'].get('conditions')
            category_match=re.search(r'Course\s+([A-G])\b',normalized['conditions'] or '')
            normalized['category']=category_match.group(1) if category_match else race['course'].get('categorieParticularite','UNKNOWN')
            ids=set();numbers=set()
            for p in race['participants']:
                num=p['numPmu'];identity=p.get('idCheval') or '-'.join(p[k] for k in ('nom','nomMere','nomPere'))
                if num in numbers or identity in ids: raise ValueError('Duplicate target runner')
                numbers.add(num);ids.add(identity)
                non_runner=p.get('statut')=='NON_PARTANT'
                h=by_number.get(num)
                if h is None and not non_runner: raise ValueError('Missing history horse identity')
                if h is not None and norm_name(h['nomCheval'])!=norm_name(p['nom']): raise ValueError('Runner identity mismatch')
                history=dated_history(h,day) if h else []
                normalized['runners'].append({'number':num,'horse_id':identity,'name':p['nom'],'non_runner':non_runner,
                    'features':features(history,day),'history':history,'won':int(p.get('ordreArrivee')==1),'rank':p.get('ordreArrivee'),'incident':p.get('incident')})
            if sum(r['won'] for r in normalized['runners'] if not r['non_runner'])!=1: raise ValueError('Single active winner required')
            payload=(json.dumps(normalized,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n').encode()
            dest=Path('data/pilot_v1')/day[:4]/day[5:7]/(race['race_id']+'.jsonl.gz')
            dest.parent.mkdir(parents=True,exist_ok=True)
            tmp=dest.with_suffix('.tmp');tmp.write_bytes(gzip.compress(payload,mtime=0));tmp.replace(dest)
            manifest['partitions'].append({'file':str(dest),'sha256':hashlib.sha256(payload).hexdigest(),'race_id':race['race_id'],'runners':len(normalized['runners'])})
        except (ValueError,KeyError,TypeError) as error:
            manifest['errors'].append({'race_id':race['race_id'],'error':str(error)})
        dump('data/pilot_v1/manifest.json',manifest)
    manifest['status']='COMPLETE' if len(manifest['partitions'])==46 and not manifest['errors'] else 'PARTIAL_WITH_QUARANTINE'
    manifest['candidate_races']=46
    manifest['quarantine_policy']='Whole race excluded on unavailable history or identity/date ambiguity; no imputation of results.'
    manifest['eligible_status']='COMPLETE' if len(manifest['partitions'])+len(manifest['errors'])==46 else 'INCOMPLETE'
    dump('data/pilot_v1/manifest.json',manifest)
    print(json.dumps({'status':manifest['status'],'races':len(manifest['partitions']),'errors':manifest['errors']}))
    if manifest['eligible_status']!='COMPLETE': raise SystemExit(1)

if __name__=='__main__': main()
