"""Collect one authorized V5 month using immutable cached responses."""
import argparse
import json
from pathlib import Path
from scripts.collect_month import collect, git_checkpoint
from turf_lab.evidence import EvidenceStore, dump


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--month',required=True)
    args=parser.parse_args()
    p=json.loads(Path('config/connections_v5_protocol.json').read_text())
    if args.month not in p['collection_development']+p['collection_test']:
        raise ValueError('Month outside V5 protocol')
    if args.month in p['collection_test']:
        from scripts.backtest_connections import verify_frozen
        verify_frozen(p)
    root=Path('evidence/month_'+args.month);out=Path('data/month_'+args.month)
    store=EvidenceStore(root,max_requests=p['max_requests_per_month'],delay=0.5)
    report=collect(args.month,store,out,lambda:git_checkpoint(root,out))
    dump('reports/month_'+args.month+'.json',report)
    print(json.dumps({'month':args.month,'status':report['status'],'races':len(report['partitions']),'new_requests':store.requests}))
    if report['status']=='PAUSED_REQUEST_BUDGET':raise SystemExit(2)

if __name__=='__main__':main()
