"""Verify recovered archives and reconcile counts, without extracting ZIP paths."""
import hashlib
import json
import zipfile
from pathlib import Path
from turf_lab.evidence import dump


def main():
    manifests=json.loads(Path('data/reference/manifest.json').read_text())
    for m in manifests:
        assert hashlib.sha256(Path(m['file']).read_bytes()).hexdigest()==m['sha256']
    with zipfile.ZipFile('data/reference/pmu-deep-audit.zip') as z:
        report=json.loads(z.read('2026-10-05/audit_report.json'))
        participants=[json.loads(z.read(n))['participants'] for n in z.namelist() if n.endswith('_participants.json')]
        counts={'races':len(participants),'runners':sum(map(len,participants)),'requests':sum(n.endswith(('_participants.json','_course_detail.json','_rapports-definitifs.json')) for n in z.namelist())}
        assert counts==report['counts']
    with zipfile.ZipFile('data/reference/pmu-probe.zip') as z:
        summary=json.loads(z.read('raw/summary.json'))
        actual=sum(n.startswith('raw/') and n.endswith('_participants.json') for n in z.namelist())
        assert actual==summary['races_saved']==149
    out={'archive_digests':'PASS','deep_audit_recount':counts,'probe_recount':actual,'scope_correction':'149 includes 50 foreign races; French scope is 99 (phase A programme recount).'}
    dump('reports/reference_reconciliation.json',out)
    print(json.dumps(out))

if __name__=='__main__': main()
