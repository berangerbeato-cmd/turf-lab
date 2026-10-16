"""Use explicit workflow inputs, or the versioned request for a push trigger."""
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    values=[os.environ.get(k,'') for k in ('RACE_DATE','RACE_MEETING','RACE_NUMBER')]
    if any(values) and not all(values):raise ValueError('All three explicit inputs required')
    if not any(values):
        data=json.loads(Path('config/prediction_request.json').read_text())
        values=[str(data[k]) for k in ('date','reunion','course')]
    from scripts.predict_operational import run
    path=run(values[0],int(values[1]),int(values[2]))
    request=json.loads(Path('config/prediction_request.json').read_text())
    if request.get('quotes') and not any(os.environ.get(k) for k in ('RACE_DATE','RACE_MEETING','RACE_NUMBER')):
        from turf_lab.operational_quotes import compare
        from turf_lab.evidence import dump
        result=compare(json.loads(path.read_text()),request['quotes'])
        dump(path.parent/'quotes.json',request['quotes'])
        dump(path.parent/'comparison.json',result)
        dump('reports/operational/latest_comparison.json',result)

if __name__=='__main__':main()
