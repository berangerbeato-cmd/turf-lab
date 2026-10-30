"""Reconcile the fixed case, excluding target-day outcomes; never rewrite it."""
import json
from pathlib import Path
from turf_lab.individual_history_check import check_all
from turf_lab.evidence import dump

def main():
    path=Path('predictions_operational/2026-10-29/2026-10-29_R4C8_20261029T183552548416Z/prediction.json')
    p=json.loads(path.read_text())
    r=check_all(p['target_snapshot'],p['models'],'evidence/individual_repair_20261029')
    dump('reports/market_repair_v1/individual_history_case.json',r)
    print([(x['number'],x['status'],len(x.get('missing_recent_starts',[]))) for x in r['runners']])
if __name__=='__main__':main()
