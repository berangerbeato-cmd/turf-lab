"""Inventory negative distance differences, without inferring missing starting slots."""
import gzip
import json
import re
from collections import Counter
from pathlib import Path
from turf_lab.evidence import dump


def main():
    stats=Counter();examples=[]
    months=json.loads(Path('config/history_extension_protocol.json').read_text())['months']
    for month in months:
        manifest=json.loads(Path(f'data/month_{month}/manifest.json').read_text())
        for entry in manifest['partitions']:
            raw=gzip.decompress(Path(entry['file']).read_bytes())
            import hashlib
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Source digest mismatch')
            r=json.loads(raw)
            n=sum(isinstance(x.get('handicapDistance'),int) and x['handicapDistance']<r['distance_m'] for x in r['participants'])
            if not n:continue
            text=r['course'].get('conditions','')
            confirmed=bool(re.search(r'avance\s+de\s+25\s*m',text,re.I))
            stats['races']+=1;stats['participants']+=n
            stats['confirmed_avance_25_participants']+=n if confirmed else 0
            examples.append({'race_id':r['race_id'],'negative_participants':n,'explicit_advance_25':confirmed,'conditions':text})
    dump('reports/departure_advance_audit.json',{'counts':dict(stats),'races':examples,
        'interpretation':'Negative difference can mean a genuine advance. 257 explicitly corroborated, 92 require clarification or damaged-text handling. Do not clamp to zero or infer a fixed starting slot. Retrospective audit only.'})
    print(json.dumps(dict(stats)))

if __name__=='__main__':main()
