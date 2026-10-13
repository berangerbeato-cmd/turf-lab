"""Bounded history refresh only. This does not activate prospective predictions."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from scripts.backtest_connections import PROTOCOL, verify_frozen
from scripts.backtest_extension import load_sources
from scripts.collect_month import collect, git_checkpoint
from turf_lab.evidence import EvidenceStore, dump


def authorized_month(month, protocol, today):
    if month not in protocol['collection_months'] or month >= today[:7]:
        raise ValueError('Only authorized completed months can be collected')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', required=True)
    args = parser.parse_args()
    p = json.loads(Path('config/connections_v5_shadow_preparation.json').read_text())
    authorized_month(args.month, p, datetime.now(ZoneInfo('Europe/Paris')).date().isoformat())
    verify_frozen(json.loads(PROTOCOL.read_text()))
    root = Path('evidence/month_' + args.month)
    output = Path('data/month_' + args.month)
    store = EvidenceStore(root, max_requests=p['max_requests_per_month'], delay=0.5)
    report = collect(args.month, store, output, lambda: git_checkpoint(root, output))
    dump('reports/month_' + args.month + '.json', report)
    if report['status'] == 'PAUSED_REQUEST_BUDGET':
        raise SystemExit(2)
    _, coverage = load_sources({'months': [args.month],
        'minimum_retained_fraction_per_month': p['minimum_retained_fraction_per_month']})
    dump('reports/connections_v5_warmup_' + args.month + '.json', {
        'status': 'HISTORY_COLLECTED_NOT_PROSPECTIVE', 'coverage': coverage,
        'new_requests': store.requests, 'next_required': p['next_required'], 'refitted': False})


if __name__ == '__main__':
    main()
