"""Inventory actual PMU slot fields; do not infer their semantics from names."""
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from turf_lab.evidence import dump


def main():
    months=json.loads(Path('config/context_v4_protocol.json').read_text())['source_months']
    counts=Counter();examples=[]
    for month in months:
        manifest=json.loads(Path(f'data/month_{month}/manifest.json').read_text())
        for entry in manifest['partitions']:
            raw=gzip.decompress(Path(entry['file']).read_bytes())
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Source digest mismatch')
            r=json.loads(raw)
            for p in r['participants']:
                counts['participants']+=1;value=p.get('placeCorde');prefix=r['start_type']
                counts[prefix+'_participants']+=1
                if isinstance(value,int) and value>0:
                    counts['positive_placeCorde']+=1;counts[prefix+'_positive_placeCorde']+=1
                    counts['placeCorde_equals_numPmu']+=value==p['numPmu']
                    if value!=p['numPmu'] and len(examples)<10:
                        examples.append({'race_id':r['race_id'],'number':p['numPmu'],'placeCorde':value})
    folder=Path('evidence/prospective_audit_2026-10-12')
    metas=json.loads((folder/'manifest.json').read_text());report=json.loads(Path('reports/prospective_audit.json').read_text())
    proofs=[]
    for race in report['races']:
        key=race['race_id']+'_participants';meta=metas[key]
        raw=gzip.decompress((folder/meta['file']).read_bytes())
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Prospective digest mismatch')
        observed=datetime.fromisoformat(meta['fetched_at_utc']).timestamp()*1000
        if observed>=race['scheduled_start_ms']:raise ValueError('Not before departure')
        ps=json.loads(raw)['participants']
        if any(p.get('ordreArrivee') for p in ps):raise ValueError('Result present')
        proofs.append({'race_id':race['race_id'],'sha256':meta['sha256'],'fetched_at_utc':meta['fetched_at_utc'],
            'scheduled_start_ms':race['scheduled_start_ms'],'runners':len(ps),
            'handicapDistance_available':sum(isinstance(p.get('handicapDistance'),int) for p in ps),
            'positive_placeCorde':sum(isinstance(p.get('placeCorde'),int) and p['placeCorde']>0 for p in ps)})
    dump('reports/start_position_audit.json',{'source_months':months,'counts':dict(counts),'different_from_number_examples':examples,
        'before_race_evidence':proofs,'decision':'placeCorde not used as autostart slot until semantic/grid mapping is verified. No slot or line derived from numPmu.',
        'limits':'Two prospective races establish availability in those cases only, not historical publication or slot semantics.'})
    print(json.dumps(dict(counts)))

if __name__=='__main__':main()
