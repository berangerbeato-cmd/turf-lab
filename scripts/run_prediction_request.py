"""Run explicit inputs or the versioned ChatGPT request; never silently use V1."""
import json,os
from datetime import datetime,timezone
from pathlib import Path
from turf_lab.evidence import dump


def main():
    values=[os.environ.get(k,'') for k in ('RACE_DATE','RACE_MEETING','RACE_NUMBER')]
    if any(values) and not all(values):raise ValueError('All three explicit inputs required')
    explicit=any(values)
    data=json.loads(Path('config/prediction_request.json').read_text()) if not explicit else {}
    if not explicit:values=[str(data[k]) for k in ('date','reunion','course')]
    state={'request_id':data.get('request_id',os.getenv('GITHUB_RUN_ID','explicit-local')),
           'race_id':f'{values[0]}_R{int(values[1])}C{int(values[2])}',
           'started_at':datetime.now(timezone.utc).isoformat(),'status':'RUNNING',
           'github_run_id':os.getenv('GITHUB_RUN_ID')}
    dump('reports/operational/request_status.json',state)
    try:
        from scripts.predict_operational import run
        path=run(values[0],int(values[1]),int(values[2]))
        if data.get('quotes'):
            from turf_lab.operational_quotes import compare
            result=compare(json.loads(path.read_text()),data['quotes'])
            dump(path.parent/'quotes.json',data['quotes'])
            dump(path.parent/'comparison.json',result)
            dump('reports/operational/latest_comparison.json',dict(result,request_id=state['request_id']))
        state.update(status='SUCCESS',prediction=str(path),quotes_compared=bool(data.get('quotes')))
        latest=json.loads(Path('reports/operational/latest.json').read_text())
        dump('reports/operational/latest.json',dict(latest,request_id=state['request_id']))
    except Exception as error:
        state.update(status='FAILED',error=str(error));raise
    finally:
        state['completed_at']=datetime.now(timezone.utc).isoformat()
        dump('reports/operational/request_status.json',state)

if __name__=='__main__':main()
