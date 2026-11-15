"""Read immutable paper selections and explicit operator payout evidence."""
import json
from turf_lab.sg_strategy_comparison import ROOT,settle,summarize

def main():
    records=[]
    for path in sorted((ROOT/'selections').glob('*.json')):
        s=json.loads(path.read_text());e=ROOT/'settlements'/path.name
        records.append((s,settle(s,json.loads(e.read_text()) if e.exists() else None)))
    report=summarize(records);ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
