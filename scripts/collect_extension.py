"""One predeclared month per cloud job; raw evidence checkpointed weekly."""
import argparse
import json
from pathlib import Path
from scripts.collect_month import collect, git_checkpoint
from turf_lab.evidence import EvidenceStore, dump


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--month',required=True)
    args=parser.parse_args()
    protocol=json.loads(Path('config/history_extension_protocol.json').read_text())
    if args.month not in protocol['months']:
        raise ValueError('Month outside frozen extension protocol')
    root=Path('evidence/month_'+args.month);out=Path('data/month_'+args.month)
    store=EvidenceStore(root, max_requests=protocol['max_requests_per_month_run'],delay=0.5)
    report=collect(args.month,store,out,lambda:git_checkpoint(root,out))
    dump('reports/month_'+args.month+'.json',report)
    print(json.dumps({'month':args.month,'status':report['status'],'races':len(report['partitions']),
        'quarantines':len(report['quarantine']),'new_requests':store.requests}))
    if report['status']=='PAUSED_REQUEST_BUDGET':raise SystemExit(2)

if __name__=='__main__':main()
