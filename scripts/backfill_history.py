"""Bounded, resumable collection into new months only; no model writes."""
import argparse
import json
from pathlib import Path
from scripts.collect_month import collect, month_days
from turf_lab.evidence import EvidenceStore, dump


class StopOnUnavailable(EvidenceStore):
    def get(self, url, key):
        value = super().get(url, key)
        meta = self.manifest[key]
        if meta.get('status') != 200 or value is None:
            raise RuntimeError('Source unavailable; stop this month without retries: '+key+' '+str(meta.get('status')))
        return value


def main():
    p=argparse.ArgumentParser();p.add_argument('--month',required=True)
    p.add_argument('--max-requests',type=int,default=3000)
    a=p.parse_args();month_days(a.month)
    if not '2022-01' <= a.month <= '2026-09':
        raise ValueError('Only closed months within authorized 2022–2026 window')
    if not 1 <= a.max_requests <= 3000:
        raise ValueError('Request budget must be 1..3000')
    out=Path('data/month_'+a.month);ev=Path('evidence/month_'+a.month)
    manifest=out/'manifest.json'
    if manifest.exists():
        previous=json.loads(manifest.read_text())
        # Never rebuild an existing completed monthly dataset.
        if previous.get('status') in ('COLLECTED','COLLECTED_WITH_GAPS'):
            print('Existing completed month preserved: '+a.month)
            return
        # Preserve every previous manifest version before resuming.
        import hashlib
        raw=manifest.read_bytes();snap=out/'checkpoints'/(hashlib.sha256(raw).hexdigest()+'.json')
        snap.parent.mkdir(parents=True,exist_ok=True)
        if not snap.exists():snap.write_bytes(raw)
    store=StopOnUnavailable(ev,max_requests=a.max_requests,delay=1.0)
    try:
        report=collect(a.month,store,out)
        dump('reports/full_history/collection_'+a.month+'.json',dict(
            month=a.month,status=report['status'],requests=store.requests,
            retained=len(report['partitions']),candidates=report['candidate_races']))
        if report['status']=='PAUSED_REQUEST_BUDGET':raise SystemExit(2)
    except Exception as error:
        dump('reports/full_history/collection_'+a.month+'.json',dict(
            month=a.month,status='BLOCKED',error=str(error),requests=store.requests))
        raise

if __name__=='__main__':main()
