"""Run explicit inputs or the versioned ChatGPT request; never silently use V1."""
import json,os
from datetime import datetime,timezone
from pathlib import Path
from turf_lab.evidence import dump


def record_history_repair_shadow(prediction_path, state):
    """Best-effort experimental forecast; never block or replace frozen V3."""
    try:
        from turf_lab.history_repair_shadow import replay
        report = replay(prediction_path)
        completed = datetime.now(timezone.utc)
        start = datetime.fromisoformat(report['scheduled_start'])
        if completed >= start:
            state['history_repair_shadow_status'] = 'LATE_NOT_ARCHIVED'
            state['history_repair_shadow_reason'] = 'Replay ended after start; not a prospective observation'
            return
        report['status'] = 'PRESTART_HISTORY_REPAIR_SHADOW'
        report['shadow_calculated_at'] = completed.isoformat()
        report['source_request_id'] = state['request_id']
        report['is_independent_prospective_validation'] = False
        report['research_only'] = True
        report['recommendations_allowed'] = False
        dump(prediction_path.parent / 'history_repair_shadow_v1_1.json', report)
        state['history_repair_shadow_status'] = 'PRESTART_RECORDED'
    except Exception as error:
        # The production frozen models and odds comparison remain usable.
        state['history_repair_shadow_status'] = 'UNAVAILABLE'
        state['history_repair_shadow_reason'] = type(error).__name__ + ': ' + str(error)


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
        record_history_repair_shadow(path, state)
        if data.get('quotes'):
            from turf_lab.operational_quotes import compare
            result=compare(json.loads(path.read_text()),data['quotes'])
            dump(path.parent/'quotes.json',data['quotes'])
            dump(path.parent/'comparison.json',result)
            dump('reports/operational/latest_comparison.json',dict(result,request_id=state['request_id']))
            # Independently record the daily paper-ticket rule, even when an early
            # odds snapshot is not eligible for the prospective SG J-15 study.
            try:
                from turf_lab.daily_ticket import make_ticket,load_protocol
                ticket=make_ticket(json.loads(path.read_text()),data['quotes'],result,load_protocol())
                dump(path.parent/'daily_ticket.json',ticket)
                dump('reports/operational/latest_ticket.json',dict(ticket,request_id=state['request_id']))
                state['daily_ticket_status']='PAPER_RECORDED'
            except ValueError as error:
                state['daily_ticket_status']='UNAVAILABLE'
                state['daily_ticket_reason']=str(error)
            from turf_lab.sg_strategy_comparison import archive
            try:
                archive(json.loads(path.read_text()),data['quotes'])
                state['sg_comparison_status']='ARCHIVED'
            except ValueError as error:
                state['sg_comparison_status']='INELIGIBLE'
                state['sg_comparison_reason']=str(error)
        state.update(status='SUCCESS',prediction=str(path),quotes_compared=bool(data.get('quotes')))
        latest=json.loads(Path('reports/operational/latest.json').read_text())
        dump('reports/operational/latest.json',dict(latest,request_id=state['request_id']))
    except Exception as error:
        state.update(status='FAILED',error=str(error));raise
    finally:
        state['completed_at']=datetime.now(timezone.utc).isoformat()
        dump('reports/operational/request_status.json',state)

if __name__=='__main__':main()
